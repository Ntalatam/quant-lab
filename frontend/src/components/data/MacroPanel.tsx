"use client";

import { useMemo } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { CHART_COLORS } from "@/lib/constants";
import type {
  EconomicIndicatorCatalogEntry,
  EconomicIndicatorSeries,
} from "@/lib/types";

const SERIES_COLORS = [
  CHART_COLORS.blue,
  CHART_COLORS.strategy,
  CHART_COLORS.yellow,
  CHART_COLORS.purple,
  CHART_COLORS.negative,
];

function formatIndicatorValue(value: number | null, unit: string) {
  if (value == null) return "—";
  if (unit === "%") return `${value.toFixed(2)}%`;
  if (unit === "index") return value.toFixed(1);
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

function normalizeSeries(series: EconomicIndicatorSeries[]) {
  const byDate = new Map<string, Record<string, string | number>>();
  for (const item of series) {
    const firstPoint = item.points[0]?.value;
    if (!firstPoint) continue;
    for (const point of item.points) {
      const entry = byDate.get(point.date) ?? { date: point.date };
      entry[item.id] = Number(((point.value / firstPoint) * 100).toFixed(2));
      byDate.set(point.date, entry);
    }
  }
  return [...byDate.values()].sort((a, b) =>
    String(a.date).localeCompare(String(b.date)),
  );
}

export function MacroPanel({
  catalog,
  selectedIds,
  onToggleIndicator,
  series,
  isLoading,
}: {
  catalog: EconomicIndicatorCatalogEntry[] | undefined;
  selectedIds: string[];
  onToggleIndicator: (seriesId: string) => void;
  series: EconomicIndicatorSeries[] | undefined;
  isLoading: boolean;
}) {
  const normalizedData = useMemo(() => normalizeSeries(series ?? []), [series]);

  return (
    <div className="card p-5 space-y-5">
      <div className="flex flex-col gap-2 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h2 className="text-sm font-semibold text-text-primary">
            Macro Regime Board
          </h2>
          <p className="text-xs text-text-muted mt-1">
            FRED-backed indicators are normalized to 100 at the start of the
            selected window so mixed units remain comparable.
          </p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {(catalog ?? []).map((item) => {
            const active = selectedIds.includes(item.id);
            return (
              <button
                key={item.id}
                onClick={() => onToggleIndicator(item.id)}
                className="px-2.5 py-1 rounded text-[11px] font-medium transition-colors"
                style={{
                  color: active
                    ? "var(--color-accent-blue)"
                    : "var(--color-text-muted)",
                  background: active ? "rgba(68,136,255,0.1)" : "transparent",
                  border: active
                    ? "1px solid rgba(68,136,255,0.25)"
                    : "1px solid var(--color-border)",
                }}
              >
                {item.name}
              </button>
            );
          })}
        </div>
      </div>

      {series && series.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
          {series.map((item, index) => (
            <div
              key={item.id}
              className="rounded p-3"
              style={{
                background: "var(--color-bg-primary)",
                border: "1px solid var(--color-border)",
              }}
            >
              <div className="flex items-center justify-between gap-2">
                <div>
                  <p className="section-label">{item.category}</p>
                  <p className="text-sm font-medium text-text-primary mt-1">
                    {item.name}
                  </p>
                </div>
                <span
                  className="w-2.5 h-2.5 rounded-full"
                  style={{
                    background: SERIES_COLORS[index % SERIES_COLORS.length],
                  }}
                />
              </div>
              <p className="text-[22px] mt-3 font-mono tabular-nums text-text-primary">
                {formatIndicatorValue(item.latest_value, item.unit)}
              </p>
              <div className="flex items-center justify-between mt-2 text-[11px]">
                <span className="text-text-muted">
                  {item.latest_date ?? "No recent print"}
                </span>
                {item.change_pct != null && (
                  <span
                    className={
                      item.change_pct >= 0
                        ? "text-accent-green"
                        : "text-accent-red"
                    }
                  >
                    {item.change_pct >= 0 ? "+" : ""}
                    {item.change_pct.toFixed(2)}%
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="h-[320px]">
        {isLoading ? (
          <div className="h-full flex items-center justify-center text-sm text-text-muted">
            Loading macro series…
          </div>
        ) : normalizedData.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={normalizedData}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.18} />
              <XAxis dataKey="date" minTickGap={28} />
              <YAxis
                domain={["auto", "auto"]}
                tickFormatter={(value: number) => `${value.toFixed(0)}`}
              />
              <Tooltip
                contentStyle={{
                  background: "var(--color-bg-card)",
                  border: "1px solid var(--color-border)",
                  borderRadius: 6,
                }}
              />
              <Legend />
              {(series ?? []).map((item, index) => (
                <Line
                  key={item.id}
                  type="monotone"
                  dataKey={item.id}
                  name={item.name}
                  stroke={SERIES_COLORS[index % SERIES_COLORS.length]}
                  dot={false}
                  strokeWidth={2}
                  isAnimationActive={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-full flex items-center justify-center text-sm text-text-muted">
            Select at least one macro indicator to chart.
          </div>
        )}
      </div>
    </div>
  );
}
