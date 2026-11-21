import Link from "next/link";
import { CircleHelp, Minus, TrendingDown, TrendingUp } from "lucide-react";
import { MarketTrendChart } from "@/components/charts/trend-chart";
import { SentimentHeatmap } from "@/components/heatmap";
import { NewsCard } from "@/components/news-card";
import { Pct, SentimentBadge } from "@/components/sentiment";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TD, TH, THead, TR } from "@/components/ui/table";
import { getMeta, getOverview } from "@/lib/data";
import { fmtDateTimeET, fmtPrice, fmtScore, LABEL_VAR } from "@/lib/format";
import type { CompanyRow, Label } from "@/lib/types";

const TILES: { label: Label; text: string; Icon: typeof TrendingUp }[] = [
  { label: "bullish", text: "Bullish", Icon: TrendingUp },
  { label: "bearish", text: "Bearish", Icon: TrendingDown },
  { label: "neutral", text: "Neutral", Icon: Minus },
  { label: "insufficient_evidence", text: "Insufficient evidence", Icon: CircleHelp },
];

function MoversTable({ rows, title }: { rows: CompanyRow[]; title: string }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <span className="text-[10px] text-muted">last session</span>
      </CardHeader>
      <Table>
        <THead>
          <tr>
            <TH>Ticker</TH>
            <TH className="text-right">Close</TH>
            <TH className="text-right">1D</TH>
            <TH>Sentiment</TH>
          </tr>
        </THead>
        <tbody>
          {rows.map((r) => (
            <TR key={r.ticker}>
              <TD>
                <Link href={`/company/${r.ticker}/`} className="font-semibold hover:text-accent">
                  {r.ticker}
                </Link>
              </TD>
              <TD className="num text-right">{fmtPrice(r.close)}</TD>
              <TD className="text-right">
                <Pct value={r.change_1d} />
              </TD>
              <TD>
                <SentimentBadge label={r.sentiment_label} short />
              </TD>
            </TR>
          ))}
        </tbody>
      </Table>
    </Card>
  );
}

export default function OverviewPage() {
  const o = getOverview();
  const meta = getMeta();
  const total = Object.values(o.counts).reduce((a, b) => a + b, 0);
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 className="text-lg font-semibold">Market Overview</h1>
          <p className="text-xs text-muted">
            News-sentiment snapshot for {total} large-cap technology companies · latest article{" "}
            {fmtDateTimeET(meta.news_as_of)}
          </p>
        </div>
      </div>

      <section aria-label="Sentiment counts" className="grid grid-cols-2 gap-2 md:grid-cols-4">
        {TILES.map(({ label, text, Icon }) => (
          <Card key={label} className="flex items-center gap-3 px-4 py-3" data-testid={`count-${label}`}>
            <Icon aria-hidden className="h-5 w-5" style={{ color: LABEL_VAR[label] }} />
            <div>
              <div className="num text-2xl font-semibold leading-none">{o.counts[label]}</div>
              <div className="mt-1 text-[11px] uppercase tracking-wide text-muted">{text}</div>
            </div>
          </Card>
        ))}
      </section>

      <Card>
        <CardHeader>
          <CardTitle>Sentiment heatmap</CardTitle>
          <span className="text-[10px] text-muted">
            tile size ≈ market cap · color strength ≈ |score| · score −1…+1
          </span>
        </CardHeader>
        <CardContent>
          <SentimentHeatmap rows={o.heatmap} />
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Market-wide sentiment trend</CardTitle>
            <span className="text-[10px] text-muted">daily, 14-day weighted window</span>
          </CardHeader>
          <CardContent>
            <MarketTrendChart data={o.trend} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Sector sentiment</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2.5">
            {o.sector.map((s) => {
              const w = Math.min(50, Math.abs(s.avg_score) * 125);
              return (
                <div key={s.industry} className="text-xs">
                  <div className="flex justify-between">
                    <span>
                      {s.industry} <span className="text-muted">({s.companies})</span>
                    </span>
                    <span className="num">{fmtScore(s.avg_score)}</span>
                  </div>
                  <div className="relative mt-1 h-1.5 rounded bg-panel-2" aria-hidden>
                    <div className="absolute left-1/2 top-0 h-full w-px bg-muted/50" />
                    <div
                      className="absolute top-0 h-full rounded"
                      style={{
                        width: `${w}%`,
                        left: s.avg_score >= 0 ? "50%" : `${50 - w}%`,
                        background: s.avg_score >= 0 ? "var(--bull)" : "var(--bear)",
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <MoversTable rows={o.top_gainers} title="Best 1-day moves" />
        <MoversTable rows={o.top_losers} title="Worst 1-day moves" />
        <Card>
          <CardHeader>
            <CardTitle>Trending companies</CardTitle>
            <span className="text-[10px] text-muted">unique stories, last 7 days</span>
          </CardHeader>
          <CardContent className="space-y-2">
            {o.trending.map((r) => {
              const max = o.trending[0]?.news_7d || 1;
              return (
                <div key={r.ticker} className="text-xs">
                  <div className="flex justify-between">
                    <Link href={`/company/${r.ticker}/`} className="font-semibold hover:text-accent">
                      {r.ticker}
                    </Link>
                    <span className="num">{r.news_7d}</span>
                  </div>
                  <div className="mt-1 h-1.5 rounded bg-panel-2" aria-hidden>
                    <div className="h-full rounded bg-accent" style={{ width: `${(r.news_7d / max) * 100}%` }} />
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Major news events</CardTitle>
          <Link href="/news/" className="text-[11px] text-accent hover:underline">
            All news →
          </Link>
        </CardHeader>
        <CardContent className="py-0">
          {o.major_events.length === 0 ? (
            <p className="py-6 text-center text-xs text-muted">No high-confidence events in this snapshot.</p>
          ) : (
            o.major_events.map((n) => <NewsCard key={`${n.article_id}-${n.ticker}`} item={n} />)
          )}
        </CardContent>
      </Card>
    </div>
  );
}
