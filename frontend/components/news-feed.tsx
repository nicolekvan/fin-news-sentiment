"use client";

import { AlertTriangle, Loader2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { NewsCard } from "@/components/news-card";
import { Button } from "@/components/ui/button";
import { Input, Select } from "@/components/ui/input";
import { EVENT_TEXT, LABEL_TEXT } from "@/lib/format";
import type { Label, NewsItem } from "@/lib/types";

type State = { status: "loading" } | { status: "error" } | { status: "ready"; items: NewsItem[] };
const PAGE = 25;

const uniq = (xs: string[]) => [...new Set(xs)].sort();

export function NewsFeed() {
  const [state, setState] = useState<State>({ status: "loading" });
  const [ticker, setTicker] = useState("");
  const [industry, setIndustry] = useState("");
  const [label, setLabel] = useState("");
  const [event, setEvent] = useState("");
  const [source, setSource] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [q, setQ] = useState("");
  const [shown, setShown] = useState(PAGE);

  useEffect(() => {
    const t = new URLSearchParams(window.location.search).get("ticker");
    if (t && /^[A-Z.]{1,10}$/.test(t)) setTicker(t);
    fetch("/data/news.json")
      .then((r) => {
        if (!r.ok) throw new Error(String(r.status));
        return r.json() as Promise<NewsItem[]>;
      })
      .then((items) => setState({ status: "ready", items }))
      .catch(() => setState({ status: "error" }));
  }, []);

  const items = state.status === "ready" ? state.items : [];
  const options = useMemo(
    () => ({
      tickers: uniq(items.map((i) => i.ticker)),
      industries: uniq(items.map((i) => i.industry)),
      events: uniq(items.map((i) => i.event_type ?? "other")),
      sources: uniq(items.map((i) => i.source_name)),
    }),
    [items],
  );

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return items.filter((i) => {
      if (ticker && i.ticker !== ticker) return false;
      if (industry && i.industry !== industry) return false;
      if (label && i.label !== label) return false;
      if (event && (i.event_type ?? "other") !== event) return false;
      if (source && i.source_name !== source) return false;
      const day = i.published_at.slice(0, 10);
      if (from && day < from) return false;
      if (to && day > to) return false;
      if (needle && !i.headline.toLowerCase().includes(needle)) return false;
      return true;
    });
  }, [items, ticker, industry, label, event, source, from, to, q]);

  useEffect(() => setShown(PAGE), [ticker, industry, label, event, source, from, to, q]);

  const reset = () => {
    setTicker(""); setIndustry(""); setLabel(""); setEvent(""); setSource(""); setFrom(""); setTo(""); setQ("");
  };

  if (state.status === "loading") {
    return (
      <div className="flex items-center justify-center gap-2 py-16 text-xs text-muted" role="status">
        <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> Loading news…
      </div>
    );
  }
  if (state.status === "error") {
    return (
      <div className="flex items-center justify-center gap-2 py-16 text-xs text-bear" role="alert">
        <AlertTriangle className="h-4 w-4" aria-hidden /> Could not load the news snapshot. Try reloading the page.
      </div>
    );
  }

  return (
    <div>
      <form
        className="grid grid-cols-2 gap-2 md:grid-cols-4 xl:grid-cols-8"
        onSubmit={(e) => e.preventDefault()}
        aria-label="News filters"
      >
        <Input
          className="col-span-2"
          type="search"
          placeholder="Search headlines…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          aria-label="Search headlines"
          maxLength={100}
        />
        <Select value={ticker} onChange={(e) => setTicker(e.target.value)} aria-label="Company">
          <option value="">All companies</option>
          {options.tickers.map((t) => <option key={t}>{t}</option>)}
        </Select>
        <Select value={industry} onChange={(e) => setIndustry(e.target.value)} aria-label="Industry">
          <option value="">All industries</option>
          {options.industries.map((t) => <option key={t}>{t}</option>)}
        </Select>
        <Select value={label} onChange={(e) => setLabel(e.target.value)} aria-label="Sentiment">
          <option value="">All sentiment</option>
          {(Object.keys(LABEL_TEXT) as Label[]).map((l) => (
            <option key={l} value={l}>{LABEL_TEXT[l]}</option>
          ))}
        </Select>
        <Select value={event} onChange={(e) => setEvent(e.target.value)} aria-label="Event type">
          <option value="">All event types</option>
          {options.events.map((t) => <option key={t} value={t}>{EVENT_TEXT[t] ?? t}</option>)}
        </Select>
        <Select value={source} onChange={(e) => setSource(e.target.value)} aria-label="Source">
          <option value="">All sources</option>
          {options.sources.map((t) => <option key={t}>{t}</option>)}
        </Select>
        <div className="col-span-2 flex items-center gap-1 md:col-span-1 xl:col-span-1">
          <Button type="button" variant="outline" size="sm" onClick={reset} className="w-full">
            Reset
          </Button>
        </div>
        <label className="col-span-1 flex items-center gap-1 text-[11px] text-muted">
          From
          <Input type="date" value={from} onChange={(e) => setFrom(e.target.value)} aria-label="From date" />
        </label>
        <label className="col-span-1 flex items-center gap-1 text-[11px] text-muted">
          To
          <Input type="date" value={to} onChange={(e) => setTo(e.target.value)} aria-label="To date" />
        </label>
      </form>

      <p className="mt-3 text-[11px] text-muted" aria-live="polite" data-testid="news-count">
        {filtered.length} of {items.length} classifications (most recent {items.length} in the snapshot;
        syndicated copies hidden)
      </p>

      {filtered.length === 0 ? (
        <div className="py-14 text-center text-xs text-muted" data-testid="news-empty">
          No articles match these filters.{" "}
          <button className="text-accent hover:underline" onClick={reset}>Clear filters</button>
        </div>
      ) : (
        <div>
          {filtered.slice(0, shown).map((n) => (
            <NewsCard key={`${n.article_id}-${n.ticker}`} item={n} />
          ))}
          {shown < filtered.length && (
            <Button variant="outline" className="mt-2 w-full" onClick={() => setShown(shown + PAGE)}>
              Show more ({filtered.length - shown} remaining)
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
