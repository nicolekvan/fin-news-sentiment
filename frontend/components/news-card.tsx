import Link from "next/link";
import { ExternalLink, Flag } from "lucide-react";
import { SentimentBadge } from "@/components/sentiment";
import { Badge } from "@/components/ui/badge";
import { EVENT_TEXT, fmtDateTimeET } from "@/lib/format";
import type { NewsItem } from "@/lib/types";

export function NewsCard({ item, compact = false }: { item: NewsItem; compact?: boolean }) {
  return (
    <article className="border-b border-border/70 py-3 last:border-0" data-testid="news-card">
      <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-muted">
        <Link href={`/company/${item.ticker}/`} className="font-semibold text-text hover:text-accent">
          {item.ticker}
        </Link>
        <SentimentBadge label={item.label} />
        {item.event_type && item.event_type !== "other" && (
          <Badge variant="outline">{EVENT_TEXT[item.event_type] ?? item.event_type}</Badge>
        )}
        {item.needs_review && (
          <Badge variant="unclear" title="Flagged for review: the text names other companies or is ambiguous">
            <Flag aria-hidden className="h-3 w-3" /> Needs review
          </Badge>
        )}
        <span>·</span>
        <span>{item.source_name}</span>
        <span>·</span>
        <time dateTime={item.published_at}>{fmtDateTimeET(item.published_at)}</time>
      </div>
      <h3 className="mt-1 text-sm font-medium leading-snug">
        <a
          href={item.url}
          target="_blank"
          rel="noopener noreferrer nofollow"
          className="hover:text-accent"
        >
          {item.headline}
          <ExternalLink aria-hidden className="ml-1 inline h-3 w-3 align-baseline text-muted" />
          <span className="sr-only"> (opens original article in a new tab)</span>
        </a>
      </h3>
      {!compact && (
        <>
          <p className="mt-1.5 text-xs leading-relaxed text-muted">{item.explanation}</p>
          {item.evidence_quotes.length > 0 && (
            <blockquote className="mt-1.5 border-l-2 border-accent/60 pl-2 text-xs italic leading-relaxed">
              {item.evidence_quotes.map((q, i) => (
                <p key={i}>“{q}”</p>
              ))}
            </blockquote>
          )}
          <p className="mt-1 text-[10px] text-muted">
            Evidence quoted verbatim from the provider summary · {item.model_name}{" "}
            {item.model_version} · confidence {(item.confidence * 100).toFixed(0)}%
          </p>
        </>
      )}
    </article>
  );
}
