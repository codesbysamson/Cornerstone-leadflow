"""Password hashing, session tokens and cookie construction.

Two hash families, used for two different problems:

* **Argon2id** for passwords. These are human-chosen and therefore low entropy,
  so they need a deliberately slow, memory-hard hash.
* **SHA-256** for session and CSRF tokens. These are 256 bits of
  ``secrets``-generated randomness with no dictionary to attack, and they must be
  *looked up* by digest, which needs a deterministic, indexable hash. Running
  Argon2 here would be both unnecessary and unusable for lookup.
"""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.config import CSRF_COOKIE_NAME, SESSION_COOKIE_NAME, settings

#: Fixed namespace so a digest from one table can never be replayed as a lookup
#: key in another (for example a session token presented as a throttle key).
_NAMESPACE_AUTH = b"leadflow:auth:v1"
_NAMESPACE_LOGIN = b"leadflow:login:v1"

_password_hasher = PasswordHasher(
    time_cost=settings.argon2_time_cost,
    memory_cost=settings.argon2_memory_cost,
    parallelism=settings.argon2_parallelism,
)

#: Verified against when the email is unknown, so that a request for a
#: non-existent account costs the same as one for a real account and the
#: response time cannot be used to enumerate staff.
_DUMMY_PASSWORD_HASH = _password_hasher.hash(secrets.token_urlsafe(32))


def hash_password(password: str) -> str:
    """Returns an Argon2id PHC string. The plaintext is never retained."""
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verifies a password, returning False rather than raising on any failure."""
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def verify_password_or_dummy(password: str, password_hash: str | None) -> bool:
    """Verifies against the real hash, or burns equivalent time if there is none.

    Without this, an unknown email would return noticeably faster than a known
    one with a wrong password, which is enough to enumerate staff accounts.
    """
    if password_hash is None:
        dummy_verify(password)
        return False
    return verify_password(password, password_hash)


def dummy_verify(password: str) -> None:
    """Deliberately performs a full verification for an unknown account, so the
    response time of a login for a non-existent email matches a real one.

    The result is discarded. It goes through ``verify_password`` so that a
    mismatch comes back as ``False`` rather than as an uncaught
    ``VerifyMismatchError`` — which is exactly what a wrong password against a
    real account produces.
    """
    verify_password(password, _DUMMY_PASSWORD_HASH)


def new_token() -> str:
    """A fresh opaque token. 32 bytes gives 256 bits of entropy."""
    return secrets.token_urlsafe(32)


def digest(value: str, namespace: bytes = _NAMESPACE_AUTH) -> str:
    """A deterministic, namespaced SHA-256 hex digest for lookup."""
    return hashlib.sha256(namespace + value.encode("utf-8")).hexdigest()


def digest_session_token(token: str) -> str:
    return digest(token, _NAMESPACE_AUTH)


def digest_csrf_token(token: str) -> str:
    # A distinct namespace so a CSRF token can never be presented as a session
    # token, or the reverse.
    return digest(token, _NAMESPACE_AUTH + b":csrf")


def digest_login_key(email: str) -> str:
    return digest(email.strip().lower(), _NAMESPACE_LOGIN)


def tokens_match(provided: str, expected: str) -> bool:
    """Constant-time comparison for tokens supplied by a client."""
    return hmac.compare_digest(provided, expected)


def normalise_email(email: str) -> str:
    """Lowercases and trims for comparison. There are no plus-addressing or
    gmail-dot rules: this is a small staff list, and silently rewriting an
    address is a worse failure than an exact match."""
    return email.strip().lower()


def session_expiry() -> datetime:
    """Absolute expiry. Deliberately not sliding: a session should not roll
    forward indefinitely on a machine that is never signed out."""
    return datetime.now(UTC) + timedelta(seconds=settings.session_max_age_seconds)


# ---------------------------------------------------------------------------
# Cookies
# ---------------------------------------------------------------------------


def session_cookie_kwargs() -> dict:
    """Attributes for the session cookie. HttpOnly so that an XSS bug cannot
    exfiltrate it; the CSRF cookie below is deliberately the opposite."""
    return {
        "key": SESSION_COOKIE_NAME,
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": "lax",
        "path": "/",
        "max_age": settings.session_max_age_seconds,
    }


def csrf_cookie_kwargs() -> dict:
    """Attributes for the CSRF cookie.

    Not HttpOnly: the browser has to be able to read it so the frontend can echo
    it in the X-CSRF-Token header. That is safe because this token is not a
    credential on its own — without the HttpOnly session cookie it authorises
    nothing.
    """
    return {
        "key": CSRF_COOKIE_NAME,
        "httponly": False,
        "secure": settings.cookie_secure,
        "samesite": "lax",
        "path": "/",
        "max_age": settings.session_max_age_seconds,
    }


def cleared_cookie_kwargs(key: str) -> dict:
    """Expire an existing cookie. Must match the original path and flags or the
    browser will treat it as a different cookie and leave it in place."""
    return {
        "key": key,
        "value": "",
        "httponly": key == SESSION_COOKIE_NAME,
        "secure": settings.cookie_secure,
        "samesite": "lax",
        "path": "/",
        "max_age": 0,
        "expires": 0,
    }
