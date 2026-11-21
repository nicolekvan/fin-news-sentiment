import type { Metadata } from "next";
import { ClipboardList } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

export const metadata: Metadata = { title: "Model Performance · MarketLens AI" };

export default function PerformancePage() {
  return (
    <div className="space-y-3">
      <div>
        <h1 className="text-lg font-semibold">Model Performance</h1>
        <p className="text-xs text-muted">
          How well the labels match human judgement, and what stocks did after bullish and bearish
          classifications.
        </p>
      </div>
      <Card>
        <CardContent className="flex flex-col items-center gap-2 py-16 text-center" data-testid="performance-empty">
          <ClipboardList className="h-6 w-6 text-muted" aria-hidden />
          <p className="text-sm font-medium">Evaluation not published yet</p>
          <p className="max-w-md text-xs text-muted">
            Metrics appear here once the manually labelled evaluation set is complete. No numbers are
            shown until they have been measured.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
