"""Database connection and session management."""

import os
from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from .schema import Base

# Default database path
DEFAULT_DB_DIR = Path.home() / ".trackai"
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "trackai.db"

# Allow override via environment variable
DB_PATH = os.getenv("TRACKAI_DB_PATH", str(DEFAULT_DB_PATH))


def get_db_url() -> str:
    """Get the database URL."""
    return f"sqlite:///{DB_PATH}"


def init_db(db_path: str | None = None) -> None:
    """
    Initialize the database by creating all tables.

    Args:
        db_path: Optional custom database path. If not provided, uses default.
    """
    global DB_PATH
    if db_path:
        DB_PATH = db_path

    # Create directory if it doesn't exist
    db_dir = Path(DB_PATH).parent
    db_dir.mkdir(parents=True, exist_ok=True)

    # Create engine and tables
    engine = create_engine(
        get_db_url(),
        connect_args={"check_same_thread": False},  # SQLite specific
        echo=False,  # Set to True for SQL query logging
    )
    Base.metadata.create_all(bind=engine)


def get_engine():
    """Get the SQLAlchemy engine."""
    return create_engine(
        get_db_url(),
        connect_args={"check_same_thread": False},
        echo=False,
    )


# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=get_engine(),
)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI to get database sessions.

    Usage:
        @app.get("/...")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session() -> Session:
    """Get a standalone database session (for non-FastAPI usage)."""
    return SessionLocal()
