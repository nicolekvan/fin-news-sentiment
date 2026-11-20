"""News pipeline: cached raw news -> normalized, deduplicated, linked, scored predictions.

python -m marketlens.jobs.news --snapshot 2026-11-20
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime

from sqlalchemy import text

from marketlens.db import get_engine
from marketlens.db.repository import log_finish, log_start
from marketlens.jobs.pull import CACHE_DIR
from marketlens.logging_utils import configure_logging
from marketlens.models.decision import DECISION_CONFIG, decide
from marketlens.pipeline.dedupe import Article, dedupe
from marketlens.pipeline.entities import company_pattern, link_article, split_sentences
from marketlens.pipeline.events import classify_event
from marketlens.pipeline.normalize import clean_text, headline_fingerprint, to_utc, url_hash
from marketlens.universe import load_universe

log = logging.getLogger("marketlens.news")
MODEL_NAME, MODEL_VERSION = "finbert-evidence", "v1"


def load_raw(snapshot) -> list[dict]:
    rows = {}
    for path in sorted(CACHE_DIR.glob(f"news_*_{snapshot.isoformat()}.jsonl")):
        for line in open(path, encoding="utf-8"):
            r = json.loads(line)
            rows[(r["provider"], r["provider_article_id"])] = r  # same story in several feeds
    return list(rows.values())


def run(snapshot, engine=None, model=None, raw: list[dict] | None = None) -> dict:
    engine = engine or get_engine()
    raw = load_raw(snapshot) if raw is None else raw
    companies = [c for c in load_universe(dev_only=True) if not c.is_benchmark]
    patterns = {c.ticker: company_pattern(c) for c in companies}
    names = {c.ticker: c.aliases[0] if c.aliases else c.name for c in companies}

    # 1. normalize
    items = {}
    for r in raw:
        headline, summary = clean_text(r["headline"]), clean_text(r["summary"])
        if not headline:
            continue
        key = url_hash(r["url"])
        if key in items:  # keep the first copy; later feeds may carry a truncated summary
            continue
        items[key] = {
            **r,
            "headline": headline,
            "summary": summary,
            "key": key,
            "fingerprint": headline_fingerprint(headline),
            "published_at": to_utc(datetime.fromisoformat(r["published_at"])),
        }
    # 2. dedupe
    kept = dedupe([Article(k, v["fingerprint"], v["published_at"]) for k, v in items.items()])
    dup_of = {a.key: a.duplicate_of for a in kept}
    # 3. link + passages
    links = {}
    for a in kept:
        it = items[a.key]
        found = link_article(it["headline"], it["summary"], companies, patterns)
        if found:
            links[a.key] = found
    keys = [k for k in dup_of if k in links]  # store only articles about a tracked company
    log.info(
        "raw=%d unique=%d linked=%d links=%d",
        len(raw),
        len(kept),
        len(keys),
        sum(len(links[k]) for k in keys),
    )

    # 4. FinBERT on unique passages and sentences (syndicated copies scored once)
    if model is None:
        from marketlens.models.finbert import FinBert

        model = FinBert()
    texts = set()
    for k in keys:
        for ln in links[k]:
            texts.add(ln.passage)
            texts.update(split_sentences(ln.passage))
    texts = sorted(texts)
    log.info("scoring %d unique texts", len(texts))
    probs = dict(zip(texts, model.predict(texts), strict=True))

    with engine.begin() as conn:
        log_id = log_start(conn, "news_pipeline", None)
        ids = {r.ticker: r.id for r in conn.execute(text("select id, ticker from companies"))}
        mv_id = conn.execute(
            text("""
            insert into model_versions (name, version, config) values (:n, :v, :c)
            on conflict (name, version) do update set config = excluded.config returning id"""),
            {
                "n": MODEL_NAME,
                "v": MODEL_VERSION,
                "c": json.dumps(
                    {
                        "finbert": getattr(model, "model_id", "test-double"),
                        "decision": DECISION_CONFIG,
                        "linking": "ticker+alias, headline/summary",
                    }
                ),
            },
        ).scalar_one()
        # articles
        art_rows = [
            {
                "provider": items[k]["provider"],
                "pid": items[k]["provider_article_id"],
                "url": items[k]["url"],
                "h": k,
                "headline": items[k]["headline"],
                "summary": items[k]["summary"][:1000],
                "src": items[k]["source_name"],
                "pub": items[k]["published_at"],
                "fp": items[k]["fingerprint"],
                "ev": classify_event(items[k]["headline"] + " " + items[k]["summary"]),
            }
            for k in keys
        ]
        conn.execute(
            text("""
            insert into news_articles (provider, provider_article_id, url, canonical_url_hash,
              headline, summary, source_name, published_at, content_fingerprint, event_type)
            values (:provider, :pid, :url, :h, :headline, :summary, :src, :pub, :fp, :ev)
            on conflict (canonical_url_hash) do nothing"""),
            art_rows,
        )
        aid = {
            r.canonical_url_hash: r.id
            for r in conn.execute(text("select id, canonical_url_hash from news_articles"))
        }
        dup_rows = [
            {"id": aid[k], "orig": aid[dup_of[k]]} for k in keys if dup_of[k] and dup_of[k] in aid
        ]
        if dup_rows:
            conn.execute(
                text("update news_articles set duplicate_of = :orig where id = :id"), dup_rows
            )
        # links + predictions
        link_rows, pred_rows = [], []
        for k in keys:
            for ln in links[k]:
                sents = split_sentences(ln.passage)
                d = decide(
                    names[ln.ticker],
                    ln.passage,
                    probs[ln.passage],
                    sents,
                    [probs[s] for s in sents],
                    ln.other_companies,
                )
                p = probs[ln.passage]
                link_rows.append(
                    {
                        "a": aid[k],
                        "c": ids[ln.ticker],
                        "r": ln.relevance,
                        "m": ln.match_method,
                        "p": ln.passage,
                    }
                )
                pred_rows.append(
                    {
                        "a": aid[k],
                        "c": ids[ln.ticker],
                        "mv": mv_id,
                        "label": d.label,
                        "pp": p.positive,
                        "pn": p.negative,
                        "pu": p.neutral,
                        "conf": d.confidence,
                        "ex": d.explanation,
                        "ev": json.dumps(d.evidence_quotes),
                        "nr": d.needs_review,
                    }
                )
        conn.execute(
            text("""
            insert into article_companies (article_id, company_id, relevance, match_method, passage)
            values (:a, :c, :r, :m, :p) on conflict do nothing"""),
            link_rows,
        )
        conn.execute(
            text("""
            insert into sentiment_predictions (article_id, company_id, model_version_id, label,
              p_positive, p_negative, p_neutral, confidence, explanation, explanation_method,
              evidence_quotes, needs_review)
            values (:a, :c, :mv, :label, :pp, :pn, :pu, :conf, :ex, 'evidence_template',
              cast(:ev as jsonb), :nr)
            on conflict (article_id, company_id, model_version_id) do update set
              label = excluded.label, p_positive = excluded.p_positive,
              p_negative = excluded.p_negative, p_neutral = excluded.p_neutral,
              confidence = excluded.confidence, explanation = excluded.explanation,
              evidence_quotes = excluded.evidence_quotes, needs_review = excluded.needs_review
            """),
            pred_rows,
        )
        log_finish(conn, log_id, "success", len(pred_rows), 0)
    return {
        "raw": len(raw),
        "unique": len(kept),
        "articles": len(keys),
        "predictions": len(pred_rows),
        "texts_scored": len(texts),
    }


def main() -> None:
    from datetime import date

    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", type=date.fromisoformat, required=True)
    args = ap.parse_args()
    configure_logging()
    print(run(args.snapshot))


if __name__ == "__main__":
    main()
