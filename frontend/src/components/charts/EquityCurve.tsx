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
  cleanEquity?: TimeSeriesPoint[];
  height?: number;
}

export function EquityCurve({
  equity,
  benchmark,
  cleanEquity,
  height = 350,
}: EquityCurveProps) {
  const showClean = cleanEquity && cleanEquity.length > 0;

  // Merge all series by date
  const dateMap = new Map<
    string,
    { date: string; equity: number; benchmark: number; clean?: number }
  >();

  equity.forEach((p) => {
    dateMap.set(p.date, { date: p.date, equity: p.value, benchmark: 0 });
  });

  benchmark.forEach((p) => {
    const ex = dateMap.get(p.date);
    if (ex) ex.benchmark = p.value;
    else dateMap.set(p.date, { date: p.date, equity: 0, benchmark: p.value });
  });

  if (showClean) {
    cleanEquity!.forEach((p) => {
      const ex = dateMap.get(p.date);
      if (ex) ex.clean = p.value;
    });
  }

  const data = Array.from(dateMap.values()).sort(
    (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
  );

  const formatLabel = (name: string) => {
    if (name === "equity") return "Strategy";
    if (name === "clean") return "No-Cost Equity";
    return "Benchmark";
  };

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={data} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
        <defs>
          <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={CHART_COLORS.strategy} stopOpacity={0.25} />
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
          formatter={(value, name) => [formatCurrency(Number(value)), formatLabel(String(name))]}
          labelFormatter={(label) => formatCompactDate(String(label))}
        />
        <Legend formatter={formatLabel} />
        <Area
          type="monotone"
          dataKey="equity"
          stroke={CHART_COLORS.strategy}
          fill="url(#equityGradient)"
          strokeWidth={2}
          dot={false}
        />
        {showClean && (
          <Line
            type="monotone"
            dataKey="clean"
            stroke={CHART_COLORS.blue}
            strokeWidth={1.5}
            dot={false}
            strokeDasharray="5 3"
          />
        )}
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
