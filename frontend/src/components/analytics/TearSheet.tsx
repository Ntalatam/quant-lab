"use client";

import { useState } from "react";
import type { BacktestResult } from "@/lib/types";
import { MetricsCard } from "./MetricsCard";
import { TradeLog } from "./TradeLog";
import { EquityCurve } from "@/components/charts/EquityCurve";
import { DrawdownChart } from "@/components/charts/DrawdownChart";
import { MonthlyReturnsHeatmap } from "@/components/charts/MonthlyReturnsHeatmap";
import { ReturnsDistribution } from "@/components/charts/ReturnsDistribution";
import { RollingMetrics } from "@/components/charts/RollingMetrics";
import { formatPercent, formatRatio, formatCurrency } from "@/lib/formatters";
import { CHART_COLORS } from "@/lib/constants";
import { api } from "@/lib/api";
import { Download } from "lucide-react";

interface TearSheetProps {
  result: BacktestResult;
}

const TABS = ["Performance", "Risk", "Trades", "Analysis"] as const;

export function TearSheet({ result }: TearSheetProps) {
  const [activeTab, setActiveTab] = useState<(typeof TABS)[number]>("Performance");
  const m = result.metrics;
  const bm = result.benchmark_metrics;

  return (
    <div>
      {/* Summary Strip */}
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
          positive={m.sharpe_ratio > 0}
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

      {/* Tabs */}
      <div className="flex items-center justify-between border-b border-border mb-4">
        <div className="flex gap-0">
          {TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-sm border-b-2 transition-colors ${
                activeTab === tab
                  ? "border-accent-blue text-text-primary"
                  : "border-transparent text-text-secondary hover:text-text-primary"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
        <a
          href={api.getExportUrl(result.id)}
          className="flex items-center gap-1.5 text-xs text-text-secondary hover:text-text-primary transition-colors px-3 py-1.5 border border-border rounded hover:border-text-muted/30"
        >
          <Download size={12} />
          Export CSV
        </a>
      </div>

      {/* Tab Content */}
      {activeTab === "Performance" && (
        <div className="space-y-6">
          <div className="bg-bg-card border border-border rounded p-4">
            <h3 className="text-sm font-medium text-text-secondary mb-3">
              Equity Curve
            </h3>
            <EquityCurve
              equity={result.equity_curve}
              benchmark={result.benchmark_curve}
            />
          </div>

          <div className="bg-bg-card border border-border rounded p-4">
            <h3 className="text-sm font-medium text-text-secondary mb-3">
              Drawdown
            </h3>
            <DrawdownChart data={result.drawdown_series} />
          </div>

          <div className="bg-bg-card border border-border rounded p-4">
            <h3 className="text-sm font-medium text-text-secondary mb-3">
              Monthly Returns
            </h3>
            <MonthlyReturnsHeatmap data={result.monthly_returns} />
          </div>
        </div>
      )}

      {activeTab === "Risk" && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <MetricsCard label="Volatility" value={formatPercent(m.annualized_volatility_pct)} />
            <MetricsCard label="Sortino" value={formatRatio(m.sortino_ratio)} positive={m.sortino_ratio > 0} />
            <MetricsCard label="Calmar" value={formatRatio(m.calmar_ratio)} positive={m.calmar_ratio > 0} />
            <MetricsCard label="Info Ratio" value={formatRatio(m.information_ratio)} positive={m.information_ratio > 0} />
            <MetricsCard label="VaR (95%)" value={formatPercent(m.var_95_pct, 3)} positive={false} />
            <MetricsCard label="CVaR (95%)" value={formatPercent(m.cvar_95_pct, 3)} positive={false} />
            <MetricsCard label="Skewness" value={formatRatio(m.skewness)} />
            <MetricsCard label="Kurtosis" value={formatRatio(m.kurtosis)} />
            <MetricsCard label="Beta" value={formatRatio(m.beta)} />
            <MetricsCard label="Alpha" value={formatPercent(m.alpha)} positive={m.alpha > 0} />
            <MetricsCard label="Correlation" value={formatRatio(m.correlation)} />
            <MetricsCard label="Tracking Error" value={formatPercent(m.tracking_error_pct)} />
          </div>

          <div className="bg-bg-card border border-border rounded p-4">
            <RollingMetrics
              data={result.rolling_sharpe}
              label="Rolling Sharpe (63-day)"
              color={CHART_COLORS.blue}
            />
          </div>

          <div className="bg-bg-card border border-border rounded p-4">
            <RollingMetrics
              data={result.rolling_volatility}
              label="Rolling Volatility (63-day)"
              color={CHART_COLORS.yellow}
              unit="%"
            />
          </div>

          <div className="bg-bg-card border border-border rounded p-4">
            <h3 className="text-sm font-medium text-text-secondary mb-3">
              Returns Distribution
            </h3>
            <ReturnsDistribution equity={result.equity_curve} />
          </div>
        </div>
      )}

      {activeTab === "Trades" && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <MetricsCard label="Total Trades" value={String(m.total_trades)} />
            <MetricsCard label="Avg Holding" value={`${m.avg_holding_period_days}d`} />
            <MetricsCard label="Best Trade" value={formatPercent(m.best_trade_pct)} positive={true} />
            <MetricsCard label="Worst Trade" value={formatPercent(m.worst_trade_pct)} positive={false} />
          </div>
          <div className="bg-bg-card border border-border rounded p-4">
            <TradeLog trades={result.trades} />
          </div>
        </div>
      )}

      {activeTab === "Analysis" && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <MetricsCard label="Alpha" value={formatPercent(m.alpha)} positive={m.alpha > 0} description="Excess return vs benchmark" />
            <MetricsCard label="Beta" value={formatRatio(m.beta)} description="Sensitivity to benchmark moves" />
            <MetricsCard label="Avg Exposure" value={formatPercent(m.avg_exposure_pct, 1)} description="Average capital invested" />
            <MetricsCard label="Max Exposure" value={formatPercent(m.max_exposure_pct, 1)} />
            <MetricsCard label="DD Duration" value={`${m.max_drawdown_duration_days}d`} description="Longest drawdown period" />
            <MetricsCard label="Current DD" value={formatPercent(m.current_drawdown_pct)} positive={m.current_drawdown_pct === 0} />
          </div>

          <div className="bg-bg-card border border-border rounded p-4">
            <h3 className="text-sm font-medium text-text-secondary mb-2">
              Configuration
            </h3>
            <div className="grid grid-cols-2 gap-x-8 gap-y-1 text-xs">
              <div className="flex justify-between py-1 border-b border-border/50">
                <span className="text-text-muted">Strategy</span>
                <span className="text-text-primary font-mono">{result.config.strategy_id}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border/50">
                <span className="text-text-muted">Tickers</span>
                <span className="text-text-primary font-mono">{result.config.tickers.join(", ")}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border/50">
                <span className="text-text-muted">Period</span>
                <span className="text-text-primary font-mono">{result.config.start_date} to {result.config.end_date}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border/50">
                <span className="text-text-muted">Capital</span>
                <span className="text-text-primary font-mono">{formatCurrency(result.config.initial_capital)}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border/50">
                <span className="text-text-muted">Slippage</span>
                <span className="text-text-primary font-mono">{result.config.slippage_bps} bps</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border/50">
                <span className="text-text-muted">Commission</span>
                <span className="text-text-primary font-mono">${result.config.commission_per_share}/share</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border/50">
                <span className="text-text-muted">Rebalance</span>
                <span className="text-text-primary font-mono">{result.config.rebalance_frequency}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-border/50">
                <span className="text-text-muted">Max Position</span>
                <span className="text-text-primary font-mono">{result.config.max_position_pct}%</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
