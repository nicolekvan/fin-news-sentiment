"""Export the snapshot for the static site by calling the real API endpoints.

    python -m marketlens.jobs.export --out ../frontend/public/data

The site therefore shows exactly what the API returns. Exported news is limited to headline,
provider summary, source, time, link, label, explanation and evidence (no full article text).
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from marketlens.api.app import app

NEWS_PER_COMPANY = 150
NEWS_FEED = 1500
PAGE = 100  # API maximum page size


def _get(client: TestClient, path: str, **params):
    r = client.get(path, params=params)
    r.raise_for_status()
    return r.json()


def _news(client, total: int, **params) -> list[dict]:
    out: list[dict] = []
    while len(out) < total:
        page = _get(
            client, "/api/news", limit=min(PAGE, total - len(out)), offset=len(out), **params
        )
        out.extend(page)
        if len(page) < PAGE:
            break
    return out


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, separators=(",", ":"), default=str))


def run(out: Path) -> dict:
    app.state.limiter.enabled = False  # local export, not public traffic
    if out.exists():
        shutil.rmtree(out)
    with TestClient(app) as client:
        meta = _get(client, "/api/meta")
        companies = _get(client, "/api/companies")
        _write(out / "meta.json", meta)
        _write(out / "companies.json", companies)
        _write(out / "overview.json", _get(client, "/api/overview"))
        _write(out / "macro.json", _get(client, "/api/macro"))
        _write(out / "news.json", _news(client, NEWS_FEED))
        end = meta["prices_as_of"]
        for c in companies:
            t = c["ticker"]
            _write(
                out / "company" / f"{t}.json",
                {
                    "detail": _get(client, f"/api/companies/{t}"),
                    "prices": _get(client, f"/api/companies/{t}/prices", end=end),
                    "sentiment": _get(client, f"/api/companies/{t}/sentiment"),
                    "events": _get(client, f"/api/companies/{t}/events"),
                    "news": [] if c["is_benchmark"] else _news(client, NEWS_PER_COMPANY, ticker=t),
                },
            )
    size = sum(f.stat().st_size for f in out.rglob("*.json"))
    return {"files": len(list(out.rglob("*.json"))), "bytes": size}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    print(run(ap.parse_args().out))


if __name__ == "__main__":
    main()
