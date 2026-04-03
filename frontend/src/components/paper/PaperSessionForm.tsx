"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { LoadingSpinner } from "@/components/shared/LoadingSpinner";
import { useStrategies } from "@/hooks/useAnalytics";
import { useCreatePaperSession } from "@/hooks/usePaperTrading";
import { BENCHMARKS, PAPER_INTERVAL_OPTIONS } from "@/lib/constants";
import type {
  BacktestConfig,
  PaperTradingSessionCreate,
  StrategyInfo,
} from "@/lib/types";

function defaultDraft(): PaperTradingSessionCreate {
  return {
    name: "Live Paper Session",
    strategy_id: "",
    params: {},
    tickers: ["AAPL"],
    benchmark: "SPY",
    initial_capital: 100_000,
    slippage_bps: 5,
    commission_per_share: 0.005,
    max_position_pct: 25,
    bar_interval: "1m",
    polling_interval_seconds: 60,
    start_immediately: true,
  };
}

function buildParamDefaults(strategy: StrategyInfo | undefined) {
  const defaults: Record<string, number | string | boolean> = {};
  strategy?.params.forEach((param) => {
    defaults[param.name] = param.default;
  });
  return defaults;
}

function isFiniteNumber(value: number) {
  return Number.isFinite(value);
}

interface PaperSessionFormProps {
  prefillConfig?: Partial<BacktestConfig> | null;
}

export function PaperSessionForm({ prefillConfig }: PaperSessionFormProps) {
  const router = useRouter();
  const createMutation = useCreatePaperSession();
  const { data: strategies, isLoading, error } = useStrategies();

  const [draft, setDraft] = useState<PaperTradingSessionCreate>(defaultDraft);
  const effectiveDraft = useMemo(() => {
    if (!strategies || strategies.length === 0) return draft;
    if (draft.strategy_id) return draft;

    if (prefillConfig) {
      const strategy =
        strategies.find((item) => item.id === prefillConfig.strategy_id) ??
        strategies[0];
      return {
        ...draft,
        name: `${strategy.name} Live Session`,
        strategy_id: strategy.id,
        params: {
          ...buildParamDefaults(strategy),
          ...(prefillConfig.params ?? {}),
        },
        tickers:
          prefillConfig.tickers && prefillConfig.tickers.length > 0
            ? prefillConfig.tickers
            : draft.tickers,
        benchmark: prefillConfig.benchmark ?? draft.benchmark,
        initial_capital: prefillConfig.initial_capital ?? draft.initial_capital,
        slippage_bps: prefillConfig.slippage_bps ?? draft.slippage_bps,
        commission_per_share:
          prefillConfig.commission_per_share ?? draft.commission_per_share,
        max_position_pct:
          prefillConfig.max_position_pct ?? draft.max_position_pct,
      };
    }

    const strategy = strategies[0];
    return {
      ...draft,
      strategy_id: strategy.id,
      name: `${strategy.name} Live Session`,
      params: buildParamDefaults(strategy),
    };
  }, [draft, prefillConfig, strategies]);

  const selectedStrategy = useMemo(
    () => strategies?.find((strategy) => strategy.id === effectiveDraft.strategy_id),
    [effectiveDraft.strategy_id, strategies]
  );

  const canSubmit =
    !!effectiveDraft.name.trim() &&
    !!effectiveDraft.strategy_id &&
    effectiveDraft.tickers.length > 0 &&
    isFiniteNumber(effectiveDraft.initial_capital) &&
    effectiveDraft.initial_capital > 0 &&
    isFiniteNumber(effectiveDraft.slippage_bps) &&
    effectiveDraft.slippage_bps >= 0 &&
    isFiniteNumber(effectiveDraft.commission_per_share) &&
    effectiveDraft.commission_per_share >= 0 &&
    isFiniteNumber(effectiveDraft.max_position_pct) &&
    effectiveDraft.max_position_pct > 0 &&
    effectiveDraft.max_position_pct <= 100 &&
    Number.isInteger(effectiveDraft.polling_interval_seconds) &&
    effectiveDraft.polling_interval_seconds >= 15;

  const handleStrategyChange = (strategyId: string) => {
    const strategy = strategies?.find((item) => item.id === strategyId);
    if (!strategy) return;

    setDraft({
      ...effectiveDraft,
      strategy_id: strategyId,
      name:
        effectiveDraft.name === "Live Paper Session" ||
        effectiveDraft.name.endsWith("Live Session")
          ? `${strategy.name} Live Session`
          : effectiveDraft.name,
      params: buildParamDefaults(strategy),
    });
  };

  const handleSubmit = async () => {
    const payload = {
      ...effectiveDraft,
      tickers: effectiveDraft.tickers
        .filter(Boolean)
        .map((ticker) => ticker.toUpperCase()),
      benchmark: effectiveDraft.benchmark.toUpperCase(),
    };
    const created = await createMutation.mutateAsync(payload);
    router.push(`/paper/${created.id}`);
  };

  if (isLoading) return <LoadingSpinner />;
  if (error) {
    return <div className="text-sm text-accent-red">{error.message}</div>;
  }
  if (!strategies || strategies.length === 0) {
    return (
      <div className="text-sm text-text-muted">
        No strategies are available for paper trading yet.
      </div>
    );
  }

  return (
    <div
      className="rounded-md p-5"
      style={{
        background: "var(--color-bg-card)",
        border: "1px solid var(--color-border)",
        boxShadow: "0 1px 3px rgba(0,0,0,0.4)",
      }}
    >
      <div className="mb-5">
        <h2 className="text-sm font-semibold text-text-primary">
          Launch Paper Session
        </h2>
        <p className="text-xs text-text-muted mt-1">
          Live signal generation with minute-by-minute mark-to-market updates.
          Existing strategy parameters are reused, so intraday intervals may need
          tighter tuning than daily backtests.
        </p>
      </div>

      <div className="space-y-5">
        <div>
          <label className="block text-sm text-text-secondary mb-1.5">
            Session Name
          </label>
          <input
            value={effectiveDraft.name}
            onChange={(event) =>
              setDraft({ ...effectiveDraft, name: event.target.value })
            }
            className="w-full bg-bg-primary border border-border rounded px-3 py-2 text-sm text-text-primary"
          />
        </div>

        <div>
          <label className="block text-sm text-text-secondary mb-1.5">
            Strategy
          </label>
          <select
            value={effectiveDraft.strategy_id}
            onChange={(event) => handleStrategyChange(event.target.value)}
            className="w-full bg-bg-primary border border-border rounded px-3 py-2 text-sm text-text-primary"
          >
            {strategies?.map((strategy) => (
              <option key={strategy.id} value={strategy.id}>
                {strategy.name}
              </option>
            ))}
          </select>
          {selectedStrategy && (
            <p className="text-xs text-text-muted mt-1">
              {selectedStrategy.description}
            </p>
          )}
        </div>

        {selectedStrategy && selectedStrategy.params.length > 0 && (
          <div>
            <p className="text-sm font-medium text-text-secondary mb-3">
              Strategy Parameters
            </p>
            <div className="space-y-3">
              {selectedStrategy.params.map((param) => {
                const value = effectiveDraft.params[param.name] ?? param.default;
                return (
                  <div key={param.name}>
                    <div className="flex justify-between items-center mb-1">
                      <label className="text-xs text-text-secondary">
                        {param.label}
                      </label>
                      <span className="text-xs font-mono text-text-primary">
                        {String(value)}
                      </span>
                    </div>
                    {(param.type === "int" || param.type === "float") && (
                      <input
                        type="range"
                        min={param.min}
                        max={param.max}
                        step={param.step}
                        value={Number(value)}
                        onChange={(event) =>
                          setDraft({
                            ...effectiveDraft,
                            params: {
                              ...effectiveDraft.params,
                              [param.name]:
                                param.type === "int"
                                  ? parseInt(event.target.value, 10)
                                  : parseFloat(event.target.value),
                            },
                          })
                        }
                        className="w-full accent-accent-blue"
                      />
                    )}
                    {param.type === "bool" && (
                      <label className="flex items-center gap-2 text-xs text-text-primary">
                        <input
                          type="checkbox"
                          checked={Boolean(value)}
                          onChange={(event) =>
                            setDraft({
                              ...effectiveDraft,
                              params: {
                                ...effectiveDraft.params,
                                [param.name]: event.target.checked,
                              },
                            })
                          }
                          className="accent-accent-blue"
                        />
                        Enable
                      </label>
                    )}
                    {param.type === "select" && param.options && (
                      <select
                        value={String(value)}
                        onChange={(event) =>
                          setDraft({
                            ...effectiveDraft,
                            params: {
                              ...effectiveDraft.params,
                              [param.name]: event.target.value,
                            },
                          })
                        }
                        className="w-full bg-bg-primary border border-border rounded px-3 py-2 text-sm text-text-primary"
                      >
                        {param.options.map((option) => (
                          <option key={option} value={option}>
                            {option}
                          </option>
                        ))}
                      </select>
                    )}
                    <p className="text-[10px] text-text-muted mt-0.5">
                      {param.description}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        <div>
          <label className="block text-sm text-text-secondary mb-1.5">
            Tickers
          </label>
          <input
            value={effectiveDraft.tickers.join(", ")}
            onChange={(event) =>
              setDraft({
                ...effectiveDraft,
                tickers: event.target.value
                  .split(",")
                  .map((ticker) => ticker.trim().toUpperCase())
                  .filter(Boolean),
              })
            }
            placeholder="AAPL, MSFT, NVDA"
            className="w-full bg-bg-primary border border-border rounded px-3 py-2 text-sm text-text-primary"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm text-text-secondary mb-1.5">
              Benchmark
            </label>
            <select
              value={effectiveDraft.benchmark}
              onChange={(event) =>
                setDraft({ ...effectiveDraft, benchmark: event.target.value })
              }
              className="w-full bg-bg-primary border border-border rounded px-3 py-2 text-sm text-text-primary"
            >
              {BENCHMARKS.map((benchmark) => (
                <option key={benchmark} value={benchmark}>
                  {benchmark}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm text-text-secondary mb-1.5">
              Initial Capital
            </label>
            <input
              type="number"
              value={effectiveDraft.initial_capital}
              onChange={(event) => {
                const nextValue = Number(event.target.value);
                if (!Number.isNaN(nextValue)) {
                  setDraft({
                    ...effectiveDraft,
                    initial_capital: nextValue,
                  });
                }
              }}
              className="w-full bg-bg-primary border border-border rounded px-3 py-2 text-sm text-text-primary"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-sm text-text-secondary mb-1.5">
              Market Interval
            </label>
            <select
              value={effectiveDraft.bar_interval}
              onChange={(event) =>
                setDraft({
                  ...effectiveDraft,
                  bar_interval: event.target.value as PaperTradingSessionCreate["bar_interval"],
                })
              }
              className="w-full bg-bg-primary border border-border rounded px-3 py-2 text-sm text-text-primary"
            >
              {PAPER_INTERVAL_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm text-text-secondary mb-1.5">
              Poll Frequency (seconds)
            </label>
            <input
              type="number"
              min={15}
              step={15}
              value={effectiveDraft.polling_interval_seconds}
              onChange={(event) => {
                const nextValue = Number.parseInt(event.target.value, 10);
                if (!Number.isNaN(nextValue)) {
                  setDraft({
                    ...effectiveDraft,
                    polling_interval_seconds: nextValue,
                  });
                }
              }}
              className="w-full bg-bg-primary border border-border rounded px-3 py-2 text-sm text-text-primary"
            />
          </div>
        </div>

        <details>
          <summary className="text-sm text-text-secondary cursor-pointer">
            Execution Controls
          </summary>
          <div className="space-y-3 mt-3">
            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="text-xs text-text-secondary">
                  Slippage (bps)
                </label>
                <span className="text-xs font-mono text-text-primary">
                  {effectiveDraft.slippage_bps}
                </span>
              </div>
              <input
                type="range"
                min={0}
                max={25}
                step={0.5}
                value={effectiveDraft.slippage_bps}
                onChange={(event) =>
                  setDraft({
                    ...effectiveDraft,
                    slippage_bps: parseFloat(event.target.value),
                  })
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
                value={effectiveDraft.commission_per_share}
                onChange={(event) => {
                  const nextValue = Number(event.target.value);
                  if (!Number.isNaN(nextValue)) {
                    setDraft({
                      ...effectiveDraft,
                      commission_per_share: nextValue,
                    });
                  }
                }}
                className="w-full bg-bg-primary border border-border rounded px-3 py-2 text-sm text-text-primary"
              />
            </div>

            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="text-xs text-text-secondary">
                  Max Position (%)
                </label>
                <span className="text-xs font-mono text-text-primary">
                  {effectiveDraft.max_position_pct}%
                </span>
              </div>
              <input
                type="range"
                min={5}
                max={100}
                step={5}
                value={effectiveDraft.max_position_pct}
                onChange={(event) =>
                  setDraft({
                    ...effectiveDraft,
                    max_position_pct: parseInt(event.target.value, 10),
                  })
                }
                className="w-full accent-accent-blue"
              />
            </div>
          </div>
        </details>

        <label className="flex items-center gap-2 text-sm text-text-secondary">
          <input
            type="checkbox"
            checked={effectiveDraft.start_immediately}
            onChange={(event) =>
              setDraft({
                ...effectiveDraft,
                start_immediately: event.target.checked,
              })
            }
            className="accent-accent-blue"
          />
          Start session immediately after creation
        </label>

        {createMutation.error && (
          <div className="text-xs text-accent-red">
            {createMutation.error.message}
          </div>
        )}

        <button
          onClick={handleSubmit}
          disabled={createMutation.isPending || !canSubmit}
          className="w-full flex items-center justify-center gap-2 py-3 rounded text-sm font-semibold transition-all disabled:opacity-50"
          style={{
            background: "var(--color-accent-green)",
            color: "var(--color-bg-primary)",
            boxShadow: "0 0 20px rgba(0,212,170,0.15)",
          }}
        >
          {createMutation.isPending ? <LoadingSpinner size={14} /> : null}
          {createMutation.isPending ? "Creating Session…" : "Create Live Session"}
        </button>
      </div>
    </div>
  );
}
