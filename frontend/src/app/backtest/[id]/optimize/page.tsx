"use client";

import { use, useState, useCallback } from "react";
import { useBacktestResult } from "@/hooks/useBacktest";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { PageLoading } from "@/components/shared/LoadingSpinner";
import { ErrorMessage } from "@/components/shared/ErrorBoundary";
import { formatPercent, formatRatio } from "@/lib/formatters";
import { ArrowLeft, Play, CheckCircle2, Copy, Check } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import type { BayesOptParamSpec, BayesOptResult } from "@/lib/types";
import { useBacktestStore } from "@/store/backtest-store";

const OPTIMIZABLE_METRICS = [
  { value: "sharpe_ratio",            label: "Sharpe Ratio" },
  { value: "total_return_pct",        label: "Total Return %" },
  { value: "cagr_pct",                label: "CAGR %" },
  { value: "sortino_ratio",           label: "Sortino Ratio" },
  { value: "calmar_ratio",            label: "Calmar Ratio" },
  { value: "max_drawdown_pct",        label: "Max Drawdown % (minimize)" },
  { value: "profit_factor",           label: "Profit Factor" },
  { value: "win_rate_pct",            label: "Win Rate %" },
];

function formatMetricValue(value: number, metric: string): string {
  if (metric.endsWith("_pct")) return formatPercent(value);
  return formatRatio(value);
}

interface ParamRow {
  name: string;
  type: "int" | "float";
  low: string;
  high: string;
  step: string;
  enabled: boolean;
}

export default function OptimizePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const router = useRouter();
  const { setConfig } = useBacktestStore();

  const { data: result, isLoading, error } = useBacktestResult(id);
  const { data: strategyInfo } = useQuery({
    queryKey: ["strategy-params", result?.config.strategy_id],
    queryFn: () => api.getStrategyParams(result!.config.strategy_id),
    enabled: !!result,
  });

  // Build initial param rows from strategy definition
  const [paramRows, setParamRows] = useState<ParamRow[]>([]);
  const [rowsInitialized, setRowsInitialized] = useState(false);
  const [metric, setMetric] = useState("sharpe_ratio");
  const [nTrials, setNTrials] = useState(30);
  const [running, setRunning] = useState(false);
  const [optResult, setOptResult] = useState<BayesOptResult | null>(null);
  const [runError, setRunError] = useState<string | null>(null);
  const [appliedParams, setAppliedParams] = useState(false);

  // Initialize rows once strategy info loads
  if (strategyInfo && !rowsInitialized) {
    const rows: ParamRow[] = strategyInfo.params
      .filter((p) => p.type === "int" || p.type === "float")
      .map((p) => {
        const current = result?.config.params[p.name];
        const defaultVal = typeof current === "number" ? current : (p.default as number);
        const range = p.max !== undefined && p.min !== undefined
          ? { low: p.min, high: p.max }
          : { low: Math.max(0, defaultVal * 0.5), high: defaultVal * 2 };
        return {
          name: p.name,
          type: p.type as "int" | "float",
          low: String(Math.floor(range.low)),
          high: String(Math.ceil(range.high)),
          step: p.step !== undefined ? String(p.step) : p.type === "int" ? "1" : "",
          enabled: true,
        };
      });
    setParamRows(rows);
    setRowsInitialized(true);
  }

  const updateRow = useCallback(
    (idx: number, field: keyof ParamRow, value: string | boolean) => {
      setParamRows((prev) =>
        prev.map((r, i) => (i === idx ? { ...r, [field]: value } : r))
      );
    },
    []
  );

  const runOptimization = async () => {
    const specs: BayesOptParamSpec[] = paramRows
      .filter((r) => r.enabled)
      .map((r) => ({
        name: r.name,
        type: r.type,
        low: parseFloat(r.low),
        high: parseFloat(r.high),
        step: r.step ? parseFloat(r.step) : null,
      }))
      .filter((s) => !isNaN(s.low) && !isNaN(s.high) && s.low < s.high);

    if (specs.length === 0) {
      setRunError("Enable at least one parameter with a valid range.");
      return;
    }

    setRunning(true);
    setRunError(null);
    setOptResult(null);
    setAppliedParams(false);

    try {
      const res = await api.runBayesOpt(id, specs, metric, nTrials);
      setOptResult(res);
    } catch (e: unknown) {
      setRunError(e instanceof Error ? e.message : "Optimization failed");
    } finally {
      setRunning(false);
    }
  };

  const applyBestParams = () => {
    if (!optResult || !result) return;
    setConfig({
      strategy_id: result.config.strategy_id,
      params: optResult.best_params as Record<string, number>,
      tickers: result.config.tickers,
      benchmark: result.config.benchmark,
      start_date: result.config.start_date,
      end_date: result.config.end_date,
      initial_capital: result.config.initial_capital,
      slippage_bps: result.config.slippage_bps,
      commission_per_share: result.config.commission_per_share,
      position_sizing: result.config.position_sizing,
      max_position_pct: result.config.max_position_pct,
      rebalance_frequency: result.config.rebalance_frequency,
    });
    setAppliedParams(true);
    setTimeout(() => router.push("/backtest"), 800);
  };

  if (isLoading) return <PageLoading />;
  if (error || !result) return <ErrorMessage message={error?.message ?? "Not found"} />;

  // Build running best line for convergence chart
  const chartData = optResult
    ? optResult.trials.map((t, i) => {
        const best = optResult.trials
          .slice(0, i + 1)
          .reduce((acc, cur) =>
            OPTIMIZABLE_METRICS.find((m) => m.value === optResult.metric)?.label.includes("minimize")
              ? cur.value < acc.value ? cur : acc
              : cur.value > acc.value ? cur : acc
          );
        return { trial: t.trial + 1, value: t.value, best: best.value };
      })
    : [];

  const selectClass =
    "bg-bg-primary border border-border rounded px-3 py-1.5 text-sm text-text-primary focus:outline-none focus:border-accent-blue";
  const inputClass =
    "w-full bg-bg-primary border border-border rounded px-2 py-1 text-sm font-mono text-text-primary focus:outline-none focus:border-accent-blue";

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
            Bayesian Optimization
          </h1>
          <p className="text-xs text-text-muted mt-0.5">
            {result.config.strategy_id} · {result.config.tickers.join(", ")} ·{" "}
            {result.config.start_date} → {result.config.end_date}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Left: Config panel */}
        <div className="lg:col-span-1 space-y-4">
          {/* Objective */}
          <div
            className="rounded-md p-4"
            style={{
              background: "var(--color-bg-card)",
              border: "1px solid var(--color-border)",
            }}
          >
            <p className="section-label mb-3">Objective</p>
            <div className="space-y-3">
              <div>
                <label className="text-[11px] text-text-muted block mb-1">
                  Metric to optimize
                </label>
                <select
                  value={metric}
                  onChange={(e) => setMetric(e.target.value)}
                  className={`w-full ${selectClass}`}
                >
                  {OPTIMIZABLE_METRICS.map((m) => (
                    <option key={m.value} value={m.value}>
                      {m.label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-[11px] text-text-muted block mb-1">
                  Trials: <span className="text-accent-blue font-mono">{nTrials}</span>
                </label>
                <input
                  type="range"
                  min={5}
                  max={50}
                  step={5}
                  value={nTrials}
                  onChange={(e) => setNTrials(Number(e.target.value))}
                  className="w-full accent-accent-blue"
                />
                <div className="flex justify-between text-[10px] text-text-muted mt-0.5">
                  <span>5</span>
                  <span>50</span>
                </div>
              </div>
            </div>
          </div>

          {/* Parameter ranges */}
          <div
            className="rounded-md p-4"
            style={{
              background: "var(--color-bg-card)",
              border: "1px solid var(--color-border)",
            }}
          >
            <p className="section-label mb-3">Parameter Ranges</p>
            {paramRows.length === 0 && (
              <p className="text-xs text-text-muted">
                No numeric parameters available for this strategy.
              </p>
            )}
            <div className="space-y-3">
              {paramRows.map((row, idx) => (
                <div key={row.name} className="space-y-1">
                  <div className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={row.enabled}
                      onChange={(e) => updateRow(idx, "enabled", e.target.checked)}
                      className="accent-accent-blue"
                    />
                    <span className="text-xs font-mono text-text-primary">{row.name}</span>
                    <span
                      className="text-[9px] px-1 rounded"
                      style={{
                        background: "rgba(68,136,255,0.1)",
                        color: "var(--color-accent-blue)",
                        border: "1px solid rgba(68,136,255,0.2)",
                      }}
                    >
                      {row.type}
                    </span>
                  </div>
                  {row.enabled && (
                    <div className="grid grid-cols-3 gap-1.5 ml-5">
                      <div>
                        <label className="text-[9px] text-text-muted block mb-0.5">Low</label>
                        <input
                          type="number"
                          value={row.low}
                          onChange={(e) => updateRow(idx, "low", e.target.value)}
                          className={inputClass}
                        />
                      </div>
                      <div>
                        <label className="text-[9px] text-text-muted block mb-0.5">High</label>
                        <input
                          type="number"
                          value={row.high}
                          onChange={(e) => updateRow(idx, "high", e.target.value)}
                          className={inputClass}
                        />
                      </div>
                      <div>
                        <label className="text-[9px] text-text-muted block mb-0.5">Step</label>
                        <input
                          type="number"
                          value={row.step}
                          placeholder={row.type === "int" ? "1" : "–"}
                          onChange={(e) => updateRow(idx, "step", e.target.value)}
                          className={inputClass}
                        />
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Run button */}
          <button
            onClick={runOptimization}
            disabled={running}
            className="w-full flex items-center justify-center gap-2 py-2.5 rounded text-sm font-semibold transition-all disabled:opacity-50"
            style={{
              background: running
                ? "rgba(136,85,255,0.15)"
                : "rgba(136,85,255,0.2)",
              border: "1px solid rgba(136,85,255,0.4)",
              color: "var(--color-accent-purple)",
            }}
          >
            <Play size={13} className={running ? "animate-pulse" : ""} />
            {running ? `Running ${nTrials} trials…` : "Run Optimization"}
          </button>

          {runError && (
            <p className="text-xs text-accent-red mt-1">{runError}</p>
          )}
        </div>

        {/* Right: Results */}
        <div className="lg:col-span-2 space-y-4">
          {!optResult && !running && (
            <div
              className="rounded-md p-10 text-center"
              style={{
                background: "var(--color-bg-card)",
                border: "1px solid var(--color-border)",
              }}
            >
              <p className="text-text-muted text-sm">
                Configure parameters on the left and click{" "}
                <span style={{ color: "var(--color-accent-purple)" }}>
                  Run Optimization
                </span>{" "}
                to begin.
              </p>
              <p className="text-text-muted text-xs mt-2">
                Optuna&apos;s TPE sampler will intelligently search the parameter space using
                Bayesian inference — typically converges within 20–30 trials.
              </p>
            </div>
          )}

          {running && (
            <div
              className="rounded-md p-10 text-center"
              style={{
                background: "var(--color-bg-card)",
                border: "1px solid var(--color-border)",
              }}
            >
              <div className="flex items-center justify-center gap-3">
                <div
                  className="w-4 h-4 rounded-full animate-ping"
                  style={{ background: "var(--color-accent-purple)" }}
                />
                <p className="text-text-secondary text-sm">
                  Running {nTrials} backtests via Optuna TPE…
                </p>
              </div>
              <p className="text-text-muted text-xs mt-3">This may take a minute.</p>
            </div>
          )}

          {optResult && (
            <>
              {/* Best result card */}
              <div
                className="rounded-md p-4"
                style={{
                  background: "var(--color-bg-card)",
                  border: "1px solid rgba(136,85,255,0.3)",
                }}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <CheckCircle2 size={14} style={{ color: "var(--color-accent-purple)" }} />
                      <p className="text-sm font-semibold text-text-primary">Best Result</p>
                    </div>
                    <p className="text-[11px] text-text-muted">
                      Optimized{" "}
                      <span className="text-accent-blue font-mono">{optResult.metric}</span>{" "}
                      over {optResult.n_trials} trials
                    </p>
                  </div>
                  <div className="text-right">
                    <p
                      className="text-2xl font-bold font-mono tabular-nums"
                      style={{ color: "var(--color-accent-purple)" }}
                    >
                      {formatMetricValue(optResult.best_value, optResult.metric)}
                    </p>
                    <p className="text-[10px] text-text-muted">{optResult.metric}</p>
                  </div>
                </div>

                <div className="mt-4 pt-4" style={{ borderTop: "1px solid var(--color-border)" }}>
                  <p className="section-label mb-2">Best Parameters</p>
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {Object.entries(optResult.best_params).map(([k, v]) => (
                      <div
                        key={k}
                        className="rounded p-2"
                        style={{
                          background: "var(--color-bg-primary)",
                          border: "1px solid var(--color-border)",
                        }}
                      >
                        <p className="text-[10px] text-text-muted font-mono">{k}</p>
                        <p className="text-sm font-bold font-mono text-text-primary tabular-nums">
                          {typeof v === "number"
                            ? Number.isInteger(v)
                              ? v
                              : v.toFixed(4)
                            : String(v)}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>

                <button
                  onClick={applyBestParams}
                  disabled={appliedParams}
                  className="mt-4 w-full flex items-center justify-center gap-2 py-2 rounded text-sm font-semibold transition-all"
                  style={{
                    background: appliedParams
                      ? "rgba(0,212,170,0.1)"
                      : "rgba(136,85,255,0.15)",
                    border: `1px solid ${appliedParams ? "rgba(0,212,170,0.3)" : "rgba(136,85,255,0.3)"}`,
                    color: appliedParams
                      ? "var(--color-accent-green)"
                      : "var(--color-accent-purple)",
                  }}
                >
                  {appliedParams ? (
                    <>
                      <Check size={13} />
                      Applied — redirecting to Backtest…
                    </>
                  ) : (
                    <>
                      <Copy size={13} />
                      Use These Params
                    </>
                  )}
                </button>
              </div>

              {/* Convergence chart */}
              <div
                className="rounded-md overflow-hidden"
                style={{
                  background: "var(--color-bg-card)",
                  border: "1px solid var(--color-border)",
                }}
              >
                <div
                  className="px-5 py-3"
                  style={{ borderBottom: "1px solid var(--color-border)" }}
                >
                  <h3 className="text-sm font-semibold text-text-primary">
                    Convergence Plot
                  </h3>
                  <p className="text-[10px] text-text-muted mt-0.5">
                    Gray = trial value · Purple = running best
                  </p>
                </div>
                <div className="p-4">
                  <ResponsiveContainer width="100%" height={240}>
                    <LineChart data={chartData} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke="rgba(37,37,53,0.8)"
                      />
                      <XAxis
                        dataKey="trial"
                        tick={{ fill: "var(--color-text-muted)", fontSize: 10 }}
                        axisLine={false}
                        tickLine={false}
                        label={{ value: "Trial", position: "insideBottom", offset: -2, fill: "var(--color-text-muted)", fontSize: 10 }}
                      />
                      <YAxis
                        tick={{ fill: "var(--color-text-muted)", fontSize: 10 }}
                        axisLine={false}
                        tickLine={false}
                        width={48}
                        tickFormatter={(v) => formatMetricValue(v, optResult.metric)}
                      />
                      <Tooltip
                        contentStyle={{
                          background: "var(--color-bg-card)",
                          border: "1px solid var(--color-border)",
                          borderRadius: 4,
                          fontSize: 11,
                        }}
                        formatter={(value: number, name: string) => [
                          formatMetricValue(value, optResult.metric),
                          name === "best" ? "Running Best" : "Trial Value",
                        ]}
                      />
                      <ReferenceLine
                        y={optResult.best_value}
                        stroke="rgba(136,85,255,0.3)"
                        strokeDasharray="4 2"
                      />
                      <Line
                        type="monotone"
                        dataKey="value"
                        stroke="rgba(136,85,255,0.3)"
                        dot={{ r: 2, fill: "rgba(136,85,255,0.5)" }}
                        activeDot={{ r: 4 }}
                        strokeWidth={1}
                        isAnimationActive={false}
                      />
                      <Line
                        type="stepAfter"
                        dataKey="best"
                        stroke="var(--color-accent-purple)"
                        dot={false}
                        strokeWidth={2}
                        isAnimationActive={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Trials table */}
              <div
                className="rounded-md overflow-hidden"
                style={{
                  background: "var(--color-bg-card)",
                  border: "1px solid var(--color-border)",
                }}
              >
                <div
                  className="px-5 py-3"
                  style={{ borderBottom: "1px solid var(--color-border)" }}
                >
                  <h3 className="text-sm font-semibold text-text-primary">
                    All Trials
                  </h3>
                </div>
                <div className="overflow-x-auto max-h-64 overflow-y-auto">
                  <table className="w-full text-xs font-mono">
                    <thead className="sticky top-0" style={{ background: "var(--color-bg-card)" }}>
                      <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
                        <th className="section-label py-2 px-4 text-left font-normal">#</th>
                        {optResult.param_specs.map((s) => (
                          <th key={s.name} className="section-label py-2 px-4 text-right font-normal">
                            {s.name}
                          </th>
                        ))}
                        <th className="section-label py-2 px-4 text-right font-normal">
                          {optResult.metric}
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {[...optResult.trials]
                        .sort((a, b) => b.value - a.value)
                        .map((t) => {
                          const isBest = t.value === optResult.best_value;
                          return (
                            <tr
                              key={t.trial}
                              className="hover:bg-bg-hover transition-colors"
                              style={{
                                borderBottom: "1px solid rgba(37,37,53,0.5)",
                                background: isBest ? "rgba(136,85,255,0.06)" : undefined,
                              }}
                            >
                              <td className="py-1.5 px-4 text-text-muted">
                                {isBest ? "★" : t.trial + 1}
                              </td>
                              {optResult.param_specs.map((s) => (
                                <td key={s.name} className="py-1.5 px-4 text-right tabular-nums text-text-secondary">
                                  {typeof t.params[s.name] === "number"
                                    ? Number.isInteger(t.params[s.name])
                                      ? t.params[s.name]
                                      : t.params[s.name].toFixed(4)
                                    : t.params[s.name]}
                                </td>
                              ))}
                              <td
                                className="py-1.5 px-4 text-right tabular-nums font-semibold"
                                style={{ color: isBest ? "var(--color-accent-purple)" : "var(--color-text-primary)" }}
                              >
                                {formatMetricValue(t.value, optResult.metric)}
                              </td>
                            </tr>
                          );
                        })}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
