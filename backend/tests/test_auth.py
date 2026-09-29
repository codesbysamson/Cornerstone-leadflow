"""The authentication boundary itself: login, CSRF, throttling, expiry, logout."""

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import CSRF_COOKIE_NAME, SESSION_COOKIE_NAME, settings
from app.models import LoginAttempt, StaffSession, StaffUser
from app.security import (
    digest_login_key,
    digest_session_token,
    hash_password,
    normalise_email,
)

from .conftest import STAFF_PASSWORD, csrf_headers, sign_in

WRONG_PASSWORD = "definitely not the password"


def _attempt(client: TestClient, email: str, password: str):
    """Logs in, doing the CSRF bootstrap the frontend does."""
    client.get("/api/auth/session")
    token = client.cookies.get(CSRF_COOKIE_NAME)
    return client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
        headers={"X-CSRF-Token": token},
    )


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


def test_login_succeeds_with_correct_credentials(
    public_client: TestClient, staff_user: StaffUser
) -> None:
    response = _attempt(public_client, staff_user.email, STAFF_PASSWORD)

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == staff_user.email
    assert body["display_name"] == staff_user.display_name
    # The hash is the one field that must never leave the database.
    assert "password_hash" not in body


def test_login_sets_an_httponly_session_cookie_and_a_readable_csrf_cookie(
    public_client: TestClient, staff_user: StaffUser
) -> None:
    response = _attempt(public_client, staff_user.email, STAFF_PASSWORD)

    cookies = response.headers.get_list("set-cookie")
    session_cookie = next(c for c in cookies if c.startswith(f"{SESSION_COOKIE_NAME}="))
    csrf_cookie = next(c for c in cookies if c.startswith(f"{CSRF_COOKIE_NAME}="))

    # The session token must be unreadable by script, or an XSS would be enough.
    assert "HttpOnly" in session_cookie
    # The CSRF token is deliberately readable: the frontend has to copy it into
    # a header.
    assert "HttpOnly" not in csrf_cookie
    for cookie in (session_cookie, csrf_cookie):
        assert "SameSite=lax" in cookie.replace("SameSite=Lax", "SameSite=lax")
        assert "Path=/" in cookie


def test_session_token_is_never_stored_in_plaintext(
    public_client: TestClient, staff_user: StaffUser, session: Session
) -> None:
    """A stolen database dump must not yield replayable sessions."""
    response = _attempt(public_client, staff_user.email, STAFF_PASSWORD)
    raw_token = public_client.cookies.get(SESSION_COOKIE_NAME)

    stored = session.execute(select(StaffSession)).scalar_one()

    assert raw_token is not None
    assert stored.token_hash == digest_session_token(raw_token)
    assert raw_token not in stored.token_hash
    # 64 hex characters: a SHA-256 digest.
    assert len(stored.token_hash) == 64


def test_login_with_wrong_password_is_rejected(
    public_client: TestClient, staff_user: StaffUser
) -> None:
    response = _attempt(public_client, staff_user.email, WRONG_PASSWORD)

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password"}


def test_login_for_unknown_account_is_indistinguishable(
    public_client: TestClient, staff_user: StaffUser
) -> None:
    """The response must not reveal whether an email has an account.

    Compared field by field, not just by status: a different detail string or a
    differing set of headers would leak the same information.
    """
    wrong_password = _attempt(public_client, staff_user.email, WRONG_PASSWORD)
    no_such_user = _attempt(public_client, "nobody@example.com", WRONG_PASSWORD)

    assert wrong_password.status_code == no_such_user.status_code == 401
    assert wrong_password.json() == no_such_user.json()
    assert set(wrong_password.headers) >= {
        k for k in no_such_user.headers if k.lower() == "www-authenticate"
    }


def test_login_is_case_insensitive_on_email(
    public_client: TestClient, staff_user: StaffUser
) -> None:
    response = _attempt(public_client, staff_user.email.upper(), STAFF_PASSWORD)

    assert response.status_code == 200


def test_disabled_account_cannot_log_in(
    public_client: TestClient, staff_user: StaffUser, session: Session
) -> None:
    staff_user.is_active = False
    session.commit()

    response = _attempt(public_client, staff_user.email, STAFF_PASSWORD)

    # Same generic response: "disabled" must not be distinguishable either.
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password"}


def test_login_rejects_unknown_fields(
    public_client: TestClient, staff_user: StaffUser
) -> None:
    public_client.get("/api/auth/session")
    token = public_client.cookies.get(CSRF_COOKIE_NAME)

    response = public_client.post(
        "/api/auth/login",
        json={
            "email": staff_user.email,
            "password": STAFF_PASSWORD,
            "is_active": True,
        },
        headers={"X-CSRF-Token": token},
    )

    # A mass-assignment attempt must not be silently accepted.
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Login CSRF
# ---------------------------------------------------------------------------


def test_login_requires_the_csrf_header(
    public_client: TestClient, staff_user: StaffUser
) -> None:
    public_client.get("/api/auth/session")

    response = public_client.post(
        "/api/auth/login",
        json={"email": staff_user.email, "password": STAFF_PASSWORD},
    )

    # Without this, an attacker could sign a victim into the attacker's account
    # and have the victim's data land there.
    assert response.status_code == 403


def test_login_rejects_a_mismatched_csrf_token(
    public_client: TestClient, staff_user: StaffUser
) -> None:
    public_client.get("/api/auth/session")

    response = public_client.post(
        "/api/auth/login",
        json={"email": staff_user.email, "password": STAFF_PASSWORD},
        headers={"X-CSRF-Token": "forged-token"},
    )

    assert response.status_code == 403


def test_session_probe_mints_a_csrf_cookie_without_a_session(
    public_client: TestClient,
) -> None:
    response = public_client.get("/api/auth/session")

    assert response.status_code == 200
    body = response.json()
    assert body["authenticated"] is False
    assert body["user"] is None
    # Also returned in the body, so a client on a different host than the API
    # can still obtain it. See tests/test_csrf_bootstrap.py.
    assert body["csrf_token"] == public_client.cookies.get(CSRF_COOKIE_NAME)
    assert public_client.cookies.get(CSRF_COOKIE_NAME) is not None


# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------


def test_probe_reports_the_signed_in_staff_member(
    client: TestClient, staff_user: StaffUser
) -> None:
    response = client.get("/api/auth/session")

    assert response.status_code == 200
    body = response.json()
    assert body["authenticated"] is True
    assert body["user"]["email"] == staff_user.email


def test_me_returns_the_current_staff_member(client: TestClient) -> None:
    response = client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json()["email"] == "staff@example.com"


def test_session_survives_repeated_probes(
    client: TestClient,
) -> None:
    """Re-opening the app must not invalidate the CSRF pairing.

    The probe is the first thing the frontend does on load, so rotating the
    token unconditionally would break the next click a staff member makes.
    """
    for _ in range(3):
        assert client.get("/api/auth/session").status_code == 200

    response = client.post("/api/leads/1/status", json={"status": "CONTACTED"})

    # 404, not 403: the CSRF check passed and the request reached the route.
    assert response.status_code == 404


def test_expired_session_is_rejected(
    public_client: TestClient, staff_user: StaffUser, session: Session
) -> None:
    sign_in(public_client, staff_user.email, STAFF_PASSWORD)

    staff_session = session.query(StaffSession).one()
    staff_session.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    session.commit()

    assert public_client.get("/api/leads").status_code == 401


def test_expired_session_row_is_deleted_on_use(
    public_client: TestClient, staff_user: StaffUser, session: Session
) -> None:
    """Expire by being read, so no background job is needed to collect them."""
    sign_in(public_client, staff_user.email, STAFF_PASSWORD)
    staff_session = session.query(StaffSession).one()
    staff_session.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    session.commit()

    public_client.get("/api/leads")

    assert session.query(StaffSession).count() == 0


def test_session_expiry_is_absolute_not_sliding(
    public_client: TestClient, staff_user: StaffUser, session: Session
) -> None:
    """No activity extends the lifetime: twelve hours from login, full stop.

    A sliding window means a stolen session can be kept alive indefinitely by
    whoever stole it, for as long as they keep poking at it.
    """
    sign_in(public_client, staff_user.email, STAFF_PASSWORD)
    sign_in(public_client, staff_user.email, STAFF_PASSWORD)

    expected = datetime.now(UTC) + timedelta(seconds=settings.session_max_age_seconds)
    for staff_session in session.query(StaffSession).all():
        expires_at = staff_session.expires_at
        if expires_at.tzinfo is None:
            # SQLite stores naive timestamps; PostgreSQL returns aware ones.
            expires_at = expires_at.replace(tzinfo=UTC)
        assert abs((expires_at - expected).total_seconds()) < 60


def test_disabling_an_account_invalidates_its_live_sessions(
    client: TestClient, staff_user: StaffUser, session: Session
) -> None:
    assert client.get("/api/leads").status_code == 200

    staff_user.is_active = False
    session.commit()

    assert client.get("/api/leads").status_code == 401


def test_logout_revokes_the_session(
    client: TestClient, session: Session
) -> None:
    assert client.get("/api/leads").status_code == 200

    response = client.post("/api/auth/logout", headers=csrf_headers(client))

    assert response.status_code == 204
    # The row is gone, so the token is worthless rather than merely expiring.
    assert session.query(StaffSession).count() == 0
    assert client.get("/api/leads").status_code == 401


def test_logout_clears_both_cookies(client: TestClient) -> None:
    response = client.post("/api/auth/logout", headers=csrf_headers(client))

    cookies = response.headers.get_list("set-cookie")
    assert any(
        c.startswith(f"{SESSION_COOKIE_NAME}=") and 'Max-Age=0' in c.replace("max-age=0", "Max-Age=0")
        for c in cookies
    )
    assert any(
        c.startswith(f"{CSRF_COOKIE_NAME}=") and 'Max-Age=0' in c.replace("max-age=0", "Max-Age=0")
        for c in cookies
    )


def test_logout_requires_csrf(
    public_client: TestClient, staff_user: StaffUser, session: Session
) -> None:
    """Otherwise an attacker could sign staff out at will.

    Driven through the raw client: ``client`` injects the CSRF header on every
    write, the way the frontend does, so it could not express this request.
    """
    sign_in(public_client, staff_user.email, STAFF_PASSWORD)

    response = public_client.post("/api/auth/logout")

    assert response.status_code == 403
    assert session.query(StaffSession).count() == 1


# ---------------------------------------------------------------------------
# Throttling
# ---------------------------------------------------------------------------


def test_repeated_failures_are_throttled_then_rejected_generically(
    public_client: TestClient, staff_user: StaffUser
) -> None:
    limit = settings.login_max_failures
    for _ in range(limit):
        assert _attempt(public_client, staff_user.email, WRONG_PASSWORD).status_code == 401

    # The account is now locked out, and the correct password is refused too.
    locked_out = _attempt(public_client, staff_user.email, STAFF_PASSWORD)

    assert locked_out.status_code == 401
    assert locked_out.json() == {"detail": "Invalid email or password"}


def test_successful_login_clears_the_failure_count(
    public_client: TestClient, staff_user: StaffUser, session: Session
) -> None:
    """A colleague who fumbled twice must not still be locked out afterwards."""
    for _ in range(settings.login_max_failures - 1):
        _attempt(public_client, staff_user.email, WRONG_PASSWORD)

    assert _attempt(public_client, staff_user.email, STAFF_PASSWORD).status_code == 200

    assert session.query(LoginAttempt).count() == 0


def test_throttle_key_is_a_digest_not_an_email(
    public_client: TestClient, staff_user: StaffUser, session: Session
) -> None:
    """The throttle table must not become a list of probed accounts."""
    _attempt(public_client, staff_user.email, WRONG_PASSWORD)

    stored = session.query(LoginAttempt).one()

    assert staff_user.email not in stored.key
    assert stored.key == digest_login_key(normalise_email(staff_user.email))
    assert session.query(StaffUser).count() == 1


def test_throttling_is_per_account(
    public_client: TestClient, staff_user: StaffUser, session: Session
) -> None:
    """One attacker hammering one account must not lock out everyone."""
    other = StaffUser(
        email="colleague@example.com",
        password_hash=hash_password(STAFF_PASSWORD),
        is_active=True,
    )
    session.add(other)
    session.commit()

    for _ in range(settings.login_max_failures):
        _attempt(public_client, staff_user.email, WRONG_PASSWORD)

    assert _attempt(public_client, other.email, STAFF_PASSWORD).status_code == 200


def test_throttle_window_lapses(
    public_client: TestClient, staff_user: StaffUser, session: Session
) -> None:
    for _ in range(settings.login_max_failures):
        _attempt(public_client, staff_user.email, WRONG_PASSWORD)

    attempt = session.query(LoginAttempt).one()
    attempt.window_started_at = datetime.now(UTC) - timedelta(
        minutes=settings.login_window_minutes + 1
    )
    session.commit()

    # The lock lifts by itself once the window passes: no one has to unlock it.
    assert _attempt(public_client, staff_user.email, STAFF_PASSWORD).status_code == 200
