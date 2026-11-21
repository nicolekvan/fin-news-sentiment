"""Settings, read only from environment variables (or a local, gitignored .env).

Secrets are `SecretStr`, so they never appear in reprs, logs or tracebacks.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    demo_mode: bool = True
    universe_scope: Literal["dev", "full"] = "full"

    finnhub_api_key: SecretStr | None = None
    twelve_data_api_key: SecretStr | None = None
    alpha_vantage_api_key: SecretStr | None = None
    fred_api_key: SecretStr | None = None
    sec_edgar_user_agent: str | None = None

    anthropic_api_key: SecretStr | None = None
    claude_enabled: bool = False
    claude_model: str = "claude-opus-5-5"
    claude_daily_request_limit: int = Field(default=0, ge=0)

    database_url_readonly: SecretStr | None = None
    database_url_writer: SecretStr | None = None
    admin_api_token: SecretStr | None = None

    def secret_values(self) -> list[str]:
        """All configured secret values, for log redaction."""
        out = []
        for value in self.__dict__.values():
            if isinstance(value, SecretStr):
                raw = value.get_secret_value()
                if raw and raw != "proxy-injected":
                    out.append(raw)
        return out


@lru_cache
def get_settings() -> Settings:
    return Settings()
