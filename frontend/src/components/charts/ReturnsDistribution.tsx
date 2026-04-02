"use client";

import { useMemo, useState } from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Cell,
  ReferenceLine,
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
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  const { buckets, mean, median, stats } = useMemo(() => {
    const values = equity.map((p) => p.value);
    const returns: number[] = [];
    for (let i = 1; i < values.length; i++) {
      returns.push(((values[i] - values[i - 1]) / values[i - 1]) * 100);
    }

    const sorted = [...returns].sort((a, b) => a - b);
    const mean = returns.reduce((a, b) => a + b, 0) / returns.length;
    const median =
      sorted.length % 2 === 0
        ? (sorted[sorted.length / 2 - 1] + sorted[sorted.length / 2]) / 2
        : sorted[Math.floor(sorted.length / 2)];

    // Count negative / positive
    const negCount = returns.filter((r) => r < 0).length;
    const posCount = returns.filter((r) => r > 0).length;

    // Build histogram buckets
    const bucketSize = 0.5;
    const min = Math.floor(Math.min(...returns) / bucketSize) * bucketSize;
    const max = Math.ceil(Math.max(...returns) / bucketSize) * bucketSize;
    const buckets: {
      range: string;
      count: number;
      center: number;
      isNegative: boolean;
    }[] = [];

    for (let b = min; b < max; b += bucketSize) {
      const count = returns.filter((r) => r >= b && r < b + bucketSize).length;
      buckets.push({
        range: `${b.toFixed(1)}`,
        count,
        center: b + bucketSize / 2,
        isNegative: b + bucketSize / 2 < 0,
      });
    }

    return {
      buckets,
      mean,
      median,
      stats: { total: returns.length, negCount, posCount },
    };
  }, [equity]);

  return (
    <div>
      {/* Stats bar */}
      <div className="flex items-center gap-4 mb-2 text-[10px] font-mono">
        <span className="text-text-muted">
          Mean:{" "}
          <span
            style={{
              color:
                mean >= 0 ? CHART_COLORS.positive : CHART_COLORS.negative,
            }}
          >
            {mean >= 0 ? "+" : ""}
            {mean.toFixed(3)}%
          </span>
        </span>
        <span className="text-text-muted">
          Median:{" "}
          <span className="text-text-secondary">
            {median >= 0 ? "+" : ""}
            {median.toFixed(3)}%
          </span>
        </span>
        <span className="text-text-muted">
          <span style={{ color: CHART_COLORS.positive }}>
            {stats.posCount}
          </span>
          {" / "}
          <span style={{ color: CHART_COLORS.negative }}>
            {stats.negCount}
          </span>
          <span className="text-text-muted"> days</span>
        </span>
      </div>

      <ResponsiveContainer width="100%" height={height}>
        <BarChart
          data={buckets}
          margin={{ top: 5, right: 5, bottom: 5, left: 5 }}
          onMouseMove={(state) => {
            if (state?.activeTooltipIndex != null) {
              setHoverIdx(Number(state.activeTooltipIndex));
            }
          }}
          onMouseLeave={() => setHoverIdx(null)}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="rgba(30,30,42,0.5)"
            horizontal
            vertical={false}
          />
          <XAxis
            dataKey="range"
            stroke={CHART_COLORS.axis}
            tick={{ fontSize: 10 }}
            interval="preserveStartEnd"
            axisLine={{ stroke: "rgba(37,37,53,0.8)" }}
          />
          <YAxis
            stroke={CHART_COLORS.axis}
            tick={{ fontSize: 10 }}
            width={35}
            axisLine={{ stroke: "rgba(37,37,53,0.8)" }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#16161f",
              border: "1px solid rgba(37,37,53,0.8)",
              borderRadius: 4,
              fontSize: 11,
              fontFamily: "ui-monospace, monospace",
              padding: "6px 10px",
            }}
            formatter={(value) => [Number(value), "Count"]}
            labelFormatter={(label) => `Return: ${label}%`}
            cursor={{ fill: "rgba(136,136,160,0.06)" }}
          />
          <ReferenceLine
            x={buckets.findIndex((b) => b.center >= 0)?.toString()}
            stroke="rgba(85,85,102,0.3)"
            strokeDasharray="3 3"
          />
          <Bar dataKey="count" radius={[2, 2, 0, 0]} maxBarSize={20}>
            {buckets.map((entry, idx) => (
              <Cell
                key={idx}
                fill={
                  entry.isNegative
                    ? CHART_COLORS.negative
                    : CHART_COLORS.positive
                }
                fillOpacity={hoverIdx === idx ? 0.9 : 0.55}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
