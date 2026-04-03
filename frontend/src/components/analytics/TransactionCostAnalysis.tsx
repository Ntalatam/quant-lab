"use client";

import { useEffect, useState } from "react";
import { Loader2, ReceiptText } from "lucide-react";

import { api } from "@/lib/api";
import type { TransactionCostAnalysisResult } from "@/lib/types";
import { formatCurrency } from "@/lib/formatters";

interface TransactionCostAnalysisProps {
  backtestId: string;
}

function shareOfTotal(value: number, total: number) {
  if (total <= 0) return 0;
  return (value / total) * 100;
}

export function TransactionCostAnalysis({
  backtestId,
}: TransactionCostAnalysisProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [result, setResult] = useState<TransactionCostAnalysisResult | null>(null);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      setError("");
      try {
        const response = await api.getTransactionCostAnalysis(backtestId);
        if (!cancelled) {
          setResult(response);
        }
      } catch (err: unknown) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Transaction cost analysis failed"
          );
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, [backtestId]);

  return (
    <div
      className="rounded-md overflow-hidden"
      style={{
        background: "var(--color-bg-card)",
        border: "1px solid var(--color-border)",
        boxShadow:
          "0 1px 3px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.02)",
      }}
    >
      <div
        className="flex items-center justify-between px-5 py-3"
        style={{ borderBottom: "1px solid var(--color-border)" }}
      >
        <div className="flex items-center gap-2">
          <ReceiptText size={13} className="text-accent-yellow" />
          <div>
            <h3 className="text-sm font-semibold text-text-primary">
              Transaction Cost Analysis
            </h3>
            <p className="text-[10px] text-text-muted mt-0.5">
              Spread, impact, timing, and missed-fill attribution for each fill
            </p>
          </div>
        </div>
        {result?.model?.market_impact_model && (
          <div className="text-right text-[10px] font-mono text-text-muted">
            <div>{result.model.market_impact_model}</div>
            <div>{result.model.max_volume_participation_pct}% max volume</div>
          </div>
        )}
      </div>

      <div className="p-5">
        {loading && (
          <div className="flex items-center gap-2 text-xs text-text-muted">
            <Loader2 size={13} className="animate-spin text-accent-yellow" />
            Running execution attribution analysis…
          </div>
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

        {result?.message && (
          <p className="text-xs text-text-muted">{result.message}</p>
        )}

        {result && !result.message && (
          <div className="space-y-5">
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
              {[
                {
                  label: "Shortfall",
                  value: formatCurrency(
                    result.summary.total_implementation_shortfall
                  ),
                  color: "var(--color-accent-red)",
                },
                {
                  label: "Spread",
                  value: formatCurrency(result.summary.total_spread_cost),
                  color: "var(--color-accent-yellow)",
                },
                {
                  label: "Impact",
                  value: formatCurrency(
                    result.summary.total_market_impact_cost
                  ),
                  color: "var(--color-accent-blue)",
                },
                {
                  label: "Timing",
                  value: formatCurrency(result.summary.total_timing_cost),
                  color: "var(--color-accent-purple)",
                },
                {
                  label: "Opportunity",
                  value: formatCurrency(result.summary.total_opportunity_cost),
                  color: "var(--color-accent-red)",
                },
                {
                  label: "Fill Rate",
                  value: `${result.summary.avg_fill_rate_pct.toFixed(1)}%`,
                  color: "var(--color-accent-green)",
                },
              ].map((item) => (
                <div
                  key={item.label}
                  className="rounded p-3 text-center"
                  style={{
                    background: "var(--color-bg-primary)",
                    border: "1px solid var(--color-border)",
                  }}
                >
                  <p className="section-label mb-1">{item.label}</p>
                  <p
                    className="font-mono tabular-nums font-semibold text-sm"
                    style={{ color: item.color }}
                  >
                    {item.value}
                  </p>
                </div>
              ))}
            </div>

            <div>
              <p className="section-label mb-2">Cost Mix</p>
              <div
                className="overflow-hidden rounded h-3"
                style={{
                  background: "var(--color-bg-primary)",
                  border: "1px solid var(--color-border)",
                }}
              >
                {[
                  {
                    key: "spread",
                    color: "var(--color-accent-yellow)",
                    width: shareOfTotal(
                      result.summary.total_spread_cost,
                      result.summary.total_implementation_shortfall
                    ),
                  },
                  {
                    key: "impact",
                    color: "var(--color-accent-blue)",
                    width: shareOfTotal(
                      result.summary.total_market_impact_cost,
                      result.summary.total_implementation_shortfall
                    ),
                  },
                  {
                    key: "timing",
                    color: "var(--color-accent-purple)",
                    width: shareOfTotal(
                      result.summary.total_timing_cost,
                      result.summary.total_implementation_shortfall
                    ),
                  },
                  {
                    key: "opportunity",
                    color: "var(--color-accent-red)",
                    width: shareOfTotal(
                      result.summary.total_opportunity_cost,
                      result.summary.total_implementation_shortfall
                    ),
                  },
                ]
                  .filter((item) => item.width > 0)
                  .map((item) => (
                    <div
                      key={item.key}
                      className="h-full inline-block align-top"
                      style={{ width: `${item.width}%`, background: item.color }}
                    />
                  ))}
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-2 text-[10px]">
                {[
                  [
                    "Spread",
                    result.summary.total_spread_cost,
                    "var(--color-accent-yellow)",
                  ],
                  [
                    "Impact",
                    result.summary.total_market_impact_cost,
                    "var(--color-accent-blue)",
                  ],
                  [
                    "Timing",
                    result.summary.total_timing_cost,
                    "var(--color-accent-purple)",
                  ],
                  [
                    "Opportunity",
                    result.summary.total_opportunity_cost,
                    "var(--color-accent-red)",
                  ],
                ].map(([label, value, color]) => (
                  <div key={String(label)} className="flex items-center gap-2">
                    <span
                      className="inline-block h-2 w-2 rounded-full"
                      style={{ background: String(color) }}
                    />
                    <span className="text-text-muted">
                      {label}: {formatCurrency(Number(value))}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div
                className="rounded p-3"
                style={{
                  background: "var(--color-bg-primary)",
                  border: "1px solid var(--color-border)",
                }}
              >
                <p className="section-label mb-1">Avg Participation</p>
                <p className="font-mono text-sm text-text-primary">
                  {result.summary.avg_participation_rate_pct.toFixed(3)}%
                </p>
              </div>
              <div
                className="rounded p-3"
                style={{
                  background: "var(--color-bg-primary)",
                  border: "1px solid var(--color-border)",
                }}
              >
                <p className="section-label mb-1">P90 Participation</p>
                <p className="font-mono text-sm text-text-primary">
                  {result.summary.p90_participation_rate_pct.toFixed(3)}%
                </p>
              </div>
              <div
                className="rounded p-3"
                style={{
                  background: "var(--color-bg-primary)",
                  border: "1px solid var(--color-border)",
                }}
              >
                <p className="section-label mb-1">Borrow + Locate</p>
                <p className="font-mono text-sm text-text-primary">
                  {formatCurrency(
                    result.summary.total_borrow_cost +
                      result.summary.total_locate_fees
                  )}
                </p>
              </div>
              <div
                className="rounded p-3"
                style={{
                  background: "var(--color-bg-primary)",
                  border: "1px solid var(--color-border)",
                }}
              >
                <p className="section-label mb-1">Capital Drag</p>
                <p className="font-mono text-sm text-text-primary">
                  {result.summary.cost_as_pct_of_initial_capital.toFixed(3)}%
                </p>
              </div>
            </div>

            <div>
              <p className="section-label mb-2">Most Expensive Fills</p>
              <div className="overflow-x-auto">
                <table className="w-full text-xs font-mono">
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
                      {[
                        "Ticker",
                        "Date",
                        "Side",
                        "Fill %",
                        "Part %",
                        "Spread",
                        "Impact",
                        "Timing",
                        "Opp",
                        "Shortfall",
                      ].map((header, index) => (
                        <th
                          key={header}
                          className={`section-label py-1.5 px-2 font-normal ${
                            index === 0 ? "text-left" : "text-right"
                          }`}
                        >
                          {header}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.top_cost_trades.map((trade) => (
                      <tr
                        key={trade.id}
                        style={{
                          borderBottom: "1px solid rgba(37,37,53,0.5)",
                        }}
                      >
                        <td className="py-1.5 px-2 text-text-secondary">
                          {trade.ticker}
                        </td>
                        <td className="py-1.5 px-2 text-right text-text-muted">
                          {trade.date}
                        </td>
                        <td className="py-1.5 px-2 text-right text-text-primary">
                          {trade.position_direction === "SHORT" && trade.side === "SELL"
                            ? "SHORT"
                            : trade.position_direction === "SHORT"
                              ? "COVER"
                              : trade.side}
                        </td>
                        <td className="py-1.5 px-2 text-right text-text-primary">
                          {trade.fill_rate_pct.toFixed(1)}%
                        </td>
                        <td className="py-1.5 px-2 text-right text-text-primary">
                          {trade.participation_rate_pct.toFixed(3)}%
                        </td>
                        <td className="py-1.5 px-2 text-right text-text-primary">
                          {formatCurrency(trade.spread_cost)}
                        </td>
                        <td className="py-1.5 px-2 text-right text-text-primary">
                          {formatCurrency(trade.market_impact_cost)}
                        </td>
                        <td className="py-1.5 px-2 text-right text-text-primary">
                          {formatCurrency(trade.timing_cost)}
                        </td>
                        <td className="py-1.5 px-2 text-right text-text-primary">
                          {formatCurrency(trade.opportunity_cost)}
                        </td>
                        <td className="py-1.5 px-2 text-right text-accent-red">
                          {formatCurrency(trade.implementation_shortfall)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div>
              <p className="section-label mb-2">Ticker Attribution</p>
              <div className="overflow-x-auto">
                <table className="w-full text-xs font-mono">
                  <thead>
                    <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
                      {[
                        "Ticker",
                        "Trades",
                        "Fill %",
                        "Part %",
                        "Impact",
                        "Timing",
                        "Opp",
                        "Shortfall",
                      ].map((header, index) => (
                        <th
                          key={header}
                          className={`section-label py-1.5 px-2 font-normal ${
                            index === 0 ? "text-left" : "text-right"
                          }`}
                        >
                          {header}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.ticker_breakdown.map((row) => (
                      <tr
                        key={row.ticker}
                        style={{
                          borderBottom: "1px solid rgba(37,37,53,0.5)",
                        }}
                      >
                        <td className="py-1.5 px-2 text-text-secondary">
                          {row.ticker}
                        </td>
                        <td className="py-1.5 px-2 text-right text-text-primary">
                          {row.trades}
                        </td>
                        <td className="py-1.5 px-2 text-right text-text-primary">
                          {row.avg_fill_rate_pct.toFixed(1)}%
                        </td>
                        <td className="py-1.5 px-2 text-right text-text-primary">
                          {row.avg_participation_rate_pct.toFixed(3)}%
                        </td>
                        <td className="py-1.5 px-2 text-right text-text-primary">
                          {formatCurrency(row.total_market_impact_cost)}
                        </td>
                        <td className="py-1.5 px-2 text-right text-text-primary">
                          {formatCurrency(row.total_timing_cost)}
                        </td>
                        <td className="py-1.5 px-2 text-right text-text-primary">
                          {formatCurrency(row.total_opportunity_cost)}
                        </td>
                        <td className="py-1.5 px-2 text-right text-accent-red">
                          {formatCurrency(row.total_implementation_shortfall)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
