"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { RegimeAnalysisResult } from "@/lib/types";
import { Loader2, BarChart3 } from "lucide-react";
import { formatPercent, formatRatio } from "@/lib/formatters";

interface RegimeAnalysisProps {
  backtestId: string;
}

export function RegimeAnalysis({ backtestId }: RegimeAnalysisProps) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<RegimeAnalysisResult | null>(null);
  const [error, setError] = useState("");

  const run = async () => {
    setError("");
    setLoading(true);
    try {
      const res = await api.getRegimeAnalysis(backtestId);
      setResult(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Regime analysis failed");
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
          <BarChart3 size={13} className="text-accent-yellow" />
          <div>
            <h3 className="text-sm font-semibold text-text-primary">Regime Analysis</h3>
            <p className="text-[10px] text-text-muted mt-0.5">
              Performance breakdown by market regime (ADX + rolling volatility)
            </p>
          </div>
        </div>
        {!result && (
          <button
            onClick={run}
            disabled={loading}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded transition-all disabled:opacity-40"
            style={{
              background: "rgba(255,204,68,0.1)",
              border: "1px solid rgba(255,204,68,0.2)",
              color: "var(--color-accent-yellow)",
            }}
          >
            {loading ? <Loader2 size={11} className="animate-spin" /> : <BarChart3 size={11} />}
            {loading ? "Analyzing…" : "Run Analysis"}
          </button>
        )}
      </div>

      <div className="p-5">
        {!result && !loading && !error && (
          <p className="text-xs text-text-muted">
            Classifies each trading day into Trending, Choppy, High Volatility, or Neutral using
            ADX (14-period) and rolling 21-day volatility on the benchmark.
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
            <Loader2 size={13} className="animate-spin text-accent-yellow" />
            Computing regime classifications…
          </div>
        )}

        {result && (
          <div className="space-y-4">
            {/* Regime bars (visual proportion) */}
            <div>
              <p className="section-label mb-2">Period Composition</p>
              <div className="flex h-4 rounded overflow-hidden w-full">
                {result.regime_stats.map((s) => (
                  <div
                    key={s.regime}
                    style={{
                      width: `${s.pct_of_period}%`,
                      background: s.color,
                      opacity: 0.8,
                    }}
                    title={`${s.regime}: ${s.pct_of_period}%`}
                  />
                ))}
              </div>
              <div className="flex flex-wrap gap-3 mt-2">
                {result.regime_stats.map((s) => (
                  <div key={s.regime} className="flex items-center gap-1.5">
                    <div
                      className="w-2.5 h-2.5 rounded-sm"
                      style={{ background: s.color, opacity: 0.8 }}
                    />
                    <span className="text-[10px] text-text-muted">
                      {s.regime} ({s.pct_of_period}%)
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Per-regime stats table */}
            <table className="w-full text-xs font-mono">
              <thead>
                <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
                  {["Regime", "Days", "Ann. Return", "Volatility", "Sharpe"].map((h, i) => (
                    <th
                      key={h}
                      className={`section-label py-2 px-3 font-normal ${i === 0 ? "text-left" : "text-right"}`}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.regime_stats.map((s) => (
                  <tr
                    key={s.regime}
                    className="hover:bg-bg-hover transition-colors"
                    style={{ borderBottom: "1px solid rgba(37,37,53,0.5)" }}
                  >
                    <td className="py-2 px-3">
                      <div className="flex items-center gap-2">
                        <div
                          className="w-2 h-2 rounded-full"
                          style={{ background: s.color }}
                        />
                        <span className="text-text-secondary">{s.regime}</span>
                      </div>
                    </td>
                    <td className="py-2 px-3 text-right tabular-nums text-text-muted">
                      {s.days}
                    </td>
                    <td
                      className="py-2 px-3 text-right tabular-nums font-semibold"
                      style={{
                        color:
                          s.ann_return_pct >= 0
                            ? "var(--color-accent-green)"
                            : "var(--color-accent-red)",
                      }}
                    >
                      {formatPercent(s.ann_return_pct)}
                    </td>
                    <td className="py-2 px-3 text-right tabular-nums text-text-muted">
                      {formatPercent(s.ann_volatility_pct)}
                    </td>
                    <td
                      className="py-2 px-3 text-right tabular-nums"
                      style={{
                        color:
                          s.sharpe >= 1
                            ? "var(--color-accent-green)"
                            : s.sharpe >= 0
                            ? "var(--color-text-secondary)"
                            : "var(--color-accent-red)",
                      }}
                    >
                      {formatRatio(s.sharpe)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <p className="text-[10px] text-text-muted leading-relaxed italic">
              {result.description}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
