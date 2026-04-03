"use client";

import Link from "next/link";
import { useBacktestList, useDeleteBacktest } from "@/hooks/useBacktest";
import { PageLoading } from "@/components/shared/LoadingSpinner";
import { ErrorMessage } from "@/components/shared/ErrorBoundary";
import { formatPercent, formatRatio, formatDate } from "@/lib/formatters";
import { Trash2, Play, ChevronRight } from "lucide-react";

const STRATEGY_CATEGORY_MAP: Record<string, { label: string; cls: string }> = {
  sma_crossover:       { label: "Trend",    cls: "badge-trend"     },
  mean_reversion:      { label: "Mean Rev", cls: "badge-reversion" },
  momentum:            { label: "Momentum", cls: "badge-momentum"  },
  pairs_trading:       { label: "Arb",      cls: "badge-arb"       },
  ml_classifier:       { label: "ML",       cls: "badge-arb"       },
  rsi_mean_reversion:  { label: "RSI",      cls: "badge-reversion" },
  macd_crossover:      { label: "MACD",     cls: "badge-trend"     },
  donchian_breakout:   { label: "Turtle",   cls: "badge-trend"     },
  vol_target_trend:    { label: "VolTgt",   cls: "badge-momentum"  },
};

function SharpeCell({ value }: { value: number }) {
  const color =
    value >= 1.5 ? "text-accent-green" :
    value >= 0.8 ? "text-accent-yellow" :
    value > 0    ? "text-text-secondary" :
                   "text-accent-red";
  return <span className={`font-mono tabular-nums ${color}`}>{formatRatio(value)}</span>;
}

export default function ResultsPage() {
  const { data: backtests, isLoading, error } = useBacktestList();
  const deleteMutation = useDeleteBacktest();

  if (isLoading) return <PageLoading />;
  if (error) return <ErrorMessage message={error.message} />;

  return (
    <div>
      {/* Page header */}
      <div className="flex items-center justify-between mb-7">
        <div>
          <h1 className="text-xl font-bold text-text-primary tracking-tight">
            Backtest Results
          </h1>
          <p className="text-xs text-text-muted mt-0.5">
            {backtests?.length ?? 0} run{backtests?.length !== 1 ? "s" : ""} on record
          </p>
        </div>
        <Link
          href="/backtest"
          className="flex items-center gap-2 text-xs font-medium px-4 py-2 rounded transition-all"
          style={{
            background: "rgba(0,212,170,0.1)",
            border: "1px solid rgba(0,212,170,0.22)",
            color: "var(--color-accent-green)",
          }}
        >
          <Play size={12} />
          New Backtest
        </Link>
      </div>

      {(!backtests || backtests.length === 0) ? (
        <div
          className="rounded-md p-12 text-center"
          style={{
            background: "var(--color-bg-card)",
            border: "1px solid var(--color-border)",
          }}
        >
          <p className="text-text-secondary text-sm mb-2">No backtest results yet.</p>
          <p className="text-text-muted text-xs mb-5">
            Load market data, configure a strategy, and run your first simulation.
          </p>
          <Link
            href="/backtest"
            className="inline-flex items-center gap-1.5 text-xs font-medium px-4 py-2 rounded transition-all"
            style={{
              background: "rgba(68,136,255,0.1)",
              border: "1px solid rgba(68,136,255,0.22)",
              color: "var(--color-accent-blue)",
            }}
          >
            <Play size={12} />
            New Backtest <ChevronRight size={11} />
          </Link>
        </div>
      ) : (
        <div
          className="rounded-md overflow-hidden"
          style={{
            background: "var(--color-bg-card)",
            border: "1px solid var(--color-border)",
            boxShadow: "0 1px 3px rgba(0,0,0,0.4)",
          }}
        >
          <table className="w-full text-sm">
            <thead>
              <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
                {["Strategy", "Type", "Tickers", "Period", "Return", "Sharpe", "Max DD", "Run", ""].map(
                  (h, i) => (
                    <th
                      key={i}
                      className={`section-label py-2.5 px-4 font-normal ${
                        ["Return", "Sharpe", "Max DD", "Run"].includes(h)
                          ? "text-right"
                          : "text-left"
                      }`}
                    >
                      {h}
                    </th>
                  )
                )}
              </tr>
            </thead>
            <tbody>
              {backtests.map((bt) => {
                const cat =
                  STRATEGY_CATEGORY_MAP[bt.strategy_name] ??
                  STRATEGY_CATEGORY_MAP[bt.strategy_name?.toLowerCase()] ?? {
                    label: "Other",
                    cls: "badge-trend",
                  };
                return (
                  <tr
                    key={bt.id}
                    className="group transition-colors hover:bg-bg-hover"
                    style={{ borderBottom: "1px solid rgba(37,37,53,0.6)" }}
                  >
                    <td className="py-2.5 px-4">
                      <Link
                        href={`/backtest/${bt.id}`}
                        className="text-accent-blue hover:underline font-medium text-[13px]"
                      >
                        {bt.strategy_name}
                      </Link>
                    </td>
                    <td className="py-2.5 px-4">
                      <span
                        className={`${cat.cls} text-[9px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full`}
                      >
                        {cat.label}
                      </span>
                    </td>
                    <td className="py-2.5 px-4 text-text-secondary font-mono text-xs">
                      {bt.tickers.join(", ")}
                    </td>
                    <td className="py-2.5 px-4 text-text-muted text-xs">
                      {bt.start_date} — {bt.end_date}
                    </td>
                    <td
                      className={`py-2.5 px-4 text-right font-mono tabular-nums text-[13px] ${
                        bt.total_return_pct >= 0 ? "text-accent-green" : "text-accent-red"
                      }`}
                    >
                      {formatPercent(bt.total_return_pct)}
                    </td>
                    <td className="py-2.5 px-4 text-right">
                      <SharpeCell value={bt.sharpe_ratio} />
                    </td>
                    <td className="py-2.5 px-4 text-right font-mono tabular-nums text-accent-red text-[13px]">
                      {formatPercent(bt.max_drawdown_pct)}
                    </td>
                    <td className="py-2.5 px-4 text-right text-text-muted text-[11px]">
                      {bt.created_at ? formatDate(bt.created_at) : "—"}
                    </td>
                    <td className="py-2.5 px-2">
                      <button
                        onClick={() => deleteMutation.mutate(bt.id)}
                        className="opacity-0 group-hover:opacity-100 text-text-muted hover:text-accent-red transition-all p-1 rounded"
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
      )}
    </div>
  );
}
