"use client";

import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from "recharts";
import type { TimeSeriesPoint } from "@/lib/types";
import { formatCurrency, formatCompactDate } from "@/lib/formatters";
import { CHART_COLORS } from "@/lib/constants";

interface EquityCurveProps {
  equity: TimeSeriesPoint[];
  benchmark: TimeSeriesPoint[];
  height?: number;
}

export function EquityCurve({
  equity,
  benchmark,
  height = 350,
}: EquityCurveProps) {
  // Merge equity and benchmark by date
  const dateMap = new Map<string, { date: string; equity: number; benchmark: number }>();

  equity.forEach((p) => {
    dateMap.set(p.date, { date: p.date, equity: p.value, benchmark: 0 });
  });

  benchmark.forEach((p) => {
    const existing = dateMap.get(p.date);
    if (existing) {
      existing.benchmark = p.value;
    } else {
      dateMap.set(p.date, { date: p.date, equity: 0, benchmark: p.value });
    }
  });

  const data = Array.from(dateMap.values()).sort(
    (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
  );

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={data} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
        <defs>
          <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={CHART_COLORS.strategy} stopOpacity={0.3} />
            <stop offset="95%" stopColor={CHART_COLORS.strategy} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
        <XAxis
          dataKey="date"
          tickFormatter={formatCompactDate}
          stroke={CHART_COLORS.axis}
          tick={{ fontSize: 11 }}
          minTickGap={50}
        />
        <YAxis
          tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
          stroke={CHART_COLORS.axis}
          tick={{ fontSize: 11 }}
          width={60}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: CHART_COLORS.tooltip,
            border: `1px solid ${CHART_COLORS.grid}`,
            borderRadius: 4,
            fontSize: 12,
          }}
          formatter={(value, name) => [
            formatCurrency(Number(value)),
            name === "equity" ? "Strategy" : "Benchmark",
          ]}
          labelFormatter={(label) => formatCompactDate(String(label))}
        />
        <Legend
          formatter={(value) =>
            value === "equity" ? "Strategy" : "Benchmark"
          }
        />
        <Area
          type="monotone"
          dataKey="equity"
          stroke={CHART_COLORS.strategy}
          fill="url(#equityGradient)"
          strokeWidth={2}
          dot={false}
        />
        <Line
          type="monotone"
          dataKey="benchmark"
          stroke={CHART_COLORS.benchmark}
          strokeWidth={1.5}
          dot={false}
          strokeDasharray="4 3"
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}
