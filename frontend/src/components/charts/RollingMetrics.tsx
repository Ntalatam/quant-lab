"use client";

import { useState, useCallback } from "react";
import type { TimeSeriesPoint } from "@/lib/types";
import { CHART_COLORS } from "@/lib/constants";
import {
  LightweightChart,
  AreaSeries,
  LineSeries,
  toTime,
  type IChartApi,
  type MouseEventParams,
  type Time,
  type LogicalRange,
} from "./LightweightChartWrapper";
import type { SingleValueData } from "lightweight-charts";

interface RollingMetricsProps {
  data: TimeSeriesPoint[];
  label: string;
  color?: string;
  height?: number;
  unit?: string;
  syncRange?: LogicalRange | null;
  onVisibleRangeChange?: (range: LogicalRange | null) => void;
}

export function RollingMetrics({
  data,
  label,
  color = CHART_COLORS.blue,
  height = 200,
  unit = "",
  syncRange,
  onVisibleRangeChange,
}: RollingMetricsProps) {
  const [currentValue, setCurrentValue] = useState<number | null>(null);

  const handleInit = useCallback(
    (chart: IChartApi) => {
      const series = chart.addSeries(AreaSeries, {
        lineColor: color,
        topColor: `${color}22`,
        bottomColor: `${color}04`,
        lineWidth: 1,
        priceFormat: {
          type: "custom",
          formatter: (v: number) => `${v.toFixed(2)}${unit}`,
        },
        crosshairMarkerRadius: 3,
        crosshairMarkerBackgroundColor: color,
      });

      const seriesData: SingleValueData<Time>[] = data.map((p) => ({
        time: toTime(p.date),
        value: p.value,
      }));
      series.setData(seriesData);

      // Zero baseline
      const baseline = chart.addSeries(LineSeries, {
        color: "rgba(85,85,102,0.4)",
        lineWidth: 1,
        lineStyle: 2,
        priceFormat: { type: "custom", formatter: () => "" },
        crosshairMarkerVisible: false,
        lastValueVisible: false,
        priceLineVisible: false,
      });
      baseline.setData(
        data.length > 0
          ? [
              { time: toTime(data[0].date), value: 0 },
              { time: toTime(data[data.length - 1].date), value: 0 },
            ]
          : [],
      );

      if (data.length > 0) setCurrentValue(data[data.length - 1].value);

      chart.subscribeCrosshairMove((param: MouseEventParams<Time>) => {
        const point = param.seriesData?.get(series) as
          | SingleValueData<Time>
          | undefined;
        if (point) setCurrentValue(point.value);
        else if (data.length > 0) setCurrentValue(data[data.length - 1].value);
      });
    },
    [data, color, unit],
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-medium text-text-secondary">{label}</h3>
        {currentValue != null && (
          <span
            className="text-xs font-mono"
            style={{
              color:
                currentValue > 0
                  ? CHART_COLORS.positive
                  : currentValue < 0
                    ? CHART_COLORS.negative
                    : CHART_COLORS.axis,
            }}
          >
            {currentValue.toFixed(3)}
            {unit}
          </span>
        )}
      </div>
      <div className="relative">
        <LightweightChart
          height={height}
          onInit={handleInit}
          syncRange={syncRange}
          onVisibleRangeChange={onVisibleRangeChange}
        />
      </div>
    </div>
  );
}
