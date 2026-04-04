"use client";

import { useCallback, useMemo, useState } from "react";

import {
  CandlestickSeries,
  HistogramSeries,
  LightweightChart,
  createSeriesMarkers,
  toTime,
  type IChartApi,
  type MouseEventParams,
  type SeriesMarker,
  type Time,
} from "@/components/charts/LightweightChartWrapper";
import { EarningsPanel } from "@/components/data/EarningsPanel";
import { MacroPanel } from "@/components/data/MacroPanel";
import { SentimentPanel } from "@/components/data/SentimentPanel";
import {
  LoadingSpinner,
  PageLoading,
} from "@/components/shared/LoadingSpinner";
import {
  useEconomicIndicatorCatalog,
  useEconomicIndicators,
  useEarningsOverview,
  useNewsSentiment,
} from "@/hooks/useAlternativeData";
import {
  useAvailableTickers,
  useLoadTicker,
  useOHLCV,
} from "@/hooks/useMarketData";
import { CHART_COLORS } from "@/lib/constants";
import type { CandlestickData, HistogramData } from "lightweight-charts";

const DEFAULT_MACRO_SERIES = ["FEDFUNDS", "CPIAUCSL", "UNRATE", "DGS10"];

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
  const fmt = (value: number) => value.toFixed(2);
  const fmtVol = (value: number) =>
    value >= 1e9
      ? `${(value / 1e9).toFixed(2)}B`
      : value >= 1e6
        ? `${(value / 1e6).toFixed(2)}M`
        : value >= 1e3
          ? `${(value / 1e3).toFixed(1)}K`
          : String(value);

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

export default function DataExplorerPage() {
  const { data: tickers, isLoading: tickersLoading } = useAvailableTickers();
  const loadMutation = useLoadTicker();

  const [newTicker, setNewTicker] = useState("");
  const [startDate, setStartDate] = useState("2020-01-01");
  const [endDate, setEndDate] = useState("2024-01-01");
  const [viewTicker, setViewTicker] = useState("");
  const [legend, setLegend] = useState<OHLCVLegend | null>(null);
  const [macroSeriesIds, setMacroSeriesIds] = useState(DEFAULT_MACRO_SERIES);

  const { data: ohlcv, isLoading: ohlcvLoading } = useOHLCV(
    viewTicker,
    startDate,
    endDate,
    !!viewTicker,
  );
  const { data: macroCatalog } = useEconomicIndicatorCatalog();
  const { data: macroIndicators, isLoading: macroLoading } =
    useEconomicIndicators(macroSeriesIds, startDate, endDate);
  const { data: earningsOverview, isLoading: earningsLoading } =
    useEarningsOverview(viewTicker, !!viewTicker);
  const { data: newsSentiment, isLoading: sentimentLoading } = useNewsSentiment(
    viewTicker,
    30,
    8,
    !!viewTicker,
  );

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

  const candleData: CandlestickData<Time>[] = (ohlcv?.data ?? []).map(
    (row) => ({
      time: toTime(row.date),
      open: row.open,
      high: row.high,
      low: row.low,
      close: row.close,
    }),
  );

  const volumeData: HistogramData<Time>[] = (ohlcv?.data ?? []).map((row) => ({
    time: toTime(row.date),
    value: row.volume,
    color:
      row.close >= row.open ? "rgba(0,212,170,0.18)" : "rgba(255,68,102,0.18)",
  }));

  const earningsMarkers = useMemo(() => {
    if (!earningsOverview || !ohlcv?.data?.length) return [];

    const tradingDates = ohlcv.data.map((row) => row.date);
    const snapToTradingDate = (eventDate: string) => {
      const exactMatch = tradingDates.find((date) => date === eventDate);
      if (exactMatch) return exactMatch;
      const nextTradingDate = tradingDates.find((date) => date > eventDate);
      return nextTradingDate ?? tradingDates[tradingDates.length - 1];
    };

    const markers: SeriesMarker<Time>[] = [];
    const seen = new Set<string>();

    for (const event of earningsOverview.events) {
      const markerDate = snapToTradingDate(event.date);
      if (!markerDate) continue;

      const key = `${markerDate}:${event.event_type}`;
      if (seen.has(key)) continue;
      seen.add(key);

      let color: string = CHART_COLORS.purple;
      if (event.event_type === "scheduled") {
        color = CHART_COLORS.yellow;
      } else if ((event.eps_surprise_pct ?? 0) >= 0) {
        color = CHART_COLORS.positive;
      } else if ((event.eps_surprise_pct ?? 0) < 0) {
        color = CHART_COLORS.negative;
      }

      markers.push({
        time: toTime(markerDate),
        position: event.event_type === "scheduled" ? "aboveBar" : "belowBar",
        color,
        shape: "circle",
        text: "E",
        size: 0.7,
      });
    }

    return markers.sort((a, b) => String(a.time).localeCompare(String(b.time)));
  }, [earningsOverview, ohlcv]);

  const toggleMacroSeries = useCallback((seriesId: string) => {
    setMacroSeriesIds((current) => {
      if (current.includes(seriesId)) {
        if (current.length === 1) return current;
        return current.filter((id) => id !== seriesId);
      }
      return [...current, seriesId];
    });
  }, []);

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
      if (earningsMarkers.length > 0) {
        createSeriesMarkers(candleSeries, earningsMarkers);
      }

      const volumeSeries = chart.addSeries(HistogramSeries, {
        priceFormat: { type: "volume" },
        priceScaleId: "volume",
      });
      volumeSeries.setData(volumeData);
      chart.priceScale("volume").applyOptions({
        scaleMargins: { top: 0.82, bottom: 0 },
      });

      const last = ohlcv?.data?.[ohlcv.data.length - 1];
      const prev = ohlcv?.data?.[ohlcv.data.length - 2];
      if (last) {
        setLegend({
          o: last.open,
          h: last.high,
          l: last.low,
          c: last.close,
          v: last.volume,
          change: prev ? ((last.close - prev.close) / prev.close) * 100 : 0,
        });
      }

      chart.subscribeCrosshairMove((param: MouseEventParams<Time>) => {
        const candle = param.seriesData?.get(candleSeries) as
          | CandlestickData<Time>
          | undefined;
        const volume = param.seriesData?.get(volumeSeries) as
          | HistogramData<Time>
          | undefined;
        if (!candle) return;

        const index = candleData.findIndex((row) => row.time === candle.time);
        const previousBar = index > 0 ? candleData[index - 1] : null;
        setLegend({
          o: candle.open,
          h: candle.high,
          l: candle.low,
          c: candle.close,
          v: volume?.value ?? 0,
          change: previousBar
            ? ((candle.close - previousBar.close) / previousBar.close) * 100
            : 0,
        });
      });
    },
    [candleData, earningsMarkers, ohlcv, volumeData],
  );

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-xl font-semibold">Data Explorer</h1>
        <p className="text-sm text-text-muted mt-1">
          Load price history, overlay earnings events, score recent news
          sentiment, and compare a ticker against macro regime signals.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="space-y-4">
          <div className="bg-bg-card border border-border rounded p-4">
            <h2 className="text-sm font-medium text-text-secondary mb-3">
              Load Ticker Data
            </h2>
            <div className="space-y-2">
              <input
                type="text"
                value={newTicker}
                onChange={(event) =>
                  setNewTicker(event.target.value.toUpperCase())
                }
                placeholder="e.g. AAPL"
                className="w-full bg-bg-primary border border-border rounded px-3 py-2 text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-accent-blue"
              />
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="date"
                  value={startDate}
                  onChange={(event) => setStartDate(event.target.value)}
                  className="bg-bg-primary border border-border rounded px-2 py-1.5 text-xs text-text-primary focus:outline-none focus:border-accent-blue"
                />
                <input
                  type="date"
                  value={endDate}
                  onChange={(event) => setEndDate(event.target.value)}
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
                {tickers.map((ticker) => (
                  <button
                    key={ticker}
                    onClick={() => setViewTicker(ticker)}
                    className={`block w-full text-left px-2 py-1 rounded text-sm ${
                      viewTicker === ticker
                        ? "bg-bg-hover text-accent-blue"
                        : "text-text-secondary hover:bg-bg-hover hover:text-text-primary"
                    } transition-colors`}
                  >
                    {ticker}
                  </button>
                ))}
              </div>
            ) : (
              <p className="text-xs text-text-muted">No data loaded yet</p>
            )}
          </div>
        </div>

        <div className="lg:col-span-2">
          {viewTicker ? (
            <div className="bg-bg-card border border-border rounded p-4">
              <div className="flex flex-col gap-2 mb-4 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <h2 className="text-sm font-semibold text-text-primary">
                    {viewTicker} Price & Event Overlay
                  </h2>
                  <p className="text-xs text-text-muted mt-1">
                    Yellow markers show scheduled earnings; purple and surprise-
                    colored markers show reported quarters.
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {earningsOverview?.next_earnings_date && (
                    <span
                      className="px-2.5 py-1 rounded text-[11px] font-medium"
                      style={{
                        background: "rgba(255,187,51,0.12)",
                        border: "1px solid rgba(255,187,51,0.22)",
                        color: "var(--color-accent-yellow)",
                      }}
                    >
                      Next earnings {earningsOverview.next_earnings_date}
                    </span>
                  )}
                  {newsSentiment && (
                    <span
                      className="px-2.5 py-1 rounded text-[11px] font-medium capitalize"
                      style={{
                        background:
                          newsSentiment.signal === "bullish"
                            ? "rgba(0,212,170,0.12)"
                            : newsSentiment.signal === "bearish"
                              ? "rgba(255,68,102,0.12)"
                              : "rgba(68,136,255,0.12)",
                        border:
                          newsSentiment.signal === "bullish"
                            ? "1px solid rgba(0,212,170,0.22)"
                            : newsSentiment.signal === "bearish"
                              ? "1px solid rgba(255,68,102,0.22)"
                              : "1px solid rgba(68,136,255,0.22)",
                        color:
                          newsSentiment.signal === "bullish"
                            ? "var(--color-accent-green)"
                            : newsSentiment.signal === "bearish"
                              ? "var(--color-accent-red)"
                              : "var(--color-accent-blue)",
                      }}
                    >
                      Sentiment {newsSentiment.signal} (
                      {newsSentiment.average_score.toFixed(2)})
                    </span>
                  )}
                </div>
              </div>

              <div className="relative">
                <OHLCVOverlay ticker={viewTicker} legend={legend} />
                {ohlcvLoading ? (
                  <PageLoading />
                ) : ohlcv && ohlcv.data.length > 0 ? (
                  <LightweightChart
                    key={`${viewTicker}-${ohlcv.data.length}-${earningsMarkers.length}`}
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
          ) : (
            <div className="bg-bg-card border border-border rounded flex items-center justify-center h-64 text-text-muted text-sm">
              Select a ticker to view its price chart
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[1.4fr_1fr] gap-6 mt-6">
        <SentimentPanel
          sentiment={newsSentiment}
          isLoading={sentimentLoading}
        />
        <EarningsPanel
          overview={earningsOverview}
          isLoading={earningsLoading}
        />
      </div>

      <div className="mt-6">
        <MacroPanel
          catalog={macroCatalog}
          selectedIds={macroSeriesIds}
          onToggleIndicator={toggleMacroSeries}
          series={macroIndicators?.series}
          isLoading={macroLoading}
        />
      </div>
    </div>
  );
}
