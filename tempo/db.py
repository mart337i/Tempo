import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from tempo.config import get_config


class Base(DeclarativeBase):
    """Inherit from this in your models: class User(Base): ..."""

    pass


_logger = logging.getLogger(__name__)


class Database:
    """Lightweight database access. Reads connection URL from config [database] url.
    No-op if url is not set — check `db.is_configured` before use.

    Usage:
        from tempo.db import db

        with db.cr as conn:                          # raw SQLAlchemy connection
            result = conn.execute(text("SELECT 1"))

        with db.session as s:                        # ORM session (SQLModel-ready)
            s.add(some_model)
            s.commit()
    """

    def __init__(self):
        url = get_config().get("database", "url")
        self._engine = create_engine(url) if url else None
        self._Session = sessionmaker(bind=self._engine) if self._engine else None
        if self._engine:
            _logger.info("Database engine created")

    @property
    def is_configured(self) -> bool:
        return self._engine is not None

    @property
    def cr(self):
        """New SQLAlchemy Connection. Use as context manager: `with db.cr as conn:`"""
        if not self._engine:
            raise RuntimeError(
                "Database not configured. Set [database] url in tempo.conf"
            )
        return self._engine.connect()

    @property
    def session(self):
        """New ORM Session. Use as context manager: `with db.session as s:`"""
        if not self._Session:
            raise RuntimeError(
                "Database not configured. Set [database] url in tempo.conf"
            )
        return self._Session()

    def create_all(self):
        """Create all tables registered on Base. Safe to call multiple times (IF NOT EXISTS)."""
        if not self._engine:
            raise RuntimeError(
                "Database not configured. Set [database] url in tempo.conf"
            )
        Base.metadata.create_all(self._engine)


db = Database()
