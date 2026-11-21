import Link from "next/link";
import { fmtPct, fmtScore, LABEL_TEXT } from "@/lib/format";
import type { CompanyRow } from "@/lib/types";

/** Tile area ~ market cap; fill strength ~ |sentiment score|; text states the label. */
function tileStyle(score: number | null) {
  if (score == null) return { background: "var(--panel-2)" };
  const strength = Math.min(1, Math.abs(score) / 0.35);
  const base = score >= 0 ? "var(--bull)" : "var(--bear)";
  const pct = Math.round(12 + strength * 50);
  return { background: `color-mix(in oklab, ${base} ${pct}%, var(--panel))` };
}

export function SentimentHeatmap({ rows }: { rows: CompanyRow[] }) {
  const maxCap = Math.max(...rows.map((r) => r.market_cap_usd ?? 0), 1);
  return (
    <ul className="flex flex-wrap gap-1.5" aria-label="Company sentiment heatmap">
      {rows.map((r) => {
        const grow = Math.sqrt((r.market_cap_usd ?? maxCap / 20) / maxCap);
        const label = r.sentiment_label ?? "insufficient_evidence";
        return (
          <li
            key={r.ticker}
            style={{ flexGrow: grow, flexBasis: `${Math.round(90 + grow * 120)}px` }}
            className="min-w-[88px]"
          >
            <Link
              href={`/company/${r.ticker}/`}
              style={tileStyle(r.sentiment_score)}
              className="flex h-24 flex-col justify-between rounded-md border border-border p-2 hover:border-accent"
              aria-label={`${r.name}: ${LABEL_TEXT[label]}, sentiment score ${fmtScore(
                r.sentiment_score,
              )}, ${fmtPct(r.change_1d)} on the day`}
            >
              <div className="flex items-baseline justify-between gap-1">
                <span className="text-sm font-bold">{r.ticker}</span>
                <span className="num text-[11px]">{fmtPct(r.change_1d)}</span>
              </div>
              <div>
                <div className="num text-lg font-semibold leading-none">
                  {fmtScore(r.sentiment_score)}
                </div>
                <div className="mt-0.5 text-[10px] uppercase tracking-wide opacity-90">
                  {LABEL_TEXT[label]}
                </div>
              </div>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
