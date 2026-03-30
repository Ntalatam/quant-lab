"use client";

import { useEffect, useRef, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { StrategyForm } from "@/components/backtest/StrategyForm";
import { useBacktestStore } from "@/store/backtest-store";
import { useBacktestProgress } from "@/hooks/useBacktestProgress";
import { Play, Zap, Wifi, TrendingUp } from "lucide-react";
import type { BacktestConfig } from "@/lib/types";

function ProgressBar({ pct }: { pct: number }) {
  return (
    <div
      className="w-full rounded-full overflow-hidden"
      style={{ height: 6, background: "rgba(68,136,255,0.12)" }}
    >
      <div
        className="h-full rounded-full transition-all duration-300"
        style={{
          width: `${Math.round(pct * 100)}%`,
          background: "linear-gradient(90deg, var(--color-accent-blue), var(--color-accent-green))",
          boxShadow: "0 0 8px rgba(0,212,170,0.4)",
        }}
      />
    </div>
  );
}

function ConfigLoader() {
  const searchParams = useSearchParams();
  const { setConfig } = useBacktestStore();
  const applied = useRef(false);

  useEffect(() => {
    if (applied.current) return;
    const encoded = searchParams.get("config");
    if (!encoded) return;
    try {
      const cfg = JSON.parse(atob(decodeURIComponent(encoded)));
      setConfig(cfg);
      applied.current = true;
    } catch {
      // Invalid config param — ignore silently
    }
  }, [searchParams, setConfig]);

  return null;
}

export default function NewBacktestPage() {
  const router = useRouter();
  const { config, setLastResult } = useBacktestStore();
  const { progress, run, reset } = useBacktestProgress();

  const isRunning = progress.status === "running" || progress.status === "connecting";

  const handleRun = async () => {
    try {
      const id = await run(config as BacktestConfig);
      router.push(`/backtest/${id}`);
    } catch {
      // Error displayed in progress state
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
      <Suspense fallback={null}>
        <ConfigLoader />
      </Suspense>
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
              {/* Error state */}
              {progress.status === "error" && (
                <div
                  className="mb-4 rounded p-3 flex items-start justify-between gap-3"
                  style={{
                    background: "rgba(255,71,87,0.08)",
                    border: "1px solid rgba(255,71,87,0.25)",
                  }}
                >
                  <p className="text-xs text-accent-red">{progress.message}</p>
                  <button
                    onClick={reset}
                    className="text-[10px] text-text-muted hover:text-text-secondary shrink-0"
                  >
                    Dismiss
                  </button>
                </div>
              )}

              {/* Live progress UI */}
              {(progress.status === "connecting" || progress.status === "running") && (
                <div
                  className="mb-4 rounded-md p-4 space-y-3"
                  style={{
                    background: "rgba(68,136,255,0.05)",
                    border: "1px solid rgba(68,136,255,0.18)",
                  }}
                >
                  {progress.status === "connecting" && (
                    <div className="flex items-center gap-2">
                      <Wifi size={13} className="text-accent-blue animate-pulse" />
                      <span className="text-xs text-accent-blue">Connecting to simulation engine…</span>
                    </div>
                  )}

                  {progress.status === "running" && (
                    <>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <TrendingUp size={13} className="text-accent-green" />
                          <span className="text-xs font-medium text-text-primary">
                            Simulating — {Math.round(progress.pct * 100)}%
                          </span>
                        </div>
                        <span className="text-[10px] font-mono text-text-muted">
                          {progress.bar.toLocaleString()} / {progress.total.toLocaleString()} bars
                        </span>
                      </div>

                      <ProgressBar pct={progress.pct} />

                      <div className="flex justify-between text-[10px] font-mono">
                        <span className="text-text-muted">
                          Date: <span className="text-text-secondary">{progress.date}</span>
                        </span>
                        <span className="text-text-muted">
                          Equity:{" "}
                          <span className="text-accent-green font-semibold">
                            ${progress.equity.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                          </span>
                        </span>
                      </div>
                    </>
                  )}
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
                {progress.status === "connecting" ? (
                  <>
                    <Wifi size={15} className="animate-pulse" />
                    Connecting…
                  </>
                ) : progress.status === "running" ? (
                  <>
                    <TrendingUp size={15} />
                    Running — {Math.round(progress.pct * 100)}%
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

          {/* WebSocket streaming note */}
          <div
            className="rounded-md p-3"
            style={{
              background: "rgba(0,212,170,0.04)",
              border: "1px solid rgba(0,212,170,0.14)",
            }}
          >
            <div className="flex items-center gap-1.5 mb-1">
              <Wifi size={10} className="text-accent-green" />
              <span className="text-[10px] font-medium text-accent-green">Live streaming</span>
            </div>
            <p className="text-[10px] text-text-muted leading-relaxed">
              Progress is streamed in real time via WebSocket — watch equity build bar-by-bar as the simulation runs.
            </p>
          </div>

          {/* Engine note */}
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
