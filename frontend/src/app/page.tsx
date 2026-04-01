"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { useBacktestList } from "@/hooks/useBacktest";
import { PageLoading } from "@/components/shared/LoadingSpinner";
import { ErrorMessage } from "@/components/shared/ErrorBoundary";
import { formatPercent, formatRatio, formatDate } from "@/lib/formatters";
import { api } from "@/lib/api";
import {
  Play,
  BarChart3,
  TrendingUp,
  Database,
  Columns3,
  ChevronRight,
  Zap,
  Activity,
  Loader2,
  Sparkles,
} from "lucide-react";

const STRATEGY_CATEGORY_MAP: Record<string, { label: string; cls: string }> = {
  sma_crossover:   { label: "Trend",   cls: "badge-trend"     },
  mean_reversion:  { label: "MeanRev", cls: "badge-reversion"  },
  momentum:        { label: "Momentum",cls: "badge-momentum"   },
  pairs_trading:   { label: "Arb",     cls: "badge-arb"        },
  ml_classifier:   { label: "ML",      cls: "badge-arb"        },
};

function SharpeCell({ value }: { value: number }) {
  const color =
    value >= 1.5
      ? "text-accent-green"
      : value >= 0.8
        ? "text-accent-yellow"
        : value > 0
          ? "text-text-secondary"
          : "text-accent-red";
  return (
    <span className={`font-mono tabular-nums ${color}`}>
      {formatRatio(value)}
    </span>
  );
}

// ── Demo seeder ───────────────────────────────────────────────────────

function DemoLoader({ onDone }: { onDone: () => void }) {
  const [state, setState] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [msg, setMsg] = useState("");

  const seed = async () => {
    setState("loading");
    setMsg("Loading SPY, AAPL, MSFT, GLD and running 3 sample backtests…");
    try {
      const result = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api"}/demo/seed`,
        { method: "POST" }
      ).then((r) => r.json());
      if (result.status === "already_seeded") {
        setState("done");
        setMsg("Demo data already loaded.");
        onDone();
      } else if (result.backtests_created?.length > 0) {
        setState("done");
        setMsg(`Created ${result.backtests_created.length} demo backtests.`);
        onDone();
      } else {
        setState("error");
        setMsg(result.errors?.[0] ?? "Demo seeding failed — check backend logs.");
      }
    } catch {
      setState("error");
      setMsg("Could not reach backend. Make sure the server is running.");
    }
  };

  return (
    <div
      className="rounded-md p-4 flex items-center justify-between gap-4"
      style={{
        background: "rgba(0,212,170,0.04)",
        border: "1px solid rgba(0,212,170,0.18)",
      }}
    >
      <div>
        <div className="flex items-center gap-1.5 mb-1">
          <Sparkles size={11} className="text-accent-green" />
          <p className="section-label">Demo Mode</p>
        </div>
        <p className="text-sm text-text-primary">
          Load 5 years of real data and run 3 sample backtests in one click
        </p>
        {msg && (
          <p
            className={`text-[11px] mt-0.5 ${
              state === "error" ? "text-accent-red" : "text-text-muted"
            }`}
          >
            {msg}
          </p>
        )}
      </div>
      <button
        onClick={seed}
        disabled={state === "loading" || state === "done"}
        className="shrink-0 flex items-center gap-2 text-xs font-medium px-4 py-2 rounded transition-all disabled:opacity-50"
        style={
          state === "done"
            ? {
                background: "rgba(0,212,170,0.2)",
                border: "1px solid rgba(0,212,170,0.4)",
                color: "var(--color-accent-green)",
              }
            : {
                background: "var(--color-accent-green)",
                color: "var(--color-bg-primary)",
                boxShadow: "0 0 12px rgba(0,212,170,0.2)",
              }
        }
      >
        {state === "loading" ? (
          <><Loader2 size={12} className="animate-spin" /> Loading…</>
        ) : state === "done" ? (
          <><Sparkles size={12} /> Done!</>
        ) : (
          <><Sparkles size={12} /> Load Demo Data</>
        )}
      </button>
    </div>
  );
}

// ── Empty state: platform onboarding ────────────────────────────────

function EmptyDashboard({ onDemoLoaded }: { onDemoLoaded: () => void }) {
  const steps = [
    {
      num: "01",
      icon: Database,
      title: "Load Market Data",
      desc: "Fetch OHLCV price history for any tickers via yfinance and cache to PostgreSQL.",
      href: "/data",
      cta: "Open Data Explorer",
      accent: "var(--color-accent-blue)",
    },
    {
      num: "02",
      icon: Play,
      title: "Configure & Run",
      desc: "Select a strategy, tune parameters, set execution constraints, and run the simulation.",
      href: "/backtest",
      cta: "New Backtest",
      accent: "var(--color-accent-green)",
    },
    {
      num: "03",
      icon: BarChart3,
      title: "Analyze Results",
      desc: "Review the full tear sheet — equity curve, drawdown, rolling metrics, trade log.",
      href: "/results",
      cta: "View Results",
      accent: "var(--color-accent-purple)",
    },
  ];

  return (
    <div>
      {/* Hero */}
      <div className="mb-10 pt-4">
        <div
          className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-[10px] uppercase tracking-widest mb-5 font-medium"
          style={{
            background: "rgba(0,212,170,0.06)",
            border: "1px solid rgba(0,212,170,0.18)",
            color: "var(--color-accent-green)",
          }}
        >
          <Activity size={9} />
          Event-driven · No lookahead bias · 25+ analytics metrics
        </div>
        <h1 className="text-3xl font-bold text-text-primary mb-3 tracking-tight">
          Quant<span className="text-accent-green">Lab</span>
        </h1>
        <p className="text-text-secondary text-sm max-w-xl leading-relaxed">
          Systematic backtesting against real historical market data. Tests
          strategies one bar at a time — no vectorized shortcuts, no peeking
          ahead. Four strategy families, realistic execution simulation, and
          a full research analytics suite.
        </p>
      </div>

      {/* 3-step workflow */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        {steps.map((step) => (
          <div
            key={step.num}
            className="relative overflow-hidden rounded-md p-5"
            style={{
              background: "var(--color-bg-card)",
              border: "1px solid var(--color-border)",
              boxShadow:
                "0 1px 3px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.025)",
            }}
          >
            {/* Top accent bar */}
            <div
              className="absolute top-0 left-0 right-0 h-[2px] rounded-t-md"
              style={{ background: step.accent, opacity: 0.7 }}
            />

            {/* Large muted step number */}
            <p
              className="font-mono font-bold text-4xl leading-none mb-3 select-none"
              style={{ color: "rgba(255,255,255,0.05)" }}
            >
              {step.num}
            </p>

            <div className="flex items-center gap-2 mb-2">
              <step.icon size={14} style={{ color: step.accent }} />
              <h3 className="font-semibold text-text-primary text-sm">
                {step.title}
              </h3>
            </div>

            <p className="text-xs text-text-secondary leading-relaxed mb-4">
              {step.desc}
            </p>

            <Link
              href={step.href}
              className="inline-flex items-center gap-1 text-xs font-medium transition-opacity hover:opacity-80"
              style={{ color: step.accent }}
            >
              {step.cta}
              <ChevronRight size={11} />
            </Link>
          </div>
        ))}
      </div>

      {/* Demo mode */}
      <DemoLoader onDone={onDemoLoaded} />

      {/* Quick start suggestion */}
      <div
        className="rounded-md p-4 flex items-center justify-between gap-4 mt-4"
        style={{
          background: "rgba(68,136,255,0.04)",
          border: "1px solid rgba(68,136,255,0.16)",
        }}
      >
        <div>
          <p className="section-label mb-1">Manual Quick Start</p>
          <p className="text-sm text-text-primary">
            Try{" "}
            <span className="font-mono text-accent-blue">AAPL, MSFT, SPY</span>
            {" · "}
            <span className="text-text-secondary">SMA Crossover · 2020–2024</span>
          </p>
          <p className="text-[11px] text-text-muted mt-0.5">
            Load the tickers first, then configure the backtest.
          </p>
        </div>
        <Link
          href="/backtest"
          className="shrink-0 flex items-center gap-2 text-xs font-medium px-4 py-2 rounded transition-all"
          style={{
            background: "rgba(68,136,255,0.12)",
            border: "1px solid rgba(68,136,255,0.25)",
            color: "var(--color-accent-blue)",
          }}
        >
          <Play size={12} />
          New Backtest
        </Link>
      </div>

      {/* Capabilities strip */}
      <div className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { icon: Zap, label: "Event-Driven Engine", desc: "One bar at a time, no lookahead" },
          { icon: Activity, label: "Realistic Execution", desc: "Slippage, commissions, volume limits" },
          { icon: BarChart3, label: "25+ Analytics", desc: "Sharpe, CVaR, alpha, beta, rolling metrics" },
          { icon: Columns3, label: "Strategy Comparison", desc: "Head-to-head with correlation analysis" },
        ].map((cap) => (
          <div
            key={cap.label}
            className="rounded p-3"
            style={{
              background: "var(--color-bg-card)",
              border: "1px solid var(--color-border)",
            }}
          >
            <cap.icon size={13} className="text-text-muted mb-2" />
            <p className="text-[11px] font-medium text-text-secondary mb-0.5">
              {cap.label}
            </p>
            <p className="text-[10px] text-text-muted leading-relaxed">
              {cap.desc}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Main dashboard ───────────────────────────────────────────────────

export default function DashboardPage() {
  const queryClient = useQueryClient();
  const { data: backtests, isLoading, error } = useBacktestList();

  const handleDemoLoaded = () => {
    queryClient.invalidateQueries({ queryKey: ["backtests"] });
  };

  if (isLoading) return <PageLoading />;
  if (error) return <ErrorMessage message={error.message} />;

  const recent = backtests?.slice(0, 10) || [];
  const totalRuns = backtests?.length || 0;

  if (totalRuns === 0) return <EmptyDashboard onDemoLoaded={handleDemoLoaded} />;

  const bestSharpe = Math.max(...backtests!.map((b) => b.sharpe_ratio));
  const bestReturn = Math.max(...backtests!.map((b) => b.total_return_pct));
  const avgReturn =
    backtests!.reduce((s, b) => s + b.total_return_pct, 0) / backtests!.length;
  const bestRun = backtests!.find((b) => b.sharpe_ratio === bestSharpe);

  const stats = [
    {
      label: "Total Runs",
      value: String(totalRuns),
      sub: `${backtests!.length} strategy runs`,
      icon: BarChart3,
      accent: "var(--color-accent-blue)",
      iconBg: "rgba(68,136,255,0.1)",
      positive: undefined,
    },
    {
      label: "Best Sharpe",
      value: formatRatio(bestSharpe),
      sub: bestRun ? bestRun.strategy_name : "",
      icon: TrendingUp,
      accent: "var(--color-accent-green)",
      iconBg: "rgba(0,212,170,0.1)",
      positive: bestSharpe > 1,
    },
    {
      label: "Best Return",
      value: formatPercent(bestReturn),
      sub: "Single backtest high",
      icon: Activity,
      accent: bestReturn >= 0 ? "var(--color-accent-green)" : "var(--color-accent-red)",
      iconBg:
        bestReturn >= 0 ? "rgba(0,212,170,0.1)" : "rgba(255,68,102,0.1)",
      positive: bestReturn >= 0,
    },
    {
      label: "Avg Return",
      value: formatPercent(avgReturn),
      sub: "Across all runs",
      icon: Columns3,
      accent: avgReturn >= 0 ? "var(--color-accent-green)" : "var(--color-accent-red)",
      iconBg:
        avgReturn >= 0 ? "rgba(0,212,170,0.1)" : "rgba(255,68,102,0.1)",
      positive: avgReturn >= 0,
    },
  ];

  return (
    <div>
      {/* Page header */}
      <div className="flex items-center justify-between mb-7">
        <div>
          <h1 className="text-xl font-bold text-text-primary tracking-tight">
            Dashboard
          </h1>
          <p className="text-xs text-text-muted mt-0.5">
            {totalRuns} backtest{totalRuns !== 1 ? "s" : ""} on record
          </p>
        </div>
        <Link
          href="/backtest"
          className="flex items-center gap-2 text-xs font-medium px-4 py-2 rounded transition-all"
          style={{
            background: "rgba(0,212,170,0.1)",
            border: "1px solid rgba(0,212,170,0.22)",
            color: "var(--color-accent-green)",
          }}
        >
          <Play size={12} />
          New Backtest
        </Link>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {stats.map((stat) => (
          <div
            key={stat.label}
            className="relative overflow-hidden rounded-md p-4"
            style={{
              background: "var(--color-bg-card)",
              border: "1px solid var(--color-border)",
              boxShadow:
                "0 1px 3px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.025)",
            }}
          >
            {/* Accent bar */}
            <div
              className="absolute top-0 left-0 right-0 h-[2px] rounded-t-md"
              style={{ background: stat.accent, opacity: 0.6 }}
            />
            <div className="flex items-start justify-between mb-3">
              <p className="section-label">{stat.label}</p>
              <div
                className="w-7 h-7 rounded flex items-center justify-center shrink-0"
                style={{ background: stat.iconBg }}
              >
                <stat.icon size={13} style={{ color: stat.accent }} />
              </div>
            </div>
            <p
              className="text-2xl font-mono tabular-nums font-bold"
              style={{
                color:
                  stat.positive === undefined
                    ? "var(--color-text-primary)"
                    : stat.positive
                      ? "var(--color-accent-green)"
                      : "var(--color-accent-red)",
              }}
            >
              {stat.value}
            </p>
            <p className="text-[10px] text-text-muted mt-1">{stat.sub}</p>
          </div>
        ))}
      </div>

      {/* Recent runs table */}
      <div
        className="rounded-md overflow-hidden"
        style={{
          background: "var(--color-bg-card)",
          border: "1px solid var(--color-border)",
          boxShadow: "0 1px 3px rgba(0,0,0,0.4)",
        }}
      >
        <div
          className="flex items-center justify-between px-5 py-3"
          style={{ borderBottom: "1px solid var(--color-border)" }}
        >
          <h2 className="text-sm font-semibold text-text-primary">
            Recent Backtests
          </h2>
          <Link
            href="/results"
            className="text-xs text-text-muted hover:text-text-secondary transition-colors flex items-center gap-1"
          >
            All results <ChevronRight size={11} />
          </Link>
        </div>

        <table className="w-full text-sm">
          <thead>
            <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
              {[
                "Strategy",
                "Type",
                "Tickers",
                "Period",
                "Return",
                "Sharpe",
                "Max DD",
                "Run",
              ].map((h) => (
                <th
                  key={h}
                  className={`section-label py-2.5 px-4 font-normal ${
                    ["Return", "Sharpe", "Max DD", "Run"].includes(h)
                      ? "text-right"
                      : "text-left"
                  }`}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {recent.map((bt) => {
              const cat = STRATEGY_CATEGORY_MAP[bt.strategy_name] ??
                STRATEGY_CATEGORY_MAP[bt.strategy_name.toLowerCase()] ?? {
                  label: "Other",
                  cls: "badge-trend",
                };
              return (
                <tr
                  key={bt.id}
                  className="transition-colors hover:bg-bg-hover"
                  style={{ borderBottom: "1px solid rgba(37,37,53,0.6)" }}
                >
                  <td className="py-2.5 px-4">
                    <Link
                      href={`/backtest/${bt.id}`}
                      className="text-accent-blue hover:underline font-medium text-[13px]"
                    >
                      {bt.strategy_name}
                    </Link>
                  </td>
                  <td className="py-2.5 px-4">
                    <span
                      className={`${cat.cls} text-[9px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full`}
                    >
                      {cat.label}
                    </span>
                  </td>
                  <td className="py-2.5 px-4 text-text-secondary font-mono text-xs">
                    {bt.tickers.join(", ")}
                  </td>
                  <td className="py-2.5 px-4 text-text-muted text-xs">
                    {bt.start_date} — {bt.end_date}
                  </td>
                  <td
                    className={`py-2.5 px-4 text-right font-mono tabular-nums text-[13px] ${
                      bt.total_return_pct >= 0
                        ? "text-accent-green"
                        : "text-accent-red"
                    }`}
                  >
                    {formatPercent(bt.total_return_pct)}
                  </td>
                  <td className="py-2.5 px-4 text-right">
                    <SharpeCell value={bt.sharpe_ratio} />
                  </td>
                  <td className="py-2.5 px-4 text-right font-mono tabular-nums text-accent-red text-[13px]">
                    {formatPercent(bt.max_drawdown_pct)}
                  </td>
                  <td className="py-2.5 px-4 text-right text-text-muted text-[11px]">
                    {bt.created_at ? formatDate(bt.created_at) : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
