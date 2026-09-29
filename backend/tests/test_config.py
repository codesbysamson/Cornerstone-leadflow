"""Configuration validation.

The point of these is that a misconfigured production deploy fails to start,
rather than quietly serving a weaker service than intended.
"""

import pytest

from app.config import (
    DEFAULT_SESSION_HOURS,
    LOW_COST_ARGON2,
    ConfigurationError,
    Settings,
    validate,
)

#: The reduced costs the test suite runs with, named as Settings spells them.
WEAK = {
    "argon2_time_cost": LOW_COST_ARGON2["time_cost"],
    "argon2_memory_cost": LOW_COST_ARGON2["memory_cost"],
    "argon2_parallelism": LOW_COST_ARGON2["parallelism"],
}

SAFE = {
    "environment": "production",
    "cookie_secure": True,
    "allowed_origins": ["https://crm.example.com"],
    "argon2_time_cost": 3,
    "argon2_memory_cost": 65536,
    "argon2_parallelism": 4,
    "session_max_age_seconds": DEFAULT_SESSION_HOURS * 3600,
}


def make(**overrides: object) -> Settings:
    return Settings(**{**SAFE, **overrides})


def test_a_safe_production_configuration_is_accepted() -> None:
    validate(make())


def test_production_without_secure_cookies_is_rejected() -> None:
    """Otherwise the session cookie travels in the clear and can be stolen off
    the wire by anyone on the network path."""
    with pytest.raises(ConfigurationError, match="COOKIE_SECURE"):
        validate(make(cookie_secure=False))


def test_production_with_weak_argon2_costs_is_rejected() -> None:
    """The test suite lowers these to keep the suite fast. If that reduction
    reached production, an offline attacker could crack a stolen hash quickly."""
    with pytest.raises(ConfigurationError, match="ARGON2"):
        validate(make(**WEAK))


def test_wildcard_cors_origin_is_rejected() -> None:
    """Credentials are enabled, so a wildcard would let any site on the
    internet make authenticated, cookie-bearing requests as a signed-in staff
    member."""
    with pytest.raises(ConfigurationError, match=r"\*"):
        validate(make(allowed_origins=["*"]))


def test_empty_cors_origins_is_rejected() -> None:
    """Silently allowing nothing looks like a working deployment until a
    browser is refused; failing at startup is far easier to diagnose."""
    with pytest.raises(ConfigurationError, match="CORS_ORIGINS"):
        validate(make(allowed_origins=[]))


def test_non_positive_session_lifetime_is_rejected() -> None:
    with pytest.raises(ConfigurationError, match="SESSION_MAX_AGE_SECONDS"):
        validate(make(session_max_age_seconds=0))


def test_problems_are_reported_together_not_one_at_a_time() -> None:
    """A deploy with three faults should be told about all three, so it is
    fixed in one pass rather than across three restarts."""
    with pytest.raises(ConfigurationError) as exc:
        validate(make(cookie_secure=False, allowed_origins=["*"], session_max_age_seconds=0))

    message = str(exc.value)
    assert "COOKIE_SECURE" in message
    assert "CORS_ORIGINS" in message
    assert "SESSION_MAX_AGE_SECONDS" in message


@pytest.mark.parametrize("environment", ["production", "prod", "PRODUCTION", " Prod "])
def test_production_is_recognised_regardless_of_spelling(environment: str) -> None:
    """A deploy labelled "Prod" must not silently get development settings."""
    assert make(environment=environment).is_production is True


@pytest.mark.parametrize("environment", ["development", "staging", "test", ""])
def test_other_environments_are_not_production(environment: str) -> None:
    assert make(environment=environment).is_production is False


def test_docs_are_disabled_in_production() -> None:
    """The OpenAPI schema publishes every internal route and payload shape."""
    assert make().docs_enabled is False
    assert make(environment="development").docs_enabled is True


def test_development_tolerates_weak_argon2_costs() -> None:
    """The test suite runs with them lowered, so validation must not stop it."""
    validate(make(environment="test", cookie_secure=False, **WEAK))
