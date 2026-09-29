import os

# Argon2id is tuned to be deliberately slow, which is the point in production
# and the opposite of what a test suite wants: at full cost the suite spends
# most of its wall clock hashing. These are set before any app import, because
# Settings reads the environment once at import time.
#
# Safe here precisely because app.config.validate only enforces the real costs
# in production, and the test environment is not production. A test that hashes
# with these parameters still exercises the real Argon2id code path, so a
# regression in hashing or verification still fails here.
os.environ.setdefault("ARGON2_TIME_COST", "1")
os.environ.setdefault("ARGON2_MEMORY_COST", "8192")
os.environ.setdefault("ARGON2_PARALLELISM", "1")

from collections.abc import Generator

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import get_db
from app.main import app
from app.models import Base, StaffUser
from app.security import hash_password

#: A real Argon2id hash, so the fixture exercises the actual verification path
#: rather than a stub. The password is not a credential for anything real.
STAFF_PASSWORD = "correct horse battery staple"

DEFAULT_TEST_DATABASE_URL = "sqlite+pysqlite:///:memory:"


def build_test_engine() -> Engine:
    url = os.getenv("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)
    if url.startswith("sqlite"):
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return create_engine(url, poolclass=StaticPool)


@pytest.fixture
def engine() -> Generator[Engine, None, None]:
    test_engine = build_test_engine()
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    yield test_engine
    Base.metadata.drop_all(test_engine)
    test_engine.dispose()


@pytest.fixture
def session(engine: Engine) -> Generator[Session, None, None]:
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    db = factory()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def staff_user(session: Session) -> StaffUser:
    """A signed-in-capable staff account.

    Created with the same hashing the application uses, so a broken hash or
    verification path fails these tests rather than passing them by accident.
    """
    user = StaffUser(
        email="staff@example.com",
        display_name="Sam Staff",
        password_hash=hash_password(STAFF_PASSWORD),
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def _build_client(
    session: Session, _client_class: type[TestClient] = TestClient
) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with _client_class(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


class StaffClient(TestClient):
    """A TestClient that behaves like the CRM frontend.

    The frontend's entire job with CSRF is to copy the `leadflow_csrf` cookie
    into the `X-CSRF-Token` header. Doing that once here, in the place that
    models the browser, is more faithful than repeating it in 130 business-rule
    tests — and it means a regression in real CSRF enforcement still fails
    tests, because the header genuinely has to be right to get through.
    """

    _STATE_CHANGING = {"POST", "PUT", "PATCH", "DELETE"}

    def request(self, method: str, url: str, **kwargs: object) -> httpx.Response:
        if method.upper() in self._STATE_CHANGING:
            token = self.cookies.get("leadflow_csrf")
            if token is not None:
                headers = dict(kwargs.get("headers") or {})
                headers.setdefault("X-CSRF-Token", token)
                kwargs["headers"] = headers
        return super().request(method, url, **kwargs)


def sign_in(client: TestClient, email: str, password: str) -> None:
    """Drives the real login flow, so the client holds genuine cookies.

    Tests therefore cover the CSRF bootstrap, the login exchange and the cookie
    handling rather than bypassing them.
    """
    client.get("/api/auth/session")
    token = client.cookies.get("leadflow_csrf")
    assert token is not None, "session probe did not mint a CSRF cookie"
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
        headers={"X-CSRF-Token": token},
    )
    assert response.status_code == 200, response.text


def csrf_headers(client: TestClient) -> dict[str, str]:
    """The header every state-changing staff request must carry.

    Reading it from the cookie the client already holds is exactly what the
    frontend does, so the tests exercise the real double-submit path.
    """
    token = client.cookies.get("leadflow_csrf")
    assert token is not None, "client is not signed in"
    return {"X-CSRF-Token": token}


@pytest.fixture
def public_client(session: Session) -> Generator[TestClient, None, None]:
    """An unauthenticated client, for the public website flows.

    Nothing here should be signed in. A customer submitting an enquiry has no
    session and never will.
    """
    yield from _build_client(session)


@pytest.fixture
def client(
    session: Session, staff_user: StaffUser
) -> Generator[TestClient, None, None]:
    """A signed-in staff client, for every CRM test.

    CRM tests are about business rules; authenticating each of them by hand
    would bury the behaviour under cookie plumbing. The authentication boundary
    itself is covered directly in test_auth.py, and the unauthenticated
    rejections in test_auth_protection.py.
    """
    gen = _build_client(session, StaffClient)
    test_client = next(gen)
    try:
        sign_in(test_client, staff_user.email, STAFF_PASSWORD)
        yield test_client
    finally:
        next(gen, None)
