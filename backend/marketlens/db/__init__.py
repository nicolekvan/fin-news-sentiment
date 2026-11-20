"""Database access (SQLAlchemy Core)."""

from __future__ import annotations

from sqlalchemy import Engine, create_engine

from marketlens.config import get_settings


def get_engine(writer: bool = True, url: str | None = None) -> Engine:
    if url is None:
        s = get_settings()
        secret = s.database_url_writer if writer else s.database_url_readonly
        if secret is None:
            raise RuntimeError("database URL not configured (DATABASE_URL_WRITER / _READONLY)")
        url = secret.get_secret_value()
    # hide_parameters keeps bound values (which could include data) out of error messages
    return create_engine(url, hide_parameters=True, pool_pre_ping=True)
