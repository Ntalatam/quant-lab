"use client";

import { useState, useMemo, useCallback } from "react";
import { useAvailableTickers, useLoadTicker } from "@/hooks/useMarketData";
import { api } from "@/lib/api";
import { CHART_COLORS } from "@/lib/constants";
import type {
  CorrelationResult,
  SpreadResult,
  PairTestResult,
} from "@/lib/types";
import {
  Loader2,
  Search,
  X,
  TrendingUp,
  ArrowRightLeft,
  Zap,
  Clock,
  AlertTriangle,
  CheckCircle,
} from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from "recharts";

const PAIR_COLORS = [
  CHART_COLORS.strategy,
  CHART_COLORS.blue,
  CHART_COLORS.yellow,
  CHART_COLORS.purple,
  CHART_COLORS.negative,
  "#ff8844",
  "#44ddff",
  "#dd44ff",
  "#88ff44",
  "#ff44aa",
];

const POPULAR_TICKERS = [
  "SPY", "QQQ", "IWM", "DIA", "AAPL", "MSFT", "GOOGL", "AMZN",
  "NVDA", "META", "TSLA", "JPM", "GS", "BAC", "XLF", "XLK",
  "XLE", "XLV", "GLD", "TLT", "HYG", "VXX",
];

export default function CorrelationPage() {
  const { data: loadedTickers } = useAvailableTickers();
  const loadTicker = useLoadTicker();

  // Configuration state
  const [selectedTickers, setSelectedTickers] = useState<string[]>([]);
  const [tickerInput, setTickerInput] = useState("");
  const [startDate, setStartDate] = useState("2020-01-01");
  const [endDate, setEndDate] = useState("2024-12-31");
  const [rollingWindow, setRollingWindow] = useState(63);

  // Results state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<CorrelationResult | null>(null);

  // Spread drill-down state
  const [spreadPair, setSpreadPair] = useState<{ a: string; b: string } | null>(null);
  const [spreadLoading, setSpreadLoading] = useState(false);
  const [spreadResult, setSpreadResult] = useState<SpreadResult | null>(null);

  // Rolling chart visibility
  const [visiblePairs, setVisiblePairs] = useState<Set<string>>(new Set());

  const addTicker = useCallback(
    (ticker: string) => {
      const t = ticker.trim().toUpperCase();
      if (t && !selectedTickers.includes(t)) {
        setSelectedTickers((prev) => [...prev, t]);
      }
      setTickerInput("");
    },
    [selectedTickers]
  );

  const removeTicker = (t: string) => {
    setSelectedTickers((prev) => prev.filter((x) => x !== t));
    setResult(null);
    setSpreadResult(null);
  };

  const filteredSuggestions = useMemo(() => {
    const all = new Set([...POPULAR_TICKERS, ...(loadedTickers || [])]);
    const input = tickerInput.toUpperCase();
    return [...all]
      .filter((t) => t.includes(input) && !selectedTickers.includes(t))
      .slice(0, 8);
  }, [tickerInput, loadedTickers, selectedTickers]);

  const runAnalysis = async () => {
    if (selectedTickers.length < 2) return;
    setLoading(true);
    setError("");
    setResult(null);
    setSpreadResult(null);
    setSpreadPair(null);

    try {
      // Ensure all tickers are loaded
      for (const ticker of selectedTickers) {
        if (!loadedTickers?.includes(ticker)) {
          await loadTicker.mutateAsync({ ticker, startDate, endDate });
        }
      }
      const res = await api.getCorrelationAnalysis(
        selectedTickers,
        startDate,
        endDate,
        rollingWindow
      );
      setResult(res);
      // Auto-show all rolling pairs
      setVisiblePairs(new Set(res.rolling_correlations.map((rc) => rc.pair)));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  };

  const loadSpread = async (pair: PairTestResult) => {
    setSpreadPair({ a: pair.ticker_a, b: pair.ticker_b });
    setSpreadLoading(true);
    try {
      const res = await api.getSpreadAnalysis(
        pair.ticker_a,
        pair.ticker_b,
        startDate,
        endDate,
        rollingWindow
      );
      setSpreadResult(res);
    } catch {
      setSpreadResult(null);
    } finally {
      setSpreadLoading(false);
    }
  };

  const togglePairVisibility = (pair: string) => {
    setVisiblePairs((prev) => {
      const next = new Set(prev);
      if (next.has(pair)) next.delete(pair);
      else next.add(pair);
      return next;
    });
  };

  return (
    <div className="p-6 space-y-6 max-w-[1400px]">
      {/* Header */}
      <div>
        <h1
          className="text-[20px] font-bold"
          style={{ color: "var(--color-text-primary)" }}
        >
          Correlation &amp; Cointegration
        </h1>
        <p
          className="text-[12px] mt-1"
          style={{ color: "var(--color-text-secondary)" }}
        >
          Analyse cross-asset relationships, detect mean-reverting pairs, and
          evaluate spread stationarity
        </p>
      </div>

      {/* Controls */}
      <div className="card p-5 space-y-4">
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_auto] gap-4">
          {/* Ticker selection */}
          <div className="space-y-2">
            <label className="section-label">Tickers</label>
            <div className="flex flex-wrap items-center gap-1.5 min-h-[36px]">
              {selectedTickers.map((t) => (
                <span
                  key={t}
                  className="inline-flex items-center gap-1 px-2 py-1 rounded text-[11px] font-mono font-medium"
                  style={{
                    background: "rgba(68,136,255,0.12)",
                    border: "1px solid rgba(68,136,255,0.25)",
                    color: "var(--color-accent-blue)",
                  }}
                >
                  {t}
                  <button onClick={() => removeTicker(t)} className="opacity-60 hover:opacity-100">
                    <X size={10} />
                  </button>
                </span>
              ))}
              <div className="relative">
                <input
                  type="text"
                  value={tickerInput}
                  onChange={(e) => setTickerInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && tickerInput.trim()) {
                      addTicker(tickerInput);
                    }
                  }}
                  placeholder={selectedTickers.length === 0 ? "Add tickers…" : ""}
                  className="w-28 px-2 py-1 rounded text-[12px] bg-transparent outline-none"
                  style={{
                    color: "var(--color-text-primary)",
                    border: "1px solid var(--color-border)",
                  }}
                />
                {tickerInput && filteredSuggestions.length > 0 && (
                  <div
                    className="absolute top-full left-0 mt-1 rounded shadow-lg z-20 overflow-hidden min-w-[120px]"
                    style={{
                      background: "var(--color-bg-card)",
                      border: "1px solid var(--color-border)",
                    }}
                  >
                    {filteredSuggestions.map((t) => (
                      <button
                        key={t}
                        onClick={() => addTicker(t)}
                        className="block w-full px-3 py-1.5 text-left text-[11px] font-mono hover:bg-bg-hover"
                        style={{ color: "var(--color-text-primary)" }}
                      >
                        {t}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
            {/* Quick-add row */}
            <div className="flex flex-wrap gap-1">
              {POPULAR_TICKERS.filter((t) => !selectedTickers.includes(t))
                .slice(0, 12)
                .map((t) => (
                  <button
                    key={t}
                    onClick={() => addTicker(t)}
                    className="px-1.5 py-0.5 rounded text-[10px] font-mono transition-colors"
                    style={{
                      color: "var(--color-text-muted)",
                      border: "1px solid var(--color-border)",
                    }}
                  >
                    +{t}
                  </button>
                ))}
            </div>
          </div>

          {/* Date + params */}
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <label className="section-label block mb-1">Start</label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="px-2 py-1.5 rounded text-[12px]"
                style={{
                  background: "var(--color-bg-primary)",
                  color: "var(--color-text-primary)",
                  border: "1px solid var(--color-border)",
                }}
              />
            </div>
            <div>
              <label className="section-label block mb-1">End</label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="px-2 py-1.5 rounded text-[12px]"
                style={{
                  background: "var(--color-bg-primary)",
                  color: "var(--color-text-primary)",
                  border: "1px solid var(--color-border)",
                }}
              />
            </div>
            <div>
              <label className="section-label block mb-1">Window</label>
              <select
                value={rollingWindow}
                onChange={(e) => setRollingWindow(Number(e.target.value))}
                className="px-2 py-1.5 rounded text-[12px]"
                style={{
                  background: "var(--color-bg-primary)",
                  color: "var(--color-text-primary)",
                  border: "1px solid var(--color-border)",
                }}
              >
                <option value={21}>21d (1mo)</option>
                <option value={63}>63d (3mo)</option>
                <option value={126}>126d (6mo)</option>
                <option value={252}>252d (1yr)</option>
              </select>
            </div>
            <button
              onClick={runAnalysis}
              disabled={selectedTickers.length < 2 || loading}
              className="px-4 py-1.5 rounded text-[12px] font-medium transition-all disabled:opacity-40"
              style={{
                background: "var(--color-accent-blue)",
                color: "#fff",
              }}
            >
              {loading ? (
                <span className="flex items-center gap-1.5">
                  <Loader2 size={12} className="animate-spin" /> Analysing…
                </span>
              ) : (
                <span className="flex items-center gap-1.5">
                  <Search size={12} /> Analyse
                </span>
              )}
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div
          className="px-4 py-3 rounded text-[12px] flex items-center gap-2"
          style={{
            background: "rgba(255,68,102,0.08)",
            border: "1px solid rgba(255,68,102,0.25)",
            color: "var(--color-accent-red)",
          }}
        >
          <AlertTriangle size={14} /> {error}
        </div>
      )}

      {result && (
        <>
          {/* Correlation Heatmap */}
          <div className="card p-5 space-y-3">
            <div className="flex items-center gap-2">
              <TrendingUp size={14} style={{ color: "var(--color-accent-blue)" }} />
              <h2
                className="text-[14px] font-semibold"
                style={{ color: "var(--color-text-primary)" }}
              >
                Correlation Matrix
              </h2>
              <span className="text-[10px]" style={{ color: "var(--color-text-muted)" }}>
                Full-period return correlation
              </span>
            </div>

            <CorrelationHeatmap
              tickers={result.tickers}
              matrix={result.static_matrix}
            />
          </div>

          {/* Rolling Correlations */}
          <div className="card p-5 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ArrowRightLeft size={14} style={{ color: "var(--color-accent-green)" }} />
                <h2
                  className="text-[14px] font-semibold"
                  style={{ color: "var(--color-text-primary)" }}
                >
                  Rolling Correlation
                </h2>
                <span className="text-[10px]" style={{ color: "var(--color-text-muted)" }}>
                  {rollingWindow}-day window
                </span>
              </div>
              {/* Pair toggles */}
              <div className="flex flex-wrap gap-1.5">
                {result.rolling_correlations.map((rc, i) => {
                  const active = visiblePairs.has(rc.pair);
                  return (
                    <button
                      key={rc.pair}
                      onClick={() => togglePairVisibility(rc.pair)}
                      className="px-2 py-0.5 rounded text-[10px] font-mono transition-all"
                      style={{
                        border: `1px solid ${active ? PAIR_COLORS[i % PAIR_COLORS.length] : "var(--color-border)"}`,
                        background: active
                          ? `${PAIR_COLORS[i % PAIR_COLORS.length]}15`
                          : "transparent",
                        color: active
                          ? PAIR_COLORS[i % PAIR_COLORS.length]
                          : "var(--color-text-muted)",
                        opacity: active ? 1 : 0.5,
                      }}
                    >
                      {rc.pair}
                    </button>
                  );
                })}
              </div>
            </div>

            <RollingCorrelationChart
              data={result.rolling_correlations}
              visiblePairs={visiblePairs}
            />
          </div>

          {/* Cointegration Test Results */}
          <div className="card p-5 space-y-3">
            <div className="flex items-center gap-2">
              <Zap size={14} style={{ color: "var(--color-accent-yellow)" }} />
              <h2
                className="text-[14px] font-semibold"
                style={{ color: "var(--color-text-primary)" }}
              >
                Pair Discovery
              </h2>
              <span className="text-[10px]" style={{ color: "var(--color-text-muted)" }}>
                Engle-Granger cointegration test — ranked by evidence strength
              </span>
            </div>

            <PairDiscoveryTable
              pairs={result.discovered_pairs}
              onSelectPair={loadSpread}
              activePair={spreadPair}
            />
          </div>

          {/* Spread Drill-Down */}
          {spreadPair && (
            <div className="card p-5 space-y-3">
              <div className="flex items-center gap-2">
                <Clock size={14} style={{ color: "var(--color-accent-purple)" }} />
                <h2
                  className="text-[14px] font-semibold"
                  style={{ color: "var(--color-text-primary)" }}
                >
                  Spread Analysis — {spreadPair.a}/{spreadPair.b}
                </h2>
                <button
                  onClick={() => {
                    setSpreadPair(null);
                    setSpreadResult(null);
                  }}
                  className="ml-auto"
                >
                  <X size={14} style={{ color: "var(--color-text-muted)" }} />
                </button>
              </div>

              {spreadLoading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 size={20} className="animate-spin" style={{ color: "var(--color-text-muted)" }} />
                </div>
              ) : spreadResult ? (
                <SpreadDrillDown result={spreadResult} />
              ) : (
                <p className="text-[12px]" style={{ color: "var(--color-text-muted)" }}>
                  Failed to load spread data.
                </p>
              )}
            </div>
          )}
        </>
      )}

      {/* Empty state */}
      {!result && !loading && (
        <div
          className="card p-12 flex flex-col items-center gap-3"
          style={{ color: "var(--color-text-muted)" }}
        >
          <ArrowRightLeft size={32} style={{ opacity: 0.3 }} />
          <p className="text-[13px]">
            Select at least 2 tickers to analyse correlations and discover tradeable pairs
          </p>
        </div>
      )}
    </div>
  );
}


/* ───────────── Correlation Heatmap ───────────── */

function CorrelationHeatmap({
  tickers,
  matrix,
}: {
  tickers: string[];
  matrix: number[][];
}) {
  const n = tickers.length;

  const getColor = (v: number): string => {
    // -1 → red, 0 → neutral, +1 → blue
    if (v >= 0) {
      const t = Math.min(v, 1);
      const r = Math.round(20 + (1 - t) * 0);
      const g = Math.round(20 + t * 50);
      const b = Math.round(31 + t * 224);
      return `rgb(${r}, ${g}, ${b})`;
    } else {
      const t = Math.min(Math.abs(v), 1);
      const r = Math.round(20 + t * 235);
      const g = Math.round(20 + (1 - t) * 0);
      const b = Math.round(31 + (1 - t) * 0);
      return `rgb(${r}, ${g}, ${b})`;
    }
  };

  const getTextColor = (v: number): string => {
    return Math.abs(v) > 0.5 ? "#fff" : "var(--color-text-secondary)";
  };

  return (
    <div className="overflow-x-auto">
      <table className="border-collapse">
        <thead>
          <tr>
            <th className="w-16" />
            {tickers.map((t) => (
              <th
                key={t}
                className="px-2 py-1.5 text-[10px] font-mono font-medium text-center"
                style={{ color: "var(--color-text-secondary)", minWidth: 56 }}
              >
                {t}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {tickers.map((rowTicker, i) => (
            <tr key={rowTicker}>
              <td
                className="px-2 py-1.5 text-[10px] font-mono font-medium text-right"
                style={{ color: "var(--color-text-secondary)" }}
              >
                {rowTicker}
              </td>
              {tickers.map((_, j) => {
                const val = matrix[i][j];
                return (
                  <td
                    key={j}
                    className="text-center text-[11px] font-mono tabular-nums"
                    style={{
                      background: getColor(val),
                      color: getTextColor(val),
                      padding: "8px 4px",
                      minWidth: 56,
                      borderRadius: 2,
                    }}
                  >
                    {val.toFixed(2)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>

      {/* Legend bar */}
      <div className="flex items-center gap-2 mt-3">
        <span className="text-[9px] font-mono" style={{ color: "var(--color-text-muted)" }}>
          -1.0
        </span>
        <div
          className="flex-1 h-2 rounded-full"
          style={{
            background: "linear-gradient(to right, #ff4466, #14141f, #4488ff)",
          }}
        />
        <span className="text-[9px] font-mono" style={{ color: "var(--color-text-muted)" }}>
          +1.0
        </span>
      </div>
    </div>
  );
}


/* ───────────── Rolling Correlation Chart ───────────── */

function RollingCorrelationChart({
  data,
  visiblePairs,
}: {
  data: CorrelationResult["rolling_correlations"];
  visiblePairs: Set<string>;
}) {
  // Merge all pair series into a shared time-indexed dataset
  const chartData = useMemo(() => {
    const dateMap = new Map<string, Record<string, string | number>>();
    for (const rc of data) {
      if (!visiblePairs.has(rc.pair)) continue;
      for (const pt of rc.series) {
        const row = dateMap.get(pt.date) || { date: pt.date };
        row[rc.pair] = pt.value;
        dateMap.set(pt.date, row);
      }
    }
    return [...dateMap.values()].sort((a, b) =>
      String(a.date).localeCompare(String(b.date))
    );
  }, [data, visiblePairs]);

  if (chartData.length === 0) {
    return (
      <div className="flex items-center justify-center py-8">
        <p className="text-[11px]" style={{ color: "var(--color-text-muted)" }}>
          Select pairs to display
        </p>
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <LineChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: -10 }}>
        <CartesianGrid
          strokeDasharray="3 3"
          stroke={CHART_COLORS.grid}
          vertical={false}
        />
        <XAxis
          dataKey="date"
          tick={{ fill: CHART_COLORS.axis, fontSize: 10 }}
          tickFormatter={(d: string) => d.slice(0, 7)}
          minTickGap={60}
        />
        <YAxis
          domain={[-1, 1]}
          tick={{ fill: CHART_COLORS.axis, fontSize: 10 }}
          tickFormatter={(v: number) => v.toFixed(1)}
        />
        <Tooltip
          contentStyle={{
            background: CHART_COLORS.tooltip,
            border: "1px solid var(--color-border)",
            borderRadius: 6,
            fontSize: 11,
          }}
          labelStyle={{ color: "var(--color-text-muted)", fontSize: 10 }}
          formatter={((value: number) => [value.toFixed(3), ""]) as never}
        />
        <ReferenceLine y={0} stroke="var(--color-border)" strokeDasharray="4 4" />
        <ReferenceLine y={0.7} stroke="rgba(255,68,102,0.2)" strokeDasharray="2 2" />
        <ReferenceLine y={-0.7} stroke="rgba(255,68,102,0.2)" strokeDasharray="2 2" />
        {data.map((rc, i) =>
          visiblePairs.has(rc.pair) ? (
            <Line
              key={rc.pair}
              type="monotone"
              dataKey={rc.pair}
              stroke={PAIR_COLORS[i % PAIR_COLORS.length]}
              strokeWidth={1.5}
              dot={false}
              name={rc.pair}
              connectNulls
            />
          ) : null
        )}
      </LineChart>
    </ResponsiveContainer>
  );
}


/* ───────────── Pair Discovery Table ───────────── */

function PairDiscoveryTable({
  pairs,
  onSelectPair,
  activePair,
}: {
  pairs: PairTestResult[];
  onSelectPair: (pair: PairTestResult) => void;
  activePair: { a: string; b: string } | null;
}) {
  if (pairs.length === 0) {
    return (
      <p className="text-[12px] py-4" style={{ color: "var(--color-text-muted)" }}>
        No pairs tested — add more tickers.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-[11px]">
        <thead>
          <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
            {["Pair", "Status", "ADF Stat", "p-value", "β", "Half-Life", "Z-Score", ""].map(
              (h) => (
                <th
                  key={h}
                  className="px-3 py-2 text-left font-medium"
                  style={{ color: "var(--color-text-muted)" }}
                >
                  {h}
                </th>
              )
            )}
          </tr>
        </thead>
        <tbody>
          {pairs.map((p) => {
            const isActive =
              activePair?.a === p.ticker_a && activePair?.b === p.ticker_b;
            return (
              <tr
                key={`${p.ticker_a}-${p.ticker_b}`}
                className="transition-colors"
                style={{
                  borderBottom: "1px solid var(--color-border)",
                  background: isActive ? "rgba(68,136,255,0.06)" : undefined,
                }}
              >
                <td className="px-3 py-2.5 font-mono font-medium" style={{ color: "var(--color-text-primary)" }}>
                  {p.ticker_a}/{p.ticker_b}
                </td>
                <td className="px-3 py-2.5">
                  {p.cointegrated ? (
                    <span className="inline-flex items-center gap-1 text-[10px] font-medium" style={{ color: "var(--color-accent-green)" }}>
                      <CheckCircle size={11} /> Cointegrated
                    </span>
                  ) : (
                    <span className="text-[10px]" style={{ color: "var(--color-text-muted)" }}>
                      Not significant
                    </span>
                  )}
                </td>
                <td className="px-3 py-2.5 font-mono tabular-nums" style={{ color: "var(--color-text-secondary)" }}>
                  {p.adf_statistic.toFixed(2)}
                </td>
                <td className="px-3 py-2.5 font-mono tabular-nums">
                  <span
                    style={{
                      color: p.adf_pvalue < 0.05
                        ? "var(--color-accent-green)"
                        : p.adf_pvalue < 0.10
                        ? "var(--color-accent-yellow)"
                        : "var(--color-text-muted)",
                    }}
                  >
                    {p.adf_pvalue < 0.001 ? "<0.001" : p.adf_pvalue.toFixed(3)}
                  </span>
                </td>
                <td className="px-3 py-2.5 font-mono tabular-nums" style={{ color: "var(--color-text-secondary)" }}>
                  {p.beta.toFixed(3)}
                </td>
                <td className="px-3 py-2.5 font-mono tabular-nums" style={{ color: "var(--color-text-secondary)" }}>
                  {p.half_life_days != null ? `${p.half_life_days}d` : "—"}
                </td>
                <td className="px-3 py-2.5 font-mono tabular-nums">
                  {p.current_zscore != null ? (
                    <span
                      style={{
                        color:
                          Math.abs(p.current_zscore) > 2
                            ? "var(--color-accent-red)"
                            : Math.abs(p.current_zscore) > 1
                            ? "var(--color-accent-yellow)"
                            : "var(--color-text-secondary)",
                      }}
                    >
                      {p.current_zscore > 0 ? "+" : ""}
                      {p.current_zscore.toFixed(2)}σ
                    </span>
                  ) : (
                    "—"
                  )}
                </td>
                <td className="px-3 py-2.5">
                  <button
                    onClick={() => onSelectPair(p)}
                    className="px-2 py-1 rounded text-[10px] font-medium transition-all"
                    style={{
                      background: isActive
                        ? "var(--color-accent-blue)"
                        : "rgba(68,136,255,0.1)",
                      color: isActive ? "#fff" : "var(--color-accent-blue)",
                      border: `1px solid ${isActive ? "var(--color-accent-blue)" : "rgba(68,136,255,0.25)"}`,
                    }}
                  >
                    Spread
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}


/* ───────────── Spread Drill-Down ───────────── */

function SpreadDrillDown({ result }: { result: SpreadResult }) {
  const coint = result.cointegration;

  return (
    <div className="space-y-5">
      {/* Key stats row */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <StatCard label="Half-Life" value={result.half_life_days != null ? `${result.half_life_days}d` : "—"} />
        <StatCard
          label="Current Z"
          value={result.current_zscore != null ? `${result.current_zscore > 0 ? "+" : ""}${result.current_zscore.toFixed(2)}σ` : "—"}
          color={
            result.current_zscore != null && Math.abs(result.current_zscore) > 2
              ? "var(--color-accent-red)"
              : result.current_zscore != null && Math.abs(result.current_zscore) > 1
              ? "var(--color-accent-yellow)"
              : undefined
          }
        />
        <StatCard label="Spread μ" value={result.spread_mean.toFixed(4)} />
        <StatCard label="Spread σ" value={result.spread_std.toFixed(4)} />
        <StatCard
          label="ADF p-value"
          value={coint.adf_pvalue < 0.001 ? "<0.001" : coint.adf_pvalue.toFixed(3)}
          color={coint.cointegrated ? "var(--color-accent-green)" : undefined}
        />
      </div>

      {/* Z-Score chart */}
      <div>
        <p className="section-label mb-2">Z-Score</p>
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={result.zscore_series} margin={{ top: 5, right: 10, bottom: 5, left: -10 }}>
            <defs>
              <linearGradient id="zscoreGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={CHART_COLORS.blue} stopOpacity={0.3} />
                <stop offset="50%" stopColor={CHART_COLORS.blue} stopOpacity={0} />
                <stop offset="100%" stopColor={CHART_COLORS.negative} stopOpacity={0.3} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} vertical={false} />
            <XAxis
              dataKey="date"
              tick={{ fill: CHART_COLORS.axis, fontSize: 10 }}
              tickFormatter={(d: string) => d.slice(0, 7)}
              minTickGap={60}
            />
            <YAxis tick={{ fill: CHART_COLORS.axis, fontSize: 10 }} />
            <Tooltip
              contentStyle={{
                background: CHART_COLORS.tooltip,
                border: "1px solid var(--color-border)",
                borderRadius: 6,
                fontSize: 11,
              }}
              labelStyle={{ color: "var(--color-text-muted)", fontSize: 10 }}
              formatter={((v: number) => [`${v.toFixed(3)}σ`, "Z-Score"]) as never}
            />
            <ReferenceLine y={0} stroke="var(--color-border)" />
            <ReferenceLine y={2} stroke="rgba(255,68,102,0.4)" strokeDasharray="4 4" label={{ value: "+2σ", fill: "var(--color-text-muted)", fontSize: 9, position: "right" }} />
            <ReferenceLine y={-2} stroke="rgba(255,68,102,0.4)" strokeDasharray="4 4" label={{ value: "-2σ", fill: "var(--color-text-muted)", fontSize: 9, position: "right" }} />
            <ReferenceLine y={1} stroke="rgba(255,187,51,0.3)" strokeDasharray="2 2" />
            <ReferenceLine y={-1} stroke="rgba(255,187,51,0.3)" strokeDasharray="2 2" />
            <Area
              type="monotone"
              dataKey="value"
              stroke={CHART_COLORS.blue}
              strokeWidth={1.5}
              fill="url(#zscoreGrad)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Log spread chart */}
      <div>
        <p className="section-label mb-2">Log Price Ratio Spread</p>
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={result.spread_series} margin={{ top: 5, right: 10, bottom: 5, left: -10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} vertical={false} />
            <XAxis
              dataKey="date"
              tick={{ fill: CHART_COLORS.axis, fontSize: 10 }}
              tickFormatter={(d: string) => d.slice(0, 7)}
              minTickGap={60}
            />
            <YAxis tick={{ fill: CHART_COLORS.axis, fontSize: 10 }} />
            <Tooltip
              contentStyle={{
                background: CHART_COLORS.tooltip,
                border: "1px solid var(--color-border)",
                borderRadius: 6,
                fontSize: 11,
              }}
              labelStyle={{ color: "var(--color-text-muted)", fontSize: 10 }}
              formatter={((v: number) => [v.toFixed(4), "Spread"]) as never}
            />
            <ReferenceLine y={result.spread_mean} stroke="rgba(136,85,255,0.5)" strokeDasharray="4 4" label={{ value: "μ", fill: "var(--color-text-muted)", fontSize: 9, position: "right" }} />
            <Line type="monotone" dataKey="value" stroke={CHART_COLORS.purple} strokeWidth={1.2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Interpretation */}
      <div
        className="px-4 py-3 rounded text-[11px] leading-relaxed"
        style={{
          background: "rgba(68,136,255,0.05)",
          border: "1px solid rgba(68,136,255,0.15)",
          color: "var(--color-text-secondary)",
        }}
      >
        <strong style={{ color: "var(--color-text-primary)" }}>Interpretation:</strong>{" "}
        {coint.cointegrated ? (
          <>
            This pair shows statistically significant cointegration (p={coint.adf_pvalue.toFixed(3)}).
            {result.half_life_days != null && result.half_life_days < 30 && (
              <> The half-life of {result.half_life_days}d suggests rapid mean reversion — suitable for pairs trading. </>
            )}
            {result.half_life_days != null && result.half_life_days >= 30 && result.half_life_days < 90 && (
              <> The half-life of {result.half_life_days}d indicates moderate mean-reversion speed. </>
            )}
            {result.half_life_days != null && result.half_life_days >= 90 && (
              <> However, the half-life of {result.half_life_days}d is quite long — mean reversion is slow. </>
            )}
            {result.current_zscore != null && Math.abs(result.current_zscore) > 2 && (
              <> The current z-score of {result.current_zscore.toFixed(2)}σ is extreme — potential entry opportunity. </>
            )}
          </>
        ) : (
          <>
            No significant cointegration detected (p={coint.adf_pvalue.toFixed(3)}).
            The spread between these assets appears non-stationary — pairs trading is not recommended.
          </>
        )}
      </div>
    </div>
  );
}


function StatCard({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <div
      className="px-3 py-2.5 rounded"
      style={{
        background: "var(--color-bg-primary)",
        border: "1px solid var(--color-border)",
      }}
    >
      <p className="text-[9px] uppercase tracking-wider mb-1" style={{ color: "var(--color-text-muted)" }}>
        {label}
      </p>
      <p
        className="text-[14px] font-mono font-semibold tabular-nums"
        style={{ color: color || "var(--color-text-primary)" }}
      >
        {value}
      </p>
    </div>
  );
}
