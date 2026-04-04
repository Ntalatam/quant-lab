"use client";

import { useEffect } from "react";
import Link from "next/link";
import type { BacktestConfig } from "@/lib/types";
import { useStrategies } from "@/hooks/useAnalytics";
import { useBacktestStore } from "@/store/backtest-store";
import {
  BENCHMARKS,
  MARKET_IMPACT_MODEL_OPTIONS,
  POSITION_SIZING_OPTIONS,
  REBALANCE_OPTIONS,
  CATEGORY_LABELS,
} from "@/lib/constants";
import { LoadingSpinner } from "@/components/shared/LoadingSpinner";

export function StrategyForm() {
  const { data: strategies, isLoading } = useStrategies();
  const { config, setConfig } = useBacktestStore();

  const selectedStrategy = strategies?.find((s) => s.id === config.strategy_id);

  // Set default params when strategy changes
  useEffect(() => {
    if (selectedStrategy) {
      const defaults: Record<string, number | string | boolean> = {};
      selectedStrategy.params.forEach((p) => {
        defaults[p.name] = p.default;
      });
      setConfig({
        params: defaults,
        allow_short_selling: selectedStrategy.requires_short_selling
          ? true
          : config.allow_short_selling,
      });
    }
  }, [
    config.allow_short_selling,
    config.strategy_id,
    selectedStrategy,
    setConfig,
  ]);

  if (isLoading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      {/* Strategy Selection */}
      <div>
        <label
          htmlFor="strategy-select"
          className="block text-sm text-text-secondary mb-1.5"
        >
          Strategy
        </label>
        <select
          id="strategy-select"
          value={config.strategy_id || ""}
          onChange={(e) => setConfig({ strategy_id: e.target.value })}
          className="w-full bg-bg-card border border-border rounded px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-blue"
        >
          {strategies?.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name} ({CATEGORY_LABELS[s.category] || s.category})
            </option>
          ))}
        </select>
        {selectedStrategy && (
          <div className="mt-1 space-y-1">
            <p className="text-xs text-text-muted">
              {selectedStrategy.description}
            </p>
            <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider">
              <span
                className="px-2 py-0.5 rounded border"
                style={{
                  borderColor:
                    selectedStrategy.signal_mode === "long_short"
                      ? "rgba(255,187,51,0.25)"
                      : "rgba(68,136,255,0.25)",
                  color:
                    selectedStrategy.signal_mode === "long_short"
                      ? "var(--color-accent-yellow)"
                      : "var(--color-accent-blue)",
                  background:
                    selectedStrategy.signal_mode === "long_short"
                      ? "rgba(255,187,51,0.08)"
                      : "rgba(68,136,255,0.08)",
                }}
              >
                {selectedStrategy.signal_mode === "long_short"
                  ? "Long / Short"
                  : "Long Only"}
              </span>
              {selectedStrategy.requires_short_selling && (
                <span className="text-accent-yellow">
                  Requires short selling
                </span>
              )}
              {selectedStrategy.source_type === "custom" && (
                <Link
                  href={`/strategies/custom?strategyId=${encodeURIComponent(selectedStrategy.id)}`}
                  className="text-accent-purple hover:opacity-80 transition-opacity"
                >
                  Edit in studio
                </Link>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Strategy Parameters */}
      {selectedStrategy && selectedStrategy.params.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-text-secondary mb-3">
            Parameters
          </h3>
          <div className="space-y-3">
            {selectedStrategy.params.map((param) => (
              <div key={param.name}>
                <div className="flex justify-between items-center mb-1">
                  <label className="text-xs text-text-secondary">
                    {param.label}
                  </label>
                  <span className="text-xs font-mono text-text-primary tabular-nums">
                    {config.params?.[param.name] ?? param.default}
                  </span>
                </div>
                {(param.type === "int" || param.type === "float") && (
                  <input
                    type="range"
                    min={param.min}
                    max={param.max}
                    step={param.step}
                    value={Number(config.params?.[param.name] ?? param.default)}
                    onChange={(e) =>
                      setConfig({
                        params: {
                          ...config.params,
                          [param.name]:
                            param.type === "int"
                              ? parseInt(e.target.value)
                              : parseFloat(e.target.value),
                        },
                      })
                    }
                    className="w-full accent-accent-blue"
                  />
                )}
                <p className="text-[10px] text-text-muted mt-0.5">
                  {param.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tickers */}
      <div>
        <label
          htmlFor="ticker-input"
          className="block text-sm text-text-secondary mb-1.5"
        >
          Tickers (comma-separated)
        </label>
        <input
          id="ticker-input"
          type="text"
          value={config.tickers?.join(", ") || ""}
          onChange={(e) =>
            setConfig({
              tickers: e.target.value
                .split(",")
                .map((t) => t.trim().toUpperCase())
                .filter(Boolean),
            })
          }
          placeholder="AAPL, MSFT, GOOG"
          className="w-full bg-bg-card border border-border rounded px-3 py-2 text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-accent-blue"
        />
      </div>

      {/* Benchmark */}
      <div>
        <label
          htmlFor="benchmark-select"
          className="block text-sm text-text-secondary mb-1.5"
        >
          Benchmark
        </label>
        <select
          id="benchmark-select"
          value={config.benchmark || "SPY"}
          onChange={(e) => setConfig({ benchmark: e.target.value })}
          className="w-full bg-bg-card border border-border rounded px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-blue"
        >
          {BENCHMARKS.map((b) => (
            <option key={b} value={b}>
              {b}
            </option>
          ))}
        </select>
      </div>

      {/* Date Range */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label
            htmlFor="start-date-input"
            className="block text-sm text-text-secondary mb-1.5"
          >
            Start Date
          </label>
          <input
            id="start-date-input"
            type="date"
            value={config.start_date || ""}
            onChange={(e) => setConfig({ start_date: e.target.value })}
            className="w-full bg-bg-card border border-border rounded px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-blue"
          />
        </div>
        <div>
          <label
            htmlFor="end-date-input"
            className="block text-sm text-text-secondary mb-1.5"
          >
            End Date
          </label>
          <input
            id="end-date-input"
            type="date"
            value={config.end_date || ""}
            onChange={(e) => setConfig({ end_date: e.target.value })}
            className="w-full bg-bg-card border border-border rounded px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-blue"
          />
        </div>
      </div>

      {/* Advanced Settings */}
      <details className="group">
        <summary className="text-sm text-text-secondary cursor-pointer hover:text-text-primary transition-colors">
          Advanced Settings
        </summary>
        <div className="mt-3 space-y-3">
          <div>
            <label className="block text-xs text-text-secondary mb-1">
              Initial Capital
            </label>
            <input
              type="number"
              value={config.initial_capital || 100000}
              onChange={(e) =>
                setConfig({ initial_capital: parseFloat(e.target.value) })
              }
              className="w-full bg-bg-card border border-border rounded px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-blue"
            />
          </div>

          <div>
            <div className="flex justify-between items-center mb-1">
              <label className="text-xs text-text-secondary">
                Slippage (bps)
              </label>
              <span className="text-xs font-mono text-text-primary tabular-nums">
                {config.slippage_bps ?? 5}
              </span>
            </div>
            <input
              type="range"
              min={0}
              max={20}
              step={0.5}
              value={config.slippage_bps ?? 5}
              onChange={(e) =>
                setConfig({ slippage_bps: parseFloat(e.target.value) })
              }
              className="w-full accent-accent-blue"
            />
          </div>

          <div>
            <label className="block text-xs text-text-secondary mb-1">
              Commission ($/share)
            </label>
            <input
              type="number"
              step={0.001}
              value={config.commission_per_share ?? 0.005}
              onChange={(e) =>
                setConfig({
                  commission_per_share: parseFloat(e.target.value),
                })
              }
              className="w-full bg-bg-card border border-border rounded px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-blue"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-text-secondary mb-1">
                Impact Model
              </label>
              <select
                value={config.market_impact_model ?? "almgren_chriss"}
                onChange={(e) =>
                  setConfig({
                    market_impact_model: e.target
                      .value as BacktestConfig["market_impact_model"],
                  })
                }
                className="w-full bg-bg-card border border-border rounded px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-blue"
              >
                {MARKET_IMPACT_MODEL_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-text-secondary mb-1">
                Max Volume Participation (%)
              </label>
              <input
                type="number"
                min={1}
                max={50}
                step={1}
                value={config.max_volume_participation_pct ?? 5}
                onChange={(e) =>
                  setConfig({
                    max_volume_participation_pct: parseFloat(e.target.value),
                  })
                }
                className="w-full bg-bg-card border border-border rounded px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-blue"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs text-text-secondary mb-1">
              Portfolio Construction
            </label>
            <select
              value={
                config.portfolio_construction_model ||
                config.position_sizing ||
                "equal_weight"
              }
              onChange={(e) =>
                setConfig({
                  position_sizing: e.target
                    .value as BacktestConfig["portfolio_construction_model"],
                  portfolio_construction_model: e.target
                    .value as BacktestConfig["portfolio_construction_model"],
                })
              }
              className="w-full bg-bg-card border border-border rounded px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-blue"
            >
              {POSITION_SIZING_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
            <p className="text-[10px] text-text-muted mt-1">
              Convert raw strategy signals into target weights before execution.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-text-secondary mb-1">
                Risk Lookback (days)
              </label>
              <input
                type="number"
                min={20}
                max={252}
                step={1}
                value={config.portfolio_lookback_days ?? 63}
                onChange={(e) =>
                  setConfig({
                    portfolio_lookback_days: parseInt(e.target.value, 10),
                  })
                }
                className="w-full bg-bg-card border border-border rounded px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-blue"
              />
            </div>
            <div>
              <label className="block text-xs text-text-secondary mb-1">
                Max Gross Exposure (%)
              </label>
              <input
                type="number"
                min={25}
                max={300}
                step={5}
                value={config.max_gross_exposure_pct ?? 150}
                onChange={(e) =>
                  setConfig({
                    max_gross_exposure_pct: parseFloat(e.target.value),
                  })
                }
                className="w-full bg-bg-card border border-border rounded px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-blue"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-text-secondary mb-1">
                Turnover Cap (%)
              </label>
              <input
                type="number"
                min={0}
                max={300}
                step={5}
                value={config.turnover_limit_pct ?? 100}
                onChange={(e) =>
                  setConfig({
                    turnover_limit_pct: parseFloat(e.target.value),
                  })
                }
                className="w-full bg-bg-card border border-border rounded px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-blue"
              />
            </div>
            <div>
              <label className="block text-xs text-text-secondary mb-1">
                Sector Cap (% gross)
              </label>
              <input
                type="number"
                min={10}
                max={200}
                step={5}
                value={config.max_sector_exposure_pct ?? 100}
                onChange={(e) =>
                  setConfig({
                    max_sector_exposure_pct: parseFloat(e.target.value),
                  })
                }
                className="w-full bg-bg-card border border-border rounded px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-blue"
              />
            </div>
          </div>

          <div>
            <div className="flex justify-between items-center mb-1">
              <label className="text-xs text-text-secondary">
                Max Position (%)
              </label>
              <span className="text-xs font-mono text-text-primary tabular-nums">
                {config.max_position_pct ?? 25}%
              </span>
            </div>
            <input
              type="range"
              min={10}
              max={100}
              step={5}
              value={config.max_position_pct ?? 25}
              onChange={(e) =>
                setConfig({ max_position_pct: parseInt(e.target.value) })
              }
              className="w-full accent-accent-blue"
            />
          </div>

          <div
            className="rounded p-3 space-y-3"
            style={{
              background: "rgba(255,187,51,0.04)",
              border: "1px solid rgba(255,187,51,0.14)",
            }}
          >
            <label className="flex items-center justify-between gap-3 text-xs text-text-secondary">
              <span>Enable Short Selling</span>
              <input
                type="checkbox"
                checked={config.allow_short_selling ?? false}
                disabled={selectedStrategy?.requires_short_selling}
                onChange={(e) =>
                  setConfig({ allow_short_selling: e.target.checked })
                }
                className="accent-accent-yellow"
              />
            </label>
            <p className="text-[10px] text-text-muted leading-relaxed">
              {selectedStrategy?.requires_short_selling
                ? "This strategy targets explicit shorts, so short selling is required."
                : "Turn this on to let long/short strategies open new short positions and to enable borrow, locate, and squeeze controls."}
            </p>

            {(config.allow_short_selling ||
              selectedStrategy?.requires_short_selling) && (
              <div className="space-y-3">
                <div>
                  <div className="flex justify-between items-center mb-1">
                    <label className="text-xs text-text-secondary">
                      Max Short Position (%)
                    </label>
                    <span className="text-xs font-mono text-text-primary tabular-nums">
                      {config.max_short_position_pct ?? 25}%
                    </span>
                  </div>
                  <input
                    type="range"
                    min={5}
                    max={100}
                    step={5}
                    value={config.max_short_position_pct ?? 25}
                    onChange={(e) =>
                      setConfig({
                        max_short_position_pct: parseInt(e.target.value, 10),
                      })
                    }
                    className="w-full accent-accent-yellow"
                  />
                </div>

                <div>
                  <label className="block text-xs text-text-secondary mb-1">
                    Margin Requirement (%)
                  </label>
                  <input
                    type="number"
                    step={1}
                    value={config.short_margin_requirement_pct ?? 50}
                    onChange={(e) =>
                      setConfig({
                        short_margin_requirement_pct: parseFloat(
                          e.target.value,
                        ),
                      })
                    }
                    className="w-full bg-bg-card border border-border rounded px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-yellow"
                  />
                </div>

                <div>
                  <label className="block text-xs text-text-secondary mb-1">
                    Borrow Rate (bps / year)
                  </label>
                  <input
                    type="number"
                    step={5}
                    value={config.short_borrow_rate_bps ?? 200}
                    onChange={(e) =>
                      setConfig({
                        short_borrow_rate_bps: parseFloat(e.target.value),
                      })
                    }
                    className="w-full bg-bg-card border border-border rounded px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-yellow"
                  />
                </div>

                <div>
                  <label className="block text-xs text-text-secondary mb-1">
                    Locate Fee (bps / short entry)
                  </label>
                  <input
                    type="number"
                    step={1}
                    value={config.short_locate_fee_bps ?? 10}
                    onChange={(e) =>
                      setConfig({
                        short_locate_fee_bps: parseFloat(e.target.value),
                      })
                    }
                    className="w-full bg-bg-card border border-border rounded px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-yellow"
                  />
                </div>

                <div>
                  <label className="block text-xs text-text-secondary mb-1">
                    Squeeze Threshold (% adverse move)
                  </label>
                  <input
                    type="number"
                    step={1}
                    value={config.short_squeeze_threshold_pct ?? 15}
                    onChange={(e) =>
                      setConfig({
                        short_squeeze_threshold_pct: parseFloat(e.target.value),
                      })
                    }
                    className="w-full bg-bg-card border border-border rounded px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-yellow"
                  />
                </div>
              </div>
            )}
          </div>

          <div>
            <label className="block text-xs text-text-secondary mb-1">
              Rebalance Frequency
            </label>
            <select
              value={config.rebalance_frequency || "daily"}
              onChange={(e) =>
                setConfig({
                  rebalance_frequency: e.target
                    .value as BacktestConfig["rebalance_frequency"],
                })
              }
              className="w-full bg-bg-card border border-border rounded px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-blue"
            >
              {REBALANCE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </details>
    </div>
  );
}
