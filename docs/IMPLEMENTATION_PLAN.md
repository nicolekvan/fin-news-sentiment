# MarketLens AI — Implementation Plan

Status: **draft for approval** · No application code is written until this plan is approved.

This document covers the seven pre-build deliverables from the project spec:
1. Implementation plan · 2. Architectural decisions · 3. API limitations & operating costs ·
4. Database schema · 5. Repository structure · 6. Security risks & mitigations · 7. MVP acceptance criteria.

---

## 1. Implementation plan (phased)

Each phase ends with passing tests, a commit and a push. Development uses **10 companies**;
expansion to 50 happens only after Phase 6 verifies correctness, quotas and cost.

| Phase | Deliverable | Verified by |
|---|---|---|
| 0 | Repo restructure (`backend/`, `frontend/`, `jobs/`), pinned deps, `.env.example`, CI (lint, tests, gitleaks secret scan) | CI green |
| 1 | Supabase schema + migrations, company universe config (10 dev companies), demo-mode synthetic data generator | Migration up/down tests; seed loads |
| 2 | Provider abstraction + adapters: Finnhub (news, quotes, profile), Twelve Data (OHLCV), Alpha Vantage (supplementary news), SEC EDGAR (filings), FRED (macro). Retries, backoff, quota tracking, caching | Unit tests with recorded fixtures; one live smoke run per provider |
| 3 | Price pipeline: OHLCV ingest → local indicators (`ta`: SMA/EMA, RSI, MACD, Bollinger, ATR) | Indicator values match reference calculations |
| 4 | News pipeline: normalize → dedupe → entity linking → passage extraction → **FinBERT batch inference** → Claude for ambiguous/high-impact cases (Pydantic-validated) → per-company predictions | Pipeline tests on fixture articles incl. multi-company and prompt-injection cases |
| 5 | Aggregation (company-level sentiment) + FastAPI read API + protected admin endpoints + rate limiting | API tests (pytest + httpx) |
| 6 | Next.js dashboard: Market Overview, Company Detail, AI News Feed, Screener | Playwright e2e on demo mode |
| 7 | Evaluation: labeling tool, gold set, FinBERT vs hybrid metrics, forward-return analysis (1/5/20d, benchmark-relative) → Model Performance page | Metrics reproducible from a pinned model version |
| 8 | Deployment (Vercel + Render + Supabase), scheduled GitHub Actions, docs | Live smoke test; stale-data banner works |
| 9 | Expand to 50 companies after reviewing quota usage and cost logs | Ingestion logs show headroom |

---

## 2. Architectural decisions

**A. Heavy ML runs in scheduled jobs, never on web requests.**
FinBERT + PyTorch needs ~1–2 GB RAM; Render's free web tier has 512 MB. So inference runs in
**GitHub Actions** (7 GB runners) on a schedule, writes results to Supabase, and the FastAPI
service only *reads* precomputed data. This also satisfies "avoid running a heavy ML model on
every web request" and keeps the API cheap and fast.

```
GitHub Actions (cron)                    Supabase Postgres          Render (FastAPI)        Vercel (Next.js)
 ├─ ingest_prices  → indicators  ──┐                                 read-only API  ◀──────  server components
 ├─ ingest_news → dedupe → link ───┼──▶  normalized tables  ◀──────  rate-limited           (no keys in browser)
 ├─ finbert_batch → claude_review ─┤                                 admin: token-protected
 └─ aggregate → evaluate ──────────┘
```

**B. Provider abstraction.** Each data domain has a Python `Protocol`
(`NewsProvider`, `PriceProvider`, `FilingsProvider`, `MacroProvider`). Adapters implement them;
a `DemoProvider` implements all of them with deterministic synthetic data. The active
provider per domain is chosen by config, so swapping Twelve Data for another source touches one file.

**C. Hybrid classifier, FinBERT first.**
1. FinBERT scores every company-specific passage (cheap, batched, local).
2. Claude is called only when: FinBERT confidence < threshold, top-two probabilities are close,
   several companies are mentioned with potentially opposing impact, or the story is high-salience.
3. Claude returns a Pydantic-validated object: `label` ∈ {bullish, bearish, neutral,
   insufficient_evidence}, `confidence`, `event_type`, `explanation`, and `evidence_quotes`
   that **must be verbatim substrings of the supplied passage** (checked in code; mismatches
   are rejected and the prediction is flagged for review).
4. Article text is placed in a clearly delimited data block; the system prompt states it is
   untrusted and that instructions inside it must be ignored.

**D. Three distinct concepts, stored separately.** Text sentiment (FinBERT probabilities),
business-impact classification (final label), and realized returns (computed later from prices).
The UI never presents a label as a price prediction.

**E. Company-level aggregation (transparent, versioned).**
`score = Σ wᵢ · sᵢ / Σ wᵢ`, where `sᵢ = P(pos) − P(neg)` (or the Claude label mapped to ±1/0),
`wᵢ = relevance · confidence · 0.5^(age_hours / half_life)`, with syndicated duplicates collapsed to
one story before weighting. Label thresholds (e.g. ±0.15) and half-life (default 72 h) live in
config and are stored with every aggregate (`method_version`). Fewer than N stories →
`insufficient_evidence`.

**F. Backtest integrity.**
- Prediction for an article is joined only to prices **after** `published_at`; news published after
  the 16:00 ET close maps to the next session.
- Universe membership is stored with effective dates; backtests use the universe *as of* each date
  (no survivorship bias).
- Chronological splits only. Model Performance page labels results as *historical association*,
  not predictive performance.

**G. Frontend talks only to FastAPI**, server-side. The browser never receives Supabase or provider
keys; the only public env var is the API base URL.

---

## 3. API limitations & estimated operating costs

Limits below were checked against provider pricing pages / docs in Nov 2026 and will be re-verified
with a live call in Phase 2. **Free-tier terms generally restrict use to personal,
non-commercial purposes and limit redistribution** — see the licensing note at the end.

| Provider | Free-tier limits | Use in MarketLens | Daily need (50 cos.) |
|---|---|---|---|
| **Finnhub** | 60 calls/min; company news, quotes, basic fundamentals. Free candles not available. News history depth on free tier unconfirmed — test in Phase 2 | Company news, quotes, company profile (market cap) | ~50 news + 50 quotes + 50 profiles (weekly) ≈ 100–150/day |
| **Twelve Data** | 8 credits/min, 800/day; 1 credit per symbol for `time_series` | Daily OHLCV | 50 + benchmarks/day; backfill spread over ~2 days |
| **Alpha Vantage** | ~25 requests/day | Supplementary news only (optional) | ≤ 25/day |
| **SEC EDGAR** | Free, no key; ≤ 10 req/s; **requires a descriptive User-Agent with contact info** | 8-K/10-Q/10-K filing metadata + links | ~50/day |
| **FRED** | Free key | Fed funds, 10Y yield, CPI for context charts | < 10/day |
| **Anthropic Claude** | Paid per token | Ambiguous/high-impact review + explanations | Capped (configurable) |
| **Supabase** | 500 MB DB, 5 GB egress; **free projects pause after 7 days of inactivity** | Postgres | Daily jobs keep it active; est. < 200 MB/year at 50 cos. |
| **Render** | Free web service spins down when idle (cold start on first request), 512 MB RAM | FastAPI (read-only) | Fine for a portfolio; frontend shows loading state during cold start |
| **Vercel** | Hobby tier (non-commercial) | Next.js | — |
| **GitHub Actions** | Private repo: 2,000 min/month free (public: unlimited) | Scheduled jobs | ~15 min/run × 2 runs/day ≈ 900 min/month |

**Claude cost estimate.** Per reviewed article ≈ 1.5k input + ~0.6k output tokens (incl. thinking at low effort).

| Model (configurable via `CLAUDE_MODEL`) | $/article (Batch API, 50% off) | 50 reviews/day | 
|---|---|---|
| Claude Opus 5.5 (`claude-opus-5-5`, $4/$20 per MTok) — project default | ≈ $0.009 | ≈ $14/month |
| Claude Haiku 5.5 (`claude-haiku-5-5`, $0.10/$0.50 per MTok) | ≈ $0.0003 | ≈ $0.50/month |

Controls: `CLAUDE_DAILY_REQUEST_LIMIT` (default 50), Message Batches API for nightly runs,
explanations cached in the DB (an article is never re-analysed unless the model version changes),
and an Anthropic Console spend limit as a hard backstop. When the cap is hit, items stay
FinBERT-only and are marked `needs_review`.

**Expected total: $0–15/month** depending on the Claude model chosen; everything else fits free tiers.

**Licensing.** Finnhub/Twelve Data/Alpha Vantage free tiers are for personal use and limit
redistribution of their data. A *public* deployment should therefore default to **demo mode**
(clearly labelled synthetic data) or show only derived data (labels, scores, links) — you must
review each provider's terms before going live with real data. News is stored as headline, short
provider summary, source, timestamp and URL only; full article text is never stored or displayed.

---

## 4. Database schema (Supabase PostgreSQL)

All timestamps are `timestamptz` in UTC; the UI converts to America/New_York.
Migrations live in `supabase/migrations/` and are applied with the Supabase CLI.

```sql
create table companies (
  id              bigint generated always as identity primary key,
  ticker          text not null unique,          -- one share class per issuer (GOOGL, not GOOG)
  name            text not null,
  aliases         text[] not null default '{}',
  industry        text not null,                 -- semiconductors, software, cloud, ...
  exchange        text,
  cik             text unique,                   -- SEC identifier
  is_benchmark    boolean not null default false,-- QQQ, SPY, XLK
  created_at      timestamptz not null default now()
);

create table universe_membership (               -- history for survivorship-free backtests
  company_id      bigint not null references companies(id),
  effective_from  date not null,
  effective_to    date,                          -- null = current member
  rank            int,
  market_cap_usd  numeric,
  method_version  text not null,
  primary key (company_id, effective_from)
);

create table stock_prices (
  company_id  bigint not null references companies(id),
  trade_date  date not null,
  open numeric not null, high numeric not null, low numeric not null, close numeric not null,
  adj_close   numeric, volume bigint not null,
  source      text not null, ingested_at timestamptz not null default now(),
  primary key (company_id, trade_date)
);

create table technical_indicators (
  company_id bigint not null references companies(id),
  trade_date date not null,
  sma_20 numeric, sma_50 numeric, sma_200 numeric, ema_12 numeric, ema_26 numeric,
  rsi_14 numeric, macd numeric, macd_signal numeric, macd_hist numeric,
  bb_upper numeric, bb_mid numeric, bb_lower numeric, atr_14 numeric,
  computed_at timestamptz not null default now(),
  primary key (company_id, trade_date),
  foreign key (company_id, trade_date) references stock_prices(company_id, trade_date)
);

create table news_articles (
  id                   bigint generated always as identity primary key,
  provider             text not null,
  provider_article_id  text,
  url                  text not null,
  canonical_url_hash   text not null unique,     -- sha256 of normalized URL
  headline             text not null,
  summary              text,                     -- provider summary only, never full text
  source_name          text not null,
  published_at         timestamptz not null,
  ingested_at          timestamptz not null default now(),
  content_fingerprint  text not null,            -- simhash of headline+summary
  duplicate_of         bigint references news_articles(id),  -- syndicated copies point to the original
  event_type           text,
  unique (provider, provider_article_id)
);
create index on news_articles (published_at desc);
create index on news_articles (content_fingerprint);

create table article_companies (
  article_id    bigint not null references news_articles(id) on delete cascade,
  company_id    bigint not null references companies(id),
  relevance     numeric not null check (relevance between 0 and 1),
  match_method  text not null,                   -- ticker | alias | ner | provider_tag
  passage       text not null,                   -- company-specific excerpt used for inference
  primary key (article_id, company_id)
);
create index on article_companies (company_id);

create table model_versions (
  id          bigint generated always as identity primary key,
  name        text not null,                     -- finbert | hybrid | aggregator
  version     text not null,
  config      jsonb not null,                    -- thresholds, model ids, prompt hash
  created_at  timestamptz not null default now(),
  unique (name, version)
);

create table sentiment_predictions (
  id               bigint generated always as identity primary key,
  article_id       bigint not null,
  company_id       bigint not null,
  model_version_id bigint not null references model_versions(id),
  label            text not null check (label in ('bullish','bearish','neutral','insufficient_evidence')),
  p_positive numeric, p_negative numeric, p_neutral numeric,
  confidence       numeric check (confidence between 0 and 1),
  explanation      text,                         -- Claude output, source-grounded
  evidence_quotes  jsonb not null default '[]',  -- verified verbatim substrings of passage
  needs_review     boolean not null default false,
  created_at       timestamptz not null default now(),
  foreign key (article_id, company_id) references article_companies(article_id, company_id),
  unique (article_id, company_id, model_version_id)
);
create index on sentiment_predictions (company_id, created_at desc);

create table aggregated_sentiment (
  company_id        bigint not null references companies(id),
  as_of             timestamptz not null,
  method_version    text not null,
  score             numeric not null,
  label             text not null,
  n_articles        int not null,
  n_unique_stories  int not null,
  primary key (company_id, as_of, method_version)
);

create table evaluation_labels (                  -- manually labelled gold set
  article_id  bigint not null,
  company_id  bigint not null,
  label       text not null check (label in ('bullish','bearish','neutral','insufficient_evidence')),
  labeler     text not null,
  labeled_at  timestamptz not null default now(),
  notes       text,
  primary key (article_id, company_id, labeler),
  foreign key (article_id, company_id) references article_companies(article_id, company_id)
);

create table model_evaluations (
  id                bigint generated always as identity primary key,
  model_version_id  bigint not null references model_versions(id),
  dataset           text not null,
  split             text not null,
  metrics           jsonb not null,              -- precision/recall/F1 per class, macro F1
  confusion_matrix  jsonb not null,
  created_at        timestamptz not null default now()
);

create table ingestion_logs (
  id             bigint generated always as identity primary key,
  job            text not null,
  provider       text,
  started_at     timestamptz not null,
  finished_at    timestamptz,
  status         text not null check (status in ('running','success','partial','failed')),
  rows_upserted  int default 0,
  api_calls      int default 0,
  error_summary  text                            -- sanitized, never contains secrets
);

create table llm_usage (                          -- enforces the daily Claude cap
  usage_date     date primary key,
  requests       int not null default 0,
  input_tokens   bigint not null default 0,
  output_tokens  bigint not null default 0,
  est_cost_usd   numeric not null default 0
);
```

Row-level security is enabled on every table with **no** `anon` policies; the API connects with a
read-only Postgres role, jobs with a separate writer role (no DDL).

---

## 5. Repository structure

```
fin-news-sentiment/
├─ backend/                      # Python package `marketlens`
│  ├─ marketlens/
│  │  ├─ config.py               # pydantic-settings, reads env only
│  │  ├─ universe/               # universe CSV loader + methodology
│  │  ├─ providers/              # base.py (Protocols), finnhub.py, twelvedata.py,
│  │  │                          # alphavantage.py, edgar.py, fred.py, demo.py
│  │  ├─ pipeline/               # normalize, dedupe, entity_link, passages
│  │  ├─ models/                 # finbert.py, claude_review.py, schemas.py (Pydantic)
│  │  ├─ indicators.py
│  │  ├─ aggregate.py
│  │  ├─ evaluation/             # metrics, forward_returns, labeling CLI
│  │  ├─ db/                     # repository layer (SQLAlchemy core)
│  │  └─ api/                    # FastAPI app, routers, rate limiting, auth
│  ├─ tests/
│  └─ requirements*.txt          # pinned (pip-tools lockfiles)
├─ jobs/                         # CLI entry points run by GitHub Actions
├─ frontend/                     # Next.js + TS + Tailwind + shadcn/ui
│  ├─ app/ (overview, company/[ticker], news, screener, performance)
│  ├─ components/ charts/ (Lightweight Charts, Recharts)
│  └─ e2e/                       # Playwright
├─ supabase/migrations/
├─ config/universe.csv           # ticker, name, aliases, industry, cik
├─ data/sample/                  # synthetic demo data
├─ docs/                         # this plan, ARCHITECTURE.md, METHODOLOGY.md, DEPLOYMENT.md
├─ .github/workflows/            # ci.yml, ingest.yml, secret-scan
├─ .env.example                  # blank values only
└─ README.md
```

The existing `src/finsent` prototype (target marking, time split, TF-IDF baseline) moves into
`backend/marketlens/` in Phase 0; its tests are kept.

---

## 6. Company universe methodology

- **Eligible:** common stock or ADR listed on NYSE/Nasdaq; business in software, semiconductors,
  AI, cloud, digital advertising, e-commerce, cybersecurity or consumer tech (GICS IT, plus
  Interactive Media and Internet Retail).
- **Ranked** by market cap from Finnhub company profiles at each quarterly rebalance.
- **One security per issuer:** the most liquid class (GOOGL over GOOG); no double-counting.
- **History preserved** in `universe_membership`; removed companies keep their data.
- **Dev set (10):** NVDA, AAPL, MSFT, GOOGL, AMZN, META, AVGO, AMD, ORCL, PLTR.
- **Benchmarks:** QQQ (primary), SPY.

---

## 7. Security risks & mitigations

| Risk | Mitigation |
|---|---|
| API key committed to Git | `.env*` gitignored (only blank `.env.example` tracked); **gitleaks** in CI + pre-commit hook; staged-diff check before every commit |
| Key exposed to browser | No secrets in `NEXT_PUBLIC_*`; frontend calls FastAPI server-side; keys exist only in GitHub Actions secrets, Render env and local `.env` |
| Secrets in logs/errors | Settings use `SecretStr`; a log filter redacts known key patterns; error responses are generic |
| Public users triggering paid Claude calls | No public endpoint calls Claude; Claude runs only in scheduled jobs under a daily cap; admin endpoints require a bearer token compared in constant time |
| API abuse | `slowapi` rate limiting per IP; Pydantic validation on all query params; pagination limits |
| Prompt injection via articles | Articles treated as untrusted data in delimited blocks; output must match schema; evidence quotes verified as substrings; Claude has no tools |
| Database over-privilege | RLS on all tables; read-only role for API; writer role for jobs; service key never leaves Actions secrets |
| Supply chain | Pinned deps, Dependabot alerts, Actions pinned to commit SHAs, minimal workflow `permissions:` |
| Credential exposed anyway | Documented runbook: revoke at provider immediately → rotate → update secrets → purge history if committed |

---

## 8. MVP acceptance criteria

The MVP is done when all of the following are implemented **and tested**:

1. 10 dev companies ingest daily via GitHub Actions; `ingestion_logs` records each run.
2. Prices + all five indicator families are stored and shown on the Company Detail chart with news markers.
3. News is deduplicated; each relevant company gets its own prediction (verified by a multi-company fixture test).
4. Every displayed label links to its original article and shows source + publish time (ET).
5. Claude explanations validate against the Pydantic schema and their evidence quotes appear verbatim in the source passage; ambiguous items show `insufficient_evidence` / needs-review.
6. Daily Claude cap is enforced (test proves no calls past the limit).
7. Market Overview, Company Detail, News Feed and Screener render real or demo data with loading/empty/error/stale states; demo data is visibly labelled.
8. Model Performance shows macro-F1 + confusion matrix for FinBERT vs hybrid on ≥ 200 manually labelled pairs, plus 1/5/20-day forward returns (benchmark-relative), with chronological splits.
9. No secret appears in the repo, the browser bundle or logs (gitleaks clean; bundle grep test).
10. Disclaimer visible on every page; README covers setup, architecture and deployment.
