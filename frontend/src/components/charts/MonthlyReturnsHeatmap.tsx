"use client";

import type { MonthlyReturn } from "@/lib/types";
import { MONTH_LABELS } from "@/lib/constants";

interface MonthlyReturnsHeatmapProps {
  data: MonthlyReturn[];
}

function getColor(value: number): string {
  if (value > 5) return "bg-accent-green/80 text-white";
  if (value > 2) return "bg-accent-green/50 text-white";
  if (value > 0) return "bg-accent-green/20 text-accent-green";
  if (value === 0) return "bg-bg-hover text-text-muted";
  if (value > -2) return "bg-accent-red/20 text-accent-red";
  if (value > -5) return "bg-accent-red/50 text-white";
  return "bg-accent-red/80 text-white";
}

export function MonthlyReturnsHeatmap({ data }: MonthlyReturnsHeatmapProps) {
  const years = [...new Set(data.map((d) => d.year))].sort();
  const byYearMonth = new Map<string, number>();
  data.forEach((d) => {
    byYearMonth.set(`${d.year}-${d.month}`, d.return_pct);
  });

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs font-mono tabular-nums">
        <thead>
          <tr>
            <th className="text-left text-text-muted py-1 px-2 font-normal">
              Year
            </th>
            {MONTH_LABELS.map((m) => (
              <th
                key={m}
                className="text-center text-text-muted py-1 px-1 font-normal"
              >
                {m}
              </th>
            ))}
            <th className="text-center text-text-muted py-1 px-2 font-normal">
              YTD
            </th>
          </tr>
        </thead>
        <tbody>
          {years.map((year) => {
            const yearReturns = Array.from({ length: 12 }, (_, i) => {
              return byYearMonth.get(`${year}-${i + 1}`) ?? null;
            });
            const ytd = yearReturns
              .filter((v): v is number => v !== null)
              .reduce((acc, v) => acc * (1 + v / 100), 1);
            const ytdPct = (ytd - 1) * 100;

            return (
              <tr key={year}>
                <td className="text-text-secondary py-1 px-2">{year}</td>
                {yearReturns.map((val, i) => (
                  <td key={i} className="p-0.5 text-center">
                    {val !== null ? (
                      <span
                        className={`inline-block w-full rounded px-1 py-0.5 ${getColor(val)}`}
                      >
                        {val.toFixed(1)}
                      </span>
                    ) : (
                      <span className="text-text-muted">-</span>
                    )}
                  </td>
                ))}
                <td className="p-0.5 text-center">
                  <span
                    className={`inline-block w-full rounded px-1 py-0.5 font-medium ${getColor(ytdPct)}`}
                  >
                    {ytdPct.toFixed(1)}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
