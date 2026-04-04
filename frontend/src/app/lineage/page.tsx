"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";
import { CHART_COLORS } from "@/lib/constants";
import { formatPercent, formatRatio, formatDate } from "@/lib/formatters";
import type { LineageResult, LineageSummary, LineageEntry } from "@/lib/types";
import {
  Loader2,
  GitBranch,
  Tag,
  ChevronRight,
  ArrowRight,
  Plus,
} from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from "recharts";

export default function LineagePage() {
  const [lineages, setLineages] = useState<LineageSummary[]>([]);
  const [loadingList, setLoadingList] = useState(true);
  const [selectedTag, setSelectedTag] = useState<string | null>(null);
  const [lineage, setLineage] = useState<LineageResult | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // Tagging UI
  const [showTagger, setShowTagger] = useState(false);
  const [tagBacktestId, setTagBacktestId] = useState("");
  const [tagName, setTagName] = useState("");
  const [tagParentId, setTagParentId] = useState("");
  const [tagging, setTagging] = useState(false);

  const loadLineages = useCallback(async () => {
    setLoadingList(true);
    try {
      const res = await api.listLineages();
      setLineages(res.lineages);
    } catch {
      setLineages([]);
    } finally {
      setLoadingList(false);
    }
  }, []);

  useEffect(() => {
    loadLineages();
  }, [loadLineages]);

  const loadLineage = async (tag: string) => {
    setSelectedTag(tag);
    setLoadingDetail(true);
    try {
      const res = await api.getLineage(tag);
      setLineage(res);
    } catch {
      setLineage(null);
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleTag = async () => {
    if (!tagBacktestId || !tagName) return;
    setTagging(true);
    try {
      await api.setLineageTag(tagBacktestId, tagName, tagParentId || undefined);
      setShowTagger(false);
      setTagBacktestId("");
      setTagName("");
      setTagParentId("");
      await loadLineages();
      if (selectedTag === tagName) loadLineage(tagName);
    } finally {
      setTagging(false);
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-[1200px]">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-[20px] font-bold" style={{ color: "var(--color-text-primary)" }}>
            Research Timeline
          </h1>
          <p className="text-[12px] mt-1" style={{ color: "var(--color-text-secondary)" }}>
            Track strategy iterations, parameter changes, and performance evolution
          </p>
        </div>
        <button
          onClick={() => setShowTagger(!showTagger)}
          className="px-3 py-1.5 rounded text-[12px] font-medium flex items-center gap-1.5"
          style={{
            background: showTagger ? "var(--color-bg-card)" : "var(--color-accent-blue)",
            color: showTagger ? "var(--color-text-secondary)" : "#fff",
            border: `1px solid ${showTagger ? "var(--color-border)" : "var(--color-accent-blue)"}`,
          }}
        >
          <Tag size={12} /> {showTagger ? "Cancel" : "Tag a Run"}
        </button>
      </div>

      {/* Tagger */}
      {showTagger && (
        <div className="card p-4 space-y-3">
          <p className="section-label">Tag a Backtest Run</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div>
              <label className="text-[10px] block mb-1" style={{ color: "var(--color-text-muted)" }}>
                Backtest ID
              </label>
              <input
                type="text"
                value={tagBacktestId}
                onChange={(e) => setTagBacktestId(e.target.value)}
                placeholder="Paste backtest ID"
                className="w-full px-2 py-1.5 rounded text-[12px] font-mono"
                style={{ background: "var(--color-bg-primary)", color: "var(--color-text-primary)", border: "1px solid var(--color-border)" }}
              />
            </div>
            <div>
              <label className="text-[10px] block mb-1" style={{ color: "var(--color-text-muted)" }}>
                Lineage Tag
              </label>
              <input
                type="text"
                value={tagName}
                onChange={(e) => setTagName(e.target.value)}
                placeholder="e.g. sma-aapl-research"
                className="w-full px-2 py-1.5 rounded text-[12px] font-mono"
                style={{ background: "var(--color-bg-primary)", color: "var(--color-text-primary)", border: "1px solid var(--color-border)" }}
              />
            </div>
            <div>
              <label className="text-[10px] block mb-1" style={{ color: "var(--color-text-muted)" }}>
                Parent ID (optional)
              </label>
              <input
                type="text"
                value={tagParentId}
                onChange={(e) => setTagParentId(e.target.value)}
                placeholder="Previous iteration ID"
                className="w-full px-2 py-1.5 rounded text-[12px] font-mono"
                style={{ background: "var(--color-bg-primary)", color: "var(--color-text-primary)", border: "1px solid var(--color-border)" }}
              />
            </div>
          </div>
          <button
            onClick={handleTag}
            disabled={!tagBacktestId || !tagName || tagging}
            className="px-4 py-1.5 rounded text-[12px] font-medium disabled:opacity-40"
            style={{ background: "var(--color-accent-green)", color: "#000" }}
          >
            {tagging ? <Loader2 size={12} className="animate-spin inline mr-1" /> : <Plus size={12} className="inline mr-1" />}
            Tag Run
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-6">
        {/* Lineage list */}
        <div className="space-y-2">
          <p className="section-label px-1">Lineages</p>
          {loadingList ? (
            <div className="flex justify-center py-8">
              <Loader2 size={16} className="animate-spin" style={{ color: "var(--color-text-muted)" }} />
            </div>
          ) : lineages.length === 0 ? (
            <div className="card p-6 text-center">
              <GitBranch size={24} style={{ color: "var(--color-text-muted)", opacity: 0.3 }} className="mx-auto mb-2" />
              <p className="text-[12px]" style={{ color: "var(--color-text-muted)" }}>
                No lineages yet. Tag backtest runs to start tracking iterations.
              </p>
            </div>
          ) : (
            lineages.map((l) => (
              <button
                key={l.tag}
                onClick={() => loadLineage(l.tag)}
                className="w-full text-left px-3 py-2.5 rounded transition-colors"
                style={{
                  background: selectedTag === l.tag ? "rgba(68,136,255,0.08)" : "var(--color-bg-card)",
                  border: `1px solid ${selectedTag === l.tag ? "rgba(68,136,255,0.25)" : "var(--color-border)"}`,
                }}
              >
                <div className="flex items-center gap-2">
                  <GitBranch size={12} style={{ color: selectedTag === l.tag ? "var(--color-accent-blue)" : "var(--color-text-muted)" }} />
                  <span className="text-[12px] font-mono font-medium" style={{ color: "var(--color-text-primary)" }}>
                    {l.tag}
                  </span>
                  <ChevronRight size={10} className="ml-auto" style={{ color: "var(--color-text-muted)" }} />
                </div>
                <p className="text-[10px] mt-0.5 ml-5" style={{ color: "var(--color-text-muted)" }}>
                  {l.count} version{l.count !== 1 ? "s" : ""}
                </p>
              </button>
            ))
          )}
        </div>

        {/* Detail view */}
        <div>
          {!selectedTag && (
            <div className="card p-12 flex flex-col items-center gap-3" style={{ color: "var(--color-text-muted)" }}>
              <GitBranch size={32} style={{ opacity: 0.3 }} />
              <p className="text-[13px]">Select a lineage to view its iteration history</p>
            </div>
          )}

          {selectedTag && loadingDetail && (
            <div className="flex justify-center py-12">
              <Loader2 size={20} className="animate-spin" style={{ color: "var(--color-text-muted)" }} />
            </div>
          )}

          {selectedTag && !loadingDetail && lineage && (
            <LineageDetail lineage={lineage} />
          )}
        </div>
      </div>
    </div>
  );
}


/* ───────────── Lineage Detail ───────────── */

function LineageDetail({ lineage }: { lineage: LineageResult }) {
  const entries = lineage.entries;

  // Performance evolution chart data
  const chartData = entries.map((e) => ({
    version: `v${e.version}`,
    sharpe: e.sharpe_ratio,
    return_pct: e.total_return_pct,
    drawdown: Math.abs(e.max_drawdown_pct),
  }));

  return (
    <div className="space-y-5">
      {/* Evolution chart */}
      <div className="card p-4">
        <p className="section-label mb-3">Performance Evolution</p>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={chartData} margin={{ top: 5, right: 10, bottom: 5, left: -10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={CHART_COLORS.grid} vertical={false} />
            <XAxis dataKey="version" tick={{ fill: CHART_COLORS.axis, fontSize: 11 }} />
            <YAxis tick={{ fill: CHART_COLORS.axis, fontSize: 10 }} />
            <Tooltip
              contentStyle={{ background: CHART_COLORS.tooltip, border: "1px solid var(--color-border)", borderRadius: 6, fontSize: 11 }}
            />
            <Line type="monotone" dataKey="sharpe" stroke={CHART_COLORS.strategy} strokeWidth={2} name="Sharpe" dot={{ r: 4 }} />
            <Line type="monotone" dataKey="return_pct" stroke={CHART_COLORS.blue} strokeWidth={1.5} name="Return %" dot={{ r: 3 }} />
            <Line type="monotone" dataKey="drawdown" stroke={CHART_COLORS.negative} strokeWidth={1.5} strokeDasharray="4 2" name="Max DD %" dot={{ r: 3 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Timeline entries */}
      <div className="space-y-0">
        {entries.map((entry, i) => (
          <VersionCard key={entry.id} entry={entry} index={i} isLast={i === entries.length - 1} />
        ))}
      </div>
    </div>
  );
}


function VersionCard({ entry, index, isLast }: { entry: LineageEntry; index: number; isLast: boolean }) {
  return (
    <div className="flex gap-4">
      {/* Timeline line */}
      <div className="flex flex-col items-center w-8 shrink-0">
        <div
          className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0"
          style={{
            background: index === 0
              ? "var(--color-accent-green)"
              : "rgba(68,136,255,0.15)",
            color: index === 0 ? "#000" : "var(--color-accent-blue)",
            border: `2px solid ${index === 0 ? "var(--color-accent-green)" : "rgba(68,136,255,0.3)"}`,
          }}
        >
          {entry.version || index + 1}
        </div>
        {!isLast && (
          <div className="flex-1 w-px" style={{ background: "var(--color-border)" }} />
        )}
      </div>

      {/* Card */}
      <div
        className="flex-1 rounded mb-3 p-4"
        style={{
          background: "var(--color-bg-card)",
          border: "1px solid var(--color-border)",
        }}
      >
        {/* Header row */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="text-[12px] font-mono font-medium" style={{ color: "var(--color-text-primary)" }}>
              {entry.strategy_id}
            </span>
            <span className="text-[10px]" style={{ color: "var(--color-text-muted)" }}>
              {entry.tickers.join(", ")}
            </span>
          </div>
          <span className="text-[10px] font-mono" style={{ color: "var(--color-text-muted)" }}>
            {entry.created_at ? formatDate(entry.created_at) : "—"}
          </span>
        </div>

        {/* Metrics row */}
        <div className="flex gap-4 mb-2">
          <MetricPill label="Sharpe" value={formatRatio(entry.sharpe_ratio)} color="var(--color-accent-green)" />
          <MetricPill label="Return" value={formatPercent(entry.total_return_pct)} color="var(--color-accent-blue)" />
          <MetricPill label="Max DD" value={formatPercent(entry.max_drawdown_pct)} color="var(--color-accent-red)" />
        </div>

        {/* Param diffs */}
        {entry.param_diffs.length > 0 && (
          <div className="mt-2 space-y-1">
            <p className="text-[9px] uppercase tracking-wider" style={{ color: "var(--color-text-muted)" }}>
              Changes from previous
            </p>
            {entry.param_diffs.map((d) => (
              <div key={d.key} className="flex items-center gap-2 text-[11px] font-mono">
                <span style={{ color: "var(--color-text-secondary)" }}>{d.key}:</span>
                <span style={{ color: "var(--color-accent-red)" }}>
                  {d.old_value != null ? String(d.old_value) : "—"}
                </span>
                <ArrowRight size={10} style={{ color: "var(--color-text-muted)" }} />
                <span style={{ color: "var(--color-accent-green)" }}>
                  {d.new_value != null ? String(d.new_value) : "—"}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Notes */}
        {entry.notes && (
          <p className="text-[11px] mt-2 italic" style={{ color: "var(--color-text-muted)" }}>
            {entry.notes}
          </p>
        )}
      </div>
    </div>
  );
}


function MetricPill({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-[9px] uppercase" style={{ color: "var(--color-text-muted)" }}>{label}</span>
      <span className="text-[12px] font-mono font-semibold tabular-nums" style={{ color }}>{value}</span>
    </div>
  );
}
