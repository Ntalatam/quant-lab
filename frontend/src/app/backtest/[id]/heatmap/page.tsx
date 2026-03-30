"use client";

import { use, useState } from "react";
import { useBacktestResult } from "@/hooks/useBacktest";
import { useStrategies } from "@/hooks/useAnalytics";
import { PageLoading } from "@/components/shared/LoadingSpinner";
import { ErrorMessage } from "@/components/shared/ErrorBoundary";
import { ParameterHeatmap } from "@/components/charts/ParameterHeatmap";
import { api } from "@/lib/api";
import type { Sweep2DResult } from "@/lib/types";
import { ArrowLeft, Loader2 } from "lucide-react";
import Link from "next/link";

const HEATMAP_METRICS = [
  { value: "sharpe_ratio",              label: "Sharpe Ratio" },
  { value: "total_return_pct",          label: "Total Return %" },
  { value: "cagr_pct",                  label: "CAGR %" },
  { value: "max_drawdown_pct",          label: "Max Drawdown %" },
  { value: "sortino_ratio",             label: "Sortino Ratio" },
  { value: "calmar_ratio",              label: "Calmar Ratio" },
];

export default function HeatmapPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: result, isLoading, error } = useBacktestResult(id);
  const { data: strategies } = useStrategies();

  const [paramX, setParamX]   = useState("");
  const [paramY, setParamY]   = useState("");
  const [stepsX, setStepsX]   = useState(5);
  const [stepsY, setStepsY]   = useState(5);
  const [metric, setMetric]   = useState("sharpe_ratio");
  const [running, setRunning] = useState(false);
  const [heatmap, setHeatmap] = useState<Sweep2DResult | null>(null);
  const [runError, setRunError] = useState("");

  if (isLoading) return <PageLoading />;
  if (error || !result) return <ErrorMessage message={error?.message ?? "Not found"} />;

  const strategy = strategies?.find((s) => s.id === result.config.strategy_id);
  const numericParams = strategy?.params.filter(
    (p) => (p.type === "int" || p.type === "float") && p.min != null && p.max != null
  ) ?? [];

  const buildValues = (paramName: string, steps: number): number[] => {
    const p = numericParams.find((np) => np.name === paramName);
    if (!p || p.min == null || p.max == null) return [];
    const step = (p.max - p.min) / (steps - 1);
    return Array.from({ length: steps }, (_, i) =>
      p.type === "int"
        ? Math.round(p.min! + step * i)
        : parseFloat((p.min! + step * i).toFixed(4))
    );
  };

  const handleRun = async () => {
    if (!paramX || !paramY || paramX === paramY) {
      setRunError("Select two different parameters.");
      return;
    }
    const vx = buildValues(paramX, stepsX);
    const vy = buildValues(paramY, stepsY);
    if (!vx.length || !vy.length) {
      setRunError("Parameters must have min/max defined.");
      return;
    }
    setRunError("");
    setRunning(true);
    try {
      const res = await api.runSweep2D(result.config, paramX, vx, paramY, vy, metric);
      setHeatmap(res);
    } catch (e: unknown) {
      setRunError(e instanceof Error ? e.message : "Sweep failed");
    } finally {
      setRunning(false);
    }
  };

  const inputCls =
    "w-full bg-bg-primary border border-border rounded px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-blue";

  return (
    <div>
      {/* Header */}
      <div className="flex items-center gap-3 mb-7">
        <Link
          href={`/backtest/${id}`}
          className="text-text-muted hover:text-text-primary transition-colors"
        >
          <ArrowLeft size={18} />
        </Link>
        <div>
          <h1 className="text-xl font-bold text-text-primary tracking-tight">
            2D Parameter Heatmap
          </h1>
          <p className="text-xs text-text-muted mt-0.5">
            {result.config.strategy_id} · {result.config.tickers.join(", ")} ·{" "}
            {result.config.start_date} → {result.config.end_date}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 mb-6">
        {/* Config panel */}
        <div
          className="lg:col-span-1 rounded-md p-5 space-y-4"
          style={{
            background: "var(--color-bg-card)",
            border: "1px solid var(--color-border)",
          }}
        >
          <div>
            <p className="section-label mb-2">X Axis Parameter</p>
            <select value={paramX} onChange={(e) => setParamX(e.target.value)} className={inputCls}>
              <option value="">Select…</option>
              {numericParams.map((p) => (
                <option key={p.name} value={p.name}>{p.label}</option>
              ))}
            </select>
          </div>
          <div>
            <div className="flex justify-between mb-1">
              <p className="section-label">X Steps</p>
              <span className="text-xs font-mono text-text-primary">{stepsX}</span>
            </div>
            <input
              type="range" min={3} max={10} value={stepsX}
              onChange={(e) => setStepsX(Number(e.target.value))}
              className="w-full accent-accent-blue"
            />
          </div>
          <div>
            <p className="section-label mb-2">Y Axis Parameter</p>
            <select value={paramY} onChange={(e) => setParamY(e.target.value)} className={inputCls}>
              <option value="">Select…</option>
              {numericParams.map((p) => (
                <option key={p.name} value={p.name}>{p.label}</option>
              ))}
            </select>
          </div>
          <div>
            <div className="flex justify-between mb-1">
              <p className="section-label">Y Steps</p>
              <span className="text-xs font-mono text-text-primary">{stepsY}</span>
            </div>
            <input
              type="range" min={3} max={10} value={stepsY}
              onChange={(e) => setStepsY(Number(e.target.value))}
              className="w-full accent-accent-blue"
            />
          </div>
          <div>
            <p className="section-label mb-2">Metric</p>
            <select value={metric} onChange={(e) => setMetric(e.target.value)} className={inputCls}>
              {HEATMAP_METRICS.map((m) => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </div>

          {runError && <p className="text-xs text-accent-red">{runError}</p>}

          <button
            onClick={handleRun}
            disabled={running || !paramX || !paramY}
            className="w-full flex items-center justify-center gap-2 font-semibold rounded py-2.5 text-sm transition-all disabled:opacity-40 disabled:cursor-not-allowed"
            style={
              !running && paramX && paramY
                ? {
                    background: "var(--color-accent-blue)",
                    color: "var(--color-bg-primary)",
                    boxShadow: "0 0 16px rgba(68,136,255,0.25)",
                  }
                : {
                    background: "rgba(68,136,255,0.12)",
                    color: "var(--color-accent-blue)",
                    border: "1px solid rgba(68,136,255,0.22)",
                  }
            }
          >
            {running ? (
              <>
                <Loader2 size={14} className="animate-spin" />
                Running {stepsX * stepsY} backtests…
              </>
            ) : (
              `Run ${stepsX * stepsY} Backtests`
            )}
          </button>

          <div
            className="rounded p-2.5 text-[10px] text-text-muted leading-relaxed"
            style={{ background: "var(--color-bg-primary)", border: "1px solid var(--color-border)" }}
          >
            A broad <span className="text-accent-green">green plateau</span> means the
            strategy is robust — parameters near each other produce similar results.
            A narrow peak surrounded by red indicates overfitting.
          </div>
        </div>

        {/* Heatmap */}
        <div className="lg:col-span-3">
          {running ? (
            <div
              className="h-80 flex flex-col items-center justify-center gap-3 rounded-md"
              style={{ background: "var(--color-bg-card)", border: "1px solid var(--color-border)" }}
            >
              <Loader2 size={28} className="animate-spin text-accent-blue" />
              <p className="text-sm text-text-secondary">
                Running {stepsX * stepsY} backtests…
              </p>
              <p className="text-xs text-text-muted">
                Each cell is a full simulation. This may take a moment.
              </p>
            </div>
          ) : heatmap ? (
            <div
              className="rounded-md p-5"
              style={{
                background: "var(--color-bg-card)",
                border: "1px solid var(--color-border)",
                boxShadow: "0 1px 3px rgba(0,0,0,0.4)",
              }}
            >
              <ParameterHeatmap result={heatmap} />
            </div>
          ) : (
            <div
              className="h-80 flex flex-col items-center justify-center gap-2 rounded-md"
              style={{ background: "var(--color-bg-card)", border: "1px solid var(--color-border)" }}
            >
              <p className="text-text-secondary text-sm">Configure parameters and run the sweep</p>
              <p className="text-text-muted text-xs max-w-sm text-center">
                Each cell in the grid represents one complete backtest. Color intensity
                shows how that parameter combination performs on the selected metric.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
