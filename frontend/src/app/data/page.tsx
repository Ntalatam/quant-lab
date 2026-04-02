"use client";

import { useState, useCallback } from "react";
import { useAvailableTickers, useLoadTicker, useOHLCV } from "@/hooks/useMarketData";
import { PageLoading } from "@/components/shared/LoadingSpinner";
import { LoadingSpinner } from "@/components/shared/LoadingSpinner";
import {
  LightweightChart,
  CandlestickSeries,
  HistogramSeries,
  toTime,
  type IChartApi,
  type MouseEventParams,
  type Time,
} from "@/components/charts/LightweightChartWrapper";
import { CHART_COLORS } from "@/lib/constants";
import type {
  CandlestickData,
  HistogramData,
} from "lightweight-charts";

// ── OHLCV legend overlay ────────────────────────────────────────────────

interface OHLCVLegend {
  o: number;
  h: number;
  l: number;
  c: number;
  v: number;
  change: number;
}

function OHLCVOverlay({
  ticker,
  legend,
}: {
  ticker: string;
  legend: OHLCVLegend | null;
}) {
  if (!legend) return null;
  const up = legend.change >= 0;
  const color = up ? CHART_COLORS.positive : CHART_COLORS.negative;
  const fmt = (v: number) => v.toFixed(2);
  const fmtVol = (v: number) =>
    v >= 1e9
      ? `${(v / 1e9).toFixed(2)}B`
      : v >= 1e6
        ? `${(v / 1e6).toFixed(2)}M`
        : v >= 1e3
          ? `${(v / 1e3).toFixed(1)}K`
          : String(v);

  return (
    <div
      className="absolute top-2 left-3 z-10 flex items-center gap-3 pointer-events-none select-none"
      style={{ fontFamily: "ui-monospace, monospace", fontSize: 11 }}
    >
      <span className="font-bold text-text-primary text-sm">{ticker}</span>
      <span>
        <span className="text-text-muted">O </span>
        <span style={{ color }}>{fmt(legend.o)}</span>
      </span>
      <span>
        <span className="text-text-muted">H </span>
        <span style={{ color }}>{fmt(legend.h)}</span>
      </span>
      <span>
        <span className="text-text-muted">L </span>
        <span style={{ color }}>{fmt(legend.l)}</span>
      </span>
      <span>
        <span className="text-text-muted">C </span>
        <span style={{ color }}>{fmt(legend.c)}</span>
      </span>
      <span style={{ color }}>
        {up ? "+" : ""}
        {legend.change.toFixed(2)}%
      </span>
      <span>
        <span className="text-text-muted">Vol </span>
        <span className="text-text-secondary">{fmtVol(legend.v)}</span>
      </span>
    </div>
  );
}

// ── Page ────────────────────────────────────────────────────────────────

export default function DataExplorerPage() {
  const { data: tickers, isLoading: tickersLoading } = useAvailableTickers();
  const loadMutation = useLoadTicker();

  const [newTicker, setNewTicker] = useState("");
  const [startDate, setStartDate] = useState("2020-01-01");
  const [endDate, setEndDate] = useState("2024-01-01");
  const [viewTicker, setViewTicker] = useState("");
  const [legend, setLegend] = useState<OHLCVLegend | null>(null);

  const {
    data: ohlcv,
    isLoading: ohlcvLoading,
  } = useOHLCV(viewTicker, startDate, endDate, !!viewTicker);

  const handleLoad = async () => {
    if (!newTicker) return;
    await loadMutation.mutateAsync({
      ticker: newTicker.toUpperCase(),
      startDate,
      endDate,
    });
    setViewTicker(newTicker.toUpperCase());
    setNewTicker("");
  };

  // Build lightweight-charts data arrays
  const candleData: CandlestickData<Time>[] = (ohlcv?.data ?? []).map((d) => ({
    time: toTime(d.date),
    open: d.open,
    high: d.high,
    low: d.low,
    close: d.close,
  }));

  const volumeData: HistogramData<Time>[] = (ohlcv?.data ?? []).map((d) => ({
    time: toTime(d.date),
    value: d.volume,
    color:
      d.close >= d.open
        ? "rgba(0,212,170,0.18)"
        : "rgba(255,68,102,0.18)",
  }));

  // Chart init callback
  const handleChartInit = useCallback(
    (chart: IChartApi) => {
      if (!candleData.length) return;

      const candleSeries = chart.addSeries(CandlestickSeries, {
        upColor: CHART_COLORS.positive,
        downColor: CHART_COLORS.negative,
        borderUpColor: CHART_COLORS.positive,
        borderDownColor: CHART_COLORS.negative,
        wickUpColor: CHART_COLORS.positive,
        wickDownColor: CHART_COLORS.negative,
      });
      candleSeries.setData(candleData);

      const volumeSeries = chart.addSeries(HistogramSeries, {
        priceFormat: { type: "volume" },
        priceScaleId: "volume",
      });
      volumeSeries.setData(volumeData);
      chart.priceScale("volume").applyOptions({
        scaleMargins: { top: 0.82, bottom: 0 },
      });

      // Set initial legend from last bar
      const last = ohlcv?.data?.[ohlcv.data.length - 1];
      const prev = ohlcv?.data?.[ohlcv.data.length - 2];
      if (last) {
        setLegend({
          o: last.open,
          h: last.high,
          l: last.low,
          c: last.close,
          v: last.volume,
          change: prev
            ? ((last.close - prev.close) / prev.close) * 100
            : 0,
        });
      }

      // Crosshair → update legend
      chart.subscribeCrosshairMove((param: MouseEventParams<Time>) => {
        const candle = param.seriesData?.get(candleSeries) as
          | CandlestickData<Time>
          | undefined;
        const vol = param.seriesData?.get(volumeSeries) as
          | HistogramData<Time>
          | undefined;
        if (candle) {
          const idx = candleData.findIndex(
            (d) => d.time === candle.time
          );
          const prevBar = idx > 0 ? candleData[idx - 1] : null;
          setLegend({
            o: candle.open,
            h: candle.high,
            l: candle.low,
            c: candle.close,
            v: vol?.value ?? 0,
            change: prevBar
              ? ((candle.close - prevBar.close) / prevBar.close) * 100
              : 0,
          });
        }
      });
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [ohlcv]
  );

  return (
    <div>
      <h1 className="text-xl font-semibold mb-6">Data Explorer</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Load + Ticker List */}
        <div className="space-y-4">
          <div className="bg-bg-card border border-border rounded p-4">
            <h2 className="text-sm font-medium text-text-secondary mb-3">
              Load Ticker Data
            </h2>
            <div className="space-y-2">
              <input
                type="text"
                value={newTicker}
                onChange={(e) => setNewTicker(e.target.value.toUpperCase())}
                placeholder="e.g. AAPL"
                className="w-full bg-bg-primary border border-border rounded px-3 py-2 text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-accent-blue"
              />
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="bg-bg-primary border border-border rounded px-2 py-1.5 text-xs text-text-primary focus:outline-none focus:border-accent-blue"
                />
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="bg-bg-primary border border-border rounded px-2 py-1.5 text-xs text-text-primary focus:outline-none focus:border-accent-blue"
                />
              </div>
              <button
                onClick={handleLoad}
                disabled={!newTicker || loadMutation.isPending}
                className="w-full bg-accent-blue/10 text-accent-blue border border-accent-blue/20 rounded px-3 py-2 text-sm hover:bg-accent-blue/20 transition-colors disabled:opacity-50"
              >
                {loadMutation.isPending ? (
                  <LoadingSpinner size={14} />
                ) : (
                  "Load Data"
                )}
              </button>
              {loadMutation.error && (
                <p className="text-xs text-accent-red">
                  {loadMutation.error.message}
                </p>
              )}
            </div>
          </div>

          <div className="bg-bg-card border border-border rounded p-4">
            <h2 className="text-sm font-medium text-text-secondary mb-3">
              Loaded Tickers
            </h2>
            {tickersLoading ? (
              <LoadingSpinner />
            ) : tickers && tickers.length > 0 ? (
              <div className="space-y-1">
                {tickers.map((t) => (
                  <button
                    key={t}
                    onClick={() => setViewTicker(t)}
                    className={`block w-full text-left px-2 py-1 rounded text-sm ${
                      viewTicker === t
                        ? "bg-bg-hover text-accent-blue"
                        : "text-text-secondary hover:bg-bg-hover hover:text-text-primary"
                    } transition-colors`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            ) : (
              <p className="text-xs text-text-muted">No data loaded yet</p>
            )}
          </div>
        </div>

        {/* Right: Chart */}
        <div className="lg:col-span-2">
          {viewTicker && (
            <div className="bg-bg-card border border-border rounded p-4">
              <div className="relative">
                <OHLCVOverlay ticker={viewTicker} legend={legend} />
                {ohlcvLoading ? (
                  <PageLoading />
                ) : ohlcv && ohlcv.data.length > 0 ? (
                  <LightweightChart
                    key={`${viewTicker}-${ohlcv.data.length}`}
                    height={480}
                    onInit={handleChartInit}
                    options={{
                      rightPriceScale: {
                        scaleMargins: { top: 0.05, bottom: 0.2 },
                      },
                    }}
                  />
                ) : (
                  <p className="text-text-muted text-sm text-center py-8">
                    No data available for this range
                  </p>
                )}
              </div>
              {ohlcv && ohlcv.original_rows > ohlcv.returned_rows && (
                <p className="text-xs text-text-muted mt-2">
                  {ohlcv.original_rows} trading days — displaying{" "}
                  {ohlcv.returned_rows} sampled points
                </p>
              )}
            </div>
          )}

          {!viewTicker && (
            <div className="bg-bg-card border border-border rounded flex items-center justify-center h-64 text-text-muted text-sm">
              Select a ticker to view its price chart
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
