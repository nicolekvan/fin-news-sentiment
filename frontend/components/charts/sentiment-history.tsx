"use client";

import {
  Area,
  Bar,
  CartesianGrid,
  ComposedChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fmtDateTimeET, LABEL_TEXT } from "@/lib/format";
import type { SentimentPoint } from "@/lib/types";

const axis = { fontSize: 10, fill: "var(--muted)" };

export function SentimentHistoryChart({ data }: { data: SentimentPoint[] }) {
  if (data.length === 0) {
    return <p className="py-10 text-center text-xs text-muted">No sentiment history for this company.</p>;
  }
  return (
    <div
      className="h-56 w-full"
      role="img"
      aria-label="Company sentiment score over time with bullish and bearish threshold bands"
    >
      <ResponsiveContainer>
        <ComposedChart data={data} margin={{ top: 6, right: 6, bottom: 0, left: -14 }}>
          <CartesianGrid stroke="var(--border)" strokeDasharray="2 4" vertical={false} />
          <XAxis dataKey="as_of" tick={axis} tickFormatter={(d: string) => d.slice(5, 10)} minTickGap={28} />
          <YAxis yAxisId="s" tick={axis} domain={[-0.6, 0.6]} />
          <YAxis yAxisId="n" orientation="right" tick={axis} allowDecimals={false} />
          <ReferenceArea yAxisId="s" y1={0.15} y2={0.6} fill="var(--bull)" fillOpacity={0.06} />
          <ReferenceArea yAxisId="s" y1={-0.6} y2={-0.15} fill="var(--bear)" fillOpacity={0.06} />
          <ReferenceLine yAxisId="s" y={0} stroke="var(--muted)" />
          <Tooltip
            contentStyle={{ background: "var(--panel)", border: "1px solid var(--border)", fontSize: 12 }}
            labelFormatter={(d) => fmtDateTimeET(String(d))}
            formatter={(v, name, item) => {
              if (name === "Score") {
                const p = item.payload as SentimentPoint;
                return [`${(v as number).toFixed(3)} (${LABEL_TEXT[p.label]})`, "Score"];
              }
              return [String(v), String(name)];
            }}
          />
          <Bar yAxisId="n" dataKey="n_unique_stories" name="Stories in window" fill="var(--muted)" opacity={0.25} />
          <Area yAxisId="s" type="monotone" dataKey="score" name="Score" stroke="var(--accent)" fill="var(--accent)" fillOpacity={0.12} strokeWidth={2} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
