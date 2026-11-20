# Project rules

## Secrets — non-negotiable
- NEVER commit, push, print, log, or publish any API key (Claude/Anthropic, Finnhub, etc.)
  to GitHub, a published artifact, or any public website.
- Keys are read only from environment variables (e.g. `ANTHROPIC_API_KEY`, `FINNHUB_API_KEY`)
  or a local `.env` that is gitignored. Never hardcode them, and never put them in configs,
  notebooks, sample data, tests, or screenshots.
- Before every commit, check the staged diff for anything that looks like a key.

## Project scope
- Universe: the **top 50 tech companies** by market cap, kept as a fixed CSV in the repo
  (refreshed quarterly).
- Every bullish/bearish call must link to its source article and include an explanation.
- The project is visual: Streamlit + Plotly dashboard (market treemap, company page with
  price chart and sentiment markers, news feed, model performance).
