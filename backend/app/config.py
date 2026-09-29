"""Environment-driven configuration.

Read once at import so the whole app agrees on one set of values, and validated
loudly at startup: an unsafe production configuration should stop the process
rather than serve cookies over plain HTTP or accept a wildcard CORS origin.
"""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()

DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"

SESSION_COOKIE_NAME = "leadflow_session"
CSRF_COOKIE_NAME = "leadflow_csrf"

#: Absolute session lifetime. Twelve hours is long enough for a working day
#: and short enough that an unattended, still-unlocked machine does not keep a
#: live session for much longer than a shift.
DEFAULT_SESSION_HOURS = 12

#: Login throttling. Five failures inside a fifteen minute window locks the
#: login endpoint for that key.
DEFAULT_LOGIN_MAX_FAILURES = 5
DEFAULT_LOGIN_WINDOW_MINUTES = 15

#: Argon2id cost. The defaults are already strong (64 MiB, t=3, p=4); the test
#: suite lowers them through the environment so it does not spend most of its
#: time hashing. A cost this low must never be reachable in production, which
#: :func:`validate` enforces.
LOW_COST_ARGON2 = {"time_cost": 1, "memory_cost": 8192, "parallelism": 1}


class ConfigurationError(RuntimeError):
    """The process is misconfigured and must not start."""


def _as_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer, got {raw!r}") from exc


@dataclass(frozen=True)
class Settings:
    # "production" turns on every safe-by-default behaviour. Anything not set
    # explicitly is treated as development.
    environment: str = os.getenv("APP_ENV", "development")

    allowed_origins: list[str] = field(
        default_factory=lambda: [
            origin.strip()
            for origin in os.getenv("CORS_ORIGINS", DEFAULT_CORS_ORIGINS).split(",")
            if origin.strip()
        ]
    )

    # Cookies cannot be Secure over http://localhost, so this is off in
    # development and mandatory in production.
    cookie_secure: bool = _as_bool("COOKIE_SECURE", False)

    session_max_age_seconds: int = _as_int(
        "SESSION_MAX_AGE_SECONDS", DEFAULT_SESSION_HOURS * 3600
    )

    login_max_failures: int = _as_int(
        "LOGIN_MAX_FAILURES", DEFAULT_LOGIN_MAX_FAILURES
    )
    login_window_minutes: int = _as_int(
        "LOGIN_WINDOW_MINUTES", DEFAULT_LOGIN_WINDOW_MINUTES
    )

    # Argon2id parameters. Lowered only by the test suite.
    argon2_time_cost: int = _as_int("ARGON2_TIME_COST", 3)
    argon2_memory_cost: int = _as_int("ARGON2_MEMORY_COST", 65536)
    argon2_parallelism: int = _as_int("ARGON2_PARALLELISM", 4)

    @property
    def is_production(self) -> bool:
        return self.environment.strip().lower() in {"production", "prod"}

    @property
    def docs_enabled(self) -> bool:
        """The OpenAPI docs publish the entire internal schema, so they are a
        development affordance rather than something to ship."""
        return not self.is_production


def validate(settings: Settings) -> None:
    """Refuses to start on an unsafe configuration."""
    problems: list[str] = []

    if settings.is_production:
        if not settings.cookie_secure:
            problems.append(
                "COOKIE_SECURE must be true in production, otherwise the "
                "session cookie would be sent over plain HTTP"
            )
        if settings.argon2_memory_cost < 32768 or settings.argon2_time_cost < 2:
            problems.append(
                "ARGON2_MEMORY_COST/ARGON2_TIME_COST are below the safe "
                "minimum; the reduced test cost must never reach production"
            )

    # A wildcard cannot be combined with credentials: browsers reject it, and
    # any origin would otherwise be allowed to make authenticated requests.
    if "*" in settings.allowed_origins:
        problems.append(
            "CORS_ORIGINS must not contain '*' while credentials are enabled"
        )
    if not settings.allowed_origins:
        problems.append("CORS_ORIGINS must list at least one explicit origin")

    if settings.session_max_age_seconds <= 0:
        problems.append("SESSION_MAX_AGE_SECONDS must be positive")

    if problems:
        raise ConfigurationError(
            "Unsafe configuration:\n- " + "\n- ".join(problems)
        )


settings = Settings()
validate(settings)
