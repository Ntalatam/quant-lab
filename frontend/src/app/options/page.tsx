"use client";

import { useState, useMemo } from "react";
import { api } from "@/lib/api";
import { CHART_COLORS } from "@/lib/constants";
import type {
  OptionPriceResult,
  VolSurfaceResult,
  PnlScenarioResult,
  OptionsChainEntry,
} from "@/lib/types";
import {
  Loader2,
  Calculator,
  BarChart3,
  Layers,
  TrendingUp,
} from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
  ScatterChart,
  Scatter,
  ZAxis,
  Cell,
} from "recharts";

const TAB_ITEMS = [
  { id: "pricer", label: "Pricer & Greeks", icon: Calculator },
  { id: "surface", label: "Vol Surface", icon: Layers },
  { id: "chain", label: "Options Chain", icon: BarChart3 },
  { id: "pnl", label: "P&L Scenario", icon: TrendingUp },
] as const;

type TabId = (typeof TAB_ITEMS)[number]["id"];

const PNL_COLORS = ["#00d4aa", "#4488ff", "#ffbb33", "#8855ff", "#ff4466"];

export default function OptionsPage() {
  const [activeTab, setActiveTab] = useState<TabId>("pricer");

  // Shared parameters
  const [spot, setSpot] = useState(150);
  const [strike, setStrike] = useState(155);
  const [dte, setDte] = useState(30);
  const [rate, setRate] = useState(0.05);
  const [vol, setVol] = useState(0.25);
  const [optionType, setOptionType] = useState<"call" | "put">("call");

  return (
    <div className="p-6 space-y-5 max-w-[1400px]">
      {/* Header */}
      <div>
        <h1 className="text-[20px] font-bold" style={{ color: "var(--color-text-primary)" }}>
          Options Lab
        </h1>
        <p className="text-[12px] mt-1" style={{ color: "var(--color-text-secondary)" }}>
          Black-Scholes pricing, Greeks analysis, volatility surface, and P&amp;L scenarios
        </p>
      </div>

      {/* Shared params bar */}
      <div className="card p-4">
        <div className="flex flex-wrap items-end gap-3">
          <ParamInput label="Spot" value={spot} onChange={setSpot} step={1} min={1} />
          <ParamInput label="Strike" value={strike} onChange={setStrike} step={1} min={1} />
          <ParamInput label="DTE" value={dte} onChange={setDte} step={1} min={0} max={3650} />
          <ParamInput label="Rate" value={rate} onChange={setRate} step={0.005} min={0} max={1} format="pct" />
          <ParamInput label="Vol" value={vol} onChange={setVol} step={0.01} min={0.01} max={5} format="pct" />
          <div>
            <label className="section-label block mb-1">Type</label>
            <div className="flex rounded overflow-hidden" style={{ border: "1px solid var(--color-border)" }}>
              {(["call", "put"] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setOptionType(t)}
                  className="px-3 py-1.5 text-[11px] font-medium transition-colors capitalize"
                  style={{
                    background: optionType === t ? "var(--color-accent-blue)" : "var(--color-bg-primary)",
                    color: optionType === t ? "#fff" : "var(--color-text-secondary)",
                  }}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1" style={{ borderBottom: "1px solid var(--color-border)" }}>
        {TAB_ITEMS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className="flex items-center gap-1.5 px-3 py-2 text-[12px] font-medium transition-colors relative"
            style={{
              color: activeTab === tab.id ? "var(--color-accent-blue)" : "var(--color-text-muted)",
              borderBottom: activeTab === tab.id ? "2px solid var(--color-accent-blue)" : "2px solid transparent",
              marginBottom: -1,
            }}
          >
            <tab.icon size={13} />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === "pricer" && (
        <PricerTab spot={spot} strike={strike} dte={dte} rate={rate} vol={vol} optionType={optionType} />
      )}
      {activeTab === "surface" && (
        <VolSurfaceTab spot={spot} rate={rate} vol={vol} />
      )}
      {activeTab === "chain" && (
        <ChainTab spot={spot} rate={rate} vol={vol} />
      )}
      {activeTab === "pnl" && (
        <PnlTab spot={spot} strike={strike} dte={dte} rate={rate} vol={vol} optionType={optionType} />
      )}
    </div>
  );
}


/* ───────────── Shared param input ───────────── */

function ParamInput({
  label, value, onChange, step, min, max, format,
}: {
  label: string; value: number; onChange: (v: number) => void;
  step: number; min?: number; max?: number; format?: "pct";
}) {
  return (
    <div>
      <label className="section-label block mb-1">{label}</label>
      <div className="flex items-center gap-1">
        <input
          type="number"
          value={format === "pct" ? (value * 100).toFixed(1) : value}
          onChange={(e) => {
            const v = parseFloat(e.target.value);
            if (!isNaN(v)) onChange(format === "pct" ? v / 100 : v);
          }}
          step={format === "pct" ? step * 100 : step}
          min={min !== undefined ? (format === "pct" ? min * 100 : min) : undefined}
          max={max !== undefined ? (format === "pct" ? max * 100 : max) : undefined}
          className="w-20 px-2 py-1.5 rounded text-[12px] font-mono tabular-nums text-right"
          style={{
            background: "var(--color-bg-primary)",
            color: "var(--color-text-primary)",
            border: "1px solid var(--color-border)",
          }}
        />
        {format === "pct" && (
          <span className="text-[10px]" style={{ color: "var(--color-text-muted)" }}>%</span>
        )}
      </div>
    </div>
  );
}


/* ───────────── Tab 1: Pricer & Greeks ───────────── */

function PricerTab({ spot, strike, dte, rate, vol, optionType }: {
  spot: number; strike: number; dte: number; rate: number; vol: number; optionType: "call" | "put";
}) {
  const [result, setResult] = useState<OptionPriceResult | null>(null);
  const [loading, setLoading] = useState(false);

  const price = async () => {
    setLoading(true);
    try {
      const r = await api.priceOption({
        spot, strike, days_to_expiry: dte, risk_free_rate: rate,
        volatility: vol, option_type: optionType,
      });
      setResult(r);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <button
        onClick={price}
        disabled={loading}
        className="px-4 py-2 rounded text-[12px] font-medium"
        style={{ background: "var(--color-accent-blue)", color: "#fff" }}
      >
        {loading ? <Loader2 size={12} className="animate-spin inline mr-1" /> : <Calculator size={12} className="inline mr-1" />}
        Price Option
      </button>

      {result && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <GreekCard label="Price" value={`$${result.price.toFixed(2)}`} sublabel={result.moneyness_label} />
          <GreekCard label="Delta (Δ)" value={result.delta.toFixed(4)} color={result.delta >= 0 ? "var(--color-accent-green)" : "var(--color-accent-red)"} />
          <GreekCard label="Gamma (Γ)" value={result.gamma.toFixed(6)} />
          <GreekCard label="Theta (Θ)" value={`${result.theta.toFixed(4)}/day`} color="var(--color-accent-red)" />
          <GreekCard label="Vega (ν)" value={`${result.vega.toFixed(4)}/1%`} />
          <GreekCard label="Rho (ρ)" value={`${result.rho.toFixed(4)}/1%`} />
          <GreekCard label="Intrinsic" value={`$${result.intrinsic.toFixed(2)}`} />
          <GreekCard label="Time Value" value={`$${result.time_value.toFixed(2)}`} />
        </div>
      )}

      {result && (
        <div
          className="px-4 py-3 rounded text-[11px] leading-relaxed space-y-1"
          style={{
            background: "rgba(68,136,255,0.05)",
            border: "1px solid rgba(68,136,255,0.15)",
            color: "var(--color-text-secondary)",
          }}
        >
          <p>
            <strong style={{ color: "var(--color-text-primary)" }}>Delta</strong> = {result.delta.toFixed(4)} → a $1 move in the underlying changes the option price by ${Math.abs(result.delta).toFixed(2)}.
          </p>
          <p>
            <strong style={{ color: "var(--color-text-primary)" }}>Theta</strong> = {result.theta.toFixed(4)}/day → the option loses ${Math.abs(result.theta).toFixed(4)} per calendar day from time decay.
          </p>
          <p>
            <strong style={{ color: "var(--color-text-primary)" }}>Vega</strong> = {result.vega.toFixed(4)} → a 1% increase in IV changes the option price by ${Math.abs(result.vega).toFixed(4)}.
          </p>
        </div>
      )}
    </div>
  );
}

function GreekCard({ label, value, sublabel, color }: {
  label: string; value: string; sublabel?: string; color?: string;
}) {
  return (
    <div className="px-3 py-2.5 rounded" style={{ background: "var(--color-bg-primary)", border: "1px solid var(--color-border)" }}>
      <p className="text-[9px] uppercase tracking-wider mb-1" style={{ color: "var(--color-text-muted)" }}>
        {label}
        {sublabel && <span className="ml-1 normal-case">({sublabel})</span>}
      </p>
      <p className="text-[15px] font-mono font-semibold tabular-nums" style={{ color: color || "var(--color-text-primary)" }}>
        {value}
      </p>
    </div>
  );
}


/* ───────────── Tab 2: Vol Surface ───────────── */

function VolSurfaceTab({ spot, rate, vol }: { spot: number; rate: number; vol: number }) {
  const [result, setResult] = useState<VolSurfaceResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [selectedExpiry, setSelectedExpiry] = useState<number | null>(null);

  const generate = async () => {
    setLoading(true);
    try {
      const r = await api.getVolSurface({ spot, risk_free_rate: rate, base_volatility: vol });
      setResult(r);
      setSelectedExpiry(null);
    } finally {
      setLoading(false);
    }
  };

  // Build per-expiry smile curves for the line chart
  const smileCurves = useMemo(() => {
    if (!result) return [];
    const expiries = selectedExpiry ? [selectedExpiry] : result.expiries;
    return expiries.map((dte) => ({
      dte,
      data: result.surface
        .filter((p) => p.dte === dte)
        .map((p) => ({ moneyness: p.moneyness, iv: p.implied_vol * 100 })),
    }));
  }, [result, selectedExpiry]);

  // Heatmap data
  const heatmapData = useMemo(() => {
    if (!result) return [];
    return result.surface.map((p) => ({
      x: p.moneyness,
      y: p.dte,
      iv: p.implied_vol * 100,
    }));
  }, [result]);

  return (
    <div className="space-y-4">
      <button
        onClick={generate}
        disabled={loading}
        className="px-4 py-2 rounded text-[12px] font-medium"
        style={{ background: "var(--color-accent-blue)", color: "#fff" }}
      >
        {loading ? <Loader2 size={12} className="animate-spin inline mr-1" /> : null}
        Generate Surface
      </button>

      {result && (
        <>
          {/* Expiry filter */}
          <div className="flex flex-wrap gap-1.5">
            <button
              onClick={() => setSelectedExpiry(null)}
              className="px-2 py-0.5 rounded text-[10px] font-mono"
              style={{
                background: !selectedExpiry ? "var(--color-accent-blue)" : "transparent",
                color: !selectedExpiry ? "#fff" : "var(--color-text-muted)",
                border: `1px solid ${!selectedExpiry ? "var(--color-accent-blue)" : "var(--color-border)"}`,
              }}
            >
              All
            </button>
            {result.expiries.map((e) => (
              <button
                key={e}
                onClick={() => setSelectedExpiry(e)}
                className="px-2 py-0.5 rounded text-[10px] font-mono"
                style={{
                  background: selectedExpiry === e ? "var(--color-accent-blue)" : "transparent",
                  color: selectedExpiry === e ? "#fff" : "var(--color-text-muted)",
                  border: `1px solid ${selectedExpiry === e ? "var(--color-accent-blue)" : "var(--color-border)"}`,
                }}
              >
                {e}d
              </button>
            ))}
          </div>

          {/* Smile chart */}
          <div className="card p-4">
            <p className="section-label mb-2">Volatility Smile</p>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} vertical={false} />
                <XAxis
                  dataKey="moneyness"
                  type="number"
                  domain={["auto", "auto"]}
                  tick={{ fill: CHART_COLORS.axis, fontSize: 10 }}
                  tickFormatter={(v: number) => v.toFixed(2)}
                  label={{ value: "Moneyness (K/S)", position: "insideBottom", offset: -2, fill: CHART_COLORS.axis, fontSize: 10 }}
                />
                <YAxis
                  tick={{ fill: CHART_COLORS.axis, fontSize: 10 }}
                  tickFormatter={(v: number) => `${v.toFixed(0)}%`}
                  label={{ value: "IV (%)", angle: -90, position: "insideLeft", fill: CHART_COLORS.axis, fontSize: 10 }}
                />
                <Tooltip
                  contentStyle={{ background: CHART_COLORS.tooltip, border: "1px solid var(--color-border)", borderRadius: 6, fontSize: 11 }}
                  formatter={((v: number) => [`${v.toFixed(1)}%`, "IV"]) as never}
                />
                <ReferenceLine x={1} stroke="var(--color-border)" strokeDasharray="4 4" />
                {smileCurves.map((curve, i) => (
                  <Line
                    key={curve.dte}
                    data={curve.data}
                    dataKey="iv"
                    stroke={PNL_COLORS[i % PNL_COLORS.length]}
                    strokeWidth={1.5}
                    dot={false}
                    name={`${curve.dte}d`}
                    type="monotone"
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Heatmap */}
          <div className="card p-4">
            <p className="section-label mb-2">Surface Heatmap (Moneyness × DTE)</p>
            <ResponsiveContainer width="100%" height={300}>
              <ScatterChart margin={{ top: 10, right: 10, bottom: 20, left: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} />
                <XAxis
                  dataKey="x"
                  type="number"
                  name="Moneyness"
                  tick={{ fill: CHART_COLORS.axis, fontSize: 10 }}
                  tickFormatter={(v: number) => v.toFixed(2)}
                  label={{ value: "Moneyness", position: "insideBottom", offset: -5, fill: CHART_COLORS.axis, fontSize: 10 }}
                />
                <YAxis
                  dataKey="y"
                  type="number"
                  name="DTE"
                  tick={{ fill: CHART_COLORS.axis, fontSize: 10 }}
                  label={{ value: "DTE", angle: -90, position: "insideLeft", fill: CHART_COLORS.axis, fontSize: 10 }}
                />
                <ZAxis dataKey="iv" range={[40, 200]} name="IV" />
                <Tooltip
                  contentStyle={{ background: CHART_COLORS.tooltip, border: "1px solid var(--color-border)", borderRadius: 6, fontSize: 11 }}
                  formatter={((v: number, name: string) => [name === "IV" ? `${v.toFixed(1)}%` : v.toFixed(3), name]) as never}
                />
                <Scatter data={heatmapData} shape="circle">
                  {heatmapData.map((entry, i) => {
                    const intensity = Math.min(Math.max((entry.iv - 15) / 40, 0), 1);
                    const r = Math.round(20 + intensity * 235);
                    const g = Math.round(50 + (1 - intensity) * 100);
                    const b = Math.round(50 + (1 - intensity) * 205);
                    return <Cell key={i} fill={`rgb(${r},${g},${b})`} />;
                  })}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  );
}


/* ───────────── Tab 3: Options Chain ───────────── */

function ChainTab({ spot, rate, vol }: { spot: number; rate: number; vol: number }) {
  const [chain, setChain] = useState<OptionsChainEntry[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [expiries, setExpiries] = useState("30,60,90");
  const [selectedDte, setSelectedDte] = useState<number | null>(null);

  const generate = async () => {
    setLoading(true);
    try {
      const dteList = expiries.split(",").map((s) => parseInt(s.trim())).filter((n) => n > 0);
      const r = await api.getOptionsChain({
        spot, risk_free_rate: rate, volatility: vol,
        days_to_expiry: dteList, n_strikes: 15,
      });
      setChain(r.chain);
      setSelectedDte(dteList[0] || null);
    } finally {
      setLoading(false);
    }
  };

  const filtered = useMemo(
    () => (chain && selectedDte ? chain.filter((e) => e.dte === selectedDte) : chain) || [],
    [chain, selectedDte]
  );

  const allDtes = useMemo(
    () => chain ? [...new Set(chain.map((e) => e.dte))].sort((a, b) => a - b) : [],
    [chain]
  );

  return (
    <div className="space-y-4">
      <div className="flex items-end gap-3">
        <div>
          <label className="section-label block mb-1">Expiries (comma-separated DTE)</label>
          <input
            type="text"
            value={expiries}
            onChange={(e) => setExpiries(e.target.value)}
            className="w-48 px-2 py-1.5 rounded text-[12px] font-mono"
            style={{ background: "var(--color-bg-primary)", color: "var(--color-text-primary)", border: "1px solid var(--color-border)" }}
          />
        </div>
        <button
          onClick={generate}
          disabled={loading}
          className="px-4 py-1.5 rounded text-[12px] font-medium"
          style={{ background: "var(--color-accent-blue)", color: "#fff" }}
        >
          {loading ? <Loader2 size={12} className="animate-spin inline mr-1" /> : null}
          Generate Chain
        </button>
      </div>

      {chain && (
        <>
          <div className="flex gap-1.5">
            {allDtes.map((d) => (
              <button
                key={d}
                onClick={() => setSelectedDte(d)}
                className="px-2 py-0.5 rounded text-[10px] font-mono"
                style={{
                  background: selectedDte === d ? "var(--color-accent-blue)" : "transparent",
                  color: selectedDte === d ? "#fff" : "var(--color-text-muted)",
                  border: `1px solid ${selectedDte === d ? "var(--color-accent-blue)" : "var(--color-border)"}`,
                }}
              >
                {d}d
              </button>
            ))}
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-[10px]">
              <thead>
                <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
                  <th colSpan={5} className="text-center py-1.5 font-medium" style={{ color: "var(--color-accent-green)", borderRight: "1px solid var(--color-border)" }}>CALLS</th>
                  <th className="text-center py-1.5 font-medium" style={{ color: "var(--color-text-muted)" }}>Strike</th>
                  <th colSpan={5} className="text-center py-1.5 font-medium" style={{ color: "var(--color-accent-red)", borderLeft: "1px solid var(--color-border)" }}>PUTS</th>
                </tr>
                <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
                  {["Price", "Δ", "Γ", "Θ", "ν"].map((h) => (
                    <th key={`c-${h}`} className="px-2 py-1 text-right font-medium" style={{ color: "var(--color-text-muted)" }}>{h}</th>
                  ))}
                  <th className="px-2 py-1 text-center font-medium" style={{ color: "var(--color-text-muted)", borderLeft: "1px solid var(--color-border)", borderRight: "1px solid var(--color-border)" }}>K</th>
                  {["Price", "Δ", "Γ", "Θ", "ν"].map((h) => (
                    <th key={`p-${h}`} className="px-2 py-1 text-right font-medium" style={{ color: "var(--color-text-muted)" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map((e) => {
                  const isAtm = Math.abs(e.moneyness - 1) < 0.02;
                  return (
                    <tr
                      key={`${e.dte}-${e.strike}`}
                      style={{
                        borderBottom: "1px solid var(--color-border)",
                        background: isAtm ? "rgba(68,136,255,0.06)" : undefined,
                      }}
                    >
                      <td className="px-2 py-1.5 text-right font-mono tabular-nums" style={{ color: "var(--color-text-primary)" }}>{e.call_price.toFixed(2)}</td>
                      <td className="px-2 py-1.5 text-right font-mono tabular-nums" style={{ color: "var(--color-text-secondary)" }}>{e.call_delta.toFixed(3)}</td>
                      <td className="px-2 py-1.5 text-right font-mono tabular-nums" style={{ color: "var(--color-text-secondary)" }}>{e.call_gamma.toFixed(4)}</td>
                      <td className="px-2 py-1.5 text-right font-mono tabular-nums" style={{ color: "var(--color-accent-red)" }}>{e.call_theta.toFixed(4)}</td>
                      <td className="px-2 py-1.5 text-right font-mono tabular-nums" style={{ color: "var(--color-text-secondary)", borderRight: "1px solid var(--color-border)" }}>{e.call_vega.toFixed(4)}</td>
                      <td className="px-2 py-1.5 text-center font-mono font-medium tabular-nums" style={{ color: isAtm ? "var(--color-accent-blue)" : "var(--color-text-primary)", borderRight: "1px solid var(--color-border)" }}>{e.strike.toFixed(0)}</td>
                      <td className="px-2 py-1.5 text-right font-mono tabular-nums" style={{ color: "var(--color-text-primary)" }}>{e.put_price.toFixed(2)}</td>
                      <td className="px-2 py-1.5 text-right font-mono tabular-nums" style={{ color: "var(--color-text-secondary)" }}>{e.put_delta.toFixed(3)}</td>
                      <td className="px-2 py-1.5 text-right font-mono tabular-nums" style={{ color: "var(--color-text-secondary)" }}>{e.put_gamma.toFixed(4)}</td>
                      <td className="px-2 py-1.5 text-right font-mono tabular-nums" style={{ color: "var(--color-accent-red)" }}>{e.put_theta.toFixed(4)}</td>
                      <td className="px-2 py-1.5 text-right font-mono tabular-nums" style={{ color: "var(--color-text-secondary)" }}>{e.put_vega.toFixed(4)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}


/* ───────────── Tab 4: P&L Scenario ───────────── */

function PnlTab({ spot, strike, dte, rate, vol, optionType }: {
  spot: number; strike: number; dte: number; rate: number; vol: number; optionType: "call" | "put";
}) {
  const [result, setResult] = useState<PnlScenarioResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [position, setPosition] = useState<1 | -1>(1);

  const generate = async () => {
    setLoading(true);
    try {
      const r = await api.getPnlScenario({
        spot, strike, days_to_expiry: dte, risk_free_rate: rate,
        volatility: vol, option_type: optionType, position,
      });
      setResult(r);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-end gap-3">
        <div>
          <label className="section-label block mb-1">Position</label>
          <div className="flex rounded overflow-hidden" style={{ border: "1px solid var(--color-border)" }}>
            {([1, -1] as const).map((p) => (
              <button
                key={p}
                onClick={() => setPosition(p)}
                className="px-3 py-1.5 text-[11px] font-medium"
                style={{
                  background: position === p ? "var(--color-accent-blue)" : "var(--color-bg-primary)",
                  color: position === p ? "#fff" : "var(--color-text-secondary)",
                }}
              >
                {p === 1 ? "Long" : "Short"}
              </button>
            ))}
          </div>
        </div>
        <button
          onClick={generate}
          disabled={loading}
          className="px-4 py-1.5 rounded text-[12px] font-medium"
          style={{ background: "var(--color-accent-blue)", color: "#fff" }}
        >
          {loading ? <Loader2 size={12} className="animate-spin inline mr-1" /> : null}
          Generate P&amp;L
        </button>
      </div>

      {result && (
        <div className="card p-4">
          <div className="flex items-center gap-3 mb-3">
            <span className="text-[12px] font-medium" style={{ color: "var(--color-text-primary)" }}>
              {result.position.toUpperCase()} {result.option_type.toUpperCase()} @ ${result.entry_price.toFixed(2)}
            </span>
            <span className="text-[10px]" style={{ color: "var(--color-text-muted)" }}>
              Strike ${result.strike} · Per contract (×100)
            </span>
          </div>

          {/* Legend */}
          <div className="flex flex-wrap gap-3 mb-2">
            {result.curves.map((c, i) => (
              <span key={c.dte} className="flex items-center gap-1.5 text-[10px] font-mono">
                <span className="w-3 h-0.5 rounded-full" style={{ background: PNL_COLORS[i % PNL_COLORS.length] }} />
                <span style={{ color: PNL_COLORS[i % PNL_COLORS.length] }}>{c.label}</span>
              </span>
            ))}
          </div>

          <ResponsiveContainer width="100%" height={320}>
            <LineChart margin={{ top: 5, right: 10, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} vertical={false} />
              <XAxis
                dataKey="spot"
                type="number"
                domain={["auto", "auto"]}
                tick={{ fill: CHART_COLORS.axis, fontSize: 10 }}
                tickFormatter={(v: number) => `$${v.toFixed(0)}`}
                label={{ value: "Underlying Price", position: "insideBottom", offset: -2, fill: CHART_COLORS.axis, fontSize: 10 }}
              />
              <YAxis
                tick={{ fill: CHART_COLORS.axis, fontSize: 10 }}
                tickFormatter={(v: number) => `$${v.toFixed(0)}`}
                label={{ value: "P&L", angle: -90, position: "insideLeft", fill: CHART_COLORS.axis, fontSize: 10 }}
              />
              <Tooltip
                contentStyle={{ background: CHART_COLORS.tooltip, border: "1px solid var(--color-border)", borderRadius: 6, fontSize: 11 }}
                formatter={((v: number) => [`$${v.toFixed(2)}`, "P&L"]) as never}
                labelFormatter={((v: number) => `Spot: $${Number(v).toFixed(2)}`) as never}
              />
              <ReferenceLine y={0} stroke="var(--color-text-muted)" strokeDasharray="4 4" />
              <ReferenceLine x={strike} stroke="rgba(136,85,255,0.3)" strokeDasharray="4 4" label={{ value: "K", fill: "var(--color-text-muted)", fontSize: 9, position: "top" }} />
              {result.curves.map((curve, i) => (
                <Line
                  key={curve.dte}
                  data={curve.points}
                  dataKey="pnl"
                  stroke={PNL_COLORS[i % PNL_COLORS.length]}
                  strokeWidth={i === result.curves.length - 1 ? 2 : 1.2}
                  strokeDasharray={i === result.curves.length - 1 ? undefined : "4 2"}
                  dot={false}
                  name={curve.label}
                  type="monotone"
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
