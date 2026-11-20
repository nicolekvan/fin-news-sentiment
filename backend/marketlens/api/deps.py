from __future__ import annotations

import hmac
from functools import lru_cache

from fastapi import Header, HTTPException
from sqlalchemy import Engine

from marketlens.config import get_settings
from marketlens.db import get_engine


@lru_cache
def read_engine() -> Engine:
    return get_engine(writer=False)


@lru_cache
def write_engine() -> Engine:
    return get_engine(writer=True)


def require_admin(authorization: str | None = Header(default=None)) -> None:
    token = get_settings().admin_api_token
    if token is None or not token.get_secret_value():
        raise HTTPException(status_code=404, detail="Not found")  # admin disabled
    expected = f"Bearer {token.get_secret_value()}"
    if authorization is None or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")
