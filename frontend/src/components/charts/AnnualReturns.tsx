"use client";

import type { TimeSeriesPoint } from "@/lib/types";

interface AnnualReturnsProps {
  equity: TimeSeriesPoint[];
  benchmark: TimeSeriesPoint[];
}

interface AnnualRow {
  year: number;
  stratReturn: number;
  benchReturn: number;
  excess: number;
  beat: boolean;
}

function groupByYear(series: TimeSeriesPoint[]): Map<number, TimeSeriesPoint[]> {
  const map = new Map<number, TimeSeriesPoint[]>();
  for (const pt of series) {
    // Parse year directly from ISO string to avoid UTC→local timezone shifts
    const yr = parseInt(pt.date.slice(0, 4), 10);
    if (!map.has(yr)) map.set(yr, []);
    map.get(yr)!.push(pt);
  }
  return map;
}

function annualReturn(pts: TimeSeriesPoint[]): number {
  if (pts.length < 2) return 0;
  const sorted = [...pts].sort((a, b) => a.date.localeCompare(b.date));
  return (sorted[sorted.length - 1].value / sorted[0].value - 1) * 100;
}

function formatPct(v: number): string {
  const sign = v >= 0 ? "+" : "";
  return `${sign}${v.toFixed(2)}%`;
}

export function AnnualReturns({ equity, benchmark }: AnnualReturnsProps) {
  if (!equity.length) return null;

  const stratByYear = groupByYear(equity);
  const benchByYear = groupByYear(benchmark);

  const years = Array.from(stratByYear.keys()).sort((a, b) => a - b);

  const rows: AnnualRow[] = years.map((yr) => {
    const s = annualReturn(stratByYear.get(yr) ?? []);
    const b = annualReturn(benchByYear.get(yr) ?? []);
    return { year: yr, stratReturn: s, benchReturn: b, excess: s - b, beat: s > b };
  });

  const wins = rows.filter((r) => r.beat).length;
  const total = rows.length;

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
        <div>
          <h3 className="text-sm font-semibold text-text-primary">Annual Performance</h3>
          <p className="text-[10px] text-text-muted mt-0.5">
            Year-by-year returns vs benchmark
          </p>
        </div>
        <div className="text-right">
          <p className="text-xs font-mono text-text-primary">
            Beat benchmark{" "}
            <span
              className="font-bold"
              style={{ color: wins / total >= 0.5 ? "var(--color-accent-green)" : "var(--color-accent-red)" }}
            >
              {wins}/{total}
            </span>{" "}
            years
          </p>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs font-mono">
          <thead>
            <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
              {["Year", "Strategy", "Benchmark", "Excess", ""].map((h, i) => (
                <th
                  key={h || i}
                  className={`section-label py-2.5 px-4 font-normal ${
                    i === 0 ? "text-left" : "text-right"
                  }`}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={row.year}
                className="hover:bg-bg-hover transition-colors"
                style={{ borderBottom: "1px solid rgba(37,37,53,0.5)" }}
              >
                <td className="py-2 px-4 text-text-secondary font-semibold">{row.year}</td>
                <td
                  className="py-2 px-4 text-right tabular-nums font-semibold"
                  style={{
                    color:
                      row.stratReturn >= 0
                        ? "var(--color-accent-green)"
                        : "var(--color-accent-red)",
                  }}
                >
                  {formatPct(row.stratReturn)}
                </td>
                <td className="py-2 px-4 text-right tabular-nums text-text-muted">
                  {formatPct(row.benchReturn)}
                </td>
                <td
                  className="py-2 px-4 text-right tabular-nums"
                  style={{
                    color:
                      row.excess > 0
                        ? "var(--color-accent-green)"
                        : "var(--color-accent-red)",
                  }}
                >
                  {formatPct(row.excess)}
                </td>
                <td className="py-2 px-4 text-right">
                  {row.beat ? (
                    <span
                      className="text-[10px] px-1.5 py-0.5 rounded"
                      style={{
                        background: "rgba(0,212,170,0.12)",
                        color: "var(--color-accent-green)",
                        border: "1px solid rgba(0,212,170,0.25)",
                      }}
                    >
                      ✓
                    </span>
                  ) : (
                    <span
                      className="text-[10px] px-1.5 py-0.5 rounded"
                      style={{
                        background: "rgba(255,71,87,0.1)",
                        color: "var(--color-accent-red)",
                        border: "1px solid rgba(255,71,87,0.2)",
                      }}
                    >
                      ✗
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
