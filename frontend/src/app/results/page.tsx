"use client";

import Link from "next/link";
import { ChevronRight, Play, Sparkles, Trash2, TrendingUp } from "lucide-react";

import { ErrorMessage } from "@/components/shared/ErrorBoundary";
import { PageHeader } from "@/components/shared/PageHeader";
import { PageLoading } from "@/components/shared/LoadingSpinner";
import { useBacktestList, useDeleteBacktest } from "@/hooks/useBacktest";
import { formatDate, formatPercent, formatRatio } from "@/lib/formatters";

const STRATEGY_CATEGORY_MAP: Record<string, { label: string; cls: string }> = {
  sma_crossover: { label: "Trend", cls: "badge-trend" },
  mean_reversion: { label: "Mean Rev", cls: "badge-reversion" },
  momentum: { label: "Momentum", cls: "badge-momentum" },
  pairs_trading: { label: "Arb", cls: "badge-arb" },
  ml_classifier: { label: "ML", cls: "badge-arb" },
  rsi_mean_reversion: { label: "RSI", cls: "badge-reversion" },
  macd_crossover: { label: "MACD", cls: "badge-trend" },
  donchian_breakout: { label: "Turtle", cls: "badge-trend" },
  vol_target_trend: { label: "VolTgt", cls: "badge-momentum" },
};

function SharpeCell({ value }: { value: number }) {
  const color =
    value >= 1.5
      ? "text-accent-green"
      : value >= 0.8
        ? "text-accent-yellow"
        : value > 0
          ? "text-text-secondary"
          : "text-accent-red";
  return (
    <span className={`font-mono tabular-nums ${color}`}>
      {formatRatio(value)}
    </span>
  );
}

export default function ResultsPage() {
  const { data: backtests, isLoading, error } = useBacktestList();
  const deleteMutation = useDeleteBacktest();

  if (isLoading) return <PageLoading />;
  if (error) return <ErrorMessage message={error.message} />;

  const bestSharpe = backtests?.length
    ? Math.max(...backtests.map((bt) => bt.sharpe_ratio))
    : 0;
  const avgReturn = backtests?.length
    ? backtests.reduce((sum, bt) => sum + bt.total_return_pct, 0) /
      backtests.length
    : 0;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Research archive"
        title="Backtest Results"
        description="Browse every saved run, triage the strongest ideas, and jump straight from a summary row into the full tear sheet."
        meta={
          <>
            <span className="status-pill">
              <Sparkles size={12} className="text-accent-blue" />
              {backtests?.length ?? 0} stored runs
            </span>
            <span className="status-pill">
              <TrendingUp size={12} className="text-accent-green" />
              Best Sharpe {formatRatio(bestSharpe)}
            </span>
            <span className="status-pill">
              <Sparkles size={12} className="text-accent-yellow" />
              Avg return {formatPercent(avgReturn)}
            </span>
          </>
        }
        actions={
          <Link href="/backtest" className="action-primary">
            <Play size={13} />
            New Backtest
          </Link>
        }
      />

      {!backtests || backtests.length === 0 ? (
        <div className="panel-soft p-12 text-center">
          <p className="text-text-secondary text-sm mb-2">
            No backtest results yet.
          </p>
          <p className="text-text-muted text-xs mb-5">
            Load market data, configure a strategy, and run your first
            simulation.
          </p>
          <Link href="/backtest" className="action-secondary">
            <Play size={12} />
            New Backtest <ChevronRight size={11} />
          </Link>
        </div>
      ) : (
        <div className="table-shell">
          <div className="table-scroll">
            <table className="min-w-full text-sm">
              <thead>
                <tr>
                  {[
                    "Strategy",
                    "Type",
                    "Tickers",
                    "Period",
                    "Return",
                    "Sharpe",
                    "Max DD",
                    "Run",
                    "",
                  ].map((h, i) => (
                    <th
                      key={i}
                      className={`section-label px-4 py-3 font-normal ${
                        ["Return", "Sharpe", "Max DD", "Run"].includes(h)
                          ? "text-right"
                          : "text-left"
                      }`}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {backtests.map((bt) => {
                  const cat = STRATEGY_CATEGORY_MAP[bt.strategy_name] ??
                    STRATEGY_CATEGORY_MAP[bt.strategy_name?.toLowerCase()] ?? {
                      label: "Other",
                      cls: "badge-trend",
                    };
                  return (
                    <tr key={bt.id} className="group">
                      <td className="px-4 py-3">
                        <Link
                          href={`/backtest/${bt.id}`}
                          className="text-accent-blue hover:underline font-medium text-[13px]"
                        >
                          {bt.strategy_name}
                        </Link>
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`${cat.cls} text-[9px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full`}
                        >
                          {cat.label}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-text-secondary font-mono text-xs">
                        {bt.tickers.join(", ")}
                      </td>
                      <td className="px-4 py-3 text-text-muted text-xs">
                        {bt.start_date} — {bt.end_date}
                      </td>
                      <td
                        className={`px-4 py-3 text-right font-mono tabular-nums text-[13px] ${
                          bt.total_return_pct >= 0
                            ? "text-accent-green"
                            : "text-accent-red"
                        }`}
                      >
                        {formatPercent(bt.total_return_pct)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <SharpeCell value={bt.sharpe_ratio} />
                      </td>
                      <td className="px-4 py-3 text-right font-mono tabular-nums text-accent-red text-[13px]">
                        {formatPercent(bt.max_drawdown_pct)}
                      </td>
                      <td className="px-4 py-3 text-right text-text-muted text-[11px]">
                        {bt.created_at ? formatDate(bt.created_at) : "—"}
                      </td>
                      <td className="px-2 py-3">
                        <button
                          onClick={() => deleteMutation.mutate(bt.id)}
                          className="rounded-full p-1 opacity-0 transition-all group-hover:opacity-100 text-text-muted hover:bg-bg-hover hover:text-accent-red"
                          title="Delete"
                        >
                          <Trash2 size={13} />
                        </button>
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
