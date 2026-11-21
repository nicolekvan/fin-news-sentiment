import { CircleHelp, Minus, TrendingDown, TrendingUp } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { fmtPct, LABEL_TEXT } from "@/lib/format";
import type { Label } from "@/lib/types";
import { cn } from "@/lib/utils";

const VARIANT = {
  bullish: "bull",
  bearish: "bear",
  neutral: "neutral",
  insufficient_evidence: "unclear",
} as const;

const ICON = {
  bullish: TrendingUp,
  bearish: TrendingDown,
  neutral: Minus,
  insufficient_evidence: CircleHelp,
} as const;

/** Icon + text, so the label never depends on color alone. */
export function SentimentBadge({ label, short = false }: { label: Label | null; short?: boolean }) {
  const l: Label = label ?? "insufficient_evidence";
  const Icon = ICON[l];
  return (
    <Badge variant={VARIANT[l]} title={LABEL_TEXT[l]}>
      <Icon aria-hidden className="h-3 w-3" />
      <span>{short && l === "insufficient_evidence" ? "Unclear" : LABEL_TEXT[l]}</span>
    </Badge>
  );
}

/** Signed percentage with color and an arrow glyph. */
export function Pct({ value, className }: { value: number | null | undefined; className?: string }) {
  if (value == null) return <span className={cn("num text-muted", className)}>—</span>;
  const tone = value > 0 ? "text-bull" : value < 0 ? "text-bear" : "text-muted";
  const arrow = value > 0 ? "▲" : value < 0 ? "▼" : "";
  return (
    <span className={cn("num", tone, className)}>
      <span aria-hidden className="mr-0.5 text-[9px]">
        {arrow}
      </span>
      {fmtPct(value)}
    </span>
  );
}
