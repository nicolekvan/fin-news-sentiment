import type { Metadata } from "next";
import { ClipboardList } from "lucide-react";
import { ReturnsChart } from "@/components/charts/returns-chart";
import { SentimentBadge } from "@/components/sentiment";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TD, TH, THead, TR } from "@/components/ui/table";
import { getPerformance } from "@/lib/data";
import { fmtPct, LABEL_TEXT } from "@/lib/format";
import type { Classification, ErrorExample, ForwardReturns, Label, SystemResult } from "@/lib/types";

export const metadata: Metadata = { title: "Model Performance · MarketLens AI" };

const SYSTEM_TEXT: Record<string, string> = {
  finbert_evidence_v1: "FinBERT + decision rules (deployed)",
  finbert_raw_argmax: "FinBERT top class, no abstention",
  majority_class: "Majority class (always the most common label)",
  hybrid_finbert_claude: "FinBERT + Claude review",
};

const f2 = (v: number | null | undefined) => (v == null ? "—" : v.toFixed(2));
const ci = (r?: [number, number]) => (r ? `${r[0].toFixed(2)}–${r[1].toFixed(2)}` : "—");

function SystemsTable({ systems }: { systems: Record<string, SystemResult> }) {
  return (
    <Table>
      <THead>
        <tr>
          <TH>System</TH>
          <TH className="text-right">n</TH>
          <TH className="text-right">Accuracy</TH>
          <TH className="text-right">95% CI</TH>
          <TH className="text-right">Macro F1</TH>
          <TH className="text-right">95% CI</TH>
        </tr>
      </THead>
      <tbody>
        {Object.entries(systems).map(([k, s]) => (
          <TR key={k}>
            <TD className={k === "finbert_evidence_v1" ? "font-semibold" : undefined}>{SYSTEM_TEXT[k] ?? k}</TD>
            {s.status === "not_run" ? (
              <TD colSpan={5} className="text-muted">Not run: {s.reason}</TD>
            ) : (
              <>
                <TD className="num text-right">{s.n}</TD>
                <TD className="num text-right">{f2(s.accuracy)}</TD>
                <TD className="num text-right text-muted">{ci(s.ci95?.accuracy)}</TD>
                <TD className="num text-right">{f2(s.macro_f1)}</TD>
                <TD className="num text-right text-muted">{ci(s.ci95?.macro_f1)}</TD>
              </>
            )}
          </TR>
        ))}
      </tbody>
    </Table>
  );
}

function Confusion({ c }: { c: Classification }) {
  const { labels, rows_gold_cols_pred: m } = c.confusion_matrix;
  const max = Math.max(1, ...m.flat());
  return (
    <div className="overflow-x-auto">
      <table className="text-xs" aria-label="Confusion matrix: rows are human labels, columns are model labels">
        <thead>
          <tr>
            <th className="p-1.5 text-left text-[10px] font-normal text-muted">human ↓ · model →</th>
            {labels.map((l) => (
              <th key={l} className="p-1.5 text-[10px] font-semibold uppercase text-muted">{LABEL_TEXT[l]}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {labels.map((g, i) => (
            <tr key={g}>
              <th className="p-1.5 text-left text-[10px] font-semibold uppercase text-muted">{LABEL_TEXT[g]}</th>
              {labels.map((p, j) => {
                const v = m[i]?.[j] ?? 0;
                const diag = i === j;
                return (
                  <td
                    key={p}
                    className="num h-11 w-20 border border-border text-center"
                    style={{
                      background: `color-mix(in oklab, ${diag ? "var(--accent)" : "var(--bear)"} ${Math.round((v / max) * 55)}%, var(--panel))`,
                    }}
                  >
                    {v}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function PerClass({ s }: { s: SystemResult }) {
  if (!s.per_class) return null;
  return (
    <Table>
      <THead>
        <tr>
          <TH>Class</TH>
          <TH className="text-right">Precision</TH>
          <TH className="text-right">Recall</TH>
          <TH className="text-right">F1</TH>
          <TH className="text-right">Support</TH>
        </tr>
      </THead>
      <tbody>
        {(Object.keys(s.per_class) as Label[]).map((l) => {
          const r = s.per_class![l];
          return (
            <TR key={l}>
              <TD><SentimentBadge label={l} /></TD>
              <TD className="num text-right">{f2(r.precision)}</TD>
              <TD className="num text-right">{f2(r.recall)}</TD>
              <TD className="num text-right">{f2(r.f1)}</TD>
              <TD className="num text-right">{r.support}</TD>
            </TR>
          );
        })}
      </tbody>
    </Table>
  );
}

function Examples({ title, items }: { title: string; items: ErrorExample[] }) {
  return (
    <div>
      <h3 className="text-xs font-semibold">{title}</h3>
      {items.length === 0 ? (
        <p className="mt-1 text-xs text-muted">None in the evaluation set.</p>
      ) : (
        <ul className="mt-1.5 space-y-2">
          {items.map((e, i) => (
            <li key={i} className="text-xs leading-snug">
              <span className="font-semibold">{e.ticker}</span> · {e.headline}
              <div className="mt-0.5 flex flex-wrap items-center gap-1 text-[11px] text-muted">
                model <SentimentBadge label={e.model} /> human <SentimentBadge label={e.human} />
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ReturnsSection({ fr }: { fr: ForwardReturns }) {
  return (
    <Card data-testid="returns-section">
      <CardHeader>
        <CardTitle>What stocks did after bullish and bearish classifications</CardTitle>
        <span className="text-[10px] text-muted">return relative to {fr.benchmark} · historical association</span>
      </CardHeader>
      <CardContent className="space-y-4">
        <ReturnsChart rows={fr.by_signal} horizons={fr.horizons} />
        <Table>
          <THead>
            <tr>
              <TH>Horizon</TH>
              <TH>After</TH>
              <TH className="text-right">Company-days</TH>
              <TH className="text-right">Mean vs {fr.benchmark}</TH>
              <TH className="text-right">95% CI</TH>
              <TH className="text-right">Median</TH>
              <TH className="text-right" title="Share of company-days that moved in the labelled direction relative to the benchmark">Hit rate</TH>
            </tr>
          </THead>
          <tbody>
            {fr.by_signal.map((r) => (
              <TR key={`${r.horizon}-${r.signal}`}>
                <TD className="num">{r.horizon}d</TD>
                <TD><SentimentBadge label={r.signal} /></TD>
                <TD className="num text-right">{r.n}</TD>
                <TD className="num text-right">{fmtPct(r.mean_rel, 2)}</TD>
                <TD className="num text-right text-muted">
                  {r.ci_low != null && r.ci_high != null ? `${fmtPct(r.ci_low, 2)} to ${fmtPct(r.ci_high, 2)}` : "—"}
                </TD>
                <TD className="num text-right">{fmtPct(r.median_rel, 2)}</TD>
                <TD className="num text-right">{r.hit_rate == null ? "—" : `${(r.hit_rate * 100).toFixed(0)}%`}</TD>
              </TR>
            ))}
          </tbody>
        </Table>
        <p className="text-xs leading-relaxed text-muted">
          Bullish-minus-bearish spread:{" "}
          {fr.spread.map((s, i) => (
            <span key={s.horizon} className="num">
              {i > 0 ? " · " : ""}
              {s.horizon}d {fmtPct(s.spread, 2)} (95% CI {fmtPct(s.ci_low, 2)} to {fmtPct(s.ci_high, 2)})
            </span>
          ))}
          . A confidence interval that includes 0% means no reliable difference.
        </p>
        <div className="rounded-md border border-border bg-panel-2/50 p-3 text-xs leading-relaxed text-muted">
          <strong className="text-text">How to read this.</strong> Each company-day nets that day&apos;s
          bullish and bearish stories into one signal ({fr.n_company_days} company-days, {fr.n_mixed} mixed
          days excluded). Entry is the first daily close after publication, so after-hours news counts
          from the next session and nothing uses information from after the story. The data covers about
          90 days and 10 stocks; 20-day windows overlap, so the intervals are optimistic. This shows what
          happened after past labels, not whether the labels can predict returns, and the 10 companies
          were chosen by today&apos;s market cap, which favours stocks that did well.
        </div>
      </CardContent>
    </Card>
  );
}

export default function PerformancePage() {
  const perf = getPerformance();
  const c = perf?.classification ?? null;
  const main = c?.systems.finbert_evidence_v1;
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold">Model Performance</h1>
        <p className="text-xs text-muted">
          Two separate questions: does the model agree with a careful human reader, and what did
          stocks do after its labels? Text sentiment, business impact and stock returns are different
          things; a bullish label is not a price prediction.
        </p>
      </div>

      {c && main ? (
        <>
          <section className="grid grid-cols-2 gap-2 md:grid-cols-4" aria-label="Headline metrics" data-testid="classification-section">
            {[
              ["Macro F1", f2(main.macro_f1), `95% CI ${ci(main.ci95?.macro_f1)}`],
              ["Accuracy", f2(main.accuracy), `95% CI ${ci(main.ci95?.accuracy)}`],
              ["Labelled pairs", String(c.n_labelled), `${main.n} used for sentiment`],
              ["Company-match precision", c.linking.precision == null ? "—" : f2(c.linking.precision), `${c.linking.not_about} of ${c.linking.n} not about the company`],
            ].map(([k, v, sub]) => (
              <Card key={k} className="px-4 py-3">
                <div className="num text-2xl font-semibold leading-none">{v}</div>
                <div className="mt-1 text-[11px] uppercase tracking-wide text-muted">{k}</div>
                <div className="mt-0.5 text-[10px] text-muted">{sub}</div>
              </Card>
            ))}
          </section>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader><CardTitle>Systems compared on the same labelled set</CardTitle></CardHeader>
              <CardContent><SystemsTable systems={c.systems} /></CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Confusion matrix (deployed model)</CardTitle></CardHeader>
              <CardContent><Confusion c={c} /></CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Per-class precision and recall</CardTitle></CardHeader>
              <CardContent><PerClass s={main} /></CardContent>
            </Card>
            <Card>
              <CardHeader><CardTitle>Stability over time</CardTitle></CardHeader>
              <CardContent className="space-y-3 text-xs">
                <Table>
                  <THead>
                    <tr><TH>Period</TH><TH className="text-right">n</TH><TH className="text-right">Accuracy</TH><TH className="text-right">Macro F1</TH></tr>
                  </THead>
                  <tbody>
                    {Object.entries(c.periods).map(([k, p]) => (
                      <TR key={k}>
                        <TD>{k === "earlier_half" ? "Earlier half" : "Later half"} <span className="text-muted">({p.from.slice(0, 10)} – {p.to.slice(0, 10)})</span></TD>
                        <TD className="num text-right">{p.n}</TD>
                        <TD className="num text-right">{f2(p.accuracy)}</TD>
                        <TD className="num text-right">{f2(p.macro_f1)}</TD>
                      </TR>
                    ))}
                  </tbody>
                </Table>
                <p className="leading-relaxed text-muted">
                  The labelled set is split by publication date. FinBERT is pretrained and the decision
                  thresholds were fixed before any label existed, so no part of this set was used for
                  training or tuning.
                </p>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader><CardTitle>Error analysis</CardTitle></CardHeader>
            <CardContent className="grid gap-5 md:grid-cols-3">
              <Examples title="False directional calls (model said bullish/bearish, human disagreed)" items={c.errors.false_directional} />
              <Examples title="Missed directional news (human said bullish/bearish)" items={c.errors.missed_directional} />
              <Examples title="Ambiguous to the human reader" items={c.errors.ambiguous} />
            </CardContent>
          </Card>
        </>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center gap-2 py-12 text-center" data-testid="performance-empty">
            <ClipboardList className="h-6 w-6 text-muted" aria-hidden />
            <p className="text-sm font-medium">Classification metrics: labelling in progress</p>
            <p className="max-w-md text-xs text-muted">
              Precision, recall and F1 appear here once the manually labelled evaluation set is
              complete. No numbers are shown until they have been measured.
            </p>
          </CardContent>
        </Card>
      )}

      {perf?.forward_returns ? (
        <ReturnsSection fr={perf.forward_returns} />
      ) : (
        <Card>
          <CardContent className="py-10 text-center text-xs text-muted">Return analysis not available in this snapshot.</CardContent>
        </Card>
      )}
    </div>
  );
}
