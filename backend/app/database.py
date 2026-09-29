import os
from collections.abc import Generator
from functools import lru_cache

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

load_dotenv()


class Base(DeclarativeBase):
    pass


def get_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Copy backend/.env.example to backend/.env "
            "and set DATABASE_URL before starting the API or running migrations."
        )
    return url


@lru_cache
def get_engine() -> Engine:
    # pool_pre_ping checks a pooled connection is still alive before handing it
    # out, and transparently replaces it if not.
    #
    # Serverless PostgreSQL, Neon included, closes connections that have been
    # idle, and can suspend compute entirely. Without this, the first request
    # after a quiet period fails on a connection the database had already
    # discarded, which presents as an intermittent 500 unrelated to the request.
    return create_engine(get_database_url(), pool_pre_ping=True)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()
