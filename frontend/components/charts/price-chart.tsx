"use client";

import {
  CandlestickSeries,
  ColorType,
  createChart,
  createSeriesMarkers,
  CrosshairMode,
  HistogramSeries,
  LineSeries,
  type IChartApi,
  type SeriesMarker,
  type Time,
  type UTCTimestamp,
} from "lightweight-charts";
import { useEffect, useMemo, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { fmtMarketDate, fmtPrice, fmtVolume } from "@/lib/format";
import type { DayEvents, PriceRow } from "@/lib/types";

type Overlay = "sma20" | "sma50" | "sma200" | "bb";
type Lower = "rsi" | "macd" | "atr";

interface Props {
  prices: PriceRow[];
  newsDays: DayEvents[];
  filings: { form: string; filed_date: string; url: string }[];
}

function css(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

const toTime = (d: string) => d as Time;

/** News on a weekend/holiday is attached to the next trading day so markers sit on a bar. */
export function alignToTradingDays(days: string[], tradingDays: string[]): Map<string, string> {
  const out = new Map<string, string>();
  let j = 0;
  for (const d of [...days].sort()) {
    while (j < tradingDays.length && tradingDays[j]! < d) j++;
    if (j < tradingDays.length) out.set(d, tradingDays[j]!);
  }
  return out;
}

export function PriceChart({ prices, newsDays, filings }: Props) {
  const box = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const [overlays, setOverlays] = useState<Set<Overlay>>(new Set(["sma50", "sma200"]));
  const [lower, setLower] = useState<Set<Lower>>(new Set(["rsi"]));
  const [showNews, setShowNews] = useState(true);
  const [hover, setHover] = useState<PriceRow | null>(null);

  const byDate = useMemo(() => new Map(prices.map((p) => [p.trade_date, p])), [prices]);
  const last = prices[prices.length - 1] ?? null;

  useEffect(() => {
    const el = box.current;
    if (!el || prices.length === 0) return;
    const text = css("--muted");
    const grid = css("--border");
    const bull = css("--bull");
    const bear = css("--bear");
    const neutral = css("--neutral");
    const accent = css("--accent");

    const chart = createChart(el, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: text,
        fontSize: 11,
        panes: { separatorColor: grid },
      },
      grid: { vertLines: { color: grid }, horzLines: { color: grid } },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: grid },
      timeScale: { borderColor: grid },
    });
    chartRef.current = chart;

    const candles = chart.addSeries(CandlestickSeries, {
      upColor: bull,
      downColor: bear,
      borderVisible: false,
      wickUpColor: bull,
      wickDownColor: bear,
    });
    candles.setData(
      prices.map((p) => ({ time: toTime(p.trade_date), open: p.open, high: p.high, low: p.low, close: p.close })),
    );

    const line = (key: keyof PriceRow, color: string, pane = 0, width: 1 | 2 = 1) => {
      const s = chart.addSeries(LineSeries, { color, lineWidth: width, priceLineVisible: false, lastValueVisible: false }, pane);
      s.setData(
        prices.filter((p) => p[key] != null).map((p) => ({ time: toTime(p.trade_date), value: p[key] as number })),
      );
      return s;
    };
    if (overlays.has("sma20")) line("sma_20", "#a78bfa");
    if (overlays.has("sma50")) line("sma_50", "#f59e0b");
    if (overlays.has("sma200")) line("sma_200", accent, 0, 2);
    if (overlays.has("bb")) {
      line("bb_upper", neutral);
      line("bb_lower", neutral);
    }

    const vol = chart.addSeries(HistogramSeries, { priceScaleId: "vol", priceFormat: { type: "volume" }, lastValueVisible: false, priceLineVisible: false });
    vol.priceScale().applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
    vol.setData(
      prices.map((p) => ({
        time: toTime(p.trade_date),
        value: p.volume,
        color: p.close >= p.open ? `${bull}55` : `${bear}55`,
      })),
    );

    let pane = 1;
    if (lower.has("rsi")) {
      const rsi = line("rsi_14", "#a78bfa", pane);
      rsi.createPriceLine({ price: 70, color: bear, lineWidth: 1, lineStyle: 2, axisLabelVisible: false });
      rsi.createPriceLine({ price: 30, color: bull, lineWidth: 1, lineStyle: 2, axisLabelVisible: false });
      pane++;
    }
    if (lower.has("macd")) {
      const hist = chart.addSeries(HistogramSeries, { priceLineVisible: false, lastValueVisible: false }, pane);
      hist.setData(
        prices.filter((p) => p.macd_hist != null).map((p) => ({
          time: toTime(p.trade_date),
          value: p.macd_hist as number,
          color: (p.macd_hist as number) >= 0 ? `${bull}99` : `${bear}99`,
        })),
      );
      line("macd", accent, pane);
      line("macd_signal", "#f59e0b", pane);
      pane++;
    }
    if (lower.has("atr")) {
      line("atr_14", "#f472b6", pane);
      pane++;
    }
    chart.panes().forEach((p, i) => p.setHeight(i === 0 ? 340 : 110));

    if (showNews) {
      const trading = prices.map((p) => p.trade_date);
      const align = alignToTradingDays(newsDays.map((n) => n.day), trading);
      const merged = new Map<string, DayEvents>();
      for (const n of newsDays) {
        const t = align.get(n.day);
        if (!t) continue;
        const m = merged.get(t) ?? { day: t, bullish: 0, bearish: 0, neutral: 0, insufficient: 0 };
        m.bullish += n.bullish;
        m.bearish += n.bearish;
        m.neutral += n.neutral;
        m.insufficient += n.insufficient;
        merged.set(t, m);
      }
      const markers: SeriesMarker<Time>[] = [];
      for (const m of [...merged.values()].sort((a, b) => a.day.localeCompare(b.day))) {
        const net = m.bullish - m.bearish;
        const total = m.bullish + m.bearish + m.neutral + m.insufficient;
        // only mark days where one direction clearly dominates, to keep the chart readable
        if (Math.abs(net) < Math.max(3, total * 0.3)) continue;
        markers.push(
          net > 0
            ? { time: toTime(m.day), position: "belowBar", shape: "arrowUp", color: bull, size: 0.8 }
            : { time: toTime(m.day), position: "aboveBar", shape: "arrowDown", color: bear, size: 0.8 },
        );
      }
      const fAlign = alignToTradingDays(filings.map((f) => f.filed_date), trading);
      for (const f of filings) {
        const t = fAlign.get(f.filed_date);
        if (t) markers.push({ time: toTime(t), position: "aboveBar", shape: "square", color: accent, text: f.form });
      }
      markers.sort((a, b) => String(a.time).localeCompare(String(b.time)));
      createSeriesMarkers(candles, markers);
    }

    chart.subscribeCrosshairMove((param) => {
      const t = param.time ? String(param.time) : null;
      setHover(t ? (byDate.get(t) ?? null) : null);
    });

    // default view: last ~6 months
    const from = prices[Math.max(0, prices.length - 126)]!.trade_date;
    chart.timeScale().setVisibleRange({ from: toTime(from), to: toTime(last!.trade_date) });

    return () => {
      chart.remove();
      chartRef.current = null;
    };
  }, [prices, newsDays, filings, overlays, lower, showNews, byDate, last]);

  const toggle = <T,>(set: Set<T>, v: T, setter: (s: Set<T>) => void) => {
    const n = new Set(set);
    if (n.has(v)) n.delete(v);
    else n.add(v);
    setter(n);
  };

  const shown = hover ?? last;
  if (prices.length === 0) {
    return <p className="py-10 text-center text-xs text-muted">No price data in this snapshot.</p>;
  }

  return (
    <div>
      <div className="mb-2 flex flex-wrap items-center gap-1.5" role="group" aria-label="Chart overlays">
        {(
          [
            ["sma20", "SMA 20"],
            ["sma50", "SMA 50"],
            ["sma200", "SMA 200"],
            ["bb", "Bollinger 20/2"],
          ] as [Overlay, string][]
        ).map(([k, l]) => (
          <Button key={k} size="sm" variant="toggle" aria-pressed={overlays.has(k)} onClick={() => toggle(overlays, k, setOverlays)}>
            {l}
          </Button>
        ))}
        <span className="mx-1 h-4 w-px bg-border" aria-hidden />
        {(
          [
            ["rsi", "RSI 14"],
            ["macd", "MACD 12/26/9"],
            ["atr", "ATR 14"],
          ] as [Lower, string][]
        ).map(([k, l]) => (
          <Button key={k} size="sm" variant="toggle" aria-pressed={lower.has(k)} onClick={() => toggle(lower, k, setLower)}>
            {l}
          </Button>
        ))}
        <span className="mx-1 h-4 w-px bg-border" aria-hidden />
        <Button size="sm" variant="toggle" aria-pressed={showNews} onClick={() => setShowNews(!showNews)}>
          News &amp; filing markers
        </Button>
      </div>
      {shown && (
        <div className="num mb-1 flex flex-wrap gap-x-3 text-[11px] text-muted" aria-live="polite">
          <span className="text-text">{fmtMarketDate(shown.trade_date)}</span>
          <span>O {fmtPrice(shown.open)}</span>
          <span>H {fmtPrice(shown.high)}</span>
          <span>L {fmtPrice(shown.low)}</span>
          <span>C {fmtPrice(shown.close)}</span>
          <span>Vol {fmtVolume(shown.volume)}</span>
          {shown.rsi_14 != null && <span>RSI {shown.rsi_14.toFixed(1)}</span>}
        </div>
      )}
      <div
        ref={box}
        data-testid="price-chart"
        className="w-full"
        style={{ height: 340 + 110 * lower.size }}
        role="img"
        aria-label="Candlestick price chart with volume, technical indicators and news markers"
      />
      <p className="mt-1.5 text-[10px] text-muted">
        ▲/▼ markers: trading days where bullish or bearish stories clearly outnumber the other
        direction (net ≥ 3 and ≥ 30% of that day’s stories). ■ SEC filings. Daily end-of-day data, not real time.
      </p>
    </div>
  );
}
