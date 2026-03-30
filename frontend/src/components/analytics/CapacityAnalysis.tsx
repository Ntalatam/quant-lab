"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { CapacityResult } from "@/lib/types";
import { Loader2, Scale } from "lucide-react";

interface CapacityAnalysisProps {
  backtestId: string;
}

function formatAUM(v: number | null): string {
  if (v === null) return "Unlimited";
  if (v >= 1_000_000_000) return `$${(v / 1_000_000_000).toFixed(1)}B`;
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `$${(v / 1_000).toFixed(0)}K`;
  return `$${v.toFixed(0)}`;
}

export function CapacityAnalysis({ backtestId }: CapacityAnalysisProps) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CapacityResult | null>(null);
  const [error, setError] = useState("");

  const run = async () => {
    setError("");
    setLoading(true);
    try {
      const res = await api.getCapacityAnalysis(backtestId);
      setResult(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Capacity analysis failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="rounded-md overflow-hidden"
      style={{
        background: "var(--color-bg-card)",
        border: "1px solid var(--color-border)",
        boxShadow: "0 1px 3px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.02)",
      }}
    >
      <div
        className="flex items-center justify-between px-5 py-3"
        style={{ borderBottom: "1px solid var(--color-border)" }}
      >
        <div className="flex items-center gap-2">
          <Scale size={13} className="text-accent-green" />
          <div>
            <h3 className="text-sm font-semibold text-text-primary">Capacity Analysis</h3>
            <p className="text-[10px] text-text-muted mt-0.5">
              Estimated AUM where market impact begins to erode strategy edge
            </p>
          </div>
        </div>
        {!result && (
          <button
            onClick={run}
            disabled={loading}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded transition-all disabled:opacity-40"
            style={{
              background: "rgba(0,212,170,0.1)",
              border: "1px solid rgba(0,212,170,0.2)",
              color: "var(--color-accent-green)",
            }}
          >
            {loading ? <Loader2 size={11} className="animate-spin" /> : <Scale size={11} />}
            {loading ? "Analyzing…" : "Run Analysis"}
          </button>
        )}
      </div>

      <div className="p-5">
        {!result && !loading && !error && (
          <p className="text-xs text-text-muted">
            Computes how many shares each trade represents relative to average daily volume (ADV).
            Estimates the portfolio size at which execution would meaningfully move the market.
          </p>
        )}

        {error && (
          <div
            className="rounded p-3 text-xs"
            style={{
              background: "rgba(255,71,87,0.07)",
              border: "1px solid rgba(255,71,87,0.2)",
              color: "var(--color-accent-red)",
            }}
          >
            {error}
          </div>
        )}

        {loading && (
          <div className="flex items-center gap-2 text-xs text-text-muted">
            <Loader2 size={13} className="animate-spin text-accent-green" />
            Computing ADV participation rates…
          </div>
        )}

        {result && result.message && (
          <p className="text-xs text-text-muted">{result.message}</p>
        )}

        {result && !result.message && (
          <div className="space-y-4">
            {/* ADV participation summary */}
            <div className="grid grid-cols-3 gap-3">
              {[
                { label: "Max ADV Usage", value: `${result.max_adv_participation_pct.toFixed(3)}%`, color: result.max_adv_participation_pct > 5 ? "var(--color-accent-red)" : "var(--color-accent-green)" },
                { label: "Avg ADV Usage", value: `${result.avg_adv_participation_pct.toFixed(3)}%`, color: "var(--color-text-primary)" },
                { label: "P90 ADV Usage", value: `${result.p90_adv_participation_pct.toFixed(3)}%`, color: "var(--color-text-primary)" },
              ].map(({ label, value, color }) => (
                <div
                  key={label}
                  className="rounded p-3 text-center"
                  style={{
                    background: "var(--color-bg-primary)",
                    border: "1px solid var(--color-border)",
                  }}
                >
                  <p className="section-label mb-1">{label}</p>
                  <p className="font-mono font-bold text-sm" style={{ color }}>{value}</p>
                </div>
              ))}
            </div>

            {/* Capacity tiers */}
            <div>
              <p className="section-label mb-2">AUM Capacity Tiers</p>
              <div className="space-y-2">
                {result.capacity_estimates.map((est) => {
                  const isUnlimited = est.capacity_aum === null || est.capacity_aum > 1e10;
                  return (
                    <div
                      key={est.adv_threshold_pct}
                      className="flex items-center justify-between rounded p-3"
                      style={{
                        background: "var(--color-bg-primary)",
                        border: "1px solid var(--color-border)",
                      }}
                    >
                      <div>
                        <p className="text-xs text-text-secondary">{est.label}</p>
                        <p className="text-[10px] text-text-muted mt-0.5">
                          {est.adv_threshold_pct}% ADV threshold
                        </p>
                      </div>
                      <p
                        className="font-mono font-bold text-sm"
                        style={{
                          color: isUnlimited
                            ? "var(--color-accent-green)"
                            : est.capacity_aum! > 10_000_000
                            ? "var(--color-accent-blue)"
                            : "var(--color-accent-yellow)",
                        }}
                      >
                        {formatAUM(est.capacity_aum)}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Top impactful trades */}
            {result.trade_adv_stats.length > 0 && (
              <div>
                <p className="section-label mb-2">Highest ADV Impact Trades</p>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs font-mono">
                    <thead>
                      <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
                        {["Ticker", "Date", "Shares", "Notional", "ADV", "ADV %"].map((h, i) => (
                          <th
                            key={h}
                            className={`section-label py-1.5 px-2 font-normal ${i === 0 ? "text-left" : "text-right"}`}
                          >
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.trade_adv_stats.slice(0, 10).map((t, i) => (
                        <tr
                          key={i}
                          style={{ borderBottom: "1px solid rgba(37,37,53,0.5)" }}
                          className="hover:bg-bg-hover transition-colors"
                        >
                          <td className="py-1.5 px-2 text-text-secondary">{t.ticker}</td>
                          <td className="py-1.5 px-2 text-right text-text-muted text-[10px]">{t.date}</td>
                          <td className="py-1.5 px-2 text-right tabular-nums text-text-primary">{t.shares.toLocaleString()}</td>
                          <td className="py-1.5 px-2 text-right tabular-nums text-text-primary">{formatAUM(t.notional)}</td>
                          <td className="py-1.5 px-2 text-right tabular-nums text-text-muted">{formatAUM(t.adv)}</td>
                          <td
                            className="py-1.5 px-2 text-right tabular-nums font-semibold"
                            style={{
                              color:
                                t.adv_participation_pct > 5
                                  ? "var(--color-accent-red)"
                                  : t.adv_participation_pct > 1
                                  ? "var(--color-accent-yellow)"
                                  : "var(--color-accent-green)",
                            }}
                          >
                            {t.adv_participation_pct.toFixed(3)}%
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
