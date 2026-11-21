"use client";

import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fmtMarketDate } from "@/lib/format";

interface Point {
  day: string;
  avg_score: number;
  bullish: number;
  bearish: number;
}

const axis = { fontSize: 10, fill: "var(--muted)" };

export function MarketTrendChart({ data }: { data: Point[] }) {
  return (
    <div className="h-64 w-full" role="img" aria-label="Market-wide average sentiment score by day, with counts of bullish and bearish companies">
      <ResponsiveContainer>
        <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
          <CartesianGrid stroke="var(--border)" strokeDasharray="2 4" vertical={false} />
          <XAxis dataKey="day" tick={axis} tickFormatter={(d: string) => d.slice(5)} minTickGap={24} />
          <YAxis yAxisId="score" tick={axis} domain={[-0.5, 0.5]} />
          <YAxis yAxisId="n" orientation="right" tick={axis} allowDecimals={false} />
          <ReferenceLine yAxisId="score" y={0} stroke="var(--muted)" />
          <Tooltip
            contentStyle={{ background: "var(--panel)", border: "1px solid var(--border)", fontSize: 12 }}
            labelFormatter={(d) => fmtMarketDate(String(d))}
            formatter={(v, name) => [typeof v === "number" && name === "Avg score" ? v.toFixed(3) : String(v), String(name)]}
          />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Bar yAxisId="n" dataKey="bullish" name="Bullish cos." fill="var(--bull)" opacity={0.45} />
          <Bar yAxisId="n" dataKey="bearish" name="Bearish cos." fill="var(--bear)" opacity={0.45} />
          <Line yAxisId="score" dataKey="avg_score" name="Avg score" stroke="var(--accent)" dot={false} strokeWidth={2} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
