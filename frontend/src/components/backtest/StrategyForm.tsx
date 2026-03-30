"use client";

import { useEffect } from "react";
import { useStrategies } from "@/hooks/useAnalytics";
import { useBacktestStore } from "@/store/backtest-store";
import {
  BENCHMARKS,
  POSITION_SIZING_OPTIONS,
  REBALANCE_OPTIONS,
  CATEGORY_LABELS,
} from "@/lib/constants";
import { LoadingSpinner } from "@/components/shared/LoadingSpinner";

export function StrategyForm() {
  const { data: strategies, isLoading } = useStrategies();
  const { config, setConfig } = useBacktestStore();

  const selectedStrategy = strategies?.find(
    (s) => s.id === config.strategy_id
  );

  // Set default params when strategy changes
  useEffect(() => {
    if (selectedStrategy) {
      const defaults: Record<string, number | string | boolean> = {};
      selectedStrategy.params.forEach((p) => {
        defaults[p.name] = p.default;
      });
      setConfig({ params: defaults });
    }
  }, [config.strategy_id, selectedStrategy, setConfig]);

  if (isLoading) return <LoadingSpinner />;

  return (
    <div className="space-y-6">
      {/* Strategy Selection */}
      <div>
        <label className="block text-sm text-text-secondary mb-1.5">
          Strategy
        </label>
        <select
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
          <p className="text-xs text-text-muted mt-1">
            {selectedStrategy.description}
          </p>
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
        <label className="block text-sm text-text-secondary mb-1.5">
          Tickers (comma-separated)
        </label>
        <input
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
        <label className="block text-sm text-text-secondary mb-1.5">
          Benchmark
        </label>
        <select
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
          <label className="block text-sm text-text-secondary mb-1.5">
            Start Date
          </label>
          <input
            type="date"
            value={config.start_date || ""}
            onChange={(e) => setConfig({ start_date: e.target.value })}
            className="w-full bg-bg-card border border-border rounded px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-blue"
          />
        </div>
        <div>
          <label className="block text-sm text-text-secondary mb-1.5">
            End Date
          </label>
          <input
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

          <div>
            <label className="block text-xs text-text-secondary mb-1">
              Position Sizing
            </label>
            <select
              value={config.position_sizing || "equal_weight"}
              onChange={(e) =>
                setConfig({ position_sizing: e.target.value as BacktestConfig["position_sizing"] })
              }
              className="w-full bg-bg-card border border-border rounded px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-blue"
            >
              {POSITION_SIZING_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
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

          <div>
            <label className="block text-xs text-text-secondary mb-1">
              Rebalance Frequency
            </label>
            <select
              value={config.rebalance_frequency || "daily"}
              onChange={(e) =>
                setConfig({ rebalance_frequency: e.target.value as BacktestConfig["rebalance_frequency"] })
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

// Fix: need to import BacktestConfig type for the cast
import type { BacktestConfig } from "@/lib/types";
