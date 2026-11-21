import type { Metadata } from "next";
import Link from "next/link";
import { Activity } from "lucide-react";
import "./globals.css";
import { SiteNav } from "@/components/site-nav";
import { ThemeToggle, themeScript } from "@/components/theme-toggle";
import { Badge } from "@/components/ui/badge";
import { getMeta } from "@/lib/data";
import { fmtDateTimeET, fmtMarketDate } from "@/lib/format";

export const metadata: Metadata = {
  title: "MarketLens AI",
  description:
    "Company-level news sentiment for large-cap technology stocks, with source-linked explanations.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const meta = getMeta();
  const demo = meta.demo_mode || meta.has_demo_prices || meta.has_demo_news;
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="min-h-screen antialiased">
        <header className="sticky top-0 z-20 border-b border-border bg-bg/95 backdrop-blur">
          <div className="mx-auto flex max-w-[1400px] flex-wrap items-center gap-x-4 gap-y-2 px-4 py-2">
            <Link href="/" className="flex items-center gap-1.5 text-sm font-semibold">
              <Activity aria-hidden className="h-4 w-4 text-accent" />
              MarketLens <span className="text-accent">AI</span>
            </Link>
            <SiteNav />
            <div className="ml-auto flex items-center gap-2">
              {demo && (
                <Badge variant="unclear" data-testid="demo-badge">
                  DEMO DATA · synthetic
                </Badge>
              )}
              <Badge variant="outline" data-testid="snapshot-badge" title={`Last ingested ${fmtDateTimeET(meta.last_ingested_at)}`}>
                Historical snapshot · prices as of {fmtMarketDate(meta.prices_as_of)}
              </Badge>
              <ThemeToggle />
            </div>
          </div>
        </header>
        <main className="mx-auto max-w-[1400px] px-4 py-4">{children}</main>
        <footer className="mx-auto max-w-[1400px] px-4 pb-8 pt-2 text-[11px] leading-relaxed text-muted">
          <p data-testid="disclaimer">
            <strong className="text-text">Disclaimer:</strong> {meta.disclaimer} Past associations
            between sentiment and returns do not imply future results.
          </p>
          <p className="mt-1">
            Data: news via Finnhub (links go to the original publishers), daily prices via Twelve
            Data (end-of-day, delayed), macro series via FRED. Technical indicators are computed
            locally. Sentiment: FinBERT ({meta.models.map((m) => `${m.name} ${m.version}`).join(", ")}).
            Times shown in US/Eastern.
          </p>
        </footer>
      </body>
    </html>
  );
}
