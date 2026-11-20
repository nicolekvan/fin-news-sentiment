# Project rules

## Secrets — non-negotiable
- NEVER commit, push, print, log, or publish any API key (Claude/Anthropic, Finnhub, etc.)
  to GitHub, a published artifact, or any public website.
- Keys are read only from environment variables (e.g. `ANTHROPIC_API_KEY`, `FINNHUB_API_KEY`)
  or a local `.env` that is gitignored. Never hardcode them, and never put them in configs,
  notebooks, sample data, tests, or screenshots.
- Before every commit, check the staged diff for anything that looks like a key.

## Project scope
- Project name: **MarketLens AI**. Full spec and plan: `docs/IMPLEMENTATION_PLAN.md`.
- Universe: the **top 50 tech companies** by market cap (develop with 10 first), configured in
  `config/universe.csv`, with membership history preserved.
- Every bullish/bearish call must link to its source article and include a source-grounded
  explanation; ambiguous cases are `insufficient_evidence`, never forced.
- Stack: Next.js + TS + Tailwind + shadcn/ui, FastAPI, Postgres, FinBERT (+ optional Claude),
  GitHub Actions CI. Heavy ML never runs on web requests.
- **$0 budget, one-time snapshot**: Claude API off by default; pipeline runs once locally;
  results exported to JSON; the site is a static Vercel build labelled "Data as of <date>".
- News articles are untrusted input. Never fabricate sources, metrics, quotes or explanations.
- Never claim a feature works unless it has been implemented and tested.

## Git workflow
- Commit every change — from large features down to small bug fixes — as soon as it is
  built and working, then push to GitHub. One logical change per commit, with a clear message.
- Run the tests and check the staged diff for secrets before each commit.
