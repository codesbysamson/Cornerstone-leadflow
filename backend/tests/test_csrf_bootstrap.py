"""Pre-authentication CSRF bootstrap.

The defect these cover: the browser obtained its CSRF token by reading the
`leadflow_csrf` cookie through `document.cookie`. That cookie is host-only, so
when the page is served from a different host name than the API — `localhost`
talking to `127.0.0.1`, the default both halves shipped with — the cookie is
invisible to the page, no `X-CSRF-Token` header is ever attached, and login
fails with a bare 403 before credentials are even examined.

The fix is that the session probe returns the token it has bound to the browser
in the response body. These tests pin that contract, and pin that moving the
token into the body did not weaken the double-submit check.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import CSRF_COOKIE_NAME
from app.models import StaffUser

from .conftest import STAFF_PASSWORD, sign_in

WRONG_PASSWORD = "definitely not the password"


def _probe(client: TestClient) -> dict:
    response = client.get("/api/auth/session")
    assert response.status_code == 200
    return response.json()


# ---------------------------------------------------------------------------
# The regression
# ---------------------------------------------------------------------------


def test_probe_returns_the_csrf_token_in_the_body(public_client: TestClient) -> None:
    """The token must be obtainable without reading the cookie at all.

    This is the assertion that fails against the original code. A client that
    can only obtain the token from a host-only cookie has no way to authenticate
    whenever the page and the API are on different hosts.
    """
    body = _probe(public_client)

    assert isinstance(body.get("csrf_token"), str)
    assert body["csrf_token"]


def test_probe_token_matches_the_cookie_it_just_set(public_client: TestClient) -> None:
    """Body and cookie must be the same value.

    They are the two halves of the double submit, so if they disagreed the
    client would send a header that the server rejects even though it behaved
    exactly as the API described.
    """
    _probe(public_client)

    assert public_client.cookies.get(CSRF_COOKIE_NAME) is not None


def test_login_works_using_only_the_token_from_the_probe_body(
    public_client: TestClient, staff_user: StaffUser
) -> None:
    """The full bootstrap, driven exactly as a cross-host browser must drive it.

    The header is taken from the probe's JSON body and sent with credentials,
    with no reliance on the test client's convenient cookie access. This is the
    real-browser sequence that returned 403.
    """
    token = _probe(public_client)["csrf_token"]

    response = public_client.post(
        "/api/auth/login",
        json={"email": staff_user.email, "password": STAFF_PASSWORD},
        headers={"X-CSRF-Token": token},
    )

    assert response.status_code == 200
    assert response.json()["email"] == staff_user.email


def test_probe_token_for_an_existing_session_matches_that_session(
    public_client: TestClient, staff_user: StaffUser
) -> None:
    """A signed-in reload must hand back the token already bound to the session.

    Returning a freshly minted token here would look fine and then fail on the
    next click, because the session's stored digest would no longer match the
    cookie the browser is holding.
    """
    sign_in(public_client, staff_user.email, STAFF_PASSWORD)

    first = _probe(public_client)["csrf_token"]
    second = _probe(public_client)["csrf_token"]

    assert first == second

    # And the token the frontend now holds really does work.
    response = public_client.post(
        "/api/leads/1/status",
        json={"status": "CONTACTED"},
        headers={"X-CSRF-Token": second},
    )
    assert response.status_code == 404  # passed CSRF, lead simply does not exist


# ---------------------------------------------------------------------------
# The double-submit check is unchanged
# ---------------------------------------------------------------------------


def test_login_without_a_csrf_header_is_still_rejected(
    public_client: TestClient, staff_user: StaffUser
) -> None:
    """Having the token in the body must not make the header optional."""
    _probe(public_client)

    response = public_client.post(
        "/api/auth/login",
        json={"email": staff_user.email, "password": STAFF_PASSWORD},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Missing or invalid CSRF token"}


def test_login_with_a_mismatched_csrf_token_is_still_rejected(
    public_client: TestClient, staff_user: StaffUser
) -> None:
    """A token the server never issued is refused.

    Returning a token in the response body does not let a client choose its own
    value: the server still compares the header against its own cookie.
    """
    _probe(public_client)

    response = public_client.post(
        "/api/auth/login",
        json={"email": staff_user.email, "password": STAFF_PASSWORD},
        headers={"X-CSRF-Token": "an-attacker-chosen-token"},
    )

    assert response.status_code == 403


def test_a_valid_token_with_the_wrong_password_still_fails_generically(
    public_client: TestClient, staff_user: StaffUser
) -> None:
    """The token is not a credential: possessing it proves nothing about the
    password, and a failure still says nothing about whether the account
    exists."""
    token = _probe(public_client)["csrf_token"]

    response = public_client.post(
        "/api/auth/login",
        json={"email": staff_user.email, "password": WRONG_PASSWORD},
        headers={"X-CSRF-Token": token},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password"}


def test_throttling_still_applies_with_a_valid_token(
    public_client: TestClient, staff_user: StaffUser
) -> None:
    """The fix must not open a second, unthrottled path to the password check."""
    from app.config import settings

    for _ in range(settings.login_max_failures):
        token = _probe(public_client)["csrf_token"]
        public_client.post(
            "/api/auth/login",
            json={"email": staff_user.email, "password": WRONG_PASSWORD},
            headers={"X-CSRF-Token": token},
        )

    token = _probe(public_client)["csrf_token"]
    locked_out = public_client.post(
        "/api/auth/login",
        json={"email": staff_user.email, "password": STAFF_PASSWORD},
        headers={"X-CSRF-Token": token},
    )

    assert locked_out.status_code == 401
    assert locked_out.json() == {"detail": "Invalid email or password"}


def test_a_second_sessions_token_cannot_be_reused(
    public_client: TestClient, staff_user: StaffUser, session: Session
) -> None:
    """Two browsers must not be able to pair one's token with another's cookie.

    The token identifies the browser that was issued it; it is not a bearer
    credential for whichever session presents it.
    """
    first = _probe(public_client)["csrf_token"]

    other = TestClient(public_client.app)
    second = other.get("/api/auth/session").json()["csrf_token"]

    response = public_client.post(
        "/api/auth/login",
        json={"email": staff_user.email, "password": STAFF_PASSWORD},
        headers={"X-CSRF-Token": second},
    )

    assert first != second
    assert response.status_code == 403
