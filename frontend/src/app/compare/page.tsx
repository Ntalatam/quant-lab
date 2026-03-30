"use client";

import { useState } from "react";
import { useBacktestList } from "@/hooks/useBacktest";
import { useCompareBacktests } from "@/hooks/useAnalytics";
import { PageLoading } from "@/components/shared/LoadingSpinner";
import { ErrorMessage } from "@/components/shared/ErrorBoundary";
import { EquityCurve } from "@/components/charts/EquityCurve";
import { formatPercent, formatRatio } from "@/lib/formatters";
import { CHART_COLORS } from "@/lib/constants";
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

const COMPARE_COLORS = [
  CHART_COLORS.strategy,
  CHART_COLORS.blue,
  CHART_COLORS.yellow,
  CHART_COLORS.purple,
  CHART_COLORS.negative,
];

export default function ComparePage() {
  const { data: backtests, isLoading } = useBacktestList();
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const { data: comparison, isLoading: isComparing } =
    useCompareBacktests(selectedIds);

  if (isLoading) return <PageLoading />;

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  };

  // Build overlay chart data
  const overlayData: Record<string, number | string>[] = [];
  if (comparison) {
    const dateMap = new Map<
      string,
      Record<string, number | string>
    >();
    comparison.backtests.forEach((bt, idx) => {
      const startVal = bt.equity_curve[0]?.value || 1;
      bt.equity_curve.forEach((pt) => {
        if (!dateMap.has(pt.date)) {
          dateMap.set(pt.date, { date: pt.date });
        }
        const entry = dateMap.get(pt.date)!;
        entry[`s${idx}`] = (pt.value / startVal) * 100;
      });
    });
    overlayData.push(
      ...Array.from(dateMap.values()).sort(
        (a, b) =>
          new Date(a.date as string).getTime() -
          new Date(b.date as string).getTime()
      )
    );
  }

  const METRICS_TO_COMPARE = [
    { key: "total_return_pct", label: "Total Return", format: formatPercent },
    { key: "cagr_pct", label: "CAGR", format: formatPercent },
    { key: "sharpe_ratio", label: "Sharpe", format: formatRatio },
    { key: "sortino_ratio", label: "Sortino", format: formatRatio },
    { key: "max_drawdown_pct", label: "Max Drawdown", format: formatPercent },
    {
      key: "annualized_volatility_pct",
      label: "Volatility",
      format: formatPercent,
    },
    { key: "alpha", label: "Alpha", format: formatPercent },
    { key: "beta", label: "Beta", format: formatRatio },
    { key: "win_rate_pct", label: "Win Rate", format: formatPercent },
    { key: "profit_factor", label: "Profit Factor", format: formatRatio },
  ];

  return (
    <div>
      <div className="mb-7">
        <h1 className="text-xl font-bold text-text-primary tracking-tight">
          Compare Backtests
        </h1>
        <p className="text-xs text-text-muted mt-0.5">
          Overlay equity curves and compare risk metrics head-to-head
        </p>
      </div>

      {/* Selector */}
      <div className="rounded-md p-4 mb-6" style={{ background: "var(--color-bg-card)", border: "1px solid var(--color-border)", boxShadow: "0 1px 3px rgba(0,0,0,0.4)" }}>
        <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider mb-3">
          Select backtests to compare
          <span className="ml-2 font-normal text-text-muted normal-case tracking-normal">(minimum 2)</span>
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
          <div className="rounded-md overflow-hidden" style={{ background: "var(--color-bg-card)", border: "1px solid var(--color-border)", boxShadow: "0 1px 3px rgba(0,0,0,0.4)" }}>
            <div className="px-5 py-3" style={{ borderBottom: "1px solid var(--color-border)" }}>
              <h3 className="text-sm font-semibold text-text-primary">Normalized Equity Curves</h3>
              <p className="text-[10px] text-text-muted mt-0.5">Base = 100 — proportional growth comparison across strategies</p>
            </div>
            <div className="p-4">
            <ResponsiveContainer width="100%" height={350}>
              <LineChart data={overlayData}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke={CHART_COLORS.grid}
                />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11 }}
                  stroke={CHART_COLORS.axis}
                  minTickGap={50}
                />
                <YAxis
                  tick={{ fontSize: 11 }}
                  stroke={CHART_COLORS.axis}
                  width={50}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: CHART_COLORS.tooltip,
                    border: `1px solid ${CHART_COLORS.grid}`,
                    borderRadius: 4,
                    fontSize: 12,
                  }}
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
              </LineChart>
            </ResponsiveContainer>
            </div>
          </div>

          {/* Metrics Table */}
          <div className="rounded-md overflow-hidden" style={{ background: "var(--color-bg-card)", border: "1px solid var(--color-border)", boxShadow: "0 1px 3px rgba(0,0,0,0.4)" }}>
            <div className="px-5 py-3" style={{ borderBottom: "1px solid var(--color-border)" }}>
              <h3 className="text-sm font-semibold text-text-primary">Metrics Comparison</h3>
              <p className="text-[10px] text-text-muted mt-0.5">Best value per metric highlighted in green</p>
            </div>
            <div className="p-4">
            <div className="overflow-x-auto">
              <table className="w-full text-xs font-mono tabular-nums">
                <thead>
                  <tr className="border-b border-border">
                    <th className="text-left font-normal py-2 px-2 text-text-muted">
                      Metric
                    </th>
                    {comparison.backtests.map((bt, idx) => (
                      <th
                        key={bt.id}
                        className="text-right font-normal py-2 px-2"
                        style={{
                          color: COMPARE_COLORS[idx % COMPARE_COLORS.length],
                        }}
                      >
                        {bt.strategy_id}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {METRICS_TO_COMPARE.map((metric) => {
                    const values = comparison.backtests.map(
                      (bt) =>
                        (bt.metrics as unknown as Record<string, number>)[metric.key] || 0
                    );
                    const best =
                      metric.key === "max_drawdown_pct"
                        ? Math.max(...values)
                        : Math.max(...values);

                    return (
                      <tr
                        key={metric.key}
                        className="border-b border-border/50"
                      >
                        <td className="py-1.5 px-2 text-text-secondary">
                          {metric.label}
                        </td>
                        {values.map((val, idx) => (
                          <td
                            key={idx}
                            className={`py-1.5 px-2 text-right ${
                              val === best
                                ? "text-accent-green font-medium"
                                : "text-text-primary"
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
        </div>
      )}
    </div>
  );
}
