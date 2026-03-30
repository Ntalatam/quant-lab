"use client";

import Link from "next/link";
import { useBacktestList, useDeleteBacktest } from "@/hooks/useBacktest";
import { PageLoading } from "@/components/shared/LoadingSpinner";
import { ErrorMessage } from "@/components/shared/ErrorBoundary";
import { formatPercent, formatRatio, formatDate } from "@/lib/formatters";
import { Trash2 } from "lucide-react";

export default function ResultsPage() {
  const { data: backtests, isLoading, error } = useBacktestList();
  const deleteMutation = useDeleteBacktest();

  if (isLoading) return <PageLoading />;
  if (error) return <ErrorMessage message={error.message} />;

  return (
    <div>
      <h1 className="text-xl font-semibold mb-6">Backtest Results</h1>

      {(!backtests || backtests.length === 0) ? (
        <div className="text-center py-16 text-text-muted">
          <p className="mb-2">No backtests yet</p>
          <Link href="/backtest" className="text-accent-blue hover:underline text-sm">
            Run your first backtest
          </Link>
        </div>
      ) : (
        <div className="bg-bg-card border border-border rounded">
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
                <th className="w-10"></th>
              </tr>
            </thead>
            <tbody>
              {backtests.map((bt) => (
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
                  <td className="py-2 px-4 text-right font-mono tabular-nums">
                    {formatRatio(bt.sharpe_ratio)}
                  </td>
                  <td className="py-2 px-4 text-right font-mono tabular-nums text-accent-red">
                    {formatPercent(bt.max_drawdown_pct)}
                  </td>
                  <td className="py-2 px-4 text-right text-text-muted text-xs">
                    {bt.created_at ? formatDate(bt.created_at) : "-"}
                  </td>
                  <td className="py-2 px-2">
                    <button
                      onClick={() => deleteMutation.mutate(bt.id)}
                      className="text-text-muted hover:text-accent-red transition-colors p-1"
                      title="Delete"
                    >
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
