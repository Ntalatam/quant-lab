"use client";

import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import type { TimeSeriesPoint } from "@/lib/types";
import { CHART_COLORS } from "@/lib/constants";

interface ReturnsDistributionProps {
  equity: TimeSeriesPoint[];
  height?: number;
}

export function ReturnsDistribution({
  equity,
  height = 250,
}: ReturnsDistributionProps) {
  // Compute daily returns
  const values = equity.map((p) => p.value);
  const returns: number[] = [];
  for (let i = 1; i < values.length; i++) {
    returns.push(((values[i] - values[i - 1]) / values[i - 1]) * 100);
  }

  // Build histogram buckets
  const bucketSize = 0.5;
  const min = Math.floor(Math.min(...returns));
  const max = Math.ceil(Math.max(...returns));
  const buckets: { range: string; count: number; center: number }[] = [];

  for (let b = min; b < max; b += bucketSize) {
    const count = returns.filter((r) => r >= b && r < b + bucketSize).length;
    buckets.push({
      range: `${b.toFixed(1)}`,
      count,
      center: b + bucketSize / 2,
    });
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={buckets} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
        <XAxis
          dataKey="range"
          stroke={CHART_COLORS.axis}
          tick={{ fontSize: 10 }}
          interval="preserveStartEnd"
        />
        <YAxis
          stroke={CHART_COLORS.axis}
          tick={{ fontSize: 11 }}
          width={40}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: CHART_COLORS.tooltip,
            border: `1px solid ${CHART_COLORS.grid}`,
            borderRadius: 4,
            fontSize: 12,
          }}
          formatter={(value) => [Number(value), "Count"]}
          labelFormatter={(label) => `Return: ${label}%`}
        />
        <Bar
          dataKey="count"
          fill={CHART_COLORS.blue}
          opacity={0.7}
          radius={[2, 2, 0, 0]}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}
