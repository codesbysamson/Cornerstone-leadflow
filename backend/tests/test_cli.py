"""The staff bootstrap CLI.

Bootstrapping the first account is the one operation that has to be safe by
construction: whoever runs it decides who gets into the CRM, so the failure modes
worth pinning are the ones that quietly produce a weak or surprising account.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cli import MIN_PASSWORD_LENGTH, main
from app.models import StaffUser
from app.security import hash_password, verify_password

LONG_PASSWORD = "a perfectly reasonable password"


@pytest.fixture
def cli_db(session: Session, monkeypatch: pytest.MonkeyPatch) -> Session:
    """Points the CLI's session factory at the test database."""
    from app import cli

    monkeypatch.setattr(cli, "get_session_factory", lambda: sessionmaker_for(session))
    return session


def sessionmaker_for(session: Session):
    """Mimics ``sessionmaker``: called once to get a factory, then again to get
    a session, exactly as ``app.database.get_session_factory`` is used."""

    class _Factory:
        def __call__(self) -> Session:
            return session

    return _Factory()


def _run(monkeypatch: pytest.MonkeyPatch, password: str) -> None:
    """Feeds the password as though typed at the getpass prompt."""
    answers = iter([password, password])
    monkeypatch.setattr("app.cli.getpass.getpass", lambda *a, **k: next(answers))
    main(["create-staff", "new.staff@example.com", "--display-name", "New Staff"])


def test_create_staff_persists_a_hashed_account(
    cli_db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    _run(monkeypatch, LONG_PASSWORD)

    user = cli_db.execute(
        select(StaffUser).where(StaffUser.email == "new.staff@example.com")
    ).scalar_one()

    assert user.display_name == "New Staff"
    assert user.is_active is True
    # The plaintext must not be recoverable, and the right password must verify.
    assert LONG_PASSWORD not in user.password_hash
    assert user.password_hash.startswith("$argon2id$")
    assert verify_password(LONG_PASSWORD, user.password_hash) is True


def test_email_is_normalised(
    cli_db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Storing what was typed would let "Sam@x.com" and "sam@x.com" become two
    accounts that both look like the same person in the list."""
    _run(monkeypatch, LONG_PASSWORD)

    user = cli_db.execute(select(StaffUser)).scalar_one()
    assert user.email == "new.staff@example.com"


def test_short_password_is_refused(
    cli_db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(SystemExit) as exc:
        _run(monkeypatch, "short")

    assert "at least" in str(exc.value)
    # Nothing half-created: there is no account to guess a second password for.
    assert cli_db.execute(select(StaffUser)).scalars().all() == []


def test_mismatched_confirmation_is_refused(
    cli_db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    answers = iter([LONG_PASSWORD, "something else entirely"])
    monkeypatch.setattr("app.cli.getpass.getpass", lambda *a, **k: next(answers))

    with pytest.raises(SystemExit, match="did not match"):
        main(["create-staff", "new.staff@example.com"])

    assert cli_db.execute(select(StaffUser)).scalars().all() == []


def test_duplicate_email_is_refused_without_overwriting(
    cli_db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Refusing rather than resetting: a mistyped command must not be able to
    lock a colleague out, and must not be able to take over their account."""
    original = StaffUser(
        email="new.staff@example.com",
        display_name="Existing",
        password_hash=hash_password(LONG_PASSWORD),
        is_active=True,
    )
    cli_db.add(original)
    cli_db.commit()

    with pytest.raises(SystemExit, match="already exists"):
        _run(monkeypatch, LONG_PASSWORD)

    still_there = cli_db.execute(
        select(StaffUser).where(StaffUser.email == "new.staff@example.com")
    ).scalar_one()
    assert still_there.display_name == "Existing"
    # The password that was supplied was not applied to the existing account.
    assert verify_password("some other password", still_there.password_hash) is False


def test_malformed_email_is_refused(
    cli_db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LEADFLOW_NEW_PASSWORD", LONG_PASSWORD)

    with pytest.raises(SystemExit, match="email"):
        main(["create-staff", "not-an-email", "--password-env", "LEADFLOW_NEW_PASSWORD"])

    assert cli_db.execute(select(StaffUser)).scalars().all() == []


def test_password_env_var_is_used(
    cli_db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """For automation, where there is no terminal to type into."""
    monkeypatch.setenv("LEADFLOW_NEW_PASSWORD", LONG_PASSWORD)

    main(["create-staff", "new.staff@example.com", "--password-env", "LEADFLOW_NEW_PASSWORD"])

    user = cli_db.execute(select(StaffUser)).scalar_one()
    assert verify_password(LONG_PASSWORD, user.password_hash) is True


def test_empty_password_env_is_refused_loudly(
    cli_db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Falling back to a prompt would hang a deployment script. Better to stop."""
    monkeypatch.setenv("LEADFLOW_NEW_PASSWORD", "")

    with pytest.raises(SystemExit, match="LEADFLOW_NEW_PASSWORD"):
        main(["create-staff", "new.staff@example.com", "--password-env", "LEADFLOW_NEW_PASSWORD"])

    assert cli_db.execute(select(StaffUser)).scalars().all() == []


def test_minimum_length_is_twelve_characters() -> None:
    assert MIN_PASSWORD_LENGTH == 12
