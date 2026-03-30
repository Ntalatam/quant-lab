"use client";

import { use, useState } from "react";
import { useBacktestResult, useBacktestList } from "@/hooks/useBacktest";
import { PageLoading } from "@/components/shared/LoadingSpinner";
import { ErrorMessage } from "@/components/shared/ErrorBoundary";
import { formatPercent, formatRatio } from "@/lib/formatters";
import { ArrowLeft, TrendingUp, TrendingDown, Minus } from "lucide-react";
import Link from "next/link";
import type { PerformanceMetrics } from "@/lib/types";

interface DiffMetric {
  key: keyof PerformanceMetrics;
  label: string;
  format: (v: number) => string;
  higherIsBetter: boolean;
}

const DIFF_METRICS: DiffMetric[] = [
  { key: "total_return_pct",        label: "Total Return",       format: formatPercent,  higherIsBetter: true  },
  { key: "cagr_pct",                label: "CAGR",               format: formatPercent,  higherIsBetter: true  },
  { key: "sharpe_ratio",            label: "Sharpe Ratio",       format: formatRatio,    higherIsBetter: true  },
  { key: "sortino_ratio",           label: "Sortino Ratio",      format: formatRatio,    higherIsBetter: true  },
  { key: "calmar_ratio",            label: "Calmar Ratio",       format: formatRatio,    higherIsBetter: true  },
  { key: "max_drawdown_pct",        label: "Max Drawdown",       format: formatPercent,  higherIsBetter: false },
  { key: "max_drawdown_duration_days", label: "DD Duration",     format: (v) => `${v}d`, higherIsBetter: false },
  { key: "annualized_volatility_pct",  label: "Volatility",      format: formatPercent,  higherIsBetter: false },
  { key: "win_rate_pct",            label: "Win Rate",           format: (v) => formatPercent(v, 1), higherIsBetter: true },
  { key: "profit_factor",           label: "Profit Factor",      format: formatRatio,    higherIsBetter: true  },
  { key: "var_95_pct",              label: "VaR (95%)",          format: formatPercent,  higherIsBetter: false },
  { key: "cvar_95_pct",             label: "CVaR (95%)",         format: formatPercent,  higherIsBetter: false },
  { key: "alpha",                   label: "Alpha",              format: formatPercent,  higherIsBetter: true  },
  { key: "beta",                    label: "Beta",               format: formatRatio,    higherIsBetter: false },
  { key: "information_ratio",       label: "Info Ratio",         format: formatRatio,    higherIsBetter: true  },
  { key: "total_cost",              label: "Total Cost",         format: (v) => `$${v.toFixed(0)}`, higherIsBetter: false },
  { key: "cost_drag_bps",           label: "Cost Drag",          format: (v) => `${v} bps`, higherIsBetter: false },
];

function DeltaCell({
  current,
  other,
  format,
  higherIsBetter,
}: {
  current: number;
  other: number;
  format: (v: number) => string;
  higherIsBetter: boolean;
}) {
  const delta = current - other;
  const improved = higherIsBetter ? delta > 0 : delta < 0;
  const neutral = Math.abs(delta) < 1e-6;

  if (neutral) {
    return (
      <div className="flex items-center justify-end gap-1 text-text-muted">
        <Minus size={10} />
        <span className="font-mono text-[11px]">0</span>
      </div>
    );
  }

  const sign = delta > 0 ? "+" : "";
  return (
    <div
      className="flex items-center justify-end gap-1"
      style={{ color: improved ? "var(--color-accent-green)" : "var(--color-accent-red)" }}
    >
      {improved ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
      <span className="font-mono text-[11px] tabular-nums font-semibold">
        {sign}{format(delta)}
      </span>
    </div>
  );
}

export default function DiffPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: current, isLoading, error } = useBacktestResult(id);
  const { data: allRuns } = useBacktestList();
  const [otherId, setOtherId] = useState<string>("");
  const { data: other } = useBacktestResult(otherId || undefined);

  if (isLoading) return <PageLoading />;
  if (error || !current) return <ErrorMessage message={error?.message ?? "Not found"} />;

  const otherOptions = allRuns?.filter((r) => r.id !== id) ?? [];

  return (
    <div>
      {/* Header */}
      <div className="flex items-center gap-3 mb-7">
        <Link href={`/backtest/${id}`} className="text-text-muted hover:text-text-primary transition-colors">
          <ArrowLeft size={18} />
        </Link>
        <div>
          <h1 className="text-xl font-bold text-text-primary tracking-tight">Backtest Diff</h1>
          <p className="text-xs text-text-muted mt-0.5">
            {current.config.strategy_id} · {current.config.tickers.join(", ")} ·{" "}
            {current.config.start_date} → {current.config.end_date}
          </p>
        </div>
      </div>

      {/* Run selector */}
      <div
        className="rounded-md p-4 mb-6"
        style={{
          background: "var(--color-bg-card)",
          border: "1px solid var(--color-border)",
          boxShadow: "0 1px 3px rgba(0,0,0,0.4)",
        }}
      >
        <label className="section-label mb-2 block">Compare against</label>
        <select
          value={otherId}
          onChange={(e) => setOtherId(e.target.value)}
          className="w-full bg-bg-primary border border-border rounded px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-blue"
        >
          <option value="">— Select a run to compare —</option>
          {otherOptions.map((r) => (
            <option key={r.id} value={r.id}>
              {r.strategy_name} · {r.tickers.join(", ")} · {r.start_date}→{r.end_date} ·{" "}
              {formatPercent(r.total_return_pct)} · Sharpe {formatRatio(r.sharpe_ratio)}
            </option>
          ))}
        </select>
      </div>

      {!other && (
        <div
          className="rounded-md p-10 text-center"
          style={{
            background: "var(--color-bg-card)",
            border: "1px solid var(--color-border)",
          }}
        >
          <p className="text-text-muted text-sm">Select a run to compare metrics</p>
        </div>
      )}

      {other && (
        <div
          className="rounded-md overflow-hidden"
          style={{
            background: "var(--color-bg-card)",
            border: "1px solid var(--color-border)",
            boxShadow: "0 1px 3px rgba(0,0,0,0.4)",
          }}
        >
          <div
            className="px-5 py-3"
            style={{ borderBottom: "1px solid var(--color-border)" }}
          >
            <h3 className="text-sm font-semibold text-text-primary">Metric Diff</h3>
            <p className="text-[10px] text-text-muted mt-0.5">
              Green delta = improvement · Red delta = regression relative to selected baseline
            </p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs font-mono">
              <thead>
                <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
                  <th className="section-label py-2.5 px-4 text-left font-normal">Metric</th>
                  <th className="section-label py-2.5 px-4 text-right font-normal text-accent-blue">
                    This Run
                  </th>
                  <th className="section-label py-2.5 px-4 text-right font-normal text-text-muted">
                    Baseline
                  </th>
                  <th className="section-label py-2.5 px-4 text-right font-normal">Δ Change</th>
                </tr>
              </thead>
              <tbody>
                {DIFF_METRICS.map((dm) => {
                  const curVal = (current.metrics as unknown as Record<string, number>)[dm.key as string] ?? 0;
                  const othVal = (other.metrics as unknown as Record<string, number>)[dm.key as string] ?? 0;
                  return (
                    <tr
                      key={dm.key as string}
                      className="hover:bg-bg-hover transition-colors"
                      style={{ borderBottom: "1px solid rgba(37,37,53,0.5)" }}
                    >
                      <td className="py-2 px-4 text-text-secondary">{dm.label}</td>
                      <td className="py-2 px-4 text-right tabular-nums text-accent-blue font-semibold">
                        {dm.format(curVal)}
                      </td>
                      <td className="py-2 px-4 text-right tabular-nums text-text-muted">
                        {dm.format(othVal)}
                      </td>
                      <td className="py-2 px-4">
                        <DeltaCell
                          current={curVal}
                          other={othVal}
                          format={dm.format}
                          higherIsBetter={dm.higherIsBetter}
                        />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
