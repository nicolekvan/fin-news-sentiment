import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { PriceChart } from "@/components/charts/price-chart";
import { SentimentHistoryChart } from "@/components/charts/sentiment-history";
import { CompanyNews } from "@/components/company-news";
import { Pct, SentimentBadge } from "@/components/sentiment";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getCompanies, getCompanyFile, getMeta } from "@/lib/data";
import { fmtCap, fmtMarketDate, fmtNum, fmtPrice, fmtScore } from "@/lib/format";

export const dynamicParams = false;

export function generateStaticParams() {
  return getCompanies().map((c) => ({ ticker: c.ticker }));
}

type Params = { params: Promise<{ ticker: string }> };

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { ticker } = await params;
  const c = getCompanies().find((x) => x.ticker === ticker);
  return { title: c ? `${c.ticker} · ${c.name} · MarketLens AI` : "MarketLens AI" };
}

function Stat({ label, children, hint }: { label: string; children: React.ReactNode; hint?: string }) {
  return (
    <div className="rounded-md border border-border bg-panel-2/50 px-3 py-2" title={hint}>
      <div className="text-[10px] uppercase tracking-wide text-muted">{label}</div>
      <div className="mt-0.5 text-sm">{children}</div>
    </div>
  );
}

export default async function CompanyPage({ params }: Params) {
  const { ticker } = await params;
  if (!getCompanies().some((c) => c.ticker === ticker)) notFound();
  const f = getCompanyFile(ticker);
  const d = f.detail;
  const meta = getMeta();
  const agg = meta.aggregation;
  const trend =
    d.sma_50 != null && d.sma_200 != null
      ? d.sma_50 > d.sma_200
        ? "50-day above 200-day"
        : "50-day below 200-day"
      : "—";

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="text-[11px] text-muted">
            <Link href="/screener/" className="hover:text-accent">
              Screener
            </Link>{" "}
            / {d.industry} {d.exchange ? `· ${d.exchange}` : ""} {d.rank ? `· rank #${d.rank} by market cap` : ""}
          </div>
          <h1 className="mt-0.5 text-xl font-semibold">
            {d.ticker} <span className="text-base font-normal text-muted">{d.name}</span>
          </h1>
        </div>
        <div className="text-right">
          <div className="num text-2xl font-semibold">${fmtPrice(d.close)}</div>
          <div className="text-xs">
            <Pct value={d.change_1d} /> <span className="text-muted">close {d.trade_date ? fmtMarketDate(d.trade_date) : "—"} (end of day)</span>
          </div>
        </div>
      </div>

      <section className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:grid-cols-8" aria-label="Key statistics">
        <Stat label="Market cap">{fmtCap(d.market_cap_usd)}</Stat>
        <Stat label="1M · vs QQQ" hint="Price return; benchmark-relative = company minus QQQ">
          <Pct value={d.perf_1m} /> · <Pct value={d.vs_qqq_1m} />
        </Stat>
        <Stat label="3M · vs QQQ">
          <Pct value={d.perf_3m} /> · <Pct value={d.vs_qqq_3m} />
        </Stat>
        <Stat label="1Y · vs QQQ">
          <Pct value={d.perf_1y} /> · <Pct value={d.vs_qqq_1y} />
        </Stat>
        <Stat label="RSI 14">
          <span className="num">{fmtNum(d.rsi_14)}</span>
        </Stat>
        <Stat label="ATR 14">
          <span className="num">{fmtPrice(d.atr_14)}</span>
        </Stat>
        <Stat label="Trend">{trend}</Stat>
        <Stat label="News, 7 days">
          <span className="num">{d.news_7d}</span> stories
        </Stat>
      </section>

      <div className="grid gap-4 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle>Price, volume &amp; indicators</CardTitle>
            <span className="text-[10px] text-muted">daily · Twelve Data · indicators computed locally</span>
          </CardHeader>
          <CardContent>
            <PriceChart prices={f.prices} newsDays={f.events.news} filings={f.events.filings} />
          </CardContent>
        </Card>

        <div className="space-y-4">
          {!d.is_benchmark && (
            <Card>
              <CardHeader>
                <CardTitle>Company sentiment</CardTitle>
                <SentimentBadge label={d.sentiment_label} />
              </CardHeader>
              <CardContent className="space-y-2 text-xs">
                <div className="flex items-baseline gap-2">
                  <span className="num text-3xl font-semibold">{fmtScore(d.sentiment_score)}</span>
                  <span className="text-muted">score from −1 to +1 · {d.n_unique_stories ?? 0} unique stories</span>
                </div>
                <p className="leading-relaxed text-muted">
                  Weighted average of FinBERT tone (P(positive) − P(negative)) over the last{" "}
                  {agg.lookback_days} days, weighting each story by relevance × confidence and a{" "}
                  {agg.half_life_hours}-hour recency half-life. Syndicated copies count once; ambiguous and
                  flagged items are excluded. ≥ +{agg.threshold} is bullish, ≤ −{agg.threshold} bearish.
                  This measures the tone of coverage, not expected returns.
                </p>
              </CardContent>
            </Card>
          )}
          {!d.is_benchmark && (
            <Card>
              <CardHeader>
                <CardTitle>Sentiment history</CardTitle>
              </CardHeader>
              <CardContent>
                <SentimentHistoryChart data={f.sentiment} />
              </CardContent>
            </Card>
          )}
          <Card>
            <CardHeader>
              <CardTitle>SEC filings</CardTitle>
            </CardHeader>
            <CardContent className="text-xs">
              {f.events.filings.length === 0 ? (
                <p className="text-muted">No filings in this snapshot (SEC EDGAR step not run yet).</p>
              ) : (
                <ul className="space-y-1">
                  {f.events.filings.slice(-8).reverse().map((x) => (
                    <li key={x.url}>
                      <a href={x.url} target="_blank" rel="noopener noreferrer" className="hover:text-accent">
                        {x.form} · {fmtMarketDate(x.filed_date)}
                      </a>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {!d.is_benchmark && (
        <Card>
          <CardHeader>
            <CardTitle>Recent news · {d.ticker}-specific classifications</CardTitle>
            <Link href={`/news/?ticker=${d.ticker}`} className="text-[11px] text-accent hover:underline">
              Open in news feed →
            </Link>
          </CardHeader>
          <CardContent>
            <CompanyNews items={f.news} />
          </CardContent>
        </Card>
      )}
    </div>
  );
}
