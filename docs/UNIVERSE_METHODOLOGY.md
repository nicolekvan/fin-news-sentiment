# Company universe methodology

**Version:** `universe-v2` (snapshot 2026-11-20) · Config: `config/universe.csv`

## Eligibility
1. Common stock or ADR listed on a US exchange (NYSE, Nasdaq).
2. Primary business in technology: software, semiconductors and semiconductor equipment, AI,
   cloud computing, cybersecurity, digital advertising, e-commerce, consumer technology,
   IT hardware and networking, electronic components, and IT services.
3. Excluded as not primarily technology businesses, although often grouped with tech:
   Netflix and Spotify (entertainment media), Uber (transportation), Coinbase (financial
   services).

## Ranking
Companies are ranked by market capitalization in US dollars on the snapshot date, computed
the same way for every company:

> market cap = latest US-listed share price × shares outstanding ÷ ADR ratio

Prices and share counts come from Finnhub. The ADR ratio (ordinary shares per US-listed
share) is recorded per company in the config: TSM 5, BABA 8, PDD 4; 1 for ordinary US-listed
stock. Finnhub's own market-cap field was not used, because cross-checks showed its reporting
currency is inconsistent for some foreign issuers (for example, a figure labelled as yuan that
matches the US-dollar value).

The top 50 eligible companies form the universe. The next candidates were NetEase ($64B),
NXP ($59B), TE Connectivity ($58B) and Datadog ($57B). The Trade Desk, named in the project
brief, is eligible but ranked well outside the top 50 (about $7B) and so is not included.

## One security per issuer
Each issuer appears once, keyed by its SEC CIK (a unique constraint on `companies.cik`). CIKs
come from SEC's official ticker file. For multi-class issuers the most liquid class is used:
Alphabet is tracked as GOOGL only.

## Company matching in news
Aliases match case-sensitively on word boundaries. Tickers that are ordinary words or brands
(NOW, NET, APP, SHOP, CRM, ARM, MSI, MU, SNOW) only count in explicit ticker notation
(`$NOW`, `(NOW)`, `NYSE: NOW`) or when the company is named, so "NOW AVAILABLE" does not link
to ServiceNow. Product names (iPhone, Azure, Temu) are not aliases.

## Development set
Development and testing used 10 companies (`dev_set=true`): NVDA, AAPL, MSFT, GOOGL, AMZN, META,
AVGO, AMD, ORCL, PLTR. `UNIVERSE_SCOPE=dev` selects them; the synthetic demo snapshot uses them.

## Benchmarks
QQQ (Nasdaq-100, primary) and SPY (S&P 500), `is_benchmark=true`, excluded from rankings and
sentiment.

## History and survivorship bias
Membership is recorded in `universe_membership` with `effective_from` / `effective_to`, the
market cap and rank used, and the `method_version`. Companies that leave the universe keep their
data. Choosing companies by today's market cap still favours stocks that did well, which the
return analysis states.
