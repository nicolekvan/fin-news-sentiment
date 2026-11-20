"""Shared HTTP client: rate limiting, retries with exponential backoff, call counting.

Credentials are only ever sent in headers (never URLs), and headers are never logged.
"""

from __future__ import annotations

import logging
import threading
import time

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from marketlens.providers.base import ProviderError

log = logging.getLogger(__name__)
RETRY_STATUS = {429, 500, 502, 503, 504}


class RateLimiter:
    """Minimum spacing between calls (simple and predictable for per-minute quotas)."""

    def __init__(self, calls_per_minute: float):
        self.interval = 60.0 / calls_per_minute
        self._next = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            if now < self._next:
                time.sleep(self._next - now)
            self._next = max(now, self._next) + self.interval


class _Retryable(Exception):
    pass


def _is_retryable(exc: BaseException) -> bool:
    return isinstance(exc, (_Retryable, httpx.TransportError))


class ApiClient:
    def __init__(
        self,
        provider: str,
        base_url: str,
        calls_per_minute: float,
        headers: dict[str, str] | None = None,
        timeout: float = 30.0,
        max_attempts: int = 5,
        backoff_initial: float = 2.0,
        transport: httpx.BaseTransport | None = None,
    ):
        self.provider = provider
        self.calls = 0
        self.limiter = RateLimiter(calls_per_minute)
        self._client = httpx.Client(
            base_url=base_url, headers=headers or {}, timeout=timeout, transport=transport
        )
        self._max_attempts = max_attempts
        self._backoff = backoff_initial

    def get(self, path: str, params: dict | None = None) -> httpx.Response:
        @retry(
            retry=retry_if_exception(_is_retryable),
            wait=wait_exponential_jitter(multiplier=self._backoff, max=60, jitter=self._backoff),
            stop=stop_after_attempt(self._max_attempts),
            reraise=True,
        )
        def _do() -> httpx.Response:
            self.limiter.wait()
            self.calls += 1
            resp = self._client.get(path, params=params)
            if resp.status_code in RETRY_STATUS:
                log.warning("%s %s -> %s, retrying", self.provider, path, resp.status_code)
                raise _Retryable(f"{self.provider} HTTP {resp.status_code}")
            return resp

        try:
            resp = _do()
        except (_Retryable, httpx.TransportError) as exc:
            raise ProviderError(f"{self.provider} {path}: gave up after retries ({exc})") from None
        if resp.status_code >= 400:
            raise ProviderError(f"{self.provider} {path}: HTTP {resp.status_code}")
        return resp

    def close(self) -> None:
        self._client.close()
