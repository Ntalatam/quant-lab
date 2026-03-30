"use client";

import Link from "next/link";
import { useBacktestList } from "@/hooks/useBacktest";
import { PageLoading } from "@/components/shared/LoadingSpinner";
import { ErrorMessage } from "@/components/shared/ErrorBoundary";
import { formatPercent, formatRatio, formatDate } from "@/lib/formatters";
import { Play, BarChart3, TrendingUp } from "lucide-react";

export default function DashboardPage() {
  const { data: backtests, isLoading, error } = useBacktestList();

  if (isLoading) return <PageLoading />;
  if (error) return <ErrorMessage message={error.message} />;

  const recent = backtests?.slice(0, 10) || [];
  const totalRuns = backtests?.length || 0;
  const bestSharpe = backtests?.length
    ? Math.max(...backtests.map((b) => b.sharpe_ratio))
    : 0;
  const avgReturn = backtests?.length
    ? backtests.reduce((sum, b) => sum + b.total_return_pct, 0) /
      backtests.length
    : 0;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold">Dashboard</h1>
        <Link
          href="/backtest"
          className="flex items-center gap-2 bg-accent-green/10 text-accent-green border border-accent-green/20 rounded px-4 py-2 text-sm hover:bg-accent-green/20 transition-colors"
        >
          <Play size={14} />
          New Backtest
        </Link>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <div className="bg-bg-card border border-border rounded p-4">
          <div className="flex items-center gap-2 mb-2">
            <BarChart3 size={14} className="text-accent-blue" />
            <span className="text-xs text-text-muted uppercase tracking-wider">
              Total Backtests
            </span>
          </div>
          <p className="text-2xl font-mono tabular-nums font-semibold">
            {totalRuns}
          </p>
        </div>
        <div className="bg-bg-card border border-border rounded p-4">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp size={14} className="text-accent-green" />
            <span className="text-xs text-text-muted uppercase tracking-wider">
              Best Sharpe
            </span>
          </div>
          <p className="text-2xl font-mono tabular-nums font-semibold text-accent-green">
            {formatRatio(bestSharpe)}
          </p>
        </div>
        <div className="bg-bg-card border border-border rounded p-4">
          <div className="flex items-center gap-2 mb-2">
            <BarChart3 size={14} className="text-accent-yellow" />
            <span className="text-xs text-text-muted uppercase tracking-wider">
              Avg Return
            </span>
          </div>
          <p
            className={`text-2xl font-mono tabular-nums font-semibold ${avgReturn >= 0 ? "text-accent-green" : "text-accent-red"}`}
          >
            {formatPercent(avgReturn)}
          </p>
        </div>
      </div>

      {/* Recent Backtests */}
      <div className="bg-bg-card border border-border rounded">
        <div className="px-4 py-3 border-b border-border">
          <h2 className="text-sm font-medium text-text-secondary">
            Recent Backtests
          </h2>
        </div>
        {recent.length === 0 ? (
          <div className="text-center py-12 text-text-muted">
            <p className="mb-2">No backtests yet</p>
            <Link
              href="/backtest"
              className="text-accent-blue hover:underline text-sm"
            >
              Run your first backtest
            </Link>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-text-muted border-b border-border">
                <th className="text-left font-normal py-2 px-4">Strategy</th>
                <th className="text-left font-normal py-2 px-4">Tickers</th>
                <th className="text-left font-normal py-2 px-4">Period</th>
                <th className="text-right font-normal py-2 px-4">Return</th>
                <th className="text-right font-normal py-2 px-4">Sharpe</th>
                <th className="text-right font-normal py-2 px-4">Max DD</th>
                <th className="text-right font-normal py-2 px-4">Date</th>
              </tr>
            </thead>
            <tbody>
              {recent.map((bt) => (
                <tr
                  key={bt.id}
                  className="border-b border-border/50 hover:bg-bg-hover transition-colors"
                >
                  <td className="py-2 px-4">
                    <Link
                      href={`/backtest/${bt.id}`}
                      className="text-accent-blue hover:underline"
                    >
                      {bt.strategy_name}
                    </Link>
                  </td>
                  <td className="py-2 px-4 text-text-secondary font-mono text-xs">
                    {bt.tickers.join(", ")}
                  </td>
                  <td className="py-2 px-4 text-text-secondary text-xs">
                    {bt.start_date} — {bt.end_date}
                  </td>
                  <td
                    className={`py-2 px-4 text-right font-mono tabular-nums ${bt.total_return_pct >= 0 ? "text-accent-green" : "text-accent-red"}`}
                  >
                    {formatPercent(bt.total_return_pct)}
                  </td>
                  <td className="py-2 px-4 text-right font-mono tabular-nums text-text-primary">
                    {formatRatio(bt.sharpe_ratio)}
                  </td>
                  <td className="py-2 px-4 text-right font-mono tabular-nums text-accent-red">
                    {formatPercent(bt.max_drawdown_pct)}
                  </td>
                  <td className="py-2 px-4 text-right text-text-muted text-xs">
                    {bt.created_at ? formatDate(bt.created_at) : "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
