"use client";

import { useStrategies } from "@/hooks/useAnalytics";
import { PageLoading } from "@/components/shared/LoadingSpinner";
import { ErrorMessage } from "@/components/shared/ErrorBoundary";
import Link from "next/link";
import { ChevronRight, Sparkles } from "lucide-react";

const CATEGORY_CONFIG: Record<
  string,
  { label: string; cls: string; accent: string; desc: string }
> = {
  trend_following: {
    label: "Trend Following",
    cls: "badge-trend",
    accent: "var(--color-accent-blue)",
    desc: "Captures directional price moves",
  },
  mean_reversion: {
    label: "Mean Reversion",
    cls: "badge-reversion",
    accent: "var(--color-accent-purple)",
    desc: "Exploits price deviations from mean",
  },
  momentum: {
    label: "Cross-Sectional Momentum",
    cls: "badge-momentum",
    accent: "var(--color-accent-green)",
    desc: "Rotates into top relative performers",
  },
  statistical_arbitrage: {
    label: "Statistical Arbitrage",
    cls: "badge-arb",
    accent: "var(--color-accent-yellow)",
    desc: "Pairs cointegration & spread z-score",
  },
  risk_management: {
    label: "Risk Management",
    cls: "badge-momentum",
    accent: "var(--color-accent-green)",
    desc: "Volatility-scaled sizing & drawdown protection",
  },
  custom: {
    label: "Custom",
    cls: "badge-trend",
    accent: "var(--color-accent-purple)",
    desc: "User-authored Python strategy with extracted params",
  },
};

function backtestHrefForStrategy(strategy: {
  id: string;
  params: { name: string; default: number | string | boolean }[];
}) {
  const defaults = Object.fromEntries(
    strategy.params.map((param) => [param.name, param.default]),
  );
  const encoded = encodeURIComponent(
    btoa(JSON.stringify({ strategy_id: strategy.id, params: defaults })),
  );
  return `/backtest?config=${encoded}`;
}

export default function StrategiesPage() {
  const { data: strategies, isLoading, error } = useStrategies();

  if (isLoading) return <PageLoading />;
  if (error) return <ErrorMessage message={error.message} />;

  return (
    <div>
      {/* Page header */}
      <div className="mb-7">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-xl font-bold text-text-primary tracking-tight">
              Strategy Library
            </h1>
            <p className="text-xs text-text-muted mt-0.5">
              Built-in research strategies plus any custom models you author in
              the Strategy Studio
            </p>
          </div>
          <Link
            href="/strategies/custom"
            className="inline-flex items-center gap-2 rounded px-3 py-2 text-xs font-medium"
            style={{
              background: "rgba(136,85,255,0.1)",
              border: "1px solid rgba(136,85,255,0.24)",
              color: "var(--color-accent-purple)",
            }}
          >
            <Sparkles size={12} />
            Open Strategy Studio
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {strategies?.map((s) => {
          const cat = CATEGORY_CONFIG[s.category] ?? {
            label: s.category,
            cls: "badge-trend",
            accent: "var(--color-accent-blue)",
            desc: "",
          };
          const isCustom = s.source_type === "custom";

          return (
            <div
              key={s.id}
              className="relative overflow-hidden rounded-md"
              style={{
                background: "var(--color-bg-card)",
                border: "1px solid var(--color-border)",
                boxShadow:
                  "0 1px 3px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.02)",
              }}
            >
              {/* Top accent bar */}
              <div
                className="absolute top-0 left-0 right-0 h-[2px]"
                style={{ background: cat.accent, opacity: 0.65 }}
              />

              <div className="p-5 pt-6">
                {/* Header */}
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <h2 className="font-semibold text-text-primary text-[15px] leading-tight">
                        {s.name}
                      </h2>
                      {isCustom && (
                        <span
                          className="text-[9px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full"
                          style={{
                            background: "rgba(136,85,255,0.12)",
                            border: "1px solid rgba(136,85,255,0.24)",
                            color: "var(--color-accent-purple)",
                          }}
                        >
                          Custom
                        </span>
                      )}
                    </div>
                    <span
                      className={`${cat.cls} text-[9px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full`}
                    >
                      {cat.label}
                    </span>
                  </div>
                  <div className="shrink-0 flex flex-col gap-2">
                    <Link
                      href={backtestHrefForStrategy(s)}
                      className="flex items-center gap-1 text-[11px] font-medium px-3 py-1.5 rounded transition-all"
                      style={{
                        background: `${cat.accent}14`,
                        border: `1px solid ${cat.accent}33`,
                        color: cat.accent,
                      }}
                    >
                      Use <ChevronRight size={10} />
                    </Link>
                    {isCustom && (
                      <Link
                        href={`/strategies/custom?strategyId=${encodeURIComponent(s.id)}`}
                        className="text-center text-[10px] px-3 py-1 rounded"
                        style={{
                          background: "rgba(136,85,255,0.08)",
                          border: "1px solid rgba(136,85,255,0.18)",
                          color: "var(--color-accent-purple)",
                        }}
                      >
                        Edit
                      </Link>
                    )}
                  </div>
                </div>

                {/* Description */}
                <p className="text-xs text-text-secondary leading-relaxed mb-4">
                  {s.description}
                </p>

                {/* Parameters */}
                <div
                  className="rounded p-3"
                  style={{
                    background: "var(--color-bg-primary)",
                    border: "1px solid var(--color-border)",
                  }}
                >
                  <p className="section-label mb-2">Parameters</p>
                  <div className="space-y-1.5">
                    {s.params.map((p) => (
                      <div
                        key={p.name}
                        className="flex justify-between items-center text-xs"
                      >
                        <span className="text-text-secondary">{p.label}</span>
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-text-primary tabular-nums">
                            {String(p.default)}
                          </span>
                          {p.min !== undefined && p.max !== undefined && (
                            <span className="text-text-muted font-mono text-[10px]">
                              [{p.min}–{p.max}]
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Category description */}
                <p className="text-[10px] text-text-muted mt-3 italic">
                  {cat.desc}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
