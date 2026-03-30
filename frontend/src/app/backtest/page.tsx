"use client";

import { useRouter } from "next/navigation";
import { StrategyForm } from "@/components/backtest/StrategyForm";
import { useBacktestStore } from "@/store/backtest-store";
import { useRunBacktest } from "@/hooks/useBacktest";
import { LoadingSpinner } from "@/components/shared/LoadingSpinner";
import { ErrorMessage } from "@/components/shared/ErrorBoundary";
import { Play } from "lucide-react";
import type { BacktestConfig } from "@/lib/types";

export default function NewBacktestPage() {
  const router = useRouter();
  const { config, setLastResult, isRunning, setIsRunning } = useBacktestStore();
  const runMutation = useRunBacktest();

  const handleRun = async () => {
    setIsRunning(true);
    try {
      const result = await runMutation.mutateAsync(config as BacktestConfig);
      setLastResult(result);
      router.push(`/backtest/${result.id}`);
    } catch {
      // Error handled by mutation state
    } finally {
      setIsRunning(false);
    }
  };

  const isValid =
    config.strategy_id &&
    config.tickers &&
    config.tickers.length > 0 &&
    config.start_date &&
    config.end_date;

  return (
    <div>
      <h1 className="text-xl font-semibold mb-6">New Backtest</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Config */}
        <div className="lg:col-span-2">
          <div className="bg-bg-card border border-border rounded p-5">
            <StrategyForm />

            <div className="mt-6 pt-4 border-t border-border">
              {runMutation.error && (
                <div className="mb-4">
                  <ErrorMessage message={runMutation.error.message} />
                </div>
              )}

              <button
                onClick={handleRun}
                disabled={!isValid || isRunning}
                className="w-full flex items-center justify-center gap-2 bg-accent-green text-bg-primary font-medium rounded px-4 py-3 text-sm hover:bg-accent-green/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isRunning ? (
                  <>
                    <LoadingSpinner size={16} />
                    Running Backtest...
                  </>
                ) : (
                  <>
                    <Play size={16} />
                    Run Backtest
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Right: Summary */}
        <div>
          <div className="bg-bg-card border border-border rounded p-5">
            <h2 className="text-sm font-medium text-text-secondary mb-4">
              Configuration Summary
            </h2>
            <dl className="space-y-2 text-xs">
              <div className="flex justify-between">
                <dt className="text-text-muted">Strategy</dt>
                <dd className="text-text-primary font-mono">
                  {config.strategy_id || "-"}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-text-muted">Tickers</dt>
                <dd className="text-text-primary font-mono">
                  {config.tickers?.join(", ") || "-"}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-text-muted">Benchmark</dt>
                <dd className="text-text-primary font-mono">
                  {config.benchmark || "SPY"}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-text-muted">Period</dt>
                <dd className="text-text-primary font-mono">
                  {config.start_date || "?"} to {config.end_date || "?"}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-text-muted">Capital</dt>
                <dd className="text-text-primary font-mono">
                  ${(config.initial_capital || 100000).toLocaleString()}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-text-muted">Slippage</dt>
                <dd className="text-text-primary font-mono">
                  {config.slippage_bps ?? 5} bps
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-text-muted">Rebalance</dt>
                <dd className="text-text-primary font-mono">
                  {config.rebalance_frequency || "daily"}
                </dd>
              </div>
            </dl>
          </div>
        </div>
      </div>
    </div>
  );
}
