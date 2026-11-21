import type { Label } from "./types";

const ET = "America/New_York";

/** UTC timestamps are shown in US/Eastern, the market's time zone. */
export function fmtDateTimeET(iso: string): string {
  return new Intl.DateTimeFormat("en-US", {
    timeZone: ET,
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  }).format(new Date(iso));
}

/** Market dates (YYYY-MM-DD) are already US/Eastern trading days: format without shifting. */
export function fmtMarketDate(d: string): string {
  const [y, m, day] = d.split("-").map(Number);
  return new Intl.DateTimeFormat("en-US", {
    timeZone: "UTC",
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(Date.UTC(y ?? 1970, (m ?? 1) - 1, day ?? 1)));
}

export function fmtPrice(v: number | null | undefined): string {
  return v == null
    ? "—"
    : v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function fmtPct(v: number | null | undefined, digits = 1): string {
  if (v == null) return "—";
  const s = (v * 100).toFixed(digits);
  if (Number(s) === 0) return `${(0).toFixed(digits)}%`; // avoid "-0.00%"
  return `${v > 0 ? "+" : ""}${s}%`;
}

export function fmtNum(v: number | null | undefined, digits = 1): string {
  return v == null ? "—" : v.toFixed(digits);
}

export function fmtScore(v: number | null | undefined): string {
  if (v == null) return "—";
  if (Math.abs(v) < 0.005) return "0.00"; // avoid "-0.00"
  return `${v > 0 ? "+" : ""}${v.toFixed(2)}`;
}

export function fmtCap(v: number | null | undefined): string {
  if (v == null) return "—";
  if (v >= 1e12) return `$${(v / 1e12).toFixed(2)}T`;
  if (v >= 1e9) return `$${(v / 1e9).toFixed(0)}B`;
  return `$${(v / 1e6).toFixed(0)}M`;
}

export function fmtVolume(v: number | null | undefined): string {
  if (v == null) return "—";
  return v >= 1e6 ? `${(v / 1e6).toFixed(1)}M` : v.toLocaleString("en-US");
}

export const LABEL_TEXT: Record<Label, string> = {
  bullish: "Bullish",
  bearish: "Bearish",
  neutral: "Neutral",
  insufficient_evidence: "Insufficient evidence",
};

export const EVENT_TEXT: Record<string, string> = {
  earnings: "Earnings",
  guidance: "Guidance",
  analyst_rating: "Analyst rating",
  mergers_acquisitions: "M&A",
  legal_regulatory: "Legal / regulatory",
  product: "Product",
  partnership_contract: "Partnership / contract",
  management: "Management",
  capital_return: "Dividends / buybacks",
  other: "Other",
};

/** Same thresholds as the backend aggregation (agg-v1). */
export function scoreLabel(score: number | null | undefined): Label {
  if (score == null) return "insufficient_evidence";
  if (score >= 0.15) return "bullish";
  if (score <= -0.15) return "bearish";
  return "neutral";
}

export const LABEL_VAR: Record<Label, string> = {
  bullish: "var(--bull)",
  bearish: "var(--bear)",
  neutral: "var(--neutral)",
  insufficient_evidence: "var(--unclear)",
};
