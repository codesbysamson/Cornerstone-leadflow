"""Staff authentication: login, logout, identity, and the CSRF bootstrap probe.

Every failed login returns an identical status and body, whether the account
does not exist, the password is wrong, or the account is disabled, so neither
the response nor its timing reveals which emails are real.
"""

from datetime import UTC, datetime, timedelta

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    Header,
    HTTPException,
    Request,
    Response,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import CSRF_COOKIE_NAME, SESSION_COOKIE_NAME, settings
from app.database import get_db
from app.dependencies import CurrentStaff, load_session_or_none, require_staff
from app.models import LoginAttempt, StaffSession, StaffUser
from app.schemas import LoginRequest, SessionProbe, StaffUserRead
from app.security import (
    cleared_cookie_kwargs,
    csrf_cookie_kwargs,
    digest_csrf_token,
    digest_login_key,
    digest_session_token,
    hash_password,
    new_token,
    normalise_email,
    session_cookie_kwargs,
    session_expiry,
    tokens_match,
    verify_password_or_dummy,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _invalid_credentials() -> HTTPException:
    """One response for every failure mode, including being throttled.

    Distinguishing "no such user" from "wrong password" or "locked out" would
    turn this endpoint into an account-enumeration oracle, so all three are the
    same 401 with the same body.
    """
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password",
        headers={"WWW-Authenticate": "Session"},
    )


def _csrf_rejected() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Missing or invalid CSRF token",
    )


# ---------------------------------------------------------------------------
# Login throttling
#
# One row per throttle key holding a failure count and a window start. Rows are
# overwritten in place and lapse with the window, so there is nothing to collect
# and no background job is needed. The state is in the database, so it survives
# a restart and is shared across worker processes — the property an in-memory
# counter would not have.
# ---------------------------------------------------------------------------


def _throttle_window() -> timedelta:
    return timedelta(minutes=settings.login_window_minutes)


def _as_aware(value: datetime) -> datetime:
    """The SQLite test database returns naive timestamps, PostgreSQL aware ones."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _is_throttled(db: Session, key: str) -> bool:
    attempt = db.execute(
        select(LoginAttempt).where(LoginAttempt.key == key)
    ).scalar_one_or_none()
    if attempt is None:
        return False

    if datetime.now(UTC) - _as_aware(attempt.window_started_at) > _throttle_window():
        # The window has lapsed, so the lock has lifted on its own.
        return False

    return attempt.failure_count >= settings.login_max_failures


def _record_failure(db: Session, key: str) -> None:
    now = datetime.now(UTC)
    attempt = db.execute(
        select(LoginAttempt).where(LoginAttempt.key == key)
    ).scalar_one_or_none()

    if attempt is None:
        db.add(LoginAttempt(key=key, failure_count=1, window_started_at=now))
    else:
        if now - _as_aware(attempt.window_started_at) > _throttle_window():
            attempt.failure_count = 1
            attempt.window_started_at = now
        else:
            attempt.failure_count += 1
        attempt.updated_at = now

    db.commit()


def _clear_failures(db: Session, key: str) -> None:
    """A success resets the counter, so a staff member who fumbled their password
    twice is not left throttled afterwards."""
    attempt = db.execute(
        select(LoginAttempt).where(LoginAttempt.key == key)
    ).scalar_one_or_none()
    if attempt is not None:
        db.delete(attempt)
        db.commit()


# ---------------------------------------------------------------------------
# Cookies
# ---------------------------------------------------------------------------


def _set_session_cookies(response: Response, session_token: str, csrf_token: str) -> None:
    response.set_cookie(value=session_token, **session_cookie_kwargs())
    response.set_cookie(value=csrf_token, **csrf_cookie_kwargs())


def _clear_cookies(response: Response) -> None:
    response.set_cookie(**cleared_cookie_kwargs(SESSION_COOKIE_NAME))
    response.set_cookie(**cleared_cookie_kwargs(CSRF_COOKIE_NAME))


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/session", response_model=SessionProbe)
def session_probe(
    response: Response,
    leadflow_session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    leadflow_csrf: str | None = Cookie(default=None, alias=CSRF_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> SessionProbe:
    """Reports whether the caller holds a valid staff session.

    Public by necessity — the frontend must be able to ask before it can log in
    — so it returns staff data only when a valid session is presented, and never
    anything about a lead, customer or quotation.

    It also mints the CSRF cookie. That is what lets the very first login carry a
    valid token without weakening login CSRF protection: the cookie is readable
    only same-origin, so a cross-origin attacker can neither read it nor forge a
    matching header.

    Always 200, with a boolean, so the frontend branches on one response shape
    rather than treating "not signed in" as an error.
    """
    resolved = load_session_or_none(db, leadflow_session or "")

    if resolved is None:
        csrf_token = new_token()
        response.set_cookie(value=csrf_token, **csrf_cookie_kwargs())
        return SessionProbe(authenticated=False, user=None, csrf_token=csrf_token)

    user, staff_session = resolved

    # Re-mint only when the browser is not already holding this session's token.
    # Rotating unconditionally would invalidate the pairing that require_staff
    # checks on every state-changing request, so a signed-in staff member who
    # simply opened the app would have their next click rejected.
    if leadflow_csrf and tokens_match(
        digest_csrf_token(leadflow_csrf), staff_session.csrf_token_hash
    ):
        # Reuse the token already bound to the session, so the value returned to
        # the frontend keeps matching the cookie the browser holds.
        csrf_token = leadflow_csrf
    else:
        csrf_token = new_token()
        staff_session.csrf_token_hash = digest_csrf_token(csrf_token)
        db.commit()
        response.set_cookie(value=csrf_token, **csrf_cookie_kwargs())

    return SessionProbe(
        authenticated=True,
        user=StaffUserRead.model_validate(user),
        csrf_token=csrf_token,
    )


@router.post("/login", response_model=StaffUserRead)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    leadflow_csrf: str | None = Cookie(default=None, alias=CSRF_COOKIE_NAME),
    x_csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
    db: Session = Depends(get_db),
) -> StaffUser:
    """Exchanges credentials for a fresh server-side session.

    Login is CSRF-protected by the double-submit token minted by
    ``GET /api/auth/session``. Without that check, an attacker could force a
    victim to sign in as the attacker's account and then unwittingly save data
    into it.
    """
    # Double-submit against the cookie only: there is no session yet to compare
    # against, which is exactly why the probe endpoint mints the cookie first.
    if not x_csrf_token or not leadflow_csrf:
        raise _csrf_rejected()
    if not tokens_match(
        digest_csrf_token(x_csrf_token), digest_csrf_token(leadflow_csrf)
    ):
        raise _csrf_rejected()

    email = normalise_email(payload.email)
    key = digest_login_key(email)

    # Checked before the account is looked up, so a throttled attempt costs the
    # same as any other and reveals nothing about whether the account exists.
    if _is_throttled(db, key):
        raise _invalid_credentials()

    user = db.execute(
        select(StaffUser).where(StaffUser.email == email)
    ).scalar_one_or_none()

    # Performs a full Argon2 verification in both branches, so a missing account
    # takes the same time as a wrong password.
    password_ok = verify_password_or_dummy(
        payload.password, user.password_hash if user is not None else None
    )

    if user is None or not password_ok or not user.is_active:
        _record_failure(db, key)
        raise _invalid_credentials()

    _clear_failures(db, key)

    # A brand new token on every login, never derived from anything the client
    # supplied: this is what prevents session fixation.
    session_token = new_token()
    csrf_token = new_token()

    db.add(
        StaffSession(
            staff_user_id=user.id,
            token_hash=digest_session_token(session_token),
            csrf_token_hash=digest_csrf_token(csrf_token),
            expires_at=session_expiry(),
        )
    )
    db.commit()

    _set_session_cookies(response, session_token, csrf_token)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    leadflow_session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    leadflow_csrf: str | None = Cookie(default=None, alias=CSRF_COOKIE_NAME),
    x_csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
    db: Session = Depends(get_db),
) -> Response:
    """Revokes the server-side session and expires both cookies.

    CSRF is required even though this changes no data, because without it an
    attacker could sign a staff member out at will.
    """
    if not x_csrf_token or not leadflow_csrf:
        raise _csrf_rejected()
    if not tokens_match(
        digest_csrf_token(x_csrf_token), digest_csrf_token(leadflow_csrf)
    ):
        raise _csrf_rejected()

    if leadflow_session:
        session = db.execute(
            select(StaffSession).where(
                StaffSession.token_hash == digest_session_token(leadflow_session)
            )
        ).scalar_one_or_none()
        if session is not None:
            # Deleting the row is what actually revokes: a captured cookie is
            # worthless from this point on, not merely until it expires.
            db.delete(session)
            db.commit()

    _clear_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=StaffUserRead)
def me(staff: CurrentStaff = Depends(require_staff)) -> StaffUser:
    """The signed-in staff member. Requires a valid, unexpired session."""
    return staff.user
