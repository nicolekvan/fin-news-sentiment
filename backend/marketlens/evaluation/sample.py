"""Draw the evaluation sample: a simple random sample of (article, company) predictions.

Uniform (not stratified by the model's label), so metrics on it estimate performance on the
news the model actually sees. Syndicated copies are excluded. Deterministic for a given seed.

    python -m marketlens.evaluation.sample --n 240 --out <file.json>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlalchemy import text

from marketlens.db import get_engine

SAMPLE_SQL = """
select a.id as article_id, c.ticker, c.name as company, c.aliases, a.headline, a.summary,
       a.url, a.source_name, a.published_at, ac.passage
from sentiment_predictions p
join news_articles a on a.id = p.article_id
join companies c on c.id = p.company_id
join article_companies ac on ac.article_id = p.article_id and ac.company_id = p.company_id
where a.duplicate_of is null
order by md5(a.id::text || ':' || c.ticker || ':' || :seed)
limit :n
"""


def draw(engine, n: int, seed: str = "marketlens-eval-v1") -> list[dict]:
    with engine.connect() as conn:
        rows = [dict(r._mapping) for r in conn.execute(text(SAMPLE_SQL), {"n": n, "seed": seed})]
    items = []
    for i, r in enumerate(rows):
        items.append(
            {
                "id": f"a{r['article_id']}-{r['ticker']}",
                "order": i,
                "article_id": r["article_id"],
                "ticker": r["ticker"],
                "company": r["company"],
                "names": [r["ticker"], r["company"], *r["aliases"]],
                "headline": r["headline"],
                "summary": r["summary"] or "",
                "url": r["url"],
                "source": r["source_name"],
                "published_at": r["published_at"].isoformat(),
            }
        )
    return items


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=240)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    items = draw(get_engine(writer=False), args.n)
    args.out.write_text(json.dumps(items, indent=0))
    print(f"{len(items)} items -> {args.out}")


if __name__ == "__main__":
    main()
