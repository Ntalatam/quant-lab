"use client";

import { useState } from "react";
import Link from "next/link";
import { useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  ArrowUpRight,
  BarChart3,
  ChevronRight,
  Columns3,
  Database,
  GitBranch,
  Loader2,
  Play,
  RadioTower,
  Sparkles,
  TrendingUp,
  Zap,
} from "lucide-react";

import { useSession } from "@/components/auth/SessionProvider";
import { ErrorMessage } from "@/components/shared/ErrorBoundary";
import { PageLoading } from "@/components/shared/LoadingSpinner";
import { useBacktestList } from "@/hooks/useBacktest";
import { formatDate, formatPercent, formatRatio } from "@/lib/formatters";
import { buildApiUrl } from "@/lib/network";

const STRATEGY_CATEGORY_MAP: Record<string, { label: string; cls: string }> = {
  sma_crossover: { label: "Trend", cls: "badge-trend" },
  mean_reversion: { label: "MeanRev", cls: "badge-reversion" },
  momentum: { label: "Momentum", cls: "badge-momentum" },
  pairs_trading: { label: "Arb", cls: "badge-arb" },
  ml_classifier: { label: "ML", cls: "badge-arb" },
  rsi_mean_reversion: { label: "RSI", cls: "badge-reversion" },
  macd_crossover: { label: "MACD", cls: "badge-trend" },
  donchian_breakout: { label: "Turtle", cls: "badge-trend" },
  vol_target_trend: { label: "VolTgt", cls: "badge-momentum" },
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

function QuickActionCard({
  href,
  icon: Icon,
  title,
  description,
  accent,
}: {
  href: string;
  icon: typeof Play;
  title: string;
  description: string;
  accent: string;
}) {
  return (
    <Link
      href={href}
      className="panel-soft group block p-4 transition-all duration-200 hover:-translate-y-1"
    >
      <div className="mb-3 flex items-center justify-between">
        <span
          className="flex h-11 w-11 items-center justify-center rounded-2xl"
          style={{
            background: `${accent}1f`,
            border: `1px solid ${accent}33`,
          }}
        >
          <Icon size={16} style={{ color: accent }} />
        </span>
        <ArrowUpRight
          size={14}
          className="text-text-muted transition-transform duration-200 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 group-hover:text-text-primary"
        />
      </div>
      <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
      <p className="mt-1 text-xs leading-relaxed text-text-muted">
        {description}
      </p>
    </Link>
  );
}

function DemoLoader({ onDone }: { onDone: () => void }) {
  const [state, setState] = useState<"idle" | "loading" | "done" | "error">(
    "idle",
  );
  const [msg, setMsg] = useState("");

  const seed = async () => {
    setState("loading");
    setMsg("Loading SPY, AAPL, MSFT, GLD and running 3 sample backtests…");
    try {
      const result = await fetch(buildApiUrl("/demo/seed"), {
        method: "POST",
      }).then((r) => r.json());
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
        setMsg(
          result.errors?.[0] ?? "Demo seeding failed — check backend logs.",
        );
      }
    } catch {
      setState("error");
      setMsg("Could not reach backend. Make sure the server is running.");
    }
  };

  return (
    <div className="panel-soft flex flex-col gap-4 p-4 lg:flex-row lg:items-center lg:justify-between">
      <div className="max-w-xl">
        <div className="mb-1 flex items-center gap-1.5">
          <Sparkles size={11} className="text-accent-green" />
          <p className="section-label">Demo Mode</p>
        </div>
        <p className="text-sm text-text-primary">
          Load 5 years of real data and run 3 sample backtests in one click
        </p>
        {msg && (
          <p
            className={`mt-1 text-[11px] ${
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
        className={`shrink-0 ${
          state === "done" ? "action-secondary" : "action-primary"
        } disabled:opacity-50`}
        style={
          state === "done"
            ? {
                color: "var(--color-accent-green)",
              }
            : undefined
        }
      >
        {state === "loading" ? (
          <>
            <Loader2 size={12} className="animate-spin" /> Loading…
          </>
        ) : state === "done" ? (
          <>
            <Sparkles size={12} /> Done!
          </>
        ) : (
          <>
            <Sparkles size={12} /> Load Demo Data
          </>
        )}
      </button>
    </div>
  );
}

function EmptyDashboard({ onDemoLoaded }: { onDemoLoaded: () => void }) {
  const { user, workspace } = useSession();
  const steps = [
    {
      num: "01",
      icon: Database,
      title: "Load market data",
      desc: "Fetch OHLCV history for any ticker and build your local research universe.",
      href: "/data",
      cta: "Open Data Explorer",
      accent: "var(--color-accent-blue)",
    },
    {
      num: "02",
      icon: Play,
      title: "Configure & run",
      desc: "Tune strategies, execution controls, and portfolio construction before launch.",
      href: "/backtest",
      cta: "New Backtest",
      accent: "var(--color-accent-green)",
    },
    {
      num: "03",
      icon: BarChart3,
      title: "Review the tear sheet",
      desc: "Inspect equity, drawdown, TCA, risk budget, and rolling diagnostics.",
      href: "/results",
      cta: "View Results",
      accent: "var(--color-accent-purple)",
    },
  ];

  return (
    <div className="space-y-6">
      <section className="panel-hero panel-grid overflow-hidden px-6 py-8 lg:px-8 lg:py-9">
        <div className="relative z-10 grid gap-8 lg:grid-cols-[1.2fr_0.8fr]">
          <div>
            <div className="page-kicker mb-5">
              <Activity size={9} />
              Research control room
            </div>
            <div className="mb-4 flex flex-wrap gap-2 text-[11px]">
              <span className="status-pill">
                <Activity size={12} className="text-accent-green" />
                {workspace?.name ?? "Workspace"}
              </span>
              <span className="status-pill">
                <TrendingUp size={12} className="text-accent-blue" />
                {user?.display_name || user?.email || "Signed in"}
              </span>
            </div>
            <h1 className="display-title text-5xl text-text-primary lg:text-6xl">
              Build a
              <span className="text-accent-green"> portfolio-grade </span>
              backtest in minutes.
            </h1>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-text-secondary lg:text-[15px]">
              QuantLab is built for serious research workflows: event-driven
              execution, realistic fills, long/short support, advanced
              analytics, and a polished strategy-to-tearsheet loop.
            </p>
            <div className="mt-6 flex flex-wrap gap-2">
              <span className="status-pill">
                <Activity size={12} className="text-accent-green" />
                No lookahead bias
              </span>
              <span className="status-pill">
                <Zap size={12} className="text-accent-blue" />
                TCA + risk budget
              </span>
              <span className="status-pill">
                <RadioTower size={12} className="text-accent-yellow" />
                Paper trading
              </span>
            </div>
          </div>

          <div className="panel-glass p-5">
            <div className="mb-4 flex items-center gap-2">
              <Sparkles size={12} className="text-accent-green" />
              <p className="section-label">Why teams use it</p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
              {[
                {
                  label: "Execution realism",
                  desc: "Commissions, slippage, impact curves, participation caps.",
                },
                {
                  label: "Research depth",
                  desc: "Walk-forward, sweeps, Bayesian search, factor and regime analysis.",
                },
                {
                  label: "Portfolio workflows",
                  desc: "Blend runs, compare correlations, and budget downside risk.",
                },
                {
                  label: "Ops ready",
                  desc: "Typed API, CI/CD, cloud deploys, and live paper sessions.",
                },
              ].map((item) => (
                <div
                  key={item.label}
                  className="rounded-2xl border border-border/60 bg-bg-card/60 px-4 py-3"
                >
                  <p className="text-xs font-semibold text-text-primary">
                    {item.label}
                  </p>
                  <p className="mt-1 text-[11px] leading-relaxed text-text-muted">
                    {item.desc}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {steps.map((step) => (
          <div
            key={step.num}
            className="panel-soft relative overflow-hidden p-5"
          >
            <div
              className="absolute inset-x-0 top-0 h-[3px]"
              style={{
                background: `linear-gradient(90deg, ${step.accent}, transparent)`,
              }}
            />
            <p
              className="font-mono text-4xl font-bold leading-none"
              style={{ color: "rgba(255,255,255,0.06)" }}
            >
              {step.num}
            </p>
            <div className="mt-4 flex items-center gap-2">
              <step.icon size={14} style={{ color: step.accent }} />
              <h3 className="text-sm font-semibold text-text-primary">
                {step.title}
              </h3>
            </div>
            <p className="mt-2 text-xs leading-relaxed text-text-secondary">
              {step.desc}
            </p>
            <Link
              href={step.href}
              className="mt-4 inline-flex items-center gap-1 text-xs font-medium transition-opacity hover:opacity-80"
              style={{ color: step.accent }}
            >
              {step.cta}
              <ChevronRight size={11} />
            </Link>
          </div>
        ))}
      </div>

      <DemoLoader onDone={onDemoLoaded} />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1.25fr_0.75fr]">
        <div className="panel-soft p-5">
          <p className="section-label mb-2">Manual Quick Start</p>
          <h2 className="text-lg font-semibold text-text-primary">
            Try a momentum basket in under five minutes.
          </h2>
          <p className="mt-2 max-w-xl text-sm leading-7 text-text-secondary">
            Load{" "}
            <span className="font-mono text-accent-blue">AAPL, MSFT, SPY</span>,
            launch an SMA crossover from 2020 to 2024, then compare it against a
            market-neutral strategy to see correlation and diversification.
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <Link href="/backtest" className="action-primary">
              <Play size={13} />
              New Backtest
            </Link>
            <Link href="/data" className="action-secondary">
              <Database size={13} />
              Load Market Data
            </Link>
          </div>
        </div>

        <div className="panel-soft p-5">
          <p className="section-label mb-3">Capabilities</p>
          <div className="space-y-3">
            {[
              {
                icon: Zap,
                label: "Event-driven engine",
                desc: "One bar at a time with realistic portfolio transitions.",
              },
              {
                icon: Activity,
                label: "Execution controls",
                desc: "Impact models, borrow carry, locate fees, and volume caps.",
              },
              {
                icon: Columns3,
                label: "Portfolio analysis",
                desc: "Compare strategies, blend weights, and inspect risk attribution.",
              },
            ].map((cap) => (
              <div
                key={cap.label}
                className="rounded-2xl border border-border/60 bg-bg-card/60 p-3"
              >
                <div className="mb-2 flex items-center gap-2">
                  <cap.icon size={13} className="text-accent-blue" />
                  <p className="text-xs font-semibold text-text-primary">
                    {cap.label}
                  </p>
                </div>
                <p className="text-[11px] leading-relaxed text-text-muted">
                  {cap.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const queryClient = useQueryClient();
  const { data: backtests, isLoading, error } = useBacktestList();
  const { user, workspace } = useSession();

  const handleDemoLoaded = () => {
    queryClient.invalidateQueries({ queryKey: ["backtests"] });
  };

  if (isLoading) return <PageLoading />;
  if (error) return <ErrorMessage message={error.message} />;

  const recent = backtests?.slice(0, 10) || [];
  const totalRuns = backtests?.length || 0;

  if (totalRuns === 0) {
    return <EmptyDashboard onDemoLoaded={handleDemoLoaded} />;
  }

  const bestSharpe = Math.max(...backtests!.map((b) => b.sharpe_ratio));
  const bestReturn = Math.max(...backtests!.map((b) => b.total_return_pct));
  const avgReturn =
    backtests!.reduce((sum, run) => sum + run.total_return_pct, 0) /
    backtests!.length;
  const bestRun = backtests!.find((run) => run.sharpe_ratio === bestSharpe);

  const stats = [
    {
      label: "Total Runs",
      value: String(totalRuns),
      sub: `${backtests!.length} strategy runs`,
      icon: BarChart3,
      accent: "var(--color-accent-blue)",
      iconBg: "rgba(107,149,255,0.12)",
      positive: undefined,
    },
    {
      label: "Best Sharpe",
      value: formatRatio(bestSharpe),
      sub: bestRun ? bestRun.strategy_name : "",
      icon: TrendingUp,
      accent: "var(--color-accent-green)",
      iconBg: "rgba(40,221,176,0.12)",
      positive: bestSharpe > 1,
    },
    {
      label: "Best Return",
      value: formatPercent(bestReturn),
      sub: "Single backtest high",
      icon: Activity,
      accent:
        bestReturn >= 0
          ? "var(--color-accent-green)"
          : "var(--color-accent-red)",
      iconBg:
        bestReturn >= 0 ? "rgba(40,221,176,0.12)" : "rgba(255,95,121,0.12)",
      positive: bestReturn >= 0,
    },
    {
      label: "Avg Return",
      value: formatPercent(avgReturn),
      sub: "Across all runs",
      icon: Columns3,
      accent:
        avgReturn >= 0
          ? "var(--color-accent-green)"
          : "var(--color-accent-red)",
      iconBg:
        avgReturn >= 0 ? "rgba(40,221,176,0.12)" : "rgba(255,95,121,0.12)",
      positive: avgReturn >= 0,
    },
  ];

  return (
    <div className="space-y-6">
      <section className="panel-hero panel-grid overflow-hidden px-6 py-7 lg:px-8 lg:py-8">
        <div className="relative z-10 grid gap-6 lg:grid-cols-[1.2fr_0.8fr] lg:items-end">
          <div>
            <div className="page-kicker mb-5">
              <Activity size={9} />
              Dashboard
            </div>
            <div className="mb-4 flex flex-wrap gap-2 text-[11px]">
              <span className="status-pill">
                <Activity size={12} className="text-accent-green" />
                {workspace?.name ?? "Workspace"}
              </span>
              <span className="status-pill">
                <TrendingUp size={12} className="text-accent-blue" />
                {user?.display_name || user?.email || "Signed in"}
              </span>
            </div>
            <h1 className="display-title text-5xl text-text-primary lg:text-6xl">
              The research
              <span className="text-accent-blue"> control room </span>
              for every run.
            </h1>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-text-secondary lg:text-[15px]">
              Track performance across your backtests, jump directly into new
              simulations, and move from ideas to portfolio decisions with a
              cleaner research loop.
            </p>
            <div className="mt-6 flex flex-wrap gap-2">
              <span className="status-pill">
                <BarChart3 size={12} className="text-accent-green" />
                {totalRuns} saved runs
              </span>
              <span className="status-pill">
                <TrendingUp size={12} className="text-accent-blue" />
                Best Sharpe {formatRatio(bestSharpe)}
              </span>
              <span className="status-pill">
                <Activity size={12} className="text-accent-yellow" />
                Avg return {formatPercent(avgReturn)}
              </span>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <QuickActionCard
              href="/backtest"
              icon={Play}
              title="Launch a new backtest"
              description="Configure a strategy, tune execution controls, and stream results live."
              accent="var(--color-accent-green)"
            />
            <QuickActionCard
              href="/paper"
              icon={RadioTower}
              title="Start paper trading"
              description="Reuse a saved configuration and watch it update bar by bar."
              accent="var(--color-accent-yellow)"
            />
            <QuickActionCard
              href="/compare"
              icon={Columns3}
              title="Compare portfolio ideas"
              description="Overlay runs, inspect correlation, and build blended allocations."
              accent="var(--color-accent-blue)"
            />
            <QuickActionCard
              href="/lineage"
              icon={GitBranch}
              title="Review research lineage"
              description="Track notes, variants, and the evolution of strategy decisions."
              accent="var(--color-accent-purple)"
            />
          </div>
        </div>
      </section>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {stats.map((stat) => (
          <div
            key={stat.label}
            className="panel-soft relative overflow-hidden p-4"
          >
            <div
              className="absolute inset-x-0 top-0 h-[3px]"
              style={{
                background: `linear-gradient(90deg, ${stat.accent}, transparent)`,
              }}
            />
            <div className="mb-3 flex items-start justify-between">
              <p className="section-label">{stat.label}</p>
              <div
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl"
                style={{
                  background: stat.iconBg,
                  border: "1px solid rgba(255,255,255,0.06)",
                }}
              >
                <stat.icon size={13} style={{ color: stat.accent }} />
              </div>
            </div>
            <p
              className="text-2xl font-bold font-mono tabular-nums"
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
            <p className="mt-1 text-[11px] text-text-muted">{stat.sub}</p>
          </div>
        ))}
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.25fr_0.75fr]">
        <div className="table-shell">
          <div
            className="flex items-center justify-between px-5 py-4"
            style={{ borderBottom: "1px solid rgba(111,130,166,0.12)" }}
          >
            <div>
              <p className="section-label mb-1">Recent backtests</p>
              <h2 className="text-base font-semibold text-text-primary">
                Your latest research snapshots
              </h2>
            </div>
            <Link href="/results" className="action-ghost">
              All results
              <ChevronRight size={12} />
            </Link>
          </div>

          <div className="table-scroll">
            <table className="min-w-full text-sm">
              <thead>
                <tr>
                  {[
                    "Strategy",
                    "Type",
                    "Tickers",
                    "Period",
                    "Return",
                    "Sharpe",
                    "Max DD",
                    "Run",
                  ].map((heading) => (
                    <th
                      key={heading}
                      className={`section-label px-4 py-3 font-normal ${
                        ["Return", "Sharpe", "Max DD", "Run"].includes(heading)
                          ? "text-right"
                          : "text-left"
                      }`}
                    >
                      {heading}
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
                    <tr key={bt.id}>
                      <td className="px-4 py-3">
                        <Link
                          href={`/backtest/${bt.id}`}
                          className="text-[13px] font-medium text-accent-blue hover:underline"
                        >
                          {bt.strategy_name}
                        </Link>
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`${cat.cls} rounded-full px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wider`}
                        >
                          {cat.label}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-mono text-xs text-text-secondary">
                        {bt.tickers.join(", ")}
                      </td>
                      <td className="px-4 py-3 text-xs text-text-muted">
                        {bt.start_date} — {bt.end_date}
                      </td>
                      <td
                        className={`px-4 py-3 text-right font-mono text-[13px] tabular-nums ${
                          bt.total_return_pct >= 0
                            ? "text-accent-green"
                            : "text-accent-red"
                        }`}
                      >
                        {formatPercent(bt.total_return_pct)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <SharpeCell value={bt.sharpe_ratio} />
                      </td>
                      <td className="px-4 py-3 text-right font-mono text-[13px] tabular-nums text-accent-red">
                        {formatPercent(bt.max_drawdown_pct)}
                      </td>
                      <td className="px-4 py-3 text-right text-[11px] text-text-muted">
                        {bt.created_at ? formatDate(bt.created_at) : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        <div className="space-y-4">
          <div className="panel-soft p-5">
            <p className="section-label mb-2">Research pulse</p>
            <h2 className="text-base font-semibold text-text-primary">
              What looks strongest right now?
            </h2>
            <div className="mt-4 space-y-3">
              <div className="rounded-2xl border border-border/60 bg-bg-card/60 p-3">
                <p className="text-[11px] text-text-muted">Top Sharpe run</p>
                <p className="mt-1 text-sm font-semibold text-text-primary">
                  {bestRun?.strategy_name ?? "—"}
                </p>
                <p className="mt-1 font-mono text-xs text-accent-green">
                  {formatRatio(bestSharpe)} Sharpe
                </p>
              </div>
              <div className="rounded-2xl border border-border/60 bg-bg-card/60 p-3">
                <p className="text-[11px] text-text-muted">Return envelope</p>
                <p className="mt-1 text-sm font-semibold text-text-primary">
                  {formatPercent(bestReturn)} best case
                </p>
                <p className="mt-1 text-[11px] text-text-muted">
                  Portfolio-wide average: {formatPercent(avgReturn)}
                </p>
              </div>
            </div>
          </div>

          <div className="panel-soft p-5">
            <p className="section-label mb-3">Next moves</p>
            <div className="space-y-3">
              {[
                {
                  href: "/compare",
                  icon: Columns3,
                  title: "Compare your best runs",
                  desc: "Inspect correlations before blending them into one portfolio.",
                },
                {
                  href: "/paper",
                  icon: RadioTower,
                  title: "Forward-test your thesis",
                  desc: "Turn a strong backtest into a live paper session instantly.",
                },
              ].map((item) => (
                <Link
                  key={item.title}
                  href={item.href}
                  className="block rounded-2xl border border-border/60 bg-bg-card/60 p-3 transition-colors hover:bg-bg-hover"
                >
                  <div className="mb-2 flex items-center gap-2">
                    <item.icon size={13} className="text-accent-blue" />
                    <p className="text-xs font-semibold text-text-primary">
                      {item.title}
                    </p>
                  </div>
                  <p className="text-[11px] leading-relaxed text-text-muted">
                    {item.desc}
                  </p>
                </Link>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
