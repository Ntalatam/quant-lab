"use client";

import type { EarningsOverview } from "@/lib/types";

function formatCurrencyCompact(value: number | null) {
  if (value == null) return "—";
  if (Math.abs(value) >= 1_000_000_000) {
    return `$${(value / 1_000_000_000).toFixed(1)}B`;
  }
  if (Math.abs(value) >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(1)}M`;
  }
  return `$${value.toFixed(2)}`;
}

export function EarningsPanel({
  overview,
  isLoading,
}: {
  overview: EarningsOverview | undefined;
  isLoading: boolean;
}) {
  const scheduled = overview?.events.find(
    (event) => event.event_type === "scheduled",
  );
  const reported =
    overview?.events.filter((event) => event.event_type === "reported") ?? [];

  return (
    <div className="card p-5 space-y-4 h-full">
      <div>
        <h2 className="text-sm font-semibold text-text-primary">
          Earnings Timeline
        </h2>
        <p className="text-xs text-text-muted mt-1">
          Upcoming calls and recent quarterly prints are overlaid on the price
          chart with event markers.
        </p>
      </div>

      {isLoading ? (
        <div className="py-10 text-sm text-text-muted text-center">
          Loading earnings events…
        </div>
      ) : overview ? (
        <>
          <div
            className="rounded p-4"
            style={{
              background: "rgba(255,187,51,0.06)",
              border: "1px solid rgba(255,187,51,0.18)",
            }}
          >
            <p className="section-label">Next Earnings</p>
            <p className="text-lg font-semibold text-text-primary mt-2">
              {scheduled?.date ?? "No scheduled date available"}
            </p>
            <div className="grid grid-cols-2 gap-3 mt-3 text-[11px] text-text-secondary">
              <div>
                <span className="text-text-muted">EPS est.</span>
                <p className="font-mono tabular-nums text-text-primary mt-1">
                  {scheduled?.eps_estimate?.toFixed(2) ?? "—"}
                </p>
              </div>
              <div>
                <span className="text-text-muted">Revenue est.</span>
                <p className="font-mono tabular-nums text-text-primary mt-1">
                  {formatCurrencyCompact(scheduled?.revenue_estimate ?? null)}
                </p>
              </div>
            </div>
          </div>

          <div className="space-y-2">
            {reported.length > 0 ? (
              reported.map((event) => (
                <div
                  key={`${event.date}-${event.event_type}`}
                  className="rounded px-3 py-2.5"
                  style={{
                    background: "var(--color-bg-primary)",
                    border: "1px solid var(--color-border)",
                  }}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-text-primary">
                        {event.quarter_label ?? event.title}
                      </p>
                      <p className="text-[11px] text-text-muted mt-0.5">
                        {event.date}
                      </p>
                    </div>
                    {event.eps_surprise_pct != null && (
                      <span
                        className={
                          event.eps_surprise_pct >= 0
                            ? "text-accent-green text-[11px] font-medium"
                            : "text-accent-red text-[11px] font-medium"
                        }
                      >
                        {event.eps_surprise_pct >= 0 ? "+" : ""}
                        {event.eps_surprise_pct.toFixed(1)}% surprise
                      </span>
                    )}
                  </div>
                  <div className="grid grid-cols-2 gap-3 mt-3 text-[11px]">
                    <div>
                      <span className="text-text-muted">EPS actual</span>
                      <p className="text-text-primary font-mono tabular-nums mt-1">
                        {event.eps_actual?.toFixed(2) ?? "—"}
                      </p>
                    </div>
                    <div>
                      <span className="text-text-muted">EPS estimate</span>
                      <p className="text-text-primary font-mono tabular-nums mt-1">
                        {event.eps_estimate?.toFixed(2) ?? "—"}
                      </p>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="py-8 text-sm text-text-muted text-center">
                No recent earnings history available for this ticker.
              </div>
            )}
          </div>
        </>
      ) : (
        <div className="py-10 text-sm text-text-muted text-center">
          Select a ticker to load earnings events.
        </div>
      )}
    </div>
  );
}
