"use client";

import { useRouter } from "next/navigation";
import { StrategyForm } from "@/components/backtest/StrategyForm";
import { useBacktestStore } from "@/store/backtest-store";
import { useRunBacktest } from "@/hooks/useBacktest";
import { LoadingSpinner } from "@/components/shared/LoadingSpinner";
import { ErrorMessage } from "@/components/shared/ErrorBoundary";
import { Play, Zap } from "lucide-react";
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
      {/* Page header */}
      <div className="mb-7">
        <h1 className="text-xl font-bold text-text-primary tracking-tight">
          New Backtest
        </h1>
        <p className="text-xs text-text-muted mt-0.5">
          Configure your strategy, set execution parameters, and run the simulation
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Config */}
        <div className="lg:col-span-2">
          <div
            className="rounded-md p-5"
            style={{
              background: "var(--color-bg-card)",
              border: "1px solid var(--color-border)",
              boxShadow: "0 1px 3px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.02)",
            }}
          >
            <StrategyForm />

            <div
              className="mt-6 pt-5"
              style={{ borderTop: "1px solid var(--color-border)" }}
            >
              {runMutation.error && (
                <div className="mb-4">
                  <ErrorMessage message={runMutation.error.message} />
                </div>
              )}

              <button
                onClick={handleRun}
                disabled={!isValid || isRunning}
                className="w-full flex items-center justify-center gap-2 font-semibold rounded py-3 text-sm transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                style={
                  isValid && !isRunning
                    ? {
                        background: "var(--color-accent-green)",
                        color: "var(--color-bg-primary)",
                        boxShadow: "0 0 20px rgba(0,212,170,0.2)",
                      }
                    : {
                        background: "rgba(0,212,170,0.15)",
                        color: "var(--color-accent-green)",
                        border: "1px solid rgba(0,212,170,0.2)",
                      }
                }
              >
                {isRunning ? (
                  <>
                    <LoadingSpinner size={15} />
                    Running Simulation…
                  </>
                ) : (
                  <>
                    <Play size={15} />
                    Run Backtest
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Right: Live preview */}
        <div className="space-y-4">
          <div
            className="rounded-md p-4"
            style={{
              background: "var(--color-bg-card)",
              border: "1px solid var(--color-border)",
              boxShadow: "0 1px 3px rgba(0,0,0,0.4)",
            }}
          >
            <div className="flex items-center gap-2 mb-4">
              <Zap size={12} className="text-accent-yellow" />
              <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
                Configuration Preview
              </h2>
            </div>

            <dl className="space-y-2.5">
              {[
                { label: "Strategy",   value: config.strategy_id || "—" },
                { label: "Tickers",    value: config.tickers?.join(", ") || "—" },
                { label: "Benchmark",  value: config.benchmark || "SPY" },
                { label: "Period",     value: config.start_date && config.end_date ? `${config.start_date} → ${config.end_date}` : "—" },
                { label: "Capital",    value: `$${(config.initial_capital || 100000).toLocaleString()}` },
                { label: "Slippage",   value: `${config.slippage_bps ?? 5} bps` },
                { label: "Commission", value: `$${config.commission_per_share ?? 0.005}/share` },
                { label: "Rebalance",  value: config.rebalance_frequency || "daily" },
                { label: "Max Pos",    value: `${config.max_position_pct ?? 25}%` },
              ].map(({ label, value }) => (
                <div
                  key={label}
                  className="flex justify-between items-center text-xs py-1"
                  style={{ borderBottom: "1px solid rgba(37,37,53,0.5)" }}
                >
                  <dt className="text-text-muted">{label}</dt>
                  <dd className="font-mono text-text-primary text-right max-w-[60%] truncate">
                    {value}
                  </dd>
                </div>
              ))}
            </dl>
          </div>

          {/* Execution note */}
          <div
            className="rounded-md p-3"
            style={{
              background: "rgba(68,136,255,0.04)",
              border: "1px solid rgba(68,136,255,0.14)",
            }}
          >
            <p className="text-[10px] text-text-muted leading-relaxed">
              <span className="text-accent-blue font-medium">Event-driven engine</span>{" "}
              — Each bar is processed sequentially. The strategy only sees data
              available at that point in time. No lookahead bias.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
