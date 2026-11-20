# Sentiment methodology

MarketLens separates three things that are easy to conflate:

| Concept | Where it lives | Meaning |
|---|---|---|
| **Text sentiment** | `sentiment_predictions.p_positive/p_negative/p_neutral` | FinBERT's reading of the company-specific passage |
| **Business-impact label** | `sentiment_predictions.label` | bullish / bearish / neutral / insufficient_evidence for one company |
| **Realized returns** | computed from `stock_prices` (Model Performance page) | what the stock actually did afterwards |

A bullish label is **not** a prediction that the price will rise.

## Pipeline (`marketlens.jobs.news`)
1. **Normalize** – HTML entities/tags removed, whitespace collapsed, URLs canonicalized
   (tracking parameters and fragments dropped), timestamps converted to UTC.
2. **Deduplicate** – exact duplicates (same canonical URL) dropped; syndicated copies (same
   normalized headline within 72 h) kept but linked via `duplicate_of`.
3. **Link companies** – ticker forms (`NVDA`, `$NVDA`, `(NVDA)`) and aliases, case-sensitive on
   word boundaries. A company must be *named* in the headline or summary; a provider ticker tag
   alone is not enough. Named-entity recognition is **not** used in this version.
4. **Passages** – for each linked company, only the sentences that name it. This is how one
   article can be bullish for one company and bearish for another.
5. **FinBERT** (`ProsusAI/finbert`) scores each passage and each of its sentences, batched on CPU;
   identical texts (syndication) are scored once.
6. **Decision rules** (`marketlens.models.decision`, config stored in `model_versions`):
   - top probability < 0.60 or margin to runner-up < 0.15 → `insufficient_evidence`
   - otherwise positive → bullish, negative → bearish, neutral → neutral
   - directional label on a passage that also names another tracked company → `needs_review`
7. **Explanation** – a template stating FinBERT's probabilities plus up to two **verbatim**
   evidence sentences chosen by sentence-level scores. Nothing is generated or paraphrased, so
   nothing can be fabricated.
8. **Optional Claude review** (`marketlens.models.claude_review`, off by default): for ambiguous
   or multi-company cases, Claude returns a Pydantic-validated verdict. Article text is treated
   as untrusted, evidence quotes must be exact substrings of the passage, and a daily request cap
   is enforced in the database.

## Company-level aggregation (`agg-v1`, `marketlens.aggregate`)
Computed at 21:00 UTC each trading day using only news published **before** that time:
- exclude `insufficient_evidence` and `needs_review` predictions;
- collapse syndicated copies into one story;
- weight = relevance × confidence × 0.5^(age / 72 h), 14-day lookback;
- score = weighted mean of P(positive) − P(negative), in [−1, 1];
- fewer than 3 stories → `insufficient_evidence`; ≥ +0.15 bullish; ≤ −0.15 bearish; else neutral.

## Known limitations
- Finnhub summaries are short (median ~115 characters); full article text is not stored.
- FinBERT was trained on analyst-report sentences; headlines with sarcasm or questions are hard.
- Alias matching can miss indirect references ("the iPhone maker") and products.
