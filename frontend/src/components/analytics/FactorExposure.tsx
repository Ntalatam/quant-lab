"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import type { FactorExposureResult } from "@/lib/types";
import { Loader2, FlaskConical } from "lucide-react";

interface FactorExposureProps {
  backtestId: string;
}

const FACTOR_COLORS: Record<string, string> = {
  Market:   "var(--color-accent-blue)",
  Size:     "var(--color-accent-yellow)",
  Value:    "var(--color-accent-green)",
  Momentum: "var(--color-accent-purple, #a78bfa)",
};

export function FactorExposure({ backtestId }: FactorExposureProps) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<FactorExposureResult | null>(null);
  const [error, setError] = useState("");

  const run = async () => {
    setError("");
    setLoading(true);
    try {
      const res = await api.getFactorExposure(backtestId);
      setResult(res);
    } catch (e: unknown) {
      setError(
        e instanceof Error
          ? e.message
          : "Factor analysis failed. Ensure SPY, IWM, VTV, MTUM are loaded in the Data page."
      );
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
          <FlaskConical size={13} className="text-accent-blue" />
          <div>
            <h3 className="text-sm font-semibold text-text-primary">Factor Exposure</h3>
            <p className="text-[10px] text-text-muted mt-0.5">
              Multi-factor regression: Market · Size · Value · Momentum
            </p>
          </div>
        </div>
        {!result && (
          <button
            onClick={run}
            disabled={loading}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded transition-all disabled:opacity-40"
            style={{
              background: "rgba(68,136,255,0.1)",
              border: "1px solid rgba(68,136,255,0.2)",
              color: "var(--color-accent-blue)",
            }}
          >
            {loading ? <Loader2 size={11} className="animate-spin" /> : <FlaskConical size={11} />}
            {loading ? "Analyzing…" : "Run Analysis"}
          </button>
        )}
      </div>

      <div className="p-5">
        {!result && !loading && !error && (
          <p className="text-xs text-text-muted">
            Requires SPY, IWM, VTV, and MTUM to be loaded in the Data page for the same date range.
            This decomposes strategy returns into systematic factor contributions.
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
            <Loader2 size={13} className="animate-spin text-accent-blue" />
            Running factor regression…
          </div>
        )}

        {result && (
          <div className="space-y-4">
            {/* Summary metrics */}
            <div className="grid grid-cols-3 gap-3">
              <div
                className="rounded p-3 text-center"
                style={{ background: "var(--color-bg-primary)", border: "1px solid var(--color-border)" }}
              >
                <p className="section-label mb-1">Annualized Alpha</p>
                <p
                  className="font-mono font-bold text-base"
                  style={{
                    color:
                      result.alpha_annualized >= 0
                        ? "var(--color-accent-green)"
                        : "var(--color-accent-red)",
                  }}
                >
                  {result.alpha_annualized >= 0 ? "+" : ""}
                  {result.alpha_annualized.toFixed(2)}%
                </p>
              </div>
              <div
                className="rounded p-3 text-center"
                style={{ background: "var(--color-bg-primary)", border: "1px solid var(--color-border)" }}
              >
                <p className="section-label mb-1">R-Squared</p>
                <p className="font-mono font-bold text-base text-accent-blue">
                  {(result.r_squared * 100).toFixed(1)}%
                </p>
              </div>
              <div
                className="rounded p-3 text-center"
                style={{ background: "var(--color-bg-primary)", border: "1px solid var(--color-border)" }}
              >
                <p className="section-label mb-1">Observations</p>
                <p className="font-mono font-bold text-base text-text-primary">
                  {result.n_obs}d
                </p>
              </div>
            </div>

            {/* Factor betas */}
            <table className="w-full text-xs font-mono">
              <thead>
                <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
                  {["Factor", "Beta", "t-Stat", "p-Value", ""].map((h, i) => (
                    <th
                      key={h || i}
                      className={`section-label py-2 px-3 font-normal ${i === 0 ? "text-left" : "text-right"}`}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.factors.map((f) => (
                  <tr
                    key={f.name}
                    className="hover:bg-bg-hover transition-colors"
                    style={{ borderBottom: "1px solid rgba(37,37,53,0.5)" }}
                  >
                    <td className="py-2 px-3">
                      <div className="flex items-center gap-2">
                        <div
                          className="w-2 h-2 rounded-full"
                          style={{ background: FACTOR_COLORS[f.name] ?? "var(--color-text-muted)" }}
                        />
                        <span className="text-text-secondary">{f.name}</span>
                      </div>
                    </td>
                    <td
                      className="py-2 px-3 text-right tabular-nums font-semibold"
                      style={{
                        color: FACTOR_COLORS[f.name] ?? "var(--color-text-primary)",
                      }}
                    >
                      {f.beta.toFixed(3)}
                    </td>
                    <td className="py-2 px-3 text-right tabular-nums text-text-secondary">
                      {f.t_stat.toFixed(2)}
                    </td>
                    <td className="py-2 px-3 text-right tabular-nums text-text-muted">
                      {f.p_value < 0.001 ? "<0.001" : f.p_value.toFixed(3)}
                    </td>
                    <td className="py-2 px-3 text-right">
                      {f.significant ? (
                        <span
                          className="text-[10px] px-1.5 py-0.5 rounded"
                          style={{
                            background: "rgba(0,212,170,0.12)",
                            color: "var(--color-accent-green)",
                            border: "1px solid rgba(0,212,170,0.25)",
                          }}
                        >
                          sig
                        </span>
                      ) : (
                        <span className="text-[10px] text-text-muted">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <p className="text-[10px] text-text-muted leading-relaxed">
              R² = {(result.r_squared * 100).toFixed(1)}% of variance explained by factors.{" "}
              {result.r_squared < 0.3
                ? "Low R² — strategy returns are largely idiosyncratic (alpha-driven)."
                : result.r_squared > 0.7
                ? "High R² — returns are closely explained by systematic factors."
                : "Moderate R² — mixed systematic and idiosyncratic contribution."}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
