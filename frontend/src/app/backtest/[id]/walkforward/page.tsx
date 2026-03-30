"use client";

import { use, useState } from "react";
import { useBacktestResult } from "@/hooks/useBacktest";
import { PageLoading } from "@/components/shared/LoadingSpinner";
import { ErrorMessage } from "@/components/shared/ErrorBoundary";
import { api } from "@/lib/api";
import type { WalkForwardResult } from "@/lib/types";
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis,
  Tooltip, CartesianGrid, Legend, ReferenceLine,
} from "recharts";
import { CHART_COLORS } from "@/lib/constants";
import { formatCompactDate, formatPercent, formatRatio } from "@/lib/formatters";
import { ArrowLeft, Loader2, CheckCircle, XCircle } from "lucide-react";
import Link from "next/link";

function EfficiencyBadge({ value }: { value: number | null }) {
  if (value === null) return <span className="text-text-muted text-xs">—</span>;
  const pct = Math.round(value * 100);
  const color = value >= 0.7 ? "var(--color-accent-green)" : value >= 0.4 ? "var(--color-accent-yellow)" : "var(--color-accent-red)";
  const label = value >= 0.7 ? "Robust" : value >= 0.4 ? "Moderate" : "Fragile";
  return (
    <div className="flex items-center gap-2">
      <span className="font-mono font-bold text-2xl" style={{ color }}>{pct}%</span>
      <span className="text-xs px-2 py-0.5 rounded font-medium" style={{
        background: `${color}18`, border: `1px solid ${color}33`, color
      }}>{label}</span>
    </div>
  );
}

export default function WalkForwardPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: result, isLoading, error } = useBacktestResult(id);

  const [nFolds, setNFolds]     = useState(5);
  const [trainPct, setTrainPct] = useState(0.7);
  const [running, setRunning]   = useState(false);
  const [wfa, setWfa]           = useState<WalkForwardResult | null>(null);
  const [runError, setRunError] = useState("");

  if (isLoading) return <PageLoading />;
  if (error || !result) return <ErrorMessage message={error?.message ?? "Not found"} />;

  const handleRun = async () => {
    setRunError("");
    setRunning(true);
    try {
      const res = await api.runWalkForward(result.config, nFolds, trainPct);
      setWfa(res);
    } catch (e: unknown) {
      setRunError(e instanceof Error ? e.message : "Walk-forward failed");
    } finally {
      setRunning(false);
    }
  };

  // Merge IS curve + OOS curve into overlay chart
  const overlayData = (() => {
    if (!wfa) return [];
    const map = new Map<string, { date: string; is?: number; oos?: number }>();
    result.equity_curve.forEach((p) => {
      map.set(p.date, { date: p.date, is: p.value });
    });
    wfa.oos_equity_curve.forEach((p) => {
      const ex = map.get(p.date);
      if (ex) ex.oos = p.value;
      else map.set(p.date, { date: p.date, oos: p.value });
    });
    return Array.from(map.values()).sort(
      (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
    );
  })();

  const inputCls = "bg-bg-primary border border-border rounded px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-blue";

  return (
    <div>
      {/* Header */}
      <div className="flex items-center gap-3 mb-7">
        <Link href={`/backtest/${id}`} className="text-text-muted hover:text-text-primary transition-colors">
          <ArrowLeft size={18} />
        </Link>
        <div>
          <h1 className="text-xl font-bold text-text-primary tracking-tight">
            Walk-Forward Analysis
          </h1>
          <p className="text-xs text-text-muted mt-0.5">
            {result.config.strategy_id} · {result.config.tickers.join(", ")} ·{" "}
            {result.config.start_date} → {result.config.end_date}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-6">
        {/* Config */}
        <div className="rounded-md p-5 space-y-5" style={{ background: "var(--color-bg-card)", border: "1px solid var(--color-border)" }}>
          <div>
            <div className="flex justify-between mb-1">
              <p className="section-label">Number of Folds</p>
              <span className="text-xs font-mono text-text-primary">{nFolds}</span>
            </div>
            <input type="range" min={2} max={10} value={nFolds}
              onChange={(e) => setNFolds(Number(e.target.value))}
              className="w-full accent-accent-blue" />
            <p className="text-[10px] text-text-muted mt-1">
              {nFolds} folds × {Math.round(100 / nFolds)}% of the date range each
            </p>
          </div>
          <div>
            <div className="flex justify-between mb-1">
              <p className="section-label">Train / Test Split</p>
              <span className="text-xs font-mono text-text-primary">
                {Math.round(trainPct * 100)}% / {Math.round((1 - trainPct) * 100)}%
              </span>
            </div>
            <input type="range" min={50} max={90} step={5} value={Math.round(trainPct * 100)}
              onChange={(e) => setTrainPct(Number(e.target.value) / 100)}
              className="w-full accent-accent-blue" />
          </div>

          {runError && <p className="text-xs text-accent-red">{runError}</p>}

          <button onClick={handleRun} disabled={running}
            className="w-full flex items-center justify-center gap-2 font-semibold rounded py-2.5 text-sm transition-all disabled:opacity-40"
            style={!running ? {
              background: "var(--color-accent-blue)",
              color: "var(--color-bg-primary)",
              boxShadow: "0 0 16px rgba(68,136,255,0.25)",
            } : {
              background: "rgba(68,136,255,0.12)",
              color: "var(--color-accent-blue)",
              border: "1px solid rgba(68,136,255,0.22)",
            }}
          >
            {running ? <><Loader2 size={14} className="animate-spin" /> Running…</> : "Run Analysis"}
          </button>

          <div className="rounded p-2.5 text-[10px] text-text-muted leading-relaxed"
            style={{ background: "var(--color-bg-primary)", border: "1px solid var(--color-border)" }}>
            <p className="text-text-secondary font-medium mb-1">How it works</p>
            Each fold divides time into in-sample (IS) and out-of-sample (OOS) windows.
            The strategy runs with <em>fixed parameters</em> on each OOS slice.
            Stitching the OOS slices gives a continuous deployable equity curve.{" "}
            <span className="text-accent-green">Sharpe Efficiency</span> = avg OOS Sharpe ÷ avg IS Sharpe.
            Values near 1.0 indicate robustness.
          </div>
        </div>

        {/* Results */}
        <div className="lg:col-span-3 space-y-5">
          {!wfa && !running && (
            <div className="h-72 flex items-center justify-center rounded-md"
              style={{ background: "var(--color-bg-card)", border: "1px solid var(--color-border)" }}>
              <p className="text-text-secondary text-sm">Configure and run the analysis</p>
            </div>
          )}

          {running && (
            <div className="h-72 flex flex-col items-center justify-center gap-3 rounded-md"
              style={{ background: "var(--color-bg-card)", border: "1px solid var(--color-border)" }}>
              <Loader2 size={28} className="animate-spin text-accent-blue" />
              <p className="text-sm text-text-secondary">Running {nFolds} fold pairs…</p>
            </div>
          )}

          {wfa && (
            <>
              {/* Efficiency summary */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {[
                  { label: "Sharpe Efficiency", content: <EfficiencyBadge value={wfa.sharpe_efficiency} /> },
                  { label: "OOS Total Return",  content: <span className={`font-mono font-bold text-lg ${(wfa.oos_metrics.total_return_pct ?? 0) >= 0 ? "text-accent-green" : "text-accent-red"}`}>{formatPercent(wfa.oos_metrics.total_return_pct ?? 0)}</span> },
                  { label: "OOS Sharpe",        content: <span className="font-mono font-bold text-lg text-accent-blue">{formatRatio(wfa.oos_metrics.sharpe_ratio ?? 0)}</span> },
                  { label: "OOS Max Drawdown",  content: <span className="font-mono font-bold text-lg text-accent-red">{formatPercent(wfa.oos_metrics.max_drawdown_pct ?? 0)}</span> },
                ].map(({ label, content }) => (
                  <div key={label} className="rounded-md p-4 relative overflow-hidden"
                    style={{ background: "var(--color-bg-card)", border: "1px solid var(--color-border)" }}>
                    <p className="section-label mb-2">{label}</p>
                    {content}
                  </div>
                ))}
              </div>

              {/* Overlay chart */}
              <div className="rounded-md overflow-hidden" style={{ background: "var(--color-bg-card)", border: "1px solid var(--color-border)" }}>
                <div className="px-5 py-3" style={{ borderBottom: "1px solid var(--color-border)" }}>
                  <h3 className="text-sm font-semibold text-text-primary">IS vs OOS Equity Curves</h3>
                  <p className="text-[10px] text-text-muted mt-0.5">
                    Grey = in-sample (full period, given params) · Teal = stitched out-of-sample
                  </p>
                </div>
                <div className="p-4">
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={overlayData} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
                      <XAxis dataKey="date" tickFormatter={formatCompactDate}
                        stroke={CHART_COLORS.axis} tick={{ fontSize: 11 }} minTickGap={50} />
                      <YAxis tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
                        stroke={CHART_COLORS.axis} tick={{ fontSize: 11 }} width={60} />
                      <Tooltip
                        contentStyle={{ backgroundColor: CHART_COLORS.tooltip, border: `1px solid ${CHART_COLORS.grid}`, borderRadius: 4, fontSize: 12 }}
                        formatter={(v, name) => [`$${Number(v).toLocaleString()}`, name === "is" ? "In-Sample" : "Out-of-Sample"]}
                        labelFormatter={(l) => formatCompactDate(String(l))}
                      />
                      <Legend formatter={(v) => v === "is" ? "In-Sample (full period)" : "Out-of-Sample (WFA)"} />
                      {/* OOS fold boundaries */}
                      {wfa.folds.map((f) => (
                        <ReferenceLine key={f.fold} x={f.oos_start}
                          stroke="rgba(68,136,255,0.2)" strokeDasharray="3 3" />
                      ))}
                      <Line type="monotone" dataKey="is"  stroke={CHART_COLORS.benchmark} strokeWidth={1.5} dot={false} strokeDasharray="4 3" />
                      <Line type="monotone" dataKey="oos" stroke={CHART_COLORS.strategy}  strokeWidth={2}   dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Fold table */}
              <div className="rounded-md overflow-hidden" style={{ background: "var(--color-bg-card)", border: "1px solid var(--color-border)" }}>
                <div className="px-5 py-3" style={{ borderBottom: "1px solid var(--color-border)" }}>
                  <h3 className="text-sm font-semibold text-text-primary">Fold Statistics</h3>
                  <p className="text-[10px] text-text-muted mt-0.5">IS = in-sample · OOS = out-of-sample</p>
                </div>
                <table className="w-full text-xs font-mono">
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
                      {["Fold", "IS Period", "OOS Period", "IS Return", "IS Sharpe", "OOS Return", "OOS Sharpe", "OOS MaxDD", ""].map((h) => (
                        <th key={h} className={`section-label py-2.5 px-3 font-normal ${["IS Return","OOS Return","IS Sharpe","OOS Sharpe","OOS MaxDD"].includes(h) ? "text-right" : "text-left"}`}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {wfa.folds.map((f) => (
                      <tr key={f.fold} className="hover:bg-bg-hover transition-colors"
                        style={{ borderBottom: "1px solid rgba(37,37,53,0.6)" }}>
                        <td className="py-2 px-3 text-text-secondary">#{f.fold}</td>
                        <td className="py-2 px-3 text-text-muted text-[10px]">{f.is_start.slice(0,7)} → {f.is_end.slice(0,7)}</td>
                        <td className="py-2 px-3 text-text-muted text-[10px]">{f.oos_start.slice(0,7)} → {f.oos_end.slice(0,7)}</td>
                        <td className={`py-2 px-3 text-right tabular-nums ${(f.is_return ?? 0) >= 0 ? "text-accent-green" : "text-accent-red"}`}>{f.is_return != null ? formatPercent(f.is_return) : "—"}</td>
                        <td className="py-2 px-3 text-right tabular-nums text-text-primary">{f.is_sharpe?.toFixed(3) ?? "—"}</td>
                        <td className={`py-2 px-3 text-right tabular-nums font-semibold ${(f.oos_return ?? 0) >= 0 ? "text-accent-green" : "text-accent-red"}`}>{f.oos_return != null ? formatPercent(f.oos_return) : "—"}</td>
                        <td className="py-2 px-3 text-right tabular-nums text-accent-blue font-semibold">{f.oos_sharpe?.toFixed(3) ?? "—"}</td>
                        <td className="py-2 px-3 text-right tabular-nums text-accent-red">{f.oos_max_dd != null ? formatPercent(f.oos_max_dd) : "—"}</td>
                        <td className="py-2 px-3">
                          {f.ok ? <CheckCircle size={12} className="text-accent-green" /> : <XCircle size={12} className="text-accent-red" />}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
