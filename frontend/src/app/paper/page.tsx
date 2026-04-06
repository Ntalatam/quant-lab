"use client";

import { Suspense, useMemo } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Activity, ArrowRight, PlayCircle, RadioTower } from "lucide-react";

import { PaperSessionForm } from "@/components/paper/PaperSessionForm";
import { PageLoading } from "@/components/shared/LoadingSpinner";
import { usePaperSessions } from "@/hooks/usePaperTrading";
import { PAPER_EXECUTION_MODE_LABELS } from "@/lib/constants";
import {
  formatCompactDate,
  formatCurrency,
  formatPercent,
} from "@/lib/formatters";
import type { BacktestConfig } from "@/lib/types";

function PrefilledForm() {
  const searchParams = useSearchParams();

  const prefillConfig = useMemo(() => {
    const encoded = searchParams.get("config");
    if (!encoded) return null;
    try {
      return JSON.parse(
        atob(decodeURIComponent(encoded)),
      ) as Partial<BacktestConfig>;
    } catch {
      return null;
    }
  }, [searchParams]);

  return <PaperSessionForm prefillConfig={prefillConfig} />;
}

function statusColor(status: string) {
  switch (status) {
    case "active":
      return "var(--color-accent-green)";
    case "paused":
      return "var(--color-accent-yellow)";
    case "error":
      return "var(--color-accent-red)";
    default:
      return "var(--color-accent-blue)";
  }
}

export default function PaperTradingPage() {
  const { data: sessions, isLoading, error } = usePaperSessions();

  if (isLoading) return <PageLoading />;
  if (error) {
    return <div className="text-sm text-accent-red">{error.message}</div>;
  }

  return (
    <div>
      <div className="mb-7">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-[10px] uppercase tracking-widest mb-4 font-medium bg-accent-green/10 text-accent-green border border-accent-green/20">
          <RadioTower size={10} />
          Live paper trading
        </div>
        <h1 className="text-xl font-bold text-text-primary tracking-tight">
          Paper Trading
        </h1>
        <p className="text-xs text-text-muted mt-1 max-w-2xl leading-relaxed">
          Run a strategy continuously against live market polling, stream
          mark-to-market equity updates over WebSocket, and review positions and
          fills in a dedicated session dashboard.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1.1fr_0.9fr] gap-6">
        <Suspense fallback={<PageLoading />}>
          <PrefilledForm />
        </Suspense>

        <div
          className="rounded-md p-5"
          style={{
            background: "var(--color-bg-card)",
            border: "1px solid var(--color-border)",
            boxShadow: "0 1px 3px rgba(0,0,0,0.4)",
          }}
        >
          <div className="flex items-start justify-between mb-4">
            <div>
              <h2 className="text-sm font-semibold text-text-primary">
                Existing Sessions
              </h2>
              <p className="text-xs text-text-muted mt-1">
                {sessions?.length ?? 0} live paper session
                {(sessions?.length ?? 0) === 1 ? "" : "s"} on record
              </p>
            </div>
            <div className="text-[10px] text-text-muted">
              Auto-refreshes every 30s
            </div>
          </div>

          {!sessions || sessions.length === 0 ? (
            <div className="h-72 flex flex-col items-center justify-center gap-3 text-center">
              <Activity size={22} className="text-text-muted" />
              <div>
                <p className="text-sm text-text-secondary">
                  No paper sessions yet
                </p>
                <p className="text-xs text-text-muted mt-1">
                  Create one on the left or launch from a saved backtest result.
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-3 max-h-[820px] overflow-y-auto pr-1">
              {sessions.map((session) => (
                <Link
                  key={session.id}
                  href={`/paper/${session.id}`}
                  className="block rounded-md p-4 transition-colors hover:bg-bg-hover"
                  style={{
                    background: "var(--color-bg-primary)",
                    border: "1px solid var(--color-border)",
                  }}
                >
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-medium text-text-primary text-sm">
                          {session.name}
                        </span>
                        <span
                          className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full border"
                          style={{
                            color: statusColor(session.status),
                            borderColor: `${statusColor(session.status)}55`,
                            background: `${statusColor(session.status)}12`,
                          }}
                        >
                          {session.status}
                        </span>
                      </div>
                      <p className="text-[11px] text-text-muted">
                        {session.strategy_id} · {session.tickers.join(", ")} ·{" "}
                        {session.bar_interval}
                      </p>
                      <div className="flex flex-wrap items-center gap-2 mt-2">
                        <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full border border-border text-text-secondary">
                          {PAPER_EXECUTION_MODE_LABELS[session.execution_mode]}
                        </span>
                        {session.broker_account_label && (
                          <span className="text-[10px] text-text-muted">
                            {session.broker_account_label}
                          </span>
                        )}
                      </div>
                    </div>
                    <ArrowRight size={14} className="text-text-muted" />
                  </div>

                  <div className="grid grid-cols-2 gap-3 mb-3">
                    <div>
                      <p className="section-label mb-1">Total Equity</p>
                      <p className="font-mono text-sm text-text-primary">
                        {formatCurrency(session.total_equity)}
                      </p>
                    </div>
                    <div>
                      <p className="section-label mb-1">Return</p>
                      <p
                        className={`font-mono text-sm ${
                          session.total_return_pct >= 0
                            ? "text-accent-green"
                            : "text-accent-red"
                        }`}
                      >
                        {formatPercent(session.total_return_pct)}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-[10px] text-text-muted">
                    <span>
                      {session.started_at
                        ? `Started ${formatCompactDate(session.started_at)}`
                        : `Created ${formatCompactDate(session.created_at)}`}
                    </span>
                    <span className="flex items-center gap-1">
                      <PlayCircle size={11} />
                      {session.polling_interval_seconds}s polling
                    </span>
                  </div>

                  {session.open_order_count > 0 && (
                    <p className="text-[10px] text-text-muted mt-2">
                      {session.open_order_count} open order
                      {session.open_order_count === 1 ? "" : "s"}
                    </p>
                  )}

                  {session.last_error && (
                    <p className="text-[10px] text-accent-red mt-2">
                      {session.last_error}
                    </p>
                  )}
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
