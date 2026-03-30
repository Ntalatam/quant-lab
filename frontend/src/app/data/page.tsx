"use client";

import { useState } from "react";
import { useAvailableTickers, useLoadTicker, useOHLCV } from "@/hooks/useMarketData";
import { PageLoading } from "@/components/shared/LoadingSpinner";
import { ErrorMessage } from "@/components/shared/ErrorBoundary";
import { LoadingSpinner } from "@/components/shared/LoadingSpinner";
import {
  ResponsiveContainer,
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";
import { CHART_COLORS } from "@/lib/constants";
import { formatCompactDate } from "@/lib/formatters";

export default function DataExplorerPage() {
  const { data: tickers, isLoading: tickersLoading } = useAvailableTickers();
  const loadMutation = useLoadTicker();

  const [newTicker, setNewTicker] = useState("");
  const [startDate, setStartDate] = useState("2020-01-01");
  const [endDate, setEndDate] = useState("2024-01-01");
  const [viewTicker, setViewTicker] = useState("");

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
              <h2 className="text-sm font-medium text-text-secondary mb-3">
                {viewTicker} Price Chart
              </h2>
              {ohlcvLoading ? (
                <PageLoading />
              ) : ohlcv && ohlcv.data.length > 0 ? (
                <ResponsiveContainer width="100%" height={400}>
                  <ComposedChart data={ohlcv.data}>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke={CHART_COLORS.grid}
                    />
                    <XAxis
                      dataKey="date"
                      tickFormatter={formatCompactDate}
                      stroke={CHART_COLORS.axis}
                      tick={{ fontSize: 11 }}
                      minTickGap={50}
                    />
                    <YAxis
                      yAxisId="price"
                      stroke={CHART_COLORS.axis}
                      tick={{ fontSize: 11 }}
                      width={60}
                      tickFormatter={(v) => `$${v}`}
                    />
                    <YAxis
                      yAxisId="volume"
                      orientation="right"
                      stroke={CHART_COLORS.axis}
                      tick={{ fontSize: 10 }}
                      width={50}
                      tickFormatter={(v) =>
                        `${(v / 1_000_000).toFixed(0)}M`
                      }
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: CHART_COLORS.tooltip,
                        border: `1px solid ${CHART_COLORS.grid}`,
                        borderRadius: 4,
                        fontSize: 12,
                      }}
                    />
                    <Bar
                      yAxisId="volume"
                      dataKey="volume"
                      fill={CHART_COLORS.blue}
                      opacity={0.15}
                    />
                    <Line
                      yAxisId="price"
                      type="monotone"
                      dataKey="close"
                      stroke={CHART_COLORS.strategy}
                      strokeWidth={1.5}
                      dot={false}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              ) : (
                <p className="text-text-muted text-sm text-center py-8">
                  No data available for this range
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
