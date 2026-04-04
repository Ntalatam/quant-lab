"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Loader2, RefreshCw, ShieldCheck } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { api } from "@/lib/api";
import { formatCurrency, formatPercent, formatRatio } from "@/lib/formatters";
import type { RiskBudgetResult, StressScenarioResult } from "@/lib/types";

interface RiskBudgetingDashboardProps {
  backtestId: string;
}

const LOOKBACK_OPTIONS = [
  { value: 63, label: "63d" },
  { value: 126, label: "126d" },
  { value: 252, label: "252d" },
];

function contributionColor(value: number): string {
  if (value > 0) return "var(--color-accent-red)";
  if (value < 0) return "var(--color-accent-green)";
  return "var(--color-text-muted)";
}

function stressTone(value: number): string {
  if (value <= -15) return "var(--color-accent-red)";
  if (value <= -5) return "var(--color-accent-yellow)";
  return "var(--color-accent-green)";
}

function StressCard({ scenario }: { scenario: StressScenarioResult }) {
  return (
    <div
      className="rounded-md p-4"
      style={{
        background: "var(--color-bg-primary)",
        border: "1px solid var(--color-border)",
      }}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-text-primary">
            {scenario.name}
          </p>
          <p className="mt-1 text-[10px] leading-relaxed text-text-muted">
            {scenario.description}
          </p>
          <p className="mt-2 text-[10px] font-mono text-text-muted">
            {scenario.start_date} to {scenario.end_date}
          </p>
        </div>
        <div className="text-right">
          <p
            className="font-mono text-lg font-bold"
            style={{ color: stressTone(scenario.portfolio_return_pct) }}
          >
            {formatPercent(scenario.portfolio_return_pct)}
          </p>
          <p className="text-[10px] text-text-muted">
            {formatCurrency(scenario.pnl_impact)}
          </p>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 text-[10px]">
        <div>
          <p className="section-label mb-1">Corr Shift</p>
          <p className="font-mono text-text-primary">
            {scenario.correlation_shift == null
              ? "n/a"
              : formatRatio(scenario.correlation_shift)}
          </p>
        </div>
        <div>
          <p className="section-label mb-1">Top Pair</p>
          <p className="font-mono text-text-primary">
            {scenario.top_pair ?? "n/a"}
            {scenario.top_pair_correlation != null
              ? ` (${formatRatio(scenario.top_pair_correlation)})`
              : ""}
          </p>
        </div>
      </div>

      {scenario.position_impacts.length > 0 && (
        <div className="mt-4">
          <p className="section-label mb-2">Largest Position Impacts</p>
          <div className="space-y-2">
            {scenario.position_impacts.slice(0, 3).map((impact) => (
              <div
                key={`${scenario.id}-${impact.ticker}`}
                className="flex items-center justify-between text-[11px]"
              >
                <div>
                  <span className="font-mono text-text-secondary">
                    {impact.ticker}
                  </span>
                  {impact.source_ticker !== impact.ticker && (
                    <span className="ml-2 text-[10px] text-text-muted">
                      via {impact.source_ticker}
                    </span>
                  )}
                </div>
                <div className="text-right">
                  <div className="font-mono text-text-primary">
                    {formatPercent(impact.scenario_return_pct)}
                  </div>
                  <div className="font-mono text-[10px] text-text-muted">
                    {formatCurrency(impact.pnl_impact)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function RiskBudgetingDashboard({
  backtestId,
}: RiskBudgetingDashboardProps) {
  const [lookbackDays, setLookbackDays] = useState(63);
  const [refreshNonce, setRefreshNonce] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [result, setResult] = useState<RiskBudgetResult | null>(null);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      setError("");

      try {
        const response = await api.getRiskBudgetAnalysis(
          backtestId,
          lookbackDays,
        );
        if (!cancelled) {
          setResult(response);
        }
      } catch (err: unknown) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Risk budget analysis failed",
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, [backtestId, lookbackDays, refreshNonce]);

  const summary = result?.summary;
  const topContributors = result?.positions.slice(0, 8) ?? [];

  return (
    <div
      className="rounded-md overflow-hidden"
      style={{
        background: "var(--color-bg-card)",
        border: "1px solid var(--color-border)",
        boxShadow:
          "0 1px 3px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.02)",
      }}
    >
      <div
        className="flex flex-col gap-3 px-5 py-3 sm:flex-row sm:items-center sm:justify-between"
        style={{ borderBottom: "1px solid var(--color-border)" }}
      >
        <div className="flex items-center gap-2">
          <ShieldCheck size={13} className="text-accent-green" />
          <div>
            <h3 className="text-sm font-semibold text-text-primary">
              Risk Budgeting Dashboard
            </h3>
            <p className="mt-0.5 text-[10px] text-text-muted">
              Position-level VaR, downside concentration, and historical stress
              tests for the live book at the latest invested snapshot
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-[10px] uppercase tracking-[0.16em] text-text-muted">
            Lookback
          </label>
          <select
            value={lookbackDays}
            onChange={(event) => setLookbackDays(Number(event.target.value))}
            className="rounded px-2 py-1 text-xs text-text-primary focus:outline-none"
            style={{
              background: "var(--color-bg-primary)",
              border: "1px solid var(--color-border)",
            }}
          >
            {LOOKBACK_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <button
            onClick={() => setRefreshNonce((current) => current + 1)}
            disabled={loading}
            className="flex items-center gap-1.5 rounded px-3 py-1.5 text-xs transition-all disabled:opacity-40"
            style={{
              background: "rgba(68,136,255,0.1)",
              border: "1px solid rgba(68,136,255,0.2)",
              color: "var(--color-accent-blue)",
            }}
          >
            {loading ? (
              <Loader2 size={11} className="animate-spin" />
            ) : (
              <RefreshCw size={11} />
            )}
            {loading ? "Running…" : "Refresh"}
          </button>
        </div>
      </div>

      <div className="p-5">
        {loading && (
          <div className="flex items-center gap-2 text-xs text-text-muted">
            <Loader2 size={13} className="animate-spin text-accent-green" />
            Reconstructing the latest risk book and running stress scenarios…
          </div>
        )}

        {error && (
          <div
            className="rounded p-3 text-xs"
            style={{
              background: "rgba(255,71,87,0.07)",
              border: "1px solid rgba(255,71,87,0.2)",
              color: "var(--color-accent-red)",
            }}
          >
            {error}
          </div>
        )}

        {result?.message && (
          <div
            className="rounded p-3 text-xs"
            style={{
              background: "rgba(255,184,77,0.08)",
              border: "1px solid rgba(255,184,77,0.18)",
              color: "var(--color-accent-yellow)",
            }}
          >
            {result.message}
          </div>
        )}

        {summary && !result?.message && (
          <div className="space-y-5">
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-6">
              {[
                {
                  label: "Snapshot",
                  value: summary.snapshot_date,
                  tone: "var(--color-text-primary)",
                },
                {
                  label: "1D VaR (95%)",
                  value: formatCurrency(summary.daily_var_95_dollar),
                  tone: "var(--color-accent-red)",
                  subvalue: `${summary.daily_var_95_pct.toFixed(2)}% loss`,
                },
                {
                  label: "1D CVaR (95%)",
                  value: formatCurrency(summary.daily_cvar_95_dollar),
                  tone: "var(--color-accent-red)",
                  subvalue: `${summary.daily_cvar_95_pct.toFixed(2)}% loss`,
                },
                {
                  label: "Diversification",
                  value: formatRatio(summary.diversification_ratio),
                  tone: "var(--color-accent-green)",
                  subvalue: "ratio",
                },
                {
                  label: "Gross / Net",
                  value: `${summary.gross_exposure_pct.toFixed(1)}% / ${summary.net_exposure_pct.toFixed(1)}%`,
                  tone: "var(--color-text-primary)",
                },
                {
                  label: "Avg Correlation",
                  value:
                    summary.average_pairwise_correlation == null
                      ? "n/a"
                      : formatRatio(summary.average_pairwise_correlation),
                  tone: "var(--color-accent-blue)",
                  subvalue: `${summary.lookback_days} obs`,
                },
              ].map((item) => (
                <div
                  key={item.label}
                  className="rounded p-3"
                  style={{
                    background: "var(--color-bg-primary)",
                    border: "1px solid var(--color-border)",
                  }}
                >
                  <p className="section-label mb-1">{item.label}</p>
                  <p
                    className="font-mono text-sm font-semibold"
                    style={{ color: item.tone }}
                  >
                    {item.value}
                  </p>
                  {item.subvalue && (
                    <p className="mt-1 text-[10px] text-text-muted">
                      {item.subvalue}
                    </p>
                  )}
                </div>
              ))}
            </div>

            <div className="grid gap-5 xl:grid-cols-[1.4fr_1fr]">
              <div
                className="rounded-md p-4"
                style={{
                  background: "var(--color-bg-primary)",
                  border: "1px solid var(--color-border)",
                }}
              >
                <div className="mb-3 flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-text-primary">
                      Position VaR Contributions
                    </p>
                    <p className="mt-0.5 text-[10px] text-text-muted">
                      Positive bars add to downside risk; negative bars indicate
                      hedging behavior.
                    </p>
                  </div>
                  <div className="text-right text-[10px] text-text-muted">
                    Top {topContributors.length} positions by contribution
                  </div>
                </div>

                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={topContributors}
                      margin={{ top: 8, right: 16, left: 0, bottom: 8 }}
                    >
                      <CartesianGrid
                        stroke="rgba(255,255,255,0.06)"
                        vertical={false}
                      />
                      <XAxis
                        dataKey="ticker"
                        tick={{ fill: "var(--color-text-muted)", fontSize: 11 }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <YAxis
                        tickFormatter={(value) =>
                          `${value < 0 ? "-" : ""}$${Math.abs(Number(value)).toFixed(0)}`
                        }
                        tick={{ fill: "var(--color-text-muted)", fontSize: 11 }}
                        axisLine={false}
                        tickLine={false}
                        width={64}
                      />
                      <Tooltip
                        cursor={{ fill: "rgba(255,255,255,0.02)" }}
                        formatter={(value, _name, item) => {
                          const numericValue =
                            typeof value === "number"
                              ? value
                              : Number(value ?? 0);
                          const contributionPct =
                            item?.payload &&
                            typeof item.payload.var_contribution_pct ===
                              "number"
                              ? item.payload.var_contribution_pct
                              : null;

                          return [
                            `${formatCurrency(numericValue)}${
                              contributionPct == null
                                ? ""
                                : ` (${contributionPct.toFixed(1)}%)`
                            }`,
                            "VaR contribution",
                          ];
                        }}
                        contentStyle={{
                          background: "var(--color-bg-card)",
                          border: "1px solid var(--color-border)",
                          borderRadius: "8px",
                          color: "var(--color-text-primary)",
                        }}
                      />
                      <Bar dataKey="var_contribution" radius={[4, 4, 0, 0]}>
                        {topContributors.map((entry) => (
                          <Cell
                            key={entry.ticker}
                            fill={contributionColor(entry.var_contribution)}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div
                className="rounded-md p-4"
                style={{
                  background: "var(--color-bg-primary)",
                  border: "1px solid var(--color-border)",
                }}
              >
                <div className="mb-3 flex items-center gap-2">
                  <AlertTriangle size={13} className="text-accent-yellow" />
                  <div>
                    <p className="text-sm font-semibold text-text-primary">
                      Stress Test Highlights
                    </p>
                    <p className="mt-0.5 text-[10px] text-text-muted">
                      Replay the current portfolio through major historical
                      shock windows.
                    </p>
                  </div>
                </div>

                <div className="space-y-3">
                  {result.scenarios.map((scenario) => (
                    <StressCard key={scenario.id} scenario={scenario} />
                  ))}
                </div>
              </div>
            </div>

            <div>
              <div className="mb-2">
                <p className="text-sm font-semibold text-text-primary">
                  Position Risk Budget
                </p>
                <p className="mt-0.5 text-[10px] text-text-muted">
                  Latest invested snapshot with sector context, portfolio beta,
                  and downside concentration.
                </p>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-xs font-mono">
                  <thead>
                    <tr
                      style={{ borderBottom: "1px solid var(--color-border)" }}
                    >
                      {[
                        "Ticker",
                        "Sector",
                        "Shares",
                        "Weight",
                        "Daily Vol",
                        "Beta",
                        "VaR $",
                        "VaR %",
                        "CVaR $",
                        "Mkt Value",
                      ].map((header, index) => (
                        <th
                          key={header}
                          className={`section-label px-2 py-1.5 font-normal ${
                            index < 2 ? "text-left" : "text-right"
                          }`}
                        >
                          {header}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.positions.map((position) => (
                      <tr
                        key={position.ticker}
                        className="hover:bg-bg-hover transition-colors"
                        style={{
                          borderBottom: "1px solid rgba(37,37,53,0.5)",
                        }}
                      >
                        <td className="px-2 py-1.5 text-text-secondary">
                          {position.ticker}
                        </td>
                        <td className="px-2 py-1.5 text-text-muted">
                          {position.sector ?? "Unknown"}
                        </td>
                        <td className="px-2 py-1.5 text-right text-text-primary">
                          {position.shares.toLocaleString()}
                        </td>
                        <td className="px-2 py-1.5 text-right text-text-primary">
                          {position.weight_pct.toFixed(2)}%
                        </td>
                        <td className="px-2 py-1.5 text-right text-text-primary">
                          {position.daily_volatility_pct.toFixed(2)}%
                        </td>
                        <td className="px-2 py-1.5 text-right text-text-primary">
                          {position.beta_to_portfolio.toFixed(2)}
                        </td>
                        <td
                          className="px-2 py-1.5 text-right font-semibold"
                          style={{
                            color: contributionColor(position.var_contribution),
                          }}
                        >
                          {formatCurrency(position.var_contribution)}
                        </td>
                        <td
                          className="px-2 py-1.5 text-right font-semibold"
                          style={{
                            color: contributionColor(position.var_contribution),
                          }}
                        >
                          {position.var_contribution_pct.toFixed(1)}%
                        </td>
                        <td className="px-2 py-1.5 text-right text-text-primary">
                          {formatCurrency(position.cvar_contribution)}
                        </td>
                        <td className="px-2 py-1.5 text-right text-text-primary">
                          {formatCurrency(position.market_value)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
