# Architecture

## Components

| Component | Path | Role |
|---|---|---|
| Provider adapters | `backend/marketlens/providers/` | One `Protocol` per data domain (news, prices, profiles, filings, macro); Finnhub, Twelve Data, SEC EDGAR, FRED and a synthetic Demo adapter. Shared HTTP client with per-provider rate limiting, exponential backoff with jitter, call counting; keys only in headers. |
| Database | `supabase/migrations/` | Postgres schema with foreign keys, check constraints, unique keys, indexes; least-privilege `marketlens_reader` / `marketlens_writer` roles and row-level security on every table. Up/down migrations. |
| Jobs | `backend/marketlens/jobs/` | `seed`, `pull`, `indicators`, `news`, `aggregate`, `evaluate`, `export`, `demo_snapshot`. Each run is recorded in `ingestion_logs`. |
| News pipeline | `backend/marketlens/pipeline/` | Normalization (HTML, canonical URLs, UTC), deduplication (exact + syndicated), company linking, per-company passages, rule-based event types. |
| Models | `backend/marketlens/models/` | FinBERT batch inference; decision rules with abstention and verbatim evidence; optional Claude reviewer (Pydantic-validated, untrusted-input safe, daily cap). |
| Aggregation | `backend/marketlens/aggregate.py` | Versioned company-level score (`agg-v1`) computed per trading day without look-ahead. |
| Evaluation | `backend/marketlens/evaluation/` | Sampling for blind labelling, classification metrics with bootstrap CIs and baselines, forward-return analysis vs QQQ. |
| API | `backend/marketlens/api/` | FastAPI read API (validated params, rate limiting, generic errors) plus a token-protected admin endpoint. |
| Website | `frontend/` | Next.js static export built from a JSON snapshot of the API; no server, no secrets at runtime. |
| Labeller | `tools/labeler/` | Private labelling page; labels exported as ids + labels only. |

## Data flow

1. **Pull** (`jobs/pull`): company profiles → ranked universe membership; daily OHLCV (≈460 days
   so 200-day averages are warmed up); 90 days of company news fetched one day at a time and
   cached raw on disk; SEC filings; FRED series.
2. **Indicators** (`jobs/indicators`): SMA/EMA, RSI, MACD, Bollinger, ATR with the `ta` library.
3. **News** (`jobs/news`): normalize → dedupe → link → passages → FinBERT on unique texts →
   decision rules → `sentiment_predictions` (one row per article × company × model version).
4. **Aggregate** (`jobs/aggregate`): daily company scores into `aggregated_sentiment`.
5. **Evaluate** (`jobs/evaluate`): forward returns and, with human labels, classification
   metrics into `model_evaluations`.
6. **Export** (`jobs/export`): calls the real API endpoints and writes their JSON responses to
   `frontend/snapshots/<name>/`, so the site shows exactly what the API returns.
7. **Build** (`npm run build`): copies the chosen snapshot into `public/data` and renders every
   page statically (company pages via `generateStaticParams`).

## Key decisions

- **Static site from a snapshot.** A $0 budget and a portfolio audience favour a site that never
  sleeps, never pauses and has nothing to attack. Live operation (scheduled jobs, hosted
  Postgres, deployed API) is documented as the production path.
- **ML outside the request path.** FinBERT needs more memory than free web tiers offer; it runs
  in jobs and only its results are served.
- **Per-company passages.** Linking by name and scoring only the sentences that name a company
  lets one article carry different labels for different companies.
- **Abstain instead of guessing.** Explicit `insufficient_evidence` and `needs_review` states,
  excluded from company scores.
- **Verbatim evidence.** Template explanations plus quoted sentences make fabricated
  explanations impossible; the optional Claude path rejects any quote not found in the source.
- **Reproducibility.** Model versions and their configuration are stored with every prediction;
  the evaluation sample is deterministic; labels are committed as ids only.

## Testing

- Backend: 79 pytest tests — providers with mocked transports (including "key never leaks"),
  migrations up/down, constraints, RLS and the read-only role, indicators against reference
  calculations, pipeline and decision rules, Claude reviewer with a fake client, aggregation
  without look-ahead, forward returns, metrics, API endpoints under the read-only role, rate
  limiting and admin auth.
- Frontend: 13 Playwright tests on the static build — every page, filters, empty and error
  states, chart toggles, theme, phone layout, and a scan of the built files for secrets.
- CI (GitHub Actions): gitleaks over the full history, ruff, pytest with a Postgres service,
  TypeScript check, demo build and Playwright.
