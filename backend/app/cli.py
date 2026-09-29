"""Administrative commands.

    python -m app.cli create-staff

The first staff account cannot come from a migration, an environment variable
read at startup, or a signup page: a migration would bake a credential hash
into a file that lives in git history forever, and startup creation is an
implicit write on every boot. An explicit command is auditable and leaves nothing
behind in the repository.

The password is read with getpass by default so it never reaches shell history,
process arguments (and therefore `ps`), or logs. An environment variable is
supported only for automation, and is opt-in per invocation.
"""

import argparse
import getpass
import os
import sys

from sqlalchemy import select

from app.database import get_session_factory
from app.models import StaffUser
from app.security import hash_password, normalise_email

#: Argon2id is deliberately slow, so anything shorter than this is not worth
#: hashing or storing.
MIN_PASSWORD_LENGTH = 12


def _prompt_password(use_env_var: str | None) -> str:
    if use_env_var:
        password = os.getenv(use_env_var, "")
        if not password:
            sys.exit(
                f"Environment variable {use_env_var} is set but empty. "
                "Unset it to be prompted securely instead."
            )
        return password

    # Prompt twice, so a typo is caught before it becomes a hash nobody can undo.
    password = getpass.getpass("Password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if password != confirmation:
        sys.exit("Passwords did not match.")
    return password


def create_staff(email: str, display_name: str | None, password_env: str | None) -> int:
    password = _prompt_password(password_env)

    if len(password) < MIN_PASSWORD_LENGTH:
        sys.exit(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters. "
            "It is stored as an Argon2id hash and cannot be recovered."
        )

    normalised = normalise_email(email)
    if "@" not in normalised or normalised.startswith("@") or normalised.endswith("@"):
        sys.exit(f"{email!r} does not look like an email address.")

    with get_session_factory()() as db:
        existing = db.execute(
            select(StaffUser).where(StaffUser.email == normalised)
        ).scalar_one_or_none()
        if existing is not None:
            # Refuse rather than reset: silently overwriting a password would let
            # a mistyped command lock a colleague out.
            sys.exit(f"A staff account already exists for {normalised}.")

        db.add(
            StaffUser(
                email=normalised,
                display_name=(display_name or None),
                password_hash=hash_password(password),
                is_active=True,
            )
        )
        db.commit()

    print(f"Created staff account {normalised}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser(
        "create-staff", help="Create a staff account for the CRM."
    )
    create.add_argument("email", help="Staff login email address.")
    create.add_argument(
        "--display-name",
        default=None,
        help="Name shown in the CRM while signed in.",
    )
    create.add_argument(
        "--password-env",
        default=None,
        metavar="VAR",
        help=(
            "Read the password from this environment variable instead of "
            "prompting. For automation only; the password then appears in the "
            "process environment."
        ),
    )

    args = parser.parse_args(argv)

    if args.command == "create-staff":
        return create_staff(args.email, args.display_name, args.password_env)

    parser.error(f"Unknown command {args.command!r}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
