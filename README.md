# MarketLens AI

Classify financial news articles as **bullish**, **bearish** or **neutral** for
individual companies.

## Problem framing

The unit of prediction is an **(article, company) pair**, not an article. One
story can be bullish for one company and bearish for another
("Boeing wins contract over Lockheed Martin"). Every mention of the target
company is wrapped in `[TGT] … [/TGT]` markers so the model knows which one to
judge (`marketlens.text.targets.mark_target`).

## Status

| Phase | | |
|---|---|---|
| 0 | Repo, pinned deps, CI with secret scanning | ✅ |
| 1 | Schema, migrations, RLS, company universe, demo data | ✅ |
| 2 | Providers (Finnhub, Twelve Data, SEC EDGAR, FRED, demo) + one-time pull | ✅ |
| 3 | Technical indicators | ✅ |
| 4 | News pipeline + FinBERT + evidence explanations (+ optional Claude review) | ✅ |
| 5 | Company-level aggregation + FastAPI | ✅ |
| 6 | Next.js dashboard (static) + Playwright tests | ✅ |
| 7 | Evaluation + Model Performance page | ⏳ |
| 8 | Static export + Vercel deployment | ⏳ |

## Data format

`data/sample/*.jsonl`, one example per line:

```json
{"id": "s1", "published_at": "2024-01-03T13:00:00Z",
 "text": "Apple beats quarterly revenue estimates...",
 "ticker": "AAPL", "company": "Apple", "aliases": ["Apple Inc"],
 "label": "bullish"}
```

`data/sample/news_sample.jsonl` holds 10 toy examples for smoke tests only.

## Quickstart

Requires Python 3.11+ and PostgreSQL 16.

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"          # add ".[ml]" for FinBERT (torch + transformers)
cp ../.env.example ../.env       # fill in locally; never commit .env
```

Run the tests (database tests need a disposable database):

```bash
TEST_DATABASE_URL=postgresql+psycopg://localhost/marketlens_test pytest
```

Build the snapshot:

```bash
python -m marketlens.db.migrate up
python -m marketlens.jobs.seed                         # companies (add --demo for synthetic data)
python -m marketlens.jobs.pull --snapshot 2026-11-20   # prices, news, profiles, filings, macro
python -m marketlens.jobs.indicators
python -m marketlens.jobs.news --snapshot 2026-11-20   # FinBERT scoring
python -m marketlens.jobs.aggregate
uvicorn marketlens.api.app:app                          # API docs at /api/docs
```

### Dashboard

```bash
cd frontend
npm ci
npm run use:demo     # or: python -m marketlens.jobs.export --out ../frontend/public/data
npm run build        # static site in ./out
npx playwright test  # end-to-end tests against ./out
```

`frontend/demo-data/` is a fully synthetic snapshot (labelled DEMO) used by CI and demo mode.

## Documentation
- `docs/IMPLEMENTATION_PLAN.md` – architecture, costs, schema, security, acceptance criteria
- `docs/METHODOLOGY.md` – how labels, explanations and company scores are produced
- `docs/UNIVERSE_METHODOLOGY.md` – how companies are selected

> MarketLens AI is an educational portfolio project. Sentiment labels describe the tone of news
> coverage and are not investment advice or price predictions.
