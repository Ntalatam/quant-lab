"use client";

import { useRef, useEffect } from "react";
import {
  createChart,
  createSeriesMarkers,
  CandlestickSeries,
  LineSeries,
  AreaSeries,
  HistogramSeries,
  type IChartApi,
  type ISeriesApi,
  type DeepPartial,
  type ChartOptions,
  type LogicalRange,
  ColorType,
  CrosshairMode,
  type MouseEventParams,
  type Time,
  type SeriesMarker,
} from "lightweight-charts";
import { CHART_COLORS } from "@/lib/constants";

// ── Theme ──────────────────────────────────────────────────────────────

export const TV_CHART_OPTIONS: DeepPartial<ChartOptions> = {
  layout: {
    background: { type: ColorType.Solid, color: "transparent" },
    textColor: CHART_COLORS.axis,
    fontFamily:
      'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
    fontSize: 11,
  },
  grid: {
    vertLines: { color: "rgba(30,30,42,0.6)" },
    horzLines: { color: "rgba(30,30,42,0.6)" },
  },
  crosshair: {
    mode: CrosshairMode.Normal,
    vertLine: {
      color: "rgba(136,136,160,0.4)",
      width: 1,
      style: 3,
      labelBackgroundColor: "#252535",
    },
    horzLine: {
      color: "rgba(136,136,160,0.4)",
      width: 1,
      style: 3,
      labelBackgroundColor: "#252535",
    },
  },
  rightPriceScale: {
    borderColor: "rgba(37,37,53,0.8)",
    scaleMargins: { top: 0.08, bottom: 0.08 },
  },
  timeScale: {
    borderColor: "rgba(37,37,53,0.8)",
    timeVisible: false,
    rightOffset: 4,
    barSpacing: 4,
    minBarSpacing: 1,
    fixLeftEdge: true,
    fixRightEdge: true,
  },
  handleScale: { axisPressedMouseMove: { time: true, price: true } },
  handleScroll: { vertTouchDrag: false },
};

// ── Types ──────────────────────────────────────────────────────────────

export interface LightweightChartProps {
  height?: number;
  options?: DeepPartial<ChartOptions>;
  /** Called once after chart creation. Add series here. */
  onInit: (chart: IChartApi, container: HTMLDivElement) => (() => void) | void;
  /** Optional: subscribe to crosshair move for synced tooltips / legends */
  onCrosshairMove?: (param: MouseEventParams<Time>) => void;
  /** Optional: sync visible range across multiple charts */
  syncRange?: LogicalRange | null;
  onVisibleRangeChange?: (range: LogicalRange | null) => void;
  className?: string;
}

// ── Component ──────────────────────────────────────────────────────────

export function LightweightChart({
  height = 300,
  options,
  onInit,
  onCrosshairMove,
  syncRange,
  onVisibleRangeChange,
  className = "",
}: LightweightChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const isSyncingRef = useRef(false);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const chart = createChart(container, {
      ...TV_CHART_OPTIONS,
      ...options,
      width: container.clientWidth,
      height,
    });
    chartRef.current = chart;

    // Auto-resize
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width } = entry.contentRect;
        if (width > 0) chart.applyOptions({ width });
      }
    });
    ro.observe(container);

    // Crosshair subscription
    if (onCrosshairMove) {
      chart.subscribeCrosshairMove(onCrosshairMove);
    }

    // Visible range sync
    if (onVisibleRangeChange) {
      chart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
        if (!isSyncingRef.current) {
          onVisibleRangeChange(range);
        }
      });
    }

    // Let the consumer add series
    const cleanup = onInit(chart, container);

    // Fit content after series are added
    chart.timeScale().fitContent();

    return () => {
      cleanup?.();
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Sync visible range from parent
  useEffect(() => {
    if (syncRange && chartRef.current) {
      isSyncingRef.current = true;
      chartRef.current.timeScale().setVisibleLogicalRange(syncRange);
      isSyncingRef.current = false;
    }
  }, [syncRange]);

  return (
    <div
      ref={containerRef}
      className={className}
      style={{ width: "100%", height, position: "relative" }}
    />
  );
}

// ── Utility: convert "YYYY-MM-DD" string to lightweight-charts Time ───

export function toTime(dateStr: string): Time {
  return dateStr as unknown as Time;
}

// Re-export series definitions and frequently used types
export {
  CandlestickSeries,
  LineSeries,
  AreaSeries,
  HistogramSeries,
  createSeriesMarkers,
};
export type {
  IChartApi,
  ISeriesApi,
  MouseEventParams,
  LogicalRange,
  Time,
  SeriesMarker,
};
