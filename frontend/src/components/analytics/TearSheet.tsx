"use client";

import { useState } from "react";
import type { BacktestResult } from "@/lib/types";
import { MetricsCard } from "./MetricsCard";
import { TradeLog } from "./TradeLog";
import { FactorExposure } from "./FactorExposure";
import { RegimeAnalysis } from "./RegimeAnalysis";
import { EquityCurve } from "@/components/charts/EquityCurve";
import { DrawdownChart } from "@/components/charts/DrawdownChart";
import { MonthlyReturnsHeatmap } from "@/components/charts/MonthlyReturnsHeatmap";
import { ReturnsDistribution } from "@/components/charts/ReturnsDistribution";
import { RollingMetrics } from "@/components/charts/RollingMetrics";
import { AnnualReturns } from "@/components/charts/AnnualReturns";
import { formatPercent, formatRatio, formatCurrency } from "@/lib/formatters";
import { CHART_COLORS } from "@/lib/constants";
import { api } from "@/lib/api";
import { Download, Grid3X3, RefreshCw } from "lucide-react";
import Link from "next/link";

interface TearSheetProps {
  result: BacktestResult;
}

const TABS = ["Performance", "Risk", "Trades", "Analysis"] as const;

function ChartPanel({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className="rounded-md overflow-hidden"
      style={{
        background: "var(--color-bg-card)",
        border: "1px solid var(--color-border)",
        boxShadow: "0 1px 3px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.02)",
      }}
    >
      <div
        className="flex items-start justify-between px-5 py-3"
        style={{ borderBottom: "1px solid rgba(37,37,53,0.7)" }}
      >
        <div>
          <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
          {subtitle && (
            <p className="text-[10px] text-text-muted mt-0.5">{subtitle}</p>
          )}
        </div>
      </div>
      <div className="p-4">{children}</div>
    </div>
  );
}

export function TearSheet({ result }: TearSheetProps) {
  const [activeTab, setActiveTab] = useState<(typeof TABS)[number]>("Performance");
  const m = result.metrics;
  const bm = result.benchmark_metrics;

  return (
    <div>
      {/* Summary strip — 6 key metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
        <MetricsCard
          label="Total Return"
          value={formatPercent(m.total_return_pct)}
          benchmark={formatPercent(bm.total_return_pct)}
          positive={m.total_return_pct > 0}
        />
        <MetricsCard
          label="CAGR"
          value={formatPercent(m.cagr_pct)}
          benchmark={formatPercent(bm.cagr_pct)}
          positive={m.cagr_pct > 0}
        />
        <MetricsCard
          label="Sharpe Ratio"
          value={formatRatio(m.sharpe_ratio)}
          benchmark={formatRatio(bm.sharpe_ratio)}
          positive={m.sharpe_ratio > 1}
        />
        <MetricsCard
          label="Max Drawdown"
          value={formatPercent(m.max_drawdown_pct)}
          benchmark={formatPercent(bm.max_drawdown_pct)}
          positive={false}
        />
        <MetricsCard
          label="Win Rate"
          value={formatPercent(m.win_rate_pct, 1)}
          positive={m.win_rate_pct > 50}
        />
        <MetricsCard
          label="Profit Factor"
          value={formatRatio(m.profit_factor)}
          positive={m.profit_factor > 1}
        />
      </div>

      {/* Tabs + export */}
      <div
        className="flex items-center justify-between mb-5"
        style={{ borderBottom: "1px solid var(--color-border)" }}
      >
        <div className="flex gap-0">
          {TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2.5 text-[13px] font-medium border-b-2 transition-all -mb-px ${
                activeTab === tab
                  ? "border-accent-blue text-text-primary"
                  : "border-transparent text-text-muted hover:text-text-secondary"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2 mb-1">
          <Link
            href={`/backtest/${result.id}/walkforward`}
            className="flex items-center gap-1.5 text-xs text-text-muted hover:text-accent-green transition-colors px-3 py-1.5 rounded"
            style={{ border: "1px solid var(--color-border)" }}
          >
            <RefreshCw size={11} />
            Walk-Forward
          </Link>
          <Link
            href={`/backtest/${result.id}/heatmap`}
            className="flex items-center gap-1.5 text-xs text-text-muted hover:text-accent-blue transition-colors px-3 py-1.5 rounded"
            style={{ border: "1px solid var(--color-border)" }}
          >
            <Grid3X3 size={11} />
            2D Heatmap
          </Link>
          <a
            href={api.getExportUrl(result.id)}
            className="flex items-center gap-1.5 text-xs text-text-muted hover:text-text-secondary transition-colors px-3 py-1.5 rounded"
            style={{ border: "1px solid var(--color-border)" }}
          >
            <Download size={11} />
            Export CSV
          </a>
        </div>
      </div>

      {/* ── Performance ── */}
      {activeTab === "Performance" && (
        <div className="space-y-5">
          <ChartPanel
            title="Equity Curve"
            subtitle="Strategy vs benchmark. ▲ green = entries, ▽ red = exits — click any marker for trade detail. Dashed blue = frictionless curve."
          >
            <EquityCurve
              equity={result.equity_curve}
              benchmark={result.benchmark_curve}
              cleanEquity={result.clean_equity_curve}
              trades={result.trades}
            />
          </ChartPanel>

          {/* Transaction cost breakdown */}
          {m.total_cost != null && (
            <div
              className="rounded-md p-4"
              style={{
                background: "var(--color-bg-card)",
                border: "1px solid var(--color-border)",
                boxShadow: "0 1px 3px rgba(0,0,0,0.4)",
              }}
            >
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h3 className="text-sm font-semibold text-text-primary">
                    Transaction Cost Breakdown
                  </h3>
                  <p className="text-[10px] text-text-muted mt-0.5">
                    Total drag vs frictionless execution
                  </p>
                </div>
                <div className="text-right">
                  <p className="font-mono tabular-nums text-accent-red font-bold text-lg">
                    −{formatPercent(m.cost_drag_pct ?? 0, 3).replace("+", "")}
                  </p>
                  <p className="text-[10px] text-text-muted">{m.cost_drag_bps ?? 0} bps total drag</p>
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3">
                {[
                  { label: "Commission", value: m.total_commission ?? 0, color: "var(--color-accent-yellow)" },
                  { label: "Slippage",   value: m.total_slippage ?? 0,   color: "var(--color-accent-red)"    },
                  { label: "Total Cost", value: m.total_cost ?? 0,       color: "var(--color-accent-red)"    },
                ].map(({ label, value, color }) => (
                  <div
                    key={label}
                    className="rounded p-3 text-center"
                    style={{ background: "var(--color-bg-primary)", border: "1px solid var(--color-border)" }}
                  >
                    <p className="section-label mb-1">{label}</p>
                    <p className="font-mono tabular-nums font-semibold text-base" style={{ color }}>
                      ${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          <ChartPanel
            title="Drawdown"
            subtitle="Percentage decline from rolling peak equity"
          >
            <DrawdownChart data={result.drawdown_series} />
          </ChartPanel>

          <ChartPanel
            title="Monthly Returns Heatmap"
            subtitle="Calendar breakdown of monthly P&L"
          >
            <MonthlyReturnsHeatmap data={result.monthly_returns} />
          </ChartPanel>

          <AnnualReturns
            equity={result.equity_curve}
            benchmark={result.benchmark_curve}
          />
        </div>
      )}

      {/* ── Risk ── */}
      {activeTab === "Risk" && (
        <div className="space-y-5">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <MetricsCard label="Volatility"   value={formatPercent(m.annualized_volatility_pct)} />
            <MetricsCard label="Sortino"      value={formatRatio(m.sortino_ratio)}     positive={m.sortino_ratio > 1} />
            <MetricsCard label="Calmar"       value={formatRatio(m.calmar_ratio)}       positive={m.calmar_ratio > 0} />
            <MetricsCard label="Info Ratio"   value={formatRatio(m.information_ratio)}  positive={m.information_ratio > 0} />
            <MetricsCard label="VaR (95%)"    value={formatPercent(m.var_95_pct, 3)}    positive={false} />
            <MetricsCard label="CVaR (95%)"   value={formatPercent(m.cvar_95_pct, 3)}   positive={false} />
            <MetricsCard label="Skewness"     value={formatRatio(m.skewness)} />
            <MetricsCard label="Kurtosis"     value={formatRatio(m.kurtosis)} />
            <MetricsCard label="Beta"         value={formatRatio(m.beta)} />
            <MetricsCard label="Alpha"        value={formatPercent(m.alpha)}            positive={m.alpha > 0} />
            <MetricsCard label="Correlation"  value={formatRatio(m.correlation)} />
            <MetricsCard label="Tracking Err" value={formatPercent(m.tracking_error_pct)} />
          </div>

          <ChartPanel
            title="Rolling Sharpe Ratio"
            subtitle="63-day rolling window — values above 1.0 indicate sustained risk-adjusted outperformance"
          >
            <RollingMetrics
              data={result.rolling_sharpe}
              label="Rolling Sharpe (63-day)"
              color={CHART_COLORS.blue}
            />
          </ChartPanel>

          <ChartPanel
            title="Rolling Volatility"
            subtitle="63-day annualized standard deviation of daily returns"
          >
            <RollingMetrics
              data={result.rolling_volatility}
              label="Rolling Volatility (63-day)"
              color={CHART_COLORS.yellow}
              unit="%"
            />
          </ChartPanel>

          <ChartPanel
            title="Returns Distribution"
            subtitle="Daily return histogram — shape indicates fat tails or skew"
          >
            <ReturnsDistribution equity={result.equity_curve} />
          </ChartPanel>
        </div>
      )}

      {/* ── Trades ── */}
      {activeTab === "Trades" && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <MetricsCard label="Total Trades"  value={String(m.total_trades)} />
            <MetricsCard label="Avg Holding"   value={`${m.avg_holding_period_days}d`} />
            <MetricsCard label="Best Trade"    value={formatPercent(m.best_trade_pct)}  positive={true} />
            <MetricsCard label="Worst Trade"   value={formatPercent(m.worst_trade_pct)} positive={false} />
          </div>
          <ChartPanel title="Trade Log" subtitle="All fills with entry / exit / P&L">
            <TradeLog trades={result.trades} />
          </ChartPanel>
        </div>
      )}

      {/* ── Analysis ── */}
      {activeTab === "Analysis" && (
        <div className="space-y-5">
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <MetricsCard label="Alpha"        value={formatPercent(m.alpha)}             positive={m.alpha > 0}   description="Excess return vs benchmark" />
            <MetricsCard label="Beta"         value={formatRatio(m.beta)}                                          description="Sensitivity to benchmark moves" />
            <MetricsCard label="Avg Exposure" value={formatPercent(m.avg_exposure_pct, 1)}                         description="Average capital invested" />
            <MetricsCard label="Max Exposure" value={formatPercent(m.max_exposure_pct, 1)} />
            <MetricsCard label="DD Duration"  value={`${m.max_drawdown_duration_days}d`}                           description="Longest drawdown period" />
            <MetricsCard label="Current DD"   value={formatPercent(m.current_drawdown_pct)} positive={m.current_drawdown_pct === 0} />
          </div>

          <RegimeAnalysis backtestId={result.id} />
          <FactorExposure backtestId={result.id} />

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
                Run Configuration
              </h3>
            </div>
            <div className="p-5">
              <div className="grid grid-cols-2 gap-x-8 gap-y-0 text-xs">
                {[
                  ["Strategy",    result.config.strategy_id],
                  ["Tickers",     result.config.tickers.join(", ")],
                  ["Period",      `${result.config.start_date} → ${result.config.end_date}`],
                  ["Capital",     formatCurrency(result.config.initial_capital)],
                  ["Slippage",    `${result.config.slippage_bps} bps`],
                  ["Commission",  `$${result.config.commission_per_share}/share`],
                  ["Rebalance",   result.config.rebalance_frequency],
                  ["Max Position",`${result.config.max_position_pct}%`],
                ].map(([label, value]) => (
                  <div
                    key={label}
                    className="flex justify-between py-2"
                    style={{ borderBottom: "1px solid rgba(37,37,53,0.5)" }}
                  >
                    <span className="text-text-muted">{label}</span>
                    <span className="font-mono text-text-primary">{value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
