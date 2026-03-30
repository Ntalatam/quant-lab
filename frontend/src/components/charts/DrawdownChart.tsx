"use client";

import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import type { TimeSeriesPoint } from "@/lib/types";
import { formatCompactDate } from "@/lib/formatters";
import { CHART_COLORS } from "@/lib/constants";

interface DrawdownChartProps {
  data: TimeSeriesPoint[];
  height?: number;
}

export function DrawdownChart({ data, height = 200 }: DrawdownChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
        <defs>
          <linearGradient id="ddGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={CHART_COLORS.negative} stopOpacity={0.4} />
            <stop offset="95%" stopColor={CHART_COLORS.negative} stopOpacity={0} />
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
          tickFormatter={(v) => `${v.toFixed(0)}%`}
          stroke={CHART_COLORS.axis}
          tick={{ fontSize: 11 }}
          width={50}
          domain={["dataMin", 0]}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: CHART_COLORS.tooltip,
            border: `1px solid ${CHART_COLORS.grid}`,
            borderRadius: 4,
            fontSize: 12,
          }}
          formatter={(value) => [`${Number(value).toFixed(2)}%`, "Drawdown"]}
          labelFormatter={(label) => formatCompactDate(String(label))}
        />
        <Area
          type="monotone"
          dataKey="value"
          stroke={CHART_COLORS.negative}
          fill="url(#ddGradient)"
          strokeWidth={1.5}
          dot={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
