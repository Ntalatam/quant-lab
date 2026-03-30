"use client";

import { useState } from "react";
import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  Scatter,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from "recharts";
import type { TimeSeriesPoint, Trade } from "@/lib/types";
import { formatCurrency, formatCompactDate, formatPercent } from "@/lib/formatters";
import { CHART_COLORS } from "@/lib/constants";
import { X } from "lucide-react";

type MarkerProps = {
  cx?: number | string;
  cy?: number | string;
  payload?: TradePoint;
  onClick?: (trade: Trade) => void;
};

// Custom BUY triangle (pointing up, green)
function BuyMarker({ cx, cy, payload, onClick }: MarkerProps) {
  const x = Number(cx ?? 0);
  const y = Number(cy ?? 0);
  return (
    <g
      onClick={(e) => { e.stopPropagation(); if (onClick && payload?.trade) onClick(payload.trade); }}
      style={{ cursor: "pointer" }}
    >
      <polygon
        points={`${x},${y - 8} ${x - 5},${y + 2} ${x + 5},${y + 2}`}
        fill={CHART_COLORS.positive}
        fillOpacity={0.9}
        stroke={CHART_COLORS.positive}
        strokeWidth={1}
      />
    </g>
  );
}

// Custom SELL triangle (pointing down, red)
function SellMarker({ cx, cy, payload, onClick }: MarkerProps) {
  const x = Number(cx ?? 0);
  const y = Number(cy ?? 0);
  return (
    <g
      onClick={(e) => { e.stopPropagation(); if (onClick && payload?.trade) onClick(payload.trade); }}
      style={{ cursor: "pointer" }}
    >
      <polygon
        points={`${x},${y + 8} ${x - 5},${y - 2} ${x + 5},${y - 2}`}
        fill={CHART_COLORS.negative}
        fillOpacity={0.9}
        stroke={CHART_COLORS.negative}
        strokeWidth={1}
      />
    </g>
  );
}

interface TradePoint {
  date: string;
  equity: number;
  trade: Trade;
}

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
      {/* Header */}
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

      {/* Body */}
      <div className="p-4 space-y-2">
        {[
          { label: "Entry Date",  value: trade.entry_date ?? "—" },
          { label: "Entry Price", value: trade.entry_price != null ? `$${trade.entry_price.toFixed(2)}` : "—" },
          { label: "Exit Date",   value: trade.exit_date ?? "Open" },
          { label: "Exit Price",  value: trade.exit_price != null ? `$${trade.exit_price.toFixed(2)}` : "—" },
          { label: "Shares",      value: String(trade.shares) },
          { label: "Commission",  value: `$${(trade.commission ?? 0).toFixed(2)}` },
          { label: "Slippage",    value: `$${(trade.slippage ?? 0).toFixed(2)}` },
        ].map(({ label, value }) => (
          <div key={label} className="flex justify-between text-xs">
            <span className="text-text-muted">{label}</span>
            <span className="font-mono text-text-primary">{value}</span>
          </div>
        ))}

        {/* P&L highlight */}
        {trade.pnl != null && (
          <div
            className="rounded p-2.5 mt-2 text-center"
            style={{
              background: pnlPositive ? "rgba(0,212,170,0.08)" : "rgba(255,68,102,0.08)",
              border: `1px solid ${pnlPositive ? "rgba(0,212,170,0.2)" : "rgba(255,68,102,0.2)"}`,
            }}
          >
            <p className="section-label mb-0.5">P&L</p>
            <p
              className="font-mono tabular-nums font-bold text-base"
              style={{ color: pnlPositive ? CHART_COLORS.positive : CHART_COLORS.negative }}
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

interface EquityCurveProps {
  equity: TimeSeriesPoint[];
  benchmark: TimeSeriesPoint[];
  cleanEquity?: TimeSeriesPoint[];
  trades?: Trade[];
  height?: number;
}

export function EquityCurve({
  equity,
  benchmark,
  cleanEquity,
  trades = [],
  height = 350,
}: EquityCurveProps) {
  const [selectedTrade, setSelectedTrade] = useState<Trade | null>(null);
  const showClean = cleanEquity && cleanEquity.length > 0;
  const showMarkers = trades.length > 0;

  // Build date → equity value map for scatter positioning
  const equityByDate = new Map<string, number>();
  equity.forEach((p) => equityByDate.set(p.date, p.value));

  // Merge main series by date
  const dateMap = new Map<
    string,
    { date: string; equity: number; benchmark: number; clean?: number }
  >();
  equity.forEach((p) => {
    dateMap.set(p.date, { date: p.date, equity: p.value, benchmark: 0 });
  });
  benchmark.forEach((p) => {
    const ex = dateMap.get(p.date);
    if (ex) ex.benchmark = p.value;
    else dateMap.set(p.date, { date: p.date, equity: 0, benchmark: p.value });
  });
  if (showClean) {
    cleanEquity!.forEach((p) => {
      const ex = dateMap.get(p.date);
      if (ex) ex.clean = p.value;
    });
  }
  const data = Array.from(dateMap.values()).sort(
    (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()
  );

  // Build trade scatter points — BUY markers at entry date, SELL markers at exit date
  const buyPoints: TradePoint[] = [];
  const sellPoints: TradePoint[] = [];

  if (showMarkers) {
    // Build sorted date array for nearest-date lookup
    const sortedDates = Array.from(equityByDate.keys()).sort();

    const nearestEquity = (dateStr: string): number => {
      if (equityByDate.has(dateStr)) return equityByDate.get(dateStr)!;
      // Find nearest available date
      const d = new Date(dateStr).getTime();
      let best = sortedDates[0];
      let bestDiff = Math.abs(new Date(best).getTime() - d);
      for (const sd of sortedDates) {
        const diff = Math.abs(new Date(sd).getTime() - d);
        if (diff < bestDiff) { bestDiff = diff; best = sd; }
      }
      return equityByDate.get(best) ?? 0;
    };

    trades.forEach((t) => {
      if (t.entry_date) {
        buyPoints.push({ date: t.entry_date, equity: nearestEquity(t.entry_date), trade: t });
      }
      if (t.exit_date) {
        sellPoints.push({ date: t.exit_date, equity: nearestEquity(t.exit_date), trade: t });
      }
    });
  }

  const formatLabel = (name: string) => {
    if (name === "equity") return "Strategy";
    if (name === "clean")  return "No-Cost";
    if (name === "benchmark") return "Benchmark";
    return name;
  };

  return (
    <div className="relative">
      <ResponsiveContainer width="100%" height={height}>
        <ComposedChart data={data} margin={{ top: 5, right: 5, bottom: 5, left: 5 }}>
          <defs>
            <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor={CHART_COLORS.strategy} stopOpacity={0.25} />
              <stop offset="95%" stopColor={CHART_COLORS.strategy} stopOpacity={0}    />
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
            tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
            stroke={CHART_COLORS.axis}
            tick={{ fontSize: 11 }}
            width={60}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: CHART_COLORS.tooltip,
              border: `1px solid ${CHART_COLORS.grid}`,
              borderRadius: 4,
              fontSize: 12,
            }}
            formatter={(value, name) =>
              typeof value === "number"
                ? [formatCurrency(value), formatLabel(String(name))]
                : [value, name]
            }
            labelFormatter={(label) => formatCompactDate(String(label))}
          />
          <Legend formatter={formatLabel} />
          <Area
            type="monotone"
            dataKey="equity"
            stroke={CHART_COLORS.strategy}
            fill="url(#equityGradient)"
            strokeWidth={2}
            dot={false}
          />
          {showClean && (
            <Line
              type="monotone"
              dataKey="clean"
              stroke={CHART_COLORS.blue}
              strokeWidth={1.5}
              dot={false}
              strokeDasharray="5 3"
            />
          )}
          <Line
            type="monotone"
            dataKey="benchmark"
            stroke={CHART_COLORS.benchmark}
            strokeWidth={1.5}
            dot={false}
            strokeDasharray="4 3"
          />

          {/* BUY markers */}
          {showMarkers && (
            <Scatter
              data={buyPoints}
              dataKey="equity"
              shape={(props: unknown) => (
                <BuyMarker
                  {...(props as MarkerProps)}
                  onClick={setSelectedTrade}
                />
              )}
              legendType="none"
            />
          )}

          {/* SELL markers */}
          {showMarkers && (
            <Scatter
              data={sellPoints}
              dataKey="equity"
              shape={(props: unknown) => (
                <SellMarker
                  {...(props as MarkerProps)}
                  onClick={setSelectedTrade}
                />
              )}
              legendType="none"
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>

      {/* Trade legend hints */}
      {showMarkers && (
        <div className="flex items-center gap-4 mt-2 ml-2">
          <div className="flex items-center gap-1.5">
            <svg width="10" height="10" viewBox="0 0 10 10">
              <polygon points="5,0 0,10 10,10" fill={CHART_COLORS.positive} />
            </svg>
            <span className="text-[10px] text-text-muted">Entry (BUY)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <svg width="10" height="10" viewBox="0 0 10 10">
              <polygon points="5,10 0,0 10,0" fill={CHART_COLORS.negative} />
            </svg>
            <span className="text-[10px] text-text-muted">Exit (SELL)</span>
          </div>
          <span className="text-[10px] text-text-muted">— click any marker for trade details</span>
        </div>
      )}

      {/* Trade detail panel */}
      {selectedTrade && (
        <TradePanel
          trade={selectedTrade}
          onClose={() => setSelectedTrade(null)}
        />
      )}
    </div>
  );
}
