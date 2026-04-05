"use client";

import { useEffect, useRef, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Play, Radar, TrendingUp, Wifi, Zap } from "lucide-react";

import type { BacktestConfig } from "@/lib/types";
import { StrategyForm } from "@/components/backtest/StrategyForm";
import { PageHeader } from "@/components/shared/PageHeader";
import { useBacktestProgress } from "@/hooks/useBacktestProgress";
import { useBacktestStore } from "@/store/backtest-store";

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
          background:
            "linear-gradient(90deg, var(--color-accent-blue), var(--color-accent-green))",
          boxShadow: "0 0 8px rgba(0,212,170,0.4)",
        }}
      />
    </div>
  );
}

function ConfigLoader() {
  const searchParams = useSearchParams();
  const setConfig = useBacktestStore((state) => state.setConfig);
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
  const config = useBacktestStore((state) => state.config);
  const { progress, run, reset } = useBacktestProgress();

  const isRunning =
    progress.status === "running" || progress.status === "connecting";

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
      <PageHeader
        eyebrow="Research launchpad"
        title="New Backtest"
        description="Configure your strategy, execution controls, and portfolio construction in one place, then stream the simulation live as equity updates bar by bar."
        meta={
          <>
            <span className="status-pill">
              <Wifi size={12} className="text-accent-blue" />
              WebSocket progress
            </span>
            <span className="status-pill">
              <Radar size={12} className="text-accent-yellow" />
              Event-driven execution
            </span>
          </>
        }
        actions={
          <button
            onClick={handleRun}
            disabled={!isValid || isRunning}
            className={`${
              isValid && !isRunning ? "action-primary" : "action-secondary"
            } min-w-[180px] disabled:opacity-40 disabled:cursor-not-allowed`}
          >
            {progress.status === "connecting" ? (
              <>
                <Wifi size={15} className="animate-pulse" />
                Launching…
              </>
            ) : progress.status === "running" ? (
              <>
                <TrendingUp size={15} />
                Live Run — {Math.round(progress.pct * 100)}%
              </>
            ) : (
              <>
                <Play size={15} />
                Launch Simulation
              </>
            )}
          </button>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <div className="panel-soft p-5 lg:p-6">
            <StrategyForm />

            <div
              className="mt-6 pt-5"
              style={{ borderTop: "1px solid rgba(111,130,166,0.12)" }}
            >
              {progress.status === "error" && (
                <div
                  className="mb-4 flex items-start justify-between gap-3 rounded-2xl p-3"
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

              {(progress.status === "connecting" ||
                progress.status === "running") && (
                <div
                  className="mb-4 space-y-3 rounded-[22px] p-4"
                  style={{
                    background:
                      "linear-gradient(135deg, rgba(107,149,255,0.12) 0%, rgba(40,221,176,0.08) 100%)",
                    border: "1px solid rgba(107,149,255,0.2)",
                  }}
                >
                  {progress.status === "connecting" && (
                    <div className="flex items-center gap-2">
                      <Wifi
                        size={13}
                        className="text-accent-blue animate-pulse"
                      />
                      <span className="text-xs text-accent-blue">
                        Connecting to simulation engine…
                      </span>
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
                          {progress.bar.toLocaleString()} /{" "}
                          {progress.total.toLocaleString()} bars
                        </span>
                      </div>

                      <ProgressBar pct={progress.pct} />

                      <div className="flex justify-between text-[10px] font-mono">
                        <span className="text-text-muted">
                          Date:{" "}
                          <span className="text-text-secondary">
                            {progress.date}
                          </span>
                        </span>
                        <span className="text-text-muted">
                          Equity:{" "}
                          <span className="text-accent-green font-semibold">
                            $
                            {progress.equity.toLocaleString(undefined, {
                              maximumFractionDigits: 0,
                            })}
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
                className={`w-full ${
                  isValid && !isRunning ? "action-primary" : "action-secondary"
                } disabled:opacity-40 disabled:cursor-not-allowed`}
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

        <div className="space-y-4">
          <div className="panel-soft p-5">
            <div className="flex items-center gap-2 mb-4">
              <Zap size={12} className="text-accent-yellow" />
              <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
                Configuration Preview
              </h2>
            </div>

            <dl className="space-y-2.5">
              {[
                { label: "Strategy", value: config.strategy_id || "—" },
                { label: "Tickers", value: config.tickers?.join(", ") || "—" },
                { label: "Benchmark", value: config.benchmark || "SPY" },
                {
                  label: "Period",
                  value:
                    config.start_date && config.end_date
                      ? `${config.start_date} → ${config.end_date}`
                      : "—",
                },
                {
                  label: "Capital",
                  value: `$${(config.initial_capital || 100000).toLocaleString()}`,
                },
                { label: "Slippage", value: `${config.slippage_bps ?? 5} bps` },
                {
                  label: "Commission",
                  value: `$${config.commission_per_share ?? 0.005}/share`,
                },
                {
                  label: "Impact",
                  value: config.market_impact_model ?? "almgren_chriss",
                },
                {
                  label: "Max Vol",
                  value: `${config.max_volume_participation_pct ?? 5}%`,
                },
                {
                  label: "Construction",
                  value:
                    config.portfolio_construction_model ??
                    config.position_sizing ??
                    "equal_weight",
                },
                {
                  label: "Rebalance",
                  value: config.rebalance_frequency || "daily",
                },
                {
                  label: "Max Pos",
                  value: `${config.max_position_pct ?? 25}%`,
                },
                {
                  label: "Max Gross",
                  value: `${config.max_gross_exposure_pct ?? 150}%`,
                },
                {
                  label: "Turnover",
                  value: `${config.turnover_limit_pct ?? 100}%`,
                },
                {
                  label: "Shorting",
                  value: config.allow_short_selling ? "Enabled" : "Disabled",
                },
                ...(config.allow_short_selling
                  ? [
                      {
                        label: "Max Short",
                        value: `${config.max_short_position_pct ?? 25}%`,
                      },
                      {
                        label: "Borrow",
                        value: `${config.short_borrow_rate_bps ?? 200} bps/yr`,
                      },
                    ]
                  : []),
              ].map(({ label, value }) => (
                <div
                  key={label}
                  className="flex justify-between items-center text-xs py-1.5"
                  style={{ borderBottom: "1px solid rgba(111,130,166,0.08)" }}
                >
                  <dt className="text-text-muted">{label}</dt>
                  <dd className="font-mono text-text-primary text-right max-w-[60%] truncate">
                    {value}
                  </dd>
                </div>
              ))}
            </dl>
          </div>

          <div
            className="panel-soft p-4"
            style={{
              background:
                "linear-gradient(135deg, rgba(40,221,176,0.09) 0%, rgba(255,255,255,0.02) 100%)",
            }}
          >
            <div className="flex items-center gap-1.5 mb-1">
              <Wifi size={10} className="text-accent-green" />
              <span className="text-[10px] font-medium text-accent-green">
                Live streaming
              </span>
            </div>
            <p className="text-[10px] text-text-muted leading-relaxed">
              Progress is streamed in real time via WebSocket — watch equity
              build bar-by-bar as the simulation runs.
            </p>
          </div>

          <div className="panel-soft p-4">
            <p className="section-label mb-2">Research brief</p>
            <div className="space-y-3 text-[11px] leading-relaxed text-text-muted">
              <p>
                <span className="font-medium text-accent-blue">
                  Event-driven engine
                </span>{" "}
                processes each bar sequentially, so every signal only sees the
                information available at that moment.
              </p>
              <p>
                Construction, shorting, and impact controls are applied before
                orders hit the execution model, giving you a more realistic
                picture of implementation drag.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
