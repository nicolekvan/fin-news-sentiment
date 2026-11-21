import type { Metadata } from "next";
import { ScreenerTable } from "@/components/screener-table";
import { Card, CardContent } from "@/components/ui/card";
import { getCompanies, getMeta } from "@/lib/data";
import { fmtMarketDate } from "@/lib/format";

export const metadata: Metadata = { title: "Screener · MarketLens AI" };

export default function ScreenerPage() {
  const rows = getCompanies();
  const meta = getMeta();
  return (
    <div className="space-y-3">
      <div>
        <h1 className="text-lg font-semibold">Stock Screener</h1>
        <p className="text-xs text-muted">
          {rows.filter((r) => !r.is_benchmark).length} companies plus benchmarks · end-of-day prices as of{" "}
          {fmtMarketDate(meta.prices_as_of)} · click a column to sort.
        </p>
      </div>
      <Card>
        <CardContent>
          <ScreenerTable rows={rows} />
        </CardContent>
      </Card>
    </div>
  );
}
