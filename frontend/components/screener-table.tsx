"use client";

import Link from "next/link";
import { ArrowDown, ArrowUp } from "lucide-react";
import { useMemo, useState } from "react";
import { Pct, SentimentBadge } from "@/components/sentiment";
import { Input } from "@/components/ui/input";
import { Table, TD, TH, THead, TR } from "@/components/ui/table";
import { fmtCap, fmtNum, fmtPrice, fmtScore, fmtVolume } from "@/lib/format";
import type { CompanyRow } from "@/lib/types";

type Key = keyof CompanyRow;
const COLS: { key: Key; label: string; num?: boolean; title?: string }[] = [
  { key: "rank", label: "#", num: true },
  { key: "ticker", label: "Ticker" },
  { key: "industry", label: "Industry" },
  { key: "close", label: "Price", num: true },
  { key: "change_1d", label: "1D", num: true },
  { key: "market_cap_usd", label: "Mkt cap", num: true },
  { key: "perf_1m", label: "1M", num: true },
  { key: "perf_3m", label: "3M", num: true },
  { key: "perf_1y", label: "1Y", num: true },
  { key: "rsi_14", label: "RSI", num: true, title: "14-day RSI" },
  { key: "macd_hist", label: "MACD h", num: true, title: "MACD histogram (12/26/9)" },
  { key: "atr_14", label: "ATR", num: true, title: "14-day average true range" },
  { key: "volume", label: "Volume", num: true },
  { key: "sentiment_score", label: "Score", num: true, title: "Aggregated sentiment score, −1…+1" },
  { key: "sentiment_label", label: "Sentiment" },
  { key: "news_7d", label: "News 7d", num: true, title: "Unique stories in the last 7 days" },
];

export function ScreenerTable({ rows }: { rows: CompanyRow[] }) {
  const [sort, setSort] = useState<{ key: Key; dir: 1 | -1 }>({ key: "rank", dir: 1 });
  const [q, setQ] = useState("");

  const data = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const r = rows.filter(
      (x) => !needle || x.ticker.toLowerCase().includes(needle) || x.name.toLowerCase().includes(needle) || x.industry.toLowerCase().includes(needle),
    );
    return [...r].sort((a, b) => {
      const av = a[sort.key];
      const bv = b[sort.key];
      if (av == null && bv == null) return 0;
      if (av == null) return 1; // missing values last, regardless of direction
      if (bv == null) return -1;
      return (av < bv ? -1 : av > bv ? 1 : 0) * sort.dir;
    });
  }, [rows, sort, q]);

  const onSort = (key: Key) =>
    setSort((s) => ({ key, dir: s.key === key ? ((-s.dir) as 1 | -1) : COLS.find((c) => c.key === key)?.num ? -1 : 1 }));

  return (
    <div>
      <Input
        type="search"
        placeholder="Filter by ticker, name or industry…"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        className="mb-2 max-w-xs"
        aria-label="Filter companies"
      />
      <Table data-testid="screener-table">
        <THead>
          <tr>
            {COLS.map((c) => (
              <TH
                key={c.key}
                className={c.num ? "text-right" : undefined}
                title={c.title}
                aria-sort={sort.key === c.key ? (sort.dir === 1 ? "ascending" : "descending") : "none"}
              >
                <button onClick={() => onSort(c.key)} className="inline-flex items-center gap-0.5 uppercase hover:text-text">
                  {c.label}
                  {sort.key === c.key &&
                    (sort.dir === 1 ? <ArrowUp className="h-3 w-3" aria-hidden /> : <ArrowDown className="h-3 w-3" aria-hidden />)}
                </button>
              </TH>
            ))}
          </tr>
        </THead>
        <tbody>
          {data.map((r) => (
            <TR key={r.ticker}>
              <TD className="num text-right text-muted">{r.rank ?? "—"}</TD>
              <TD>
                <Link href={`/company/${r.ticker}/`} className="font-semibold hover:text-accent">
                  {r.ticker}
                </Link>
                <div className="max-w-[160px] truncate text-[10px] text-muted">{r.name}</div>
              </TD>
              <TD className="text-muted">{r.industry}</TD>
              <TD className="num text-right">{fmtPrice(r.close)}</TD>
              <TD className="text-right"><Pct value={r.change_1d} /></TD>
              <TD className="num text-right">{fmtCap(r.market_cap_usd)}</TD>
              <TD className="text-right"><Pct value={r.perf_1m} /></TD>
              <TD className="text-right"><Pct value={r.perf_3m} /></TD>
              <TD className="text-right"><Pct value={r.perf_1y} /></TD>
              <TD className="num text-right">{fmtNum(r.rsi_14)}</TD>
              <TD className="num text-right">{fmtNum(r.macd_hist, 2)}</TD>
              <TD className="num text-right">{fmtPrice(r.atr_14)}</TD>
              <TD className="num text-right">{fmtVolume(r.volume)}</TD>
              <TD className="num text-right">{r.is_benchmark ? "—" : fmtScore(r.sentiment_score)}</TD>
              <TD>{r.is_benchmark ? <span className="text-[11px] text-muted">Benchmark</span> : <SentimentBadge label={r.sentiment_label} short />}</TD>
              <TD className="num text-right">{r.is_benchmark ? "—" : r.news_7d}</TD>
            </TR>
          ))}
        </tbody>
      </Table>
      {data.length === 0 && <p className="py-8 text-center text-xs text-muted">No companies match.</p>}
    </div>
  );
}
