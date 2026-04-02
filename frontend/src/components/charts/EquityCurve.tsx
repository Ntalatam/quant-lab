"use client";

import { useState, useCallback, useRef } from "react";
import type { TimeSeriesPoint, Trade } from "@/lib/types";
import { formatCurrency, formatPercent } from "@/lib/formatters";
import { CHART_COLORS } from "@/lib/constants";
import { X } from "lucide-react";
import {
  LightweightChart,
  AreaSeries,
  LineSeries,
  createSeriesMarkers,
  toTime,
  type IChartApi,
  type ISeriesApi,
  type MouseEventParams,
  type Time,
  type LogicalRange,
  type SeriesMarker,
} from "./LightweightChartWrapper";
import type { SingleValueData, LineData } from "lightweight-charts";

// ── Floating legend ──────────────────────────────────────────────────────

interface LegendData {
  date: string;
  strategy: number | null;
  benchmark: number | null;
  clean: number | null;
}

function ChartLegend({
  legend,
  initialCapital,
}: {
  legend: LegendData | null;
  initialCapital: number;
}) {
  if (!legend) return null;
  const pct = (val: number | null) =>
    val != null
      ? formatPercent(((val - initialCapital) / initialCapital) * 100)
      : "—";
  const fmt = (val: number | null) =>
    val != null ? formatCurrency(val) : "—";
  const color = (val: number | null) =>
    val != null && val >= initialCapital
      ? CHART_COLORS.positive
      : CHART_COLORS.negative;

  return (
    <div
      className="absolute top-2 left-3 z-10 flex items-center gap-5 pointer-events-none select-none"
      style={{ fontFamily: "ui-monospace, monospace", fontSize: 11 }}
    >
      {legend.strategy != null && (
        <span className="flex items-center gap-1.5">
          <span
            className="inline-block w-2.5 h-0.5 rounded-full"
            style={{ background: CHART_COLORS.strategy }}
          />
          <span className="text-text-muted">Strategy</span>
          <span style={{ color: color(legend.strategy) }}>
            {fmt(legend.strategy)}
          </span>
          <span style={{ color: color(legend.strategy), opacity: 0.7 }}>
            {pct(legend.strategy)}
          </span>
        </span>
      )}
      {legend.benchmark != null && (
        <span className="flex items-center gap-1.5">
          <span
            className="inline-block w-2.5 h-0.5 rounded-full"
            style={{ background: CHART_COLORS.benchmark }}
          />
          <span className="text-text-muted">Benchmark</span>
          <span className="text-text-secondary">
            {fmt(legend.benchmark)}
          </span>
        </span>
      )}
      {legend.clean != null && (
        <span className="flex items-center gap-1.5">
          <span
            className="inline-block w-2.5 h-0.5 rounded-full"
            style={{ background: CHART_COLORS.blue, opacity: 0.6 }}
          />
          <span className="text-text-muted">No-Cost</span>
          <span className="text-text-secondary">
            {fmt(legend.clean)}
          </span>
        </span>
      )}
    </div>
  );
}

// ── Trade detail panel ─────────────────────────────────────────────────

interface TradePanelProps {
  trade: Trade;
  onClose: () => void;
}

function TradePanel({ trade, onClose }: TradePanelProps) {
  const pnlPositive = (trade.pnl ?? 0) >= 0;
  return (
    <div
      className="absolute top-0 right-0 w-64 z-20 rounded-md"
      style={{
        background: "var(--color-bg-card-alt)",
        border: "1px solid var(--color-border-strong)",
        boxShadow: "0 4px 24px rgba(0,0,0,0.7)",
      }}
    >
      <div
        className="flex items-center justify-between px-4 py-2.5"
        style={{ borderBottom: "1px solid var(--color-border)" }}
      >
        <div className="flex items-center gap-2">
          <span
            className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded"
            style={{
              background:
                trade.side === "BUY"
                  ? "rgba(0,212,170,0.15)"
                  : "rgba(255,68,102,0.15)",
              color:
                trade.side === "BUY"
                  ? CHART_COLORS.positive
                  : CHART_COLORS.negative,
              border: `1px solid ${trade.side === "BUY" ? "rgba(0,212,170,0.3)" : "rgba(255,68,102,0.3)"}`,
            }}
          >
            {trade.side}
          </span>
          <span className="font-mono font-semibold text-text-primary text-sm">
            {trade.ticker}
          </span>
        </div>
        <button
          onClick={onClose}
          className="text-text-muted hover:text-text-primary transition-colors"
        >
          <X size={14} />
        </button>
      </div>
      <div className="p-4 space-y-2">
        {[
          { label: "Entry Date", value: trade.entry_date ?? "—" },
          {
            label: "Entry Price",
            value:
              trade.entry_price != null
                ? `$${trade.entry_price.toFixed(2)}`
                : "—",
          },
          { label: "Exit Date", value: trade.exit_date ?? "Open" },
          {
            label: "Exit Price",
            value:
              trade.exit_price != null
                ? `$${trade.exit_price.toFixed(2)}`
                : "—",
          },
          { label: "Shares", value: String(trade.shares) },
          {
            label: "Commission",
            value: `$${(trade.commission ?? 0).toFixed(2)}`,
          },
          {
            label: "Slippage",
            value: `$${(trade.slippage ?? 0).toFixed(2)}`,
          },
        ].map(({ label, value }) => (
          <div key={label} className="flex justify-between text-xs">
            <span className="text-text-muted">{label}</span>
            <span className="font-mono text-text-primary">{value}</span>
          </div>
        ))}
        {trade.pnl != null && (
          <div
            className="rounded p-2.5 mt-2 text-center"
            style={{
              background: pnlPositive
                ? "rgba(0,212,170,0.08)"
                : "rgba(255,68,102,0.08)",
              border: `1px solid ${pnlPositive ? "rgba(0,212,170,0.2)" : "rgba(255,68,102,0.2)"}`,
            }}
          >
            <p className="section-label mb-0.5">P&L</p>
            <p
              className="font-mono tabular-nums font-bold text-base"
              style={{
                color: pnlPositive
                  ? CHART_COLORS.positive
                  : CHART_COLORS.negative,
              }}
            >
              {pnlPositive ? "+" : ""}${trade.pnl.toFixed(2)}
            </p>
            {trade.pnl_pct != null && (
              <p className="text-[10px] text-text-muted mt-0.5 font-mono">
                {formatPercent(trade.pnl_pct, 2)}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────

interface EquityCurveProps {
  equity: TimeSeriesPoint[];
  benchmark: TimeSeriesPoint[];
  cleanEquity?: TimeSeriesPoint[];
  trades?: Trade[];
  height?: number;
  syncRange?: LogicalRange | null;
  onVisibleRangeChange?: (range: LogicalRange | null) => void;
}

export function EquityCurve({
  equity,
  benchmark,
  cleanEquity,
  trades = [],
  height = 380,
  syncRange,
  onVisibleRangeChange,
}: EquityCurveProps) {
  const [selectedTrade, setSelectedTrade] = useState<Trade | null>(null);
  const [legend, setLegend] = useState<LegendData | null>(null);
  const initialCapital = equity.length > 0 ? equity[0].value : 100_000;

  const showClean = cleanEquity && cleanEquity.length > 0;

  // Build lookup maps for crosshair legend
  const benchMap = useRef(new Map<string, number>());
  const cleanMap = useRef(new Map<string, number>());
  if (benchMap.current.size === 0) {
    benchmark.forEach((p) => benchMap.current.set(p.date, p.value));
    cleanEquity?.forEach((p) => cleanMap.current.set(p.date, p.value));
  }

  // Trade index for click lookup
  const tradesByDate = useRef(new Map<string, Trade>());
  if (tradesByDate.current.size === 0 && trades.length > 0) {
    trades.forEach((t) => {
      if (t.entry_date) tradesByDate.current.set(t.entry_date, t);
      if (t.exit_date) tradesByDate.current.set(t.exit_date, t);
    });
  }

  const handleInit = useCallback(
    (chart: IChartApi) => {
      // ── Strategy area ──
      const strategySeries = chart.addSeries(AreaSeries, {
        lineColor: CHART_COLORS.strategy,
        topColor: "rgba(0,212,170,0.28)",
        bottomColor: "rgba(0,212,170,0.02)",
        lineWidth: 2,
        priceFormat: {
          type: "custom",
          formatter: (v: number) => `$${(v / 1000).toFixed(1)}k`,
        },
        crosshairMarkerRadius: 4,
        crosshairMarkerBackgroundColor: CHART_COLORS.strategy,
        crosshairMarkerBorderWidth: 1,
        crosshairMarkerBorderColor: "#fff",
      });

      const equityData: SingleValueData<Time>[] = equity.map((p) => ({
        time: toTime(p.date),
        value: p.value,
      }));
      strategySeries.setData(equityData);

      // ── Trade markers ──
      if (trades.length > 0) {
        const markers: SeriesMarker<Time>[] = [];
        trades.forEach((t) => {
          if (t.entry_date) {
            markers.push({
              time: toTime(t.entry_date),
              position: "belowBar",
              color: CHART_COLORS.positive,
              shape: "arrowUp",
              text: "",
              size: 0.8,
            });
          }
          if (t.exit_date) {
            markers.push({
              time: toTime(t.exit_date),
              position: "aboveBar",
              color: CHART_COLORS.negative,
              shape: "arrowDown",
              text: "",
              size: 0.8,
            });
          }
        });
        markers.sort(
          (a, b) => (a.time as string).localeCompare(b.time as string)
        );
        createSeriesMarkers(strategySeries, markers);
      }

      // ── Benchmark line ──
      const benchSeries = chart.addSeries(LineSeries, {
        color: CHART_COLORS.benchmark,
        lineWidth: 1,
        lineStyle: 2, // dashed
        priceFormat: {
          type: "custom",
          formatter: (v: number) => `$${(v / 1000).toFixed(1)}k`,
        },
        crosshairMarkerRadius: 3,
        crosshairMarkerBackgroundColor: CHART_COLORS.benchmark,
      });
      benchSeries.setData(
        benchmark.map((p) => ({
          time: toTime(p.date),
          value: p.value,
        })) as LineData<Time>[]
      );

      // ── Clean (no-cost) line ──
      let cleanSeries: ISeriesApi<"Line"> | null = null;
      if (showClean && cleanEquity) {
        cleanSeries = chart.addSeries(LineSeries, {
          color: CHART_COLORS.blue,
          lineWidth: 1,
          lineStyle: 2,
          priceFormat: {
            type: "custom",
            formatter: (v: number) => `$${(v / 1000).toFixed(1)}k`,
          },
          crosshairMarkerRadius: 3,
          crosshairMarkerBackgroundColor: CHART_COLORS.blue,
        });
        cleanSeries.setData(
          cleanEquity.map((p) => ({
            time: toTime(p.date),
            value: p.value,
          })) as LineData<Time>[]
        );
      }

      // ── Crosshair legend ──
      chart.subscribeCrosshairMove((param: MouseEventParams<Time>) => {
        if (!param.time) {
          const last = equity[equity.length - 1];
          if (last) {
            setLegend({
              date: last.date,
              strategy: last.value,
              benchmark: benchMap.current.get(last.date) ?? null,
              clean: cleanMap.current.get(last.date) ?? null,
            });
          }
          return;
        }
        const dateStr = param.time as string;
        const strat = param.seriesData?.get(strategySeries) as
          | SingleValueData<Time>
          | undefined;
        const bench = param.seriesData?.get(benchSeries) as
          | SingleValueData<Time>
          | undefined;
        const clean = cleanSeries
          ? (param.seriesData?.get(cleanSeries) as
              | SingleValueData<Time>
              | undefined)
          : undefined;

        setLegend({
          date: dateStr,
          strategy: strat?.value ?? null,
          benchmark: bench?.value ?? null,
          clean: clean?.value ?? null,
        });
      });

      // ── Click → trade panel ──
      chart.subscribeClick((param: MouseEventParams<Time>) => {
        if (!param.time) return;
        const dateStr = param.time as string;
        const trade = tradesByDate.current.get(dateStr);
        if (trade) setSelectedTrade(trade);
        else setSelectedTrade(null);
      });

      // Set initial legend
      const last = equity[equity.length - 1];
      if (last) {
        setLegend({
          date: last.date,
          strategy: last.value,
          benchmark: benchMap.current.get(last.date) ?? null,
          clean: cleanMap.current.get(last.date) ?? null,
        });
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [equity, benchmark, cleanEquity, trades]
  );

  return (
    <div className="relative">
      <ChartLegend legend={legend} initialCapital={initialCapital} />
      <LightweightChart
        key={equity.length}
        height={height}
        onInit={handleInit}
        syncRange={syncRange}
        onVisibleRangeChange={onVisibleRangeChange}
      />

      {/* Trade legend hints */}
      {trades.length > 0 && (
        <div className="flex items-center gap-4 mt-1.5 ml-1">
          <div className="flex items-center gap-1.5">
            <span style={{ color: CHART_COLORS.positive, fontSize: 14 }}>
              ▲
            </span>
            <span className="text-[10px] text-text-muted">
              Entry (BUY)
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <span style={{ color: CHART_COLORS.negative, fontSize: 14 }}>
              ▼
            </span>
            <span className="text-[10px] text-text-muted">
              Exit (SELL)
            </span>
          </div>
          <span className="text-[10px] text-text-muted">
            — click any marker for trade details
          </span>
        </div>
      )}

      {selectedTrade && (
        <TradePanel
          trade={selectedTrade}
          onClose={() => setSelectedTrade(null)}
        />
      )}
    </div>
  );
}
