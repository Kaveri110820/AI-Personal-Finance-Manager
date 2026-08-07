"""SQLAlchemy-backed SQLite database setup.

Provides a session factory scoped to a database path, automatic table creation
and a session context manager for services to use.
"""

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from database.models import Base

DB_PATH = Path(os.environ.get("FINANCE_DB_PATH", Path(__file__).resolve().parent / "finance.db"))

_engines: dict[str, Engine] = {}
_sessionmakers: dict[str, sessionmaker] = {}


def _path_key(path: Path) -> str:
    return str(path.resolve())


def _get_engine(db_path: str | Path) -> Engine:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    key = _path_key(path)
    if key not in _engines:
        engine = create_engine(
            f"sqlite:///{path}",
            connect_args={"check_same_thread": False},
        )
        _wire_pragmas(engine)
        _engines[key] = engine
    return _engines[key]


def _get_sessionmaker(db_path: str | Path) -> sessionmaker:
    key = _path_key(Path(db_path))
    if key not in _sessionmakers:
        _sessionmakers[key] = sessionmaker(
            bind=_get_engine(db_path),
            expire_on_commit=False,
        )
    return _sessionmakers[key]


def _wire_pragmas(engine: Engine) -> None:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, connection_record):  # noqa: ARG001
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode = WAL")
            cursor.execute("PRAGMA foreign_keys = ON")
        finally:
            cursor.close()


@contextmanager
def session_scope(db_path: str | Path | None = None) -> Iterator[Session]:
    """Yield a bound Session, committing on success and rolling back on error."""
    session_factory = _get_sessionmaker(Path(db_path) if db_path else DB_PATH)
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(db_path: str | Path | None = None) -> None:
    """Create all tables if missing (idempotent)."""
    engine = _get_engine(Path(db_path) if db_path else DB_PATH)
    Base.metadata.create_all(engine)
