# Company universe methodology

**Version:** `universe-v1` · Config: `config/universe.csv`

## Eligibility
1. Common stock or ADR listed on a US exchange (NYSE, Nasdaq).
2. Primary business in software, semiconductors, AI, cloud computing, digital advertising,
   e-commerce, cybersecurity or consumer technology.
3. Ranked by market capitalization (Finnhub company profile) on the snapshot date.

## One security per issuer
Each issuer appears once, keyed by its SEC CIK (enforced by a unique constraint on
`companies.cik`). For multi-class issuers the most liquid class is used — e.g. Alphabet is tracked
as **GOOGL** only, never GOOGL + GOOG. CIKs were verified against SEC EDGAR submissions data.

## Development set
Per the spec, development uses 10 companies (`dev_set=true`): NVDA, AAPL, MSFT, GOOGL, AMZN,
META, AVGO, AMD, ORCL, PLTR. Expansion to 50 follows the same rules.

## Benchmarks
QQQ (Nasdaq-100, primary) and SPY (S&P 500) are stored with `is_benchmark=true` and excluded from
rankings and sentiment.

## History and survivorship bias
Membership is recorded in `universe_membership` with `effective_from` / `effective_to`, the
market cap and rank used, and the `method_version`. Companies that leave the universe keep
their rows and data, so backtests can reconstruct the universe as of any past date.

## Aliases
Aliases are matched case-sensitively on word boundaries to limit false matches (e.g. "Meta" the
company vs. the word "meta"). Product names (iPhone, Azure) are not aliases: an article about a
product is only linked to the company if the company is also named or tagged by the provider.
