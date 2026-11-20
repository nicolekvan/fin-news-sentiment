# fin-news-sentiment

Classify financial news articles as **bullish**, **bearish** or **neutral** for
individual companies.

## Problem framing

The unit of prediction is an **(article, company) pair**, not an article. One
story can be bullish for one company and bearish for another
("Boeing wins contract over Lockheed Martin"). Every mention of the target
company is wrapped in `[TGT] … [/TGT]` markers so the model knows which one to
judge (`finsent.data.mark_target`).

## Roadmap

1. **Baseline** – TF-IDF + logistic regression (`finsent.baseline`). ✅ scaffolded
2. **Data** – assemble labelled (article, company) pairs. Candidate sources:
   - SEntFiN – entity-level sentiment on financial headlines (closest fit)
   - FiQA-2018 Task 1 – aspect/entity sentiment on news and microblogs
   - Financial PhraseBank – sentence-level, useful for pre-training
   - Weak labels from market reaction: abnormal return of the ticker in a
     window after `published_at`, bucketed into the three classes
3. **Transformer model** – fine-tune FinBERT / DeBERTa with the target markers
   added as special tokens; long articles chunked around target mentions.
4. **Evaluation** – macro-F1 on a *time-based* split (never random: news is
   autocorrelated), plus a check of whether predictions relate to subsequent
   returns.
5. **Serving** – a `predict(text, company)` API / CLI.

## Data format

`data/*.jsonl`, one example per line:

```json
{"id": "s1", "published_at": "2024-01-03T13:00:00Z",
 "text": "Apple beats quarterly revenue estimates...",
 "ticker": "AAPL", "company": "Apple", "aliases": ["Apple Inc"],
 "label": "bullish"}
```

`data/sample.jsonl` holds 10 toy examples for smoke tests only.

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
python -m finsent.baseline data/sample.jsonl
```
