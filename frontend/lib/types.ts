export type Label = "bullish" | "bearish" | "neutral" | "insufficient_evidence";

export interface Meta {
  prices_as_of: string;
  news_as_of: string;
  last_ingested_at: string;
  has_demo_prices: boolean;
  has_demo_news: boolean;
  demo_mode: boolean;
  disclaimer: string;
  aggregation: Record<string, string | number>;
  models: { name: string; version: string; config: Record<string, unknown> }[];
}

export interface CompanyRow {
  ticker: string;
  name: string;
  industry: string;
  exchange: string | null;
  is_benchmark: boolean;
  rank: number | null;
  market_cap_usd: number | null;
  trade_date: string | null;
  close: number | null;
  volume: number | null;
  change_1d: number | null;
  perf_1m: number | null;
  perf_3m: number | null;
  perf_1y: number | null;
  rsi_14: number | null;
  sma_50: number | null;
  sma_200: number | null;
  macd_hist: number | null;
  atr_14: number | null;
  sentiment_score: number | null;
  sentiment_label: Label | null;
  n_unique_stories: number | null;
  news_7d: number;
}

export interface CompanyDetail extends CompanyRow {
  vs_qqq_1m: number | null;
  vs_qqq_3m: number | null;
  vs_qqq_1y: number | null;
  benchmark: string;
}

export interface PriceRow {
  trade_date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  source: string;
  sma_20: number | null;
  sma_50: number | null;
  sma_200: number | null;
  rsi_14: number | null;
  macd: number | null;
  macd_signal: number | null;
  macd_hist: number | null;
  bb_upper: number | null;
  bb_mid: number | null;
  bb_lower: number | null;
  atr_14: number | null;
}

export interface SentimentPoint {
  as_of: string;
  score: number;
  label: Label;
  n_articles: number;
  n_unique_stories: number;
}

export interface NewsItem {
  article_id: number;
  headline: string;
  summary: string | null;
  url: string;
  source_name: string;
  provider: string;
  published_at: string;
  event_type: string | null;
  ticker: string;
  company: string;
  industry: string;
  label: Label;
  confidence: number;
  p_positive: number;
  p_negative: number;
  p_neutral: number;
  explanation: string;
  explanation_method: string;
  evidence_quotes: string[];
  needs_review: boolean;
  relevance: number;
  model_name: string;
  model_version: string;
}

export interface DayEvents {
  day: string;
  bullish: number;
  bearish: number;
  neutral: number;
  insufficient: number;
}

export interface CompanyFile {
  detail: CompanyDetail;
  prices: PriceRow[];
  sentiment: SentimentPoint[];
  events: {
    news: DayEvents[];
    filings: { form: string; filed_date: string; url: string }[];
  };
  news: NewsItem[];
}

export interface Overview {
  counts: Record<Label, number>;
  heatmap: CompanyRow[];
  sector: { industry: string; avg_score: number; companies: number }[];
  trend: { day: string; avg_score: number; bullish: number; bearish: number }[];
  top_gainers: CompanyRow[];
  top_losers: CompanyRow[];
  trending: CompanyRow[];
  major_events: NewsItem[];
}
