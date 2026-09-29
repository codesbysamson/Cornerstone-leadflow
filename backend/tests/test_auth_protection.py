"""The authentication boundary as seen from outside.

These assert that a caller with no session gets nowhere. The tests in
``test_auth.py`` cover what a signed-in caller can do; the two together are the
complete statement of the boundary.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import CSRF_COOKIE_NAME, SESSION_COOKIE_NAME
from app.main import app
from app.models import StaffUser

from .conftest import STAFF_PASSWORD, sign_in

#: Everything the app serves that is *not* a staff route. A customer on the
#: website has no session, so these must stay reachable.
PUBLIC_ROUTES = {
    ("POST", "/api/leads"),
    ("GET", "/api/auth/session"),
    ("POST", "/api/auth/login"),
    ("GET", "/health"),
}

#: Logout is deliberately excluded from the session requirement: signing out when
#: there is nothing to sign out of is a no-op, not an error, and demanding a
#: valid session would make a stale-cookie logout fail confusingly. It is still
#: CSRF-protected, and it still deletes a real session when one is presented.
SESSION_OPTIONAL_ROUTES = {("POST", "/api/auth/logout")}

#: Every remaining route must be behind require_staff.
#:
#: Derived from the app rather than written out by hand, so that a route added
#: later without protection fails this test. The router-level dependencies in
#: leads.py and quotations.py are what make new routes safe by default; this is
#: what proves they are.
def _staff_routes() -> list[tuple[str, str]]:
    routes: list[tuple[str, str]] = []
    for route in app.routes:
        path = getattr(route, "path", "")
        if not path.startswith("/api"):
            continue
        for method in getattr(route, "methods", set()) - {"HEAD", "OPTIONS"}:
            if (method, path) not in PUBLIC_ROUTES | SESSION_OPTIONAL_ROUTES:
                routes.append((method, path))
    return sorted(routes)


STAFF_ROUTES = _staff_routes()


@pytest.mark.parametrize(("method", "path"), STAFF_ROUTES)
def test_staff_route_requires_a_session(
    public_client: TestClient, method: str, path: str
) -> None:
    response = public_client.request(method, path)

    assert response.status_code == 401, f"{method} {path} was reachable unauthenticated"


@pytest.mark.parametrize(("method", "path"), STAFF_ROUTES)
def test_rejection_is_bare_and_leaks_nothing(
    public_client: TestClient, method: str, path: str

) -> None:
    """A 401 must not confirm the target exists.

    ``GET /api/leads/1`` and ``GET /api/leads/999999`` have to be
    indistinguishable, or the error becomes a way to probe for leads.
    """
    response = public_client.request(method, path)

    assert response.json() == {"detail": "Not authenticated"}


def test_health_stays_public(public_client: TestClient) -> None:
    """A load balancer must be able to reach it without credentials."""
    assert public_client.get("/health").status_code == 200


def test_session_probe_stays_public(public_client: TestClient) -> None:
    """It has to be: the frontend asks it before it can log in."""
    response = public_client.get("/api/auth/session")

    assert response.status_code == 200
    body = response.json()
    # It exposes no staff data and nothing about any lead, customer or
    # quotation; the CSRF token is the only thing it hands out, and it is
    # worthless without the cookie that must accompany it.
    assert body["authenticated"] is False
    assert body["user"] is None
    assert set(body) == {"authenticated", "user", "csrf_token"}


def test_public_enquiry_submission_stays_open(public_client: TestClient) -> None:
    """The website has no session and never will.

    This is the regression guard for the router split: putting the staff
    dependency on the combined router would 401 the customer form and take the
    public site offline.
    """
    response = public_client.post(
        "/api/leads",
        json={
            "customer_name": "Sarah Johnson",
            "email": "sarah@example.com",
            "phone": "+44 7700 900123",
            "service": "Office Cleaning",
            "property_type": "Office",
            "location": "Manchester",
            "property_size": "2,500 sq ft",
            "frequency": "Weekly",
            "preferred_date": "2026-10-05",
            "requirements": "Cleaning required outside normal office hours.",
        },
    )

    assert response.status_code == 201


def test_a_public_submission_is_immediately_visible_to_staff(
    public_client: TestClient, client: TestClient
) -> None:
    created = public_client.post(
        "/api/leads",
        json={
            "customer_name": "Sarah Johnson",
            "email": "sarah@example.com",
            "phone": "+44 7700 900123",
            "service": "Office Cleaning",
            "property_type": "Office",
            "location": "Manchester",
            "property_size": "2,500 sq ft",
            "frequency": "Weekly",
            "preferred_date": "2026-10-05",
            "requirements": "Cleaning required outside normal office hours.",
        },
    ).json()

    assert client.get("/api/leads").json()[0]["id"] == created["id"]


# ---------------------------------------------------------------------------
# CSRF
# ---------------------------------------------------------------------------


def test_forged_session_cookie_is_rejected(public_client: TestClient) -> None:
    """The cookie is the whole session, so guessing is the only attack.

    256 bits of ``secrets`` entropy makes this infeasible; the test pins that a
    plausible-looking forged value gets nowhere.
    """
    public_client.cookies.set(SESSION_COOKIE_NAME, "forged-session-token")

    assert public_client.get("/api/leads").status_code == 401


def test_state_changing_request_without_csrf_header_is_rejected(
    public_client: TestClient, staff_user: StaffUser
) -> None:
    """CORS does not cover this.

    CORS stops a cross-origin *script* from reading a response. It does not stop
    a cross-origin form POST from being delivered with the session cookie
    attached, so without this check a hostile page could change lead data.
    """
    sign_in(public_client, staff_user.email, STAFF_PASSWORD)

    response = public_client.post(
        "/api/leads/1/status", json={"status": "CONTACTED"}
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Missing or invalid CSRF token"}


def test_state_changing_request_with_mismatched_csrf_is_rejected(
    public_client: TestClient, staff_user: StaffUser
) -> None:
    sign_in(public_client, staff_user.email, STAFF_PASSWORD)

    response = public_client.post(
        "/api/leads/1/status",
        json={"status": "CONTACTED"},
        headers={"X-CSRF-Token": "forged-csrf-token"},
    )

    assert response.status_code == 403


def test_reads_do_not_require_csrf(
    public_client: TestClient, staff_user: StaffUser, session: Session
) -> None:
    """A GET cannot change state, so demanding a token would only add friction
    and break the app on a fresh tab where the cookie has not been read yet."""
    sign_in(public_client, staff_user.email, STAFF_PASSWORD)
    public_client.cookies.delete(CSRF_COOKIE_NAME)

    assert public_client.get("/api/leads").status_code == 200


def test_csrf_cookie_from_another_session_does_not_work(
    public_client: TestClient, staff_user: StaffUser
) -> None:
    """A token is bound to the session that issued it, so a token harvested
    from one browser cannot be replayed alongside a different session."""
    other_client = TestClient(public_client.app)
    other_client.get("/api/auth/session")
    stolen = other_client.cookies.get(CSRF_COOKIE_NAME)

    sign_in(public_client, staff_user.email, STAFF_PASSWORD)

    response = public_client.post(
        "/api/leads/1/status",
        json={"status": "CONTACTED"},
        headers={"X-CSRF-Token": stolen},
    )

    assert response.status_code == 403


def test_logout_without_a_session_is_harmless(public_client: TestClient) -> None:
    """Signing out when there is nothing to sign out of.

    Returns 403 because the CSRF check runs first, which is the correct answer:
    an unauthenticated cross-site POST should not be able to act here either.
    """
    public_client.get("/api/auth/session")

    response = public_client.post("/api/auth/logout")

    assert response.status_code == 403
    # Nothing is revealed about whether a session existed.
    assert response.json() == {"detail": "Missing or invalid CSRF token"}
