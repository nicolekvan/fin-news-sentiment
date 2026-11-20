import logging

from marketlens.config import Settings
from marketlens.logging_utils import REDACTED, RedactingFilter, redact


def test_secrets_hidden_in_repr():
    s = Settings(_env_file=None, finnhub_api_key="abc123secretvalue")
    assert "abc123secretvalue" not in repr(s)
    assert "abc123secretvalue" not in str(s.model_dump())


def test_redact_known_secret_and_patterns():
    msg = "GET /news?token=zzz999 key sk-ant-api03-XYZ and abc123secretvalue"
    out = redact(msg, ["abc123secretvalue"])
    assert "zzz999" not in out and "sk-ant-api03-XYZ" not in out
    assert "abc123secretvalue" not in out
    assert out.count(REDACTED) == 3


def test_logging_filter_redacts_args(caplog):
    logger = logging.getLogger("t")
    logger.addFilter(RedactingFilter(["topsecret"]))
    with caplog.at_level(logging.INFO):
        logger.info("calling with %s", "topsecret")
    assert "topsecret" not in caplog.text and REDACTED in caplog.text


def test_claude_disabled_by_default(monkeypatch):
    for var in ("DEMO_MODE", "CLAUDE_ENABLED", "CLAUDE_DAILY_REQUEST_LIMIT"):
        monkeypatch.delenv(var, raising=False)
    s = Settings(_env_file=None)
    assert s.claude_enabled is False and s.claude_daily_request_limit == 0
    assert s.demo_mode is True
