"use client";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from "recharts";
import type { TimeSeriesPoint } from "@/lib/types";
import { formatCompactDate } from "@/lib/formatters";
import { CHART_COLORS } from "@/lib/constants";

interface RollingMetricsProps {
  data: TimeSeriesPoint[];
  label: string;
  color?: string;
  height?: number;
  unit?: string;
}

export function RollingMetrics({
  data,
  label,
  color = CHART_COLORS.blue,
  height = 200,
  unit = "",
}: RollingMetricsProps) {
  return (
    <div>
      <h3 className="text-sm font-medium text-text-secondary mb-2">{label}</h3>
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
          <XAxis
            dataKey="date"
            tickFormatter={formatCompactDate}
            stroke={CHART_COLORS.axis}
            tick={{ fontSize: 11 }}
            minTickGap={50}
          />
          <YAxis
            tickFormatter={(v) => `${v.toFixed(1)}${unit}`}
            stroke={CHART_COLORS.axis}
            tick={{ fontSize: 11 }}
            width={50}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: CHART_COLORS.tooltip,
              border: `1px solid ${CHART_COLORS.grid}`,
              borderRadius: 4,
              fontSize: 12,
            }}
            formatter={(value) => [
              `${Number(value).toFixed(3)}${unit}`,
              label,
            ]}
            labelFormatter={(label) => formatCompactDate(String(label))}
          />
          <ReferenceLine y={0} stroke={CHART_COLORS.axis} strokeDasharray="3 3" />
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={1.5}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
