# Project rules

## Secrets — non-negotiable
- NEVER commit, push, print, log, or publish any API key (Claude/Anthropic, Finnhub, etc.)
  to GitHub, a published artifact, or any public website.
- Keys are read only from environment variables (e.g. `ANTHROPIC_API_KEY`, `FINNHUB_API_KEY`)
  or a local `.env` that is gitignored. Never hardcode them, and never put them in configs,
  notebooks, sample data, tests, or screenshots.
- Before every commit, check the staged diff for anything that looks like a key.
