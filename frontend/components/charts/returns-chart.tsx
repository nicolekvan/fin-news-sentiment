"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ErrorBar,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ReturnRow } from "@/lib/types";

const axis = { fontSize: 10, fill: "var(--muted)" };
const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

export function ReturnsChart({ rows, horizons }: { rows: ReturnRow[]; horizons: number[] }) {
  const get = (h: number, s: "bullish" | "bearish") => rows.find((r) => r.horizon === h && r.signal === s);
  const data = horizons.map((h) => {
    const b = get(h, "bullish");
    const r = get(h, "bearish");
    const err = (x?: ReturnRow) =>
      x && x.mean_rel != null && x.ci_low != null && x.ci_high != null
        ? [x.mean_rel - x.ci_low, x.ci_high - x.mean_rel]
        : [0, 0];
    return {
      label: `${h} day${h > 1 ? "s" : ""}`,
      bullish: b?.mean_rel ?? 0,
      bearish: r?.mean_rel ?? 0,
      bullErr: err(b),
      bearErr: err(r),
      nb: b?.n ?? 0,
      nr: r?.n ?? 0,
    };
  });
  return (
    <div
      className="h-72 w-full"
      role="img"
      aria-label="Average return relative to QQQ after bullish and bearish company-days, by horizon, with 95% confidence intervals"
    >
      <ResponsiveContainer>
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="var(--border)" strokeDasharray="2 4" vertical={false} />
          <XAxis dataKey="label" tick={axis} />
          <YAxis tick={axis} tickFormatter={pct} />
          <ReferenceLine y={0} stroke="var(--muted)" />
          <Tooltip
            contentStyle={{ background: "var(--panel)", border: "1px solid var(--border)", fontSize: 12 }}
            formatter={(v, name, item) => {
              const p = item.payload as (typeof data)[number];
              const n = name === "After bullish" ? p.nb : p.nr;
              return [`${pct(Number(v))} vs QQQ (n=${n} company-days)`, String(name)];
            }}
          />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Bar dataKey="bullish" name="After bullish" fill="var(--bull)" fillOpacity={0.75}>
            <ErrorBar dataKey="bullErr" width={6} stroke="var(--text)" strokeWidth={1.2} />
          </Bar>
          <Bar dataKey="bearish" name="After bearish" fill="var(--bear)" fillOpacity={0.75}>
            <ErrorBar dataKey="bearErr" width={6} stroke="var(--text)" strokeWidth={1.2} />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
