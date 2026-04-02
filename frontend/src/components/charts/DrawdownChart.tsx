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

interface DrawdownChartProps {
  data: TimeSeriesPoint[];
  height?: number;
  syncRange?: LogicalRange | null;
  onVisibleRangeChange?: (range: LogicalRange | null) => void;
}

function DrawdownLegend({ value }: { value: number | null }) {
  if (value == null) return null;
  return (
    <div
      className="absolute top-2 left-3 z-10 flex items-center gap-2 pointer-events-none select-none"
      style={{ fontFamily: "ui-monospace, monospace", fontSize: 11 }}
    >
      <span
        className="inline-block w-2.5 h-0.5 rounded-full"
        style={{ background: CHART_COLORS.negative }}
      />
      <span className="text-text-muted">Drawdown</span>
      <span
        style={{
          color:
            value < -5 ? CHART_COLORS.negative : CHART_COLORS.axis,
        }}
      >
        {value.toFixed(2)}%
      </span>
    </div>
  );
}

export function DrawdownChart({
  data,
  height = 200,
  syncRange,
  onVisibleRangeChange,
}: DrawdownChartProps) {
  const [ddValue, setDdValue] = useState<number | null>(null);

  const handleInit = useCallback(
    (chart: IChartApi) => {
      const series = chart.addSeries(AreaSeries, {
        lineColor: CHART_COLORS.negative,
        topColor: "rgba(255,68,102,0.02)",
        bottomColor: "rgba(255,68,102,0.35)",
        lineWidth: 1,
        priceFormat: {
          type: "custom",
          formatter: (v: number) => `${v.toFixed(1)}%`,
        },
        crosshairMarkerRadius: 3,
        crosshairMarkerBackgroundColor: CHART_COLORS.negative,
        invertFilledArea: true,
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
          : []
      );

      if (data.length > 0) {
        setDdValue(data[data.length - 1].value);
      }

      chart.subscribeCrosshairMove((param: MouseEventParams<Time>) => {
        const point = param.seriesData?.get(series) as
          | SingleValueData<Time>
          | undefined;
        if (point) setDdValue(point.value);
        else if (data.length > 0)
          setDdValue(data[data.length - 1].value);
      });
    },
    [data]
  );

  return (
    <div className="relative">
      <DrawdownLegend value={ddValue} />
      <LightweightChart
        key={data.length}
        height={height}
        onInit={handleInit}
        syncRange={syncRange}
        onVisibleRangeChange={onVisibleRangeChange}
        options={{
          rightPriceScale: {
            scaleMargins: { top: 0.05, bottom: 0.05 },
            invertScale: false,
          },
        }}
      />
    </div>
  );
}
