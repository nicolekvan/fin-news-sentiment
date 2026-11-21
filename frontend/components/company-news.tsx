"use client";

import { useMemo, useState } from "react";
import { NewsCard } from "@/components/news-card";
import { Button } from "@/components/ui/button";
import { LABEL_TEXT } from "@/lib/format";
import type { Label, NewsItem } from "@/lib/types";

const LABELS: Label[] = ["bullish", "bearish", "neutral", "insufficient_evidence"];

export function CompanyNews({ items }: { items: NewsItem[] }) {
  const [label, setLabel] = useState<Label | "all">("all");
  const [shown, setShown] = useState(15);
  const filtered = useMemo(
    () => (label === "all" ? items : items.filter((i) => i.label === label)),
    [items, label],
  );
  return (
    <div>
      <div className="flex flex-wrap gap-1.5" role="group" aria-label="Filter by sentiment">
        {(["all", ...LABELS] as const).map((l) => (
          <Button
            key={l}
            size="sm"
            variant="toggle"
            aria-pressed={label === l}
            onClick={() => {
              setLabel(l);
              setShown(15);
            }}
          >
            {l === "all" ? `All (${items.length})` : `${LABEL_TEXT[l]} (${items.filter((i) => i.label === l).length})`}
          </Button>
        ))}
      </div>
      {filtered.length === 0 ? (
        <p className="py-8 text-center text-xs text-muted">No articles with this label.</p>
      ) : (
        <div className="mt-1">
          {filtered.slice(0, shown).map((n) => (
            <NewsCard key={`${n.article_id}-${n.ticker}`} item={n} />
          ))}
          {shown < filtered.length && (
            <Button variant="outline" className="mt-2 w-full" onClick={() => setShown(shown + 15)}>
              Show more ({filtered.length - shown} remaining)
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
