"use client";

import { useState } from "react";
import { useBacktestList } from "@/hooks/useBacktest";
import { useCompareBacktests } from "@/hooks/useAnalytics";
import { PageLoading } from "@/components/shared/LoadingSpinner";
import { formatPercent, formatRatio, formatCompactDate } from "@/lib/formatters";
import { CHART_COLORS } from "@/lib/constants";
import { api } from "@/lib/api";
import type { PortfolioBlendResult } from "@/lib/types";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from "recharts";
import { Loader2, PieChart, Sliders } from "lucide-react";

const COMPARE_COLORS = [
  CHART_COLORS.strategy,
  CHART_COLORS.blue,
  CHART_COLORS.yellow,
  CHART_COLORS.purple,
  CHART_COLORS.negative,
];

const METRICS_TO_COMPARE = [
  { key: "total_return_pct", label: "Total Return", format: formatPercent, lowerIsBetter: false },
  { key: "cagr_pct", label: "CAGR", format: formatPercent, lowerIsBetter: false },
  { key: "sharpe_ratio", label: "Sharpe", format: formatRatio, lowerIsBetter: false },
  { key: "sortino_ratio", label: "Sortino", format: formatRatio, lowerIsBetter: false },
  { key: "max_drawdown_pct", label: "Max Drawdown", format: formatPercent, lowerIsBetter: true },
  { key: "annualized_volatility_pct", label: "Volatility", format: formatPercent, lowerIsBetter: true },
  { key: "alpha", label: "Alpha", format: formatPercent, lowerIsBetter: false },
  { key: "beta", label: "Beta", format: formatRatio, lowerIsBetter: false },
  { key: "win_rate_pct", label: "Win Rate", format: formatPercent, lowerIsBetter: false },
  { key: "profit_factor", label: "Profit Factor", format: formatRatio, lowerIsBetter: false },
];

export default function ComparePage() {
  const { data: backtests, isLoading } = useBacktestList();
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const { data: comparison, isLoading: isComparing } = useCompareBacktests(selectedIds);

  // Portfolio builder state
  const [weights, setWeights] = useState<Record<string, number>>({});
  const [blending, setBlending] = useState(false);
  const [blend, setBlend] = useState<PortfolioBlendResult | null>(null);
  const [blendError, setBlendError] = useState("");

  if (isLoading) return <PageLoading />;

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
    setBlend(null);
  };

  const getWeight = (id: string) => weights[id] ?? Math.round(100 / selectedIds.length);

  const handleBlend = async (optimize: "custom" | "equal" | "max_sharpe" | "min_dd") => {
    setBlendError("");
    setBlending(true);
    try {
      const w = selectedIds.map((id) => getWeight(id) / 100);
      const result = await api.portfolioBlend(selectedIds, w, optimize);
      setBlend(result);
      // Update displayed weights if optimizer changed them
      if (optimize !== "custom") {
        const newW: Record<string, number> = {};
        selectedIds.forEach((id, i) => {
          newW[id] = Math.round((result.weights[i] ?? 0) * 100);
        });
        setWeights(newW);
      }
    } catch (e: unknown) {
      setBlendError(e instanceof Error ? e.message : "Portfolio blend failed");
    } finally {
      setBlending(false);
    }
  };

  // Build overlay chart data
  const overlayData: Record<string, number | string>[] = [];
  if (comparison) {
    const dateMap = new Map<string, Record<string, number | string>>();
    comparison.backtests.forEach((bt, idx) => {
      const startVal = bt.equity_curve[0]?.value || 1;
      bt.equity_curve.forEach((pt) => {
        if (!dateMap.has(pt.date)) dateMap.set(pt.date, { date: pt.date });
        dateMap.get(pt.date)![`s${idx}`] = (pt.value / startVal) * 100;
      });
    });
    if (blend) {
      const startVal = blend.equity_curve[0]?.value || 1;
      blend.equity_curve.forEach((pt) => {
        if (!dateMap.has(pt.date)) dateMap.set(pt.date, { date: pt.date });
        dateMap.get(pt.date)!["portfolio"] = (pt.value / startVal) * 100;
      });
    }
    overlayData.push(
      ...Array.from(dateMap.values()).sort(
        (a, b) => new Date(a.date as string).getTime() - new Date(b.date as string).getTime()
      )
    );
  }

  const canBlend = selectedIds.length >= 2 && !!comparison;

  return (
    <div>
      <div className="mb-7">
        <h1 className="text-xl font-bold text-text-primary tracking-tight">
          Compare Backtests
        </h1>
        <p className="text-xs text-text-muted mt-0.5">
          Overlay equity curves, compare risk metrics, and blend strategies into a portfolio
        </p>
      </div>

      {/* Selector */}
      <div
        className="rounded-md p-4 mb-6"
        style={{
          background: "var(--color-bg-card)",
          border: "1px solid var(--color-border)",
          boxShadow: "0 1px 3px rgba(0,0,0,0.4)",
        }}
      >
        <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-3">
          Select backtests to compare
          <span className="ml-2 font-normal text-text-muted normal-case tracking-normal">
            (minimum 2)
          </span>
        </h2>
        <div className="space-y-1 max-h-48 overflow-y-auto">
          {backtests?.map((bt) => (
            <label
              key={bt.id}
              className="flex items-center gap-3 text-sm py-1.5 px-2 rounded hover:bg-bg-hover cursor-pointer"
            >
              <input
                type="checkbox"
                checked={selectedIds.includes(bt.id)}
                onChange={() => toggleSelect(bt.id)}
                className="accent-accent-blue"
              />
              <span className="text-text-primary">{bt.strategy_name}</span>
              <span className="text-text-muted font-mono text-xs">
                {bt.tickers.join(", ")}
              </span>
              <span className="ml-auto font-mono tabular-nums text-xs text-text-secondary">
                {formatPercent(bt.total_return_pct)}
              </span>
            </label>
          ))}
        </div>
        {(!backtests || backtests.length < 2) && (
          <p className="text-text-muted text-xs mt-2">
            Run at least 2 backtests to compare.
          </p>
        )}
      </div>

      {isComparing && <PageLoading />}

      {comparison && (
        <div className="space-y-6">
          {/* Overlay Chart */}
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
              <h3 className="text-sm font-semibold text-text-primary">
                Normalized Equity Curves
              </h3>
              <p className="text-[10px] text-text-muted mt-0.5">
                Base = 100 — proportional growth comparison{blend ? " · dashed white = blended portfolio" : ""}
              </p>
            </div>
            <div className="p-4">
              <ResponsiveContainer width="100%" height={350}>
                <LineChart data={overlayData} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
                  <XAxis
                    dataKey="date"
                    tickFormatter={formatCompactDate}
                    tick={{ fontSize: 11 }}
                    stroke={CHART_COLORS.axis}
                    minTickGap={50}
                  />
                  <YAxis tick={{ fontSize: 11 }} stroke={CHART_COLORS.axis} width={50} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: CHART_COLORS.tooltip,
                      border: `1px solid ${CHART_COLORS.grid}`,
                      borderRadius: 4,
                      fontSize: 12,
                    }}
                    labelFormatter={(l) => formatCompactDate(String(l))}
                  />
                  <Legend />
                  {comparison.backtests.map((bt, idx) => (
                    <Line
                      key={bt.id}
                      type="monotone"
                      dataKey={`s${idx}`}
                      name={`${bt.strategy_id} (${bt.tickers?.join(", ")})`}
                      stroke={COMPARE_COLORS[idx % COMPARE_COLORS.length]}
                      strokeWidth={1.5}
                      dot={false}
                    />
                  ))}
                  {blend && (
                    <Line
                      type="monotone"
                      dataKey="portfolio"
                      name="Blended Portfolio"
                      stroke="#ffffff"
                      strokeWidth={2}
                      strokeDasharray="5 3"
                      dot={false}
                    />
                  )}
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Correlation Matrix */}
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
              <h3 className="text-sm font-semibold text-text-primary">Return Correlation Matrix</h3>
              <p className="text-[10px] text-text-muted mt-0.5">
                Daily return correlation — low values indicate diversification benefit
              </p>
            </div>
            <div className="p-4 overflow-x-auto">
              <table className="text-xs font-mono">
                <thead>
                  <tr>
                    <th className="py-1 px-3 text-left text-text-muted section-label font-normal w-32"></th>
                    {comparison.backtests.map((bt, idx) => (
                      <th
                        key={bt.id}
                        className="py-1 px-3 text-center text-[10px] font-normal"
                        style={{ color: COMPARE_COLORS[idx % COMPARE_COLORS.length] }}
                      >
                        {bt.strategy_id.slice(0, 10)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {comparison.correlation_matrix.map((row, i) => (
                    <tr key={i}>
                      <td
                        className="py-1 px-3 text-[10px]"
                        style={{ color: COMPARE_COLORS[i % COMPARE_COLORS.length] }}
                      >
                        {comparison.backtests[i].strategy_id.slice(0, 12)}
                      </td>
                      {row.map((val, j) => {
                        const v = typeof val === "number" ? val : 0;
                        const bg =
                          i === j
                            ? "rgba(68,136,255,0.15)"
                            : v > 0.7
                            ? "rgba(255,71,87,0.15)"
                            : v < 0.2
                            ? "rgba(0,212,170,0.12)"
                            : "transparent";
                        return (
                          <td
                            key={j}
                            className="py-1 px-3 text-center tabular-nums"
                            style={{ background: bg }}
                          >
                            {v.toFixed(2)}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Portfolio Builder */}
          <div
            className="rounded-md overflow-hidden"
            style={{
              background: "var(--color-bg-card)",
              border: "1px solid var(--color-border)",
              boxShadow: "0 1px 3px rgba(0,0,0,0.4)",
            }}
          >
            <div
              className="flex items-center gap-2 px-5 py-3"
              style={{ borderBottom: "1px solid var(--color-border)" }}
            >
              <PieChart size={13} className="text-accent-blue" />
              <div>
                <h3 className="text-sm font-semibold text-text-primary">Portfolio Builder</h3>
                <p className="text-[10px] text-text-muted mt-0.5">
                  Blend strategies with custom or optimized weights — see blended curve on chart above
                </p>
              </div>
            </div>
            <div className="p-5">
              {/* Weight sliders */}
              <div className="space-y-3 mb-5">
                {comparison.backtests.map((bt, idx) => {
                  const w = getWeight(bt.id);
                  return (
                    <div key={bt.id} className="flex items-center gap-3">
                      <div
                        className="w-2 h-2 rounded-full shrink-0"
                        style={{ background: COMPARE_COLORS[idx % COMPARE_COLORS.length] }}
                      />
                      <span className="text-xs text-text-secondary w-32 truncate">
                        {bt.strategy_id}
                      </span>
                      <input
                        type="range"
                        min={0}
                        max={100}
                        step={5}
                        value={w}
                        onChange={(e) => {
                          setWeights((prev) => ({ ...prev, [bt.id]: Number(e.target.value) }));
                          setBlend(null);
                        }}
                        className="flex-1 accent-accent-blue"
                      />
                      <span className="text-xs font-mono text-text-primary w-10 text-right">
                        {w}%
                      </span>
                    </div>
                  );
                })}
              </div>

              {blendError && (
                <p className="text-xs text-accent-red mb-3">{blendError}</p>
              )}

              {/* Action buttons */}
              <div className="flex flex-wrap gap-2 mb-5">
                {(["equal", "max_sharpe", "min_dd"] as const).map((mode) => (
                  <button
                    key={mode}
                    onClick={() => handleBlend(mode)}
                    disabled={!canBlend || blending}
                    className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded transition-all disabled:opacity-40"
                    style={{
                      background: "rgba(68,136,255,0.1)",
                      border: "1px solid rgba(68,136,255,0.2)",
                      color: "var(--color-accent-blue)",
                    }}
                  >
                    {blending ? <Loader2 size={11} className="animate-spin" /> : <Sliders size={11} />}
                    {mode === "equal" ? "Equal Weight" : mode === "max_sharpe" ? "Max Sharpe" : "Min Drawdown"}
                  </button>
                ))}
                <button
                  onClick={() => handleBlend("custom")}
                  disabled={!canBlend || blending}
                  className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded transition-all disabled:opacity-40"
                  style={{
                    background: "rgba(0,212,170,0.1)",
                    border: "1px solid rgba(0,212,170,0.2)",
                    color: "var(--color-accent-green)",
                  }}
                >
                  {blending ? <Loader2 size={11} className="animate-spin" /> : <PieChart size={11} />}
                  Apply Weights
                </button>
              </div>

              {/* Blend results */}
              {blend && (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {[
                      { label: "Portfolio Return", value: formatPercent(blend.metrics.total_return_pct ?? 0), positive: (blend.metrics.total_return_pct ?? 0) >= 0 },
                      { label: "Portfolio Sharpe", value: formatRatio(blend.metrics.sharpe_ratio ?? 0), positive: (blend.metrics.sharpe_ratio ?? 0) > 1 },
                      { label: "Max Drawdown", value: formatPercent(blend.metrics.max_drawdown_pct ?? 0), positive: false },
                      { label: "Volatility", value: formatPercent(blend.metrics.annualized_volatility_pct ?? 0), positive: false },
                    ].map(({ label, value, positive }) => (
                      <div
                        key={label}
                        className="rounded p-3 text-center"
                        style={{
                          background: "var(--color-bg-primary)",
                          border: "1px solid var(--color-border)",
                        }}
                      >
                        <p className="section-label mb-1">{label}</p>
                        <p
                          className="font-mono tabular-nums font-semibold text-sm"
                          style={{
                            color: positive
                              ? "var(--color-accent-green)"
                              : "var(--color-accent-red)",
                          }}
                        >
                          {value}
                        </p>
                      </div>
                    ))}
                  </div>

                  {/* Asset contributions */}
                  <table className="w-full text-xs font-mono">
                    <thead>
                      <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
                        {["Strategy", "Weight", "Asset Return", "Contribution"].map((h) => (
                          <th
                            key={h}
                            className={`section-label py-2 px-3 font-normal ${h === "Strategy" ? "text-left" : "text-right"}`}
                          >
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {blend.asset_contributions.map((ac, i) => (
                        <tr
                          key={ac.id}
                          style={{ borderBottom: "1px solid rgba(37,37,53,0.5)" }}
                        >
                          <td className="py-2 px-3 text-text-secondary">
                            <span
                              className="inline-block w-2 h-2 rounded-full mr-2"
                              style={{ background: COMPARE_COLORS[i % COMPARE_COLORS.length] }}
                            />
                            {ac.strategy_id}
                          </td>
                          <td className="py-2 px-3 text-right text-text-primary">
                            {Math.round(ac.weight * 100)}%
                          </td>
                          <td
                            className="py-2 px-3 text-right tabular-nums"
                            style={{
                              color:
                                ac.asset_return_pct >= 0
                                  ? "var(--color-accent-green)"
                                  : "var(--color-accent-red)",
                            }}
                          >
                            {formatPercent(ac.asset_return_pct)}
                          </td>
                          <td
                            className="py-2 px-3 text-right tabular-nums font-semibold"
                            style={{
                              color:
                                ac.contribution_pct >= 0
                                  ? "var(--color-accent-green)"
                                  : "var(--color-accent-red)",
                            }}
                          >
                            {formatPercent(ac.contribution_pct)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          {/* Metrics Table */}
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
              <h3 className="text-sm font-semibold text-text-primary">Metrics Comparison</h3>
              <p className="text-[10px] text-text-muted mt-0.5">
                Best value per metric highlighted in green
              </p>
            </div>
            <div className="p-4 overflow-x-auto">
              <table className="w-full text-xs font-mono tabular-nums">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left font-normal py-2 px-2 text-text-muted">Metric</th>
                    {comparison.backtests.map((bt, idx) => (
                      <th
                        key={bt.id}
                        className="text-right font-normal py-2 px-2"
                        style={{ color: COMPARE_COLORS[idx % COMPARE_COLORS.length] }}
                      >
                        {bt.strategy_id}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {METRICS_TO_COMPARE.map((metric) => {
                    const values = comparison.backtests.map(
                      (bt) => (bt.metrics as unknown as Record<string, number>)[metric.key] || 0
                    );
                    const best = metric.lowerIsBetter ? Math.min(...values) : Math.max(...values);
                    return (
                      <tr key={metric.key} className="border-b border-border/50">
                        <td className="py-1.5 px-2 text-text-secondary">{metric.label}</td>
                        {values.map((val, idx) => (
                          <td
                            key={idx}
                            className={`py-1.5 px-2 text-right ${
                              val === best ? "text-accent-green font-medium" : "text-text-primary"
                            }`}
                          >
                            {metric.format(val)}
                          </td>
                        ))}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
