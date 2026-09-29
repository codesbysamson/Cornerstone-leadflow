"""Request dependencies that enforce staff authentication and CSRF.

These are the security boundary. Hiding the CRM in the frontend is a usability
measure, not a control: every staff route is protected here, on the server, so
knowing a URL is not enough.
"""

from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import CSRF_COOKIE_NAME, SESSION_COOKIE_NAME
from app.database import get_db
from app.models import StaffSession, StaffUser
from app.security import digest_csrf_token, digest_session_token, tokens_match

#: Deliberately bare. A rejected request must not confirm that a lead, a
#: customer or a quotation exists, so nothing is echoed back about the target.
_UNAUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Session"},
)

#: 403 rather than 401: the session is valid, this request simply is not
#: authorised to be made from the caller's origin.
_CSRF_REJECTED = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail="Missing or invalid CSRF token",
)

_STATE_CHANGING = {"POST", "PUT", "PATCH", "DELETE"}


@dataclass(frozen=True)
class CurrentStaff:
    """The resolved session, for routes that need the staff identity."""

    user: StaffUser
    session: StaffSession


def load_session_or_none(
    db: Session, raw_token: str
) -> tuple[StaffUser, StaffSession] | None:
    """Resolves a raw cookie value to a live session, or None.

    Expired and deactivated sessions are deleted as they are encountered, so
    they expire naturally with no background job.
    """
    if not raw_token:
        return None

    result = db.execute(
        select(StaffSession).where(
            StaffSession.token_hash == digest_session_token(raw_token)
        )
    )
    staff_session = result.scalar_one_or_none()
    if staff_session is None:
        return None

    now = datetime.now(UTC)
    expires_at = staff_session.expires_at
    if expires_at.tzinfo is None:
        # The SQLite test database returns naive timestamps; PostgreSQL returns
        # offset-aware ones. Normalising here keeps one code path.
        expires_at = expires_at.replace(tzinfo=UTC)

    if expires_at <= now:
        db.delete(staff_session)
        db.commit()
        return None

    user = db.get(StaffUser, staff_session.staff_user_id)
    if user is None or not user.is_active:
        # Disabling an account invalidates its live sessions immediately.
        db.delete(staff_session)
        db.commit()
        return None

    return user, staff_session


def require_staff(
    request: Request,
    x_csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
    leadflow_session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    leadflow_csrf: str | None = Cookie(default=None, alias=CSRF_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> CurrentStaff:
    """The single staff dependency: resolves the session, then checks CSRF.

    Both checks run against the same resolved session row, and reads skip the
    CSRF check because they are not state-changing.

    CSRF is a double-submit token, which CORS cannot replace. CORS decides
    whether a browser lets *script* read a cross-origin response; it does not
    stop a cross-origin form POST from being delivered with the session cookie
    attached. The header is validated against the digest stored on the
    authenticated session, and also against the cookie, so a stale cookie in the
    browser cannot be paired with a fresh session.
    """
    resolved = load_session_or_none(db, leadflow_session or "")
    if resolved is None:
        raise _UNAUTHENTICATED

    staff = CurrentStaff(user=resolved[0], session=resolved[1])

    if request.method.upper() in _STATE_CHANGING:
        if not x_csrf_token or not leadflow_csrf:
            raise _CSRF_REJECTED
        if not tokens_match(
            digest_csrf_token(x_csrf_token), staff.session.csrf_token_hash
        ):
            raise _CSRF_REJECTED
        if not tokens_match(
            digest_csrf_token(x_csrf_token), digest_csrf_token(leadflow_csrf)
        ):
            raise _CSRF_REJECTED

    return staff
