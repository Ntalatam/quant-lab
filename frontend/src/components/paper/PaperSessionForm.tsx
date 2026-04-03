"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { LoadingSpinner } from "@/components/shared/LoadingSpinner";
import { useStrategies } from "@/hooks/useAnalytics";
import { useCreatePaperSession } from "@/hooks/usePaperTrading";
import {
  BENCHMARKS,
  MARKET_IMPACT_MODEL_OPTIONS,
  PAPER_INTERVAL_OPTIONS,
  POSITION_SIZING_OPTIONS,
} from "@/lib/constants";
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
    market_impact_model: "almgren_chriss",
    max_volume_participation_pct: 5,
    portfolio_construction_model: "equal_weight",
    portfolio_lookback_days: 63,
    max_position_pct: 25,
    max_gross_exposure_pct: 150,
    turnover_limit_pct: 100,
    max_sector_exposure_pct: 100,
    allow_short_selling: false,
    max_short_position_pct: 25,
    short_margin_requirement_pct: 50,
    short_borrow_rate_bps: 200,
    short_locate_fee_bps: 10,
    short_squeeze_threshold_pct: 15,
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
        market_impact_model:
          prefillConfig.market_impact_model ?? draft.market_impact_model,
        max_volume_participation_pct:
          prefillConfig.max_volume_participation_pct ??
          draft.max_volume_participation_pct,
        portfolio_construction_model:
          prefillConfig.portfolio_construction_model ??
          prefillConfig.position_sizing ??
          draft.portfolio_construction_model,
        portfolio_lookback_days:
          prefillConfig.portfolio_lookback_days ?? draft.portfolio_lookback_days,
        max_position_pct:
          prefillConfig.max_position_pct ?? draft.max_position_pct,
        max_gross_exposure_pct:
          prefillConfig.max_gross_exposure_pct ?? draft.max_gross_exposure_pct,
        turnover_limit_pct:
          prefillConfig.turnover_limit_pct ?? draft.turnover_limit_pct,
        max_sector_exposure_pct:
          prefillConfig.max_sector_exposure_pct ?? draft.max_sector_exposure_pct,
        allow_short_selling:
          strategy.requires_short_selling
            ? true
            : prefillConfig.allow_short_selling ?? draft.allow_short_selling,
        max_short_position_pct:
          prefillConfig.max_short_position_pct ?? draft.max_short_position_pct,
        short_margin_requirement_pct:
          prefillConfig.short_margin_requirement_pct ??
          draft.short_margin_requirement_pct,
        short_borrow_rate_bps:
          prefillConfig.short_borrow_rate_bps ?? draft.short_borrow_rate_bps,
        short_locate_fee_bps:
          prefillConfig.short_locate_fee_bps ?? draft.short_locate_fee_bps,
        short_squeeze_threshold_pct:
          prefillConfig.short_squeeze_threshold_pct ??
          draft.short_squeeze_threshold_pct,
      };
    }

    const strategy = strategies[0];
    return {
      ...draft,
      strategy_id: strategy.id,
      name: `${strategy.name} Live Session`,
      params: buildParamDefaults(strategy),
      allow_short_selling: strategy.requires_short_selling,
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
    !!effectiveDraft.market_impact_model &&
    isFiniteNumber(effectiveDraft.max_volume_participation_pct) &&
    effectiveDraft.max_volume_participation_pct > 0 &&
    effectiveDraft.max_volume_participation_pct <= 100 &&
    !!effectiveDraft.portfolio_construction_model &&
    Number.isInteger(effectiveDraft.portfolio_lookback_days) &&
    effectiveDraft.portfolio_lookback_days >= 20 &&
    effectiveDraft.portfolio_lookback_days <= 252 &&
    isFiniteNumber(effectiveDraft.max_position_pct) &&
    effectiveDraft.max_position_pct > 0 &&
    effectiveDraft.max_position_pct <= 100 &&
    isFiniteNumber(effectiveDraft.max_gross_exposure_pct) &&
    effectiveDraft.max_gross_exposure_pct > 0 &&
    isFiniteNumber(effectiveDraft.turnover_limit_pct) &&
    effectiveDraft.turnover_limit_pct >= 0 &&
    isFiniteNumber(effectiveDraft.max_sector_exposure_pct) &&
    effectiveDraft.max_sector_exposure_pct > 0 &&
    (!effectiveDraft.allow_short_selling ||
      (isFiniteNumber(effectiveDraft.max_short_position_pct) &&
        effectiveDraft.max_short_position_pct > 0 &&
        effectiveDraft.max_short_position_pct <= 100 &&
        isFiniteNumber(effectiveDraft.short_margin_requirement_pct) &&
        effectiveDraft.short_margin_requirement_pct >= 0 &&
        effectiveDraft.short_margin_requirement_pct <= 100 &&
        isFiniteNumber(effectiveDraft.short_borrow_rate_bps) &&
        effectiveDraft.short_borrow_rate_bps >= 0 &&
        isFiniteNumber(effectiveDraft.short_locate_fee_bps) &&
        effectiveDraft.short_locate_fee_bps >= 0 &&
        isFiniteNumber(effectiveDraft.short_squeeze_threshold_pct) &&
        effectiveDraft.short_squeeze_threshold_pct >= 1)) &&
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
      allow_short_selling: strategy.requires_short_selling
        ? true
        : effectiveDraft.allow_short_selling,
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
              </div>
            </div>
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

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs text-text-secondary mb-1">
                  Impact Model
                </label>
                <select
                  value={effectiveDraft.market_impact_model}
                  onChange={(event) =>
                    setDraft({
                      ...effectiveDraft,
                      market_impact_model:
                        event.target.value as PaperTradingSessionCreate["market_impact_model"],
                    })
                  }
                  className="w-full bg-bg-primary border border-border rounded px-3 py-2 text-sm text-text-primary"
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
                  value={effectiveDraft.max_volume_participation_pct}
                  onChange={(event) => {
                    const nextValue = Number(event.target.value);
                    if (!Number.isNaN(nextValue)) {
                      setDraft({
                        ...effectiveDraft,
                        max_volume_participation_pct: nextValue,
                      });
                    }
                  }}
                  className="w-full bg-bg-primary border border-border rounded px-3 py-2 text-sm text-text-primary"
                />
              </div>
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

            <div>
              <label className="block text-xs text-text-secondary mb-1">
                Portfolio Construction
              </label>
              <select
                value={effectiveDraft.portfolio_construction_model}
                onChange={(event) =>
                  setDraft({
                    ...effectiveDraft,
                    portfolio_construction_model:
                      event.target.value as PaperTradingSessionCreate["portfolio_construction_model"],
                  })
                }
                className="w-full bg-bg-primary border border-border rounded px-3 py-2 text-sm text-text-primary"
              >
                {POSITION_SIZING_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
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
                  value={effectiveDraft.portfolio_lookback_days}
                  onChange={(event) => {
                    const nextValue = Number.parseInt(event.target.value, 10);
                    if (!Number.isNaN(nextValue)) {
                      setDraft({
                        ...effectiveDraft,
                        portfolio_lookback_days: nextValue,
                      });
                    }
                  }}
                  className="w-full bg-bg-primary border border-border rounded px-3 py-2 text-sm text-text-primary"
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
                  value={effectiveDraft.max_gross_exposure_pct}
                  onChange={(event) => {
                    const nextValue = Number(event.target.value);
                    if (!Number.isNaN(nextValue)) {
                      setDraft({
                        ...effectiveDraft,
                        max_gross_exposure_pct: nextValue,
                      });
                    }
                  }}
                  className="w-full bg-bg-primary border border-border rounded px-3 py-2 text-sm text-text-primary"
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
                  value={effectiveDraft.turnover_limit_pct}
                  onChange={(event) => {
                    const nextValue = Number(event.target.value);
                    if (!Number.isNaN(nextValue)) {
                      setDraft({
                        ...effectiveDraft,
                        turnover_limit_pct: nextValue,
                      });
                    }
                  }}
                  className="w-full bg-bg-primary border border-border rounded px-3 py-2 text-sm text-text-primary"
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
                  value={effectiveDraft.max_sector_exposure_pct}
                  onChange={(event) => {
                    const nextValue = Number(event.target.value);
                    if (!Number.isNaN(nextValue)) {
                      setDraft({
                        ...effectiveDraft,
                        max_sector_exposure_pct: nextValue,
                      });
                    }
                  }}
                  className="w-full bg-bg-primary border border-border rounded px-3 py-2 text-sm text-text-primary"
                />
              </div>
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
                  checked={effectiveDraft.allow_short_selling}
                  disabled={selectedStrategy?.requires_short_selling}
                  onChange={(event) =>
                    setDraft({
                      ...effectiveDraft,
                      allow_short_selling: event.target.checked,
                    })
                  }
                  className="accent-accent-yellow"
                />
              </label>
              <p className="text-[10px] text-text-muted leading-relaxed">
                {selectedStrategy?.requires_short_selling
                  ? "This strategy opens explicit short positions, so paper trading must allow short selling."
                  : "Enable short entries, borrow carry, locate fees, and squeeze protection for long/short strategies."}
              </p>

              {effectiveDraft.allow_short_selling && (
                <div className="space-y-3">
                  <div>
                    <div className="flex justify-between items-center mb-1">
                      <label className="text-xs text-text-secondary">
                        Max Short Position (%)
                      </label>
                      <span className="text-xs font-mono text-text-primary">
                        {effectiveDraft.max_short_position_pct}%
                      </span>
                    </div>
                    <input
                      type="range"
                      min={5}
                      max={100}
                      step={5}
                      value={effectiveDraft.max_short_position_pct}
                      onChange={(event) =>
                        setDraft({
                          ...effectiveDraft,
                          max_short_position_pct: parseInt(event.target.value, 10),
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
                      value={effectiveDraft.short_margin_requirement_pct}
                      onChange={(event) => {
                        const nextValue = Number(event.target.value);
                        if (!Number.isNaN(nextValue)) {
                          setDraft({
                            ...effectiveDraft,
                            short_margin_requirement_pct: nextValue,
                          });
                        }
                      }}
                      className="w-full bg-bg-primary border border-border rounded px-3 py-2 text-sm text-text-primary"
                    />
                  </div>

                  <div>
                    <label className="block text-xs text-text-secondary mb-1">
                      Borrow Rate (bps / year)
                    </label>
                    <input
                      type="number"
                      step={5}
                      value={effectiveDraft.short_borrow_rate_bps}
                      onChange={(event) => {
                        const nextValue = Number(event.target.value);
                        if (!Number.isNaN(nextValue)) {
                          setDraft({
                            ...effectiveDraft,
                            short_borrow_rate_bps: nextValue,
                          });
                        }
                      }}
                      className="w-full bg-bg-primary border border-border rounded px-3 py-2 text-sm text-text-primary"
                    />
                  </div>

                  <div>
                    <label className="block text-xs text-text-secondary mb-1">
                      Locate Fee (bps / entry)
                    </label>
                    <input
                      type="number"
                      step={1}
                      value={effectiveDraft.short_locate_fee_bps}
                      onChange={(event) => {
                        const nextValue = Number(event.target.value);
                        if (!Number.isNaN(nextValue)) {
                          setDraft({
                            ...effectiveDraft,
                            short_locate_fee_bps: nextValue,
                          });
                        }
                      }}
                      className="w-full bg-bg-primary border border-border rounded px-3 py-2 text-sm text-text-primary"
                    />
                  </div>

                  <div>
                    <label className="block text-xs text-text-secondary mb-1">
                      Squeeze Threshold (% adverse move)
                    </label>
                    <input
                      type="number"
                      step={1}
                      value={effectiveDraft.short_squeeze_threshold_pct}
                      onChange={(event) => {
                        const nextValue = Number(event.target.value);
                        if (!Number.isNaN(nextValue)) {
                          setDraft({
                            ...effectiveDraft,
                            short_squeeze_threshold_pct: nextValue,
                          });
                        }
                      }}
                      className="w-full bg-bg-primary border border-border rounded px-3 py-2 text-sm text-text-primary"
                    />
                  </div>
                </div>
              )}
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
