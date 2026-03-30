"use client";

import { useState, useCallback } from "react";
import type { Sweep2DResult, Sweep2DCell } from "@/lib/types";

interface HeatmapProps {
  result: Sweep2DResult;
}

function lerp(t: number, fromR: number, fromG: number, fromB: number, toR: number, toG: number, toB: number) {
  return [
    Math.round(fromR + (toR - fromR) * t),
    Math.round(fromG + (toG - fromG) * t),
    Math.round(fromB + (toB - fromB) * t),
  ];
}

function metricColor(value: number | null, min: number, max: number): string {
  if (value === null) return "rgba(255,255,255,0.04)";
  const range = max - min;
  if (range === 0) return "rgba(68,136,255,0.4)";
  const t = Math.max(0, Math.min(1, (value - min) / range));

  let rgb: number[];
  if (t < 0.5) {
    // red → yellow
    const t2 = t * 2;
    rgb = lerp(t2, 220, 40, 60, 255, 187, 51);
  } else {
    // yellow → green
    const t2 = (t - 0.5) * 2;
    rgb = lerp(t2, 255, 187, 51, 0, 212, 170);
  }
  const opacity = 0.15 + t * 0.65;
  return `rgba(${rgb[0]},${rgb[1]},${rgb[2]},${opacity})`;
}

function metricTextColor(value: number | null, min: number, max: number): string {
  if (value === null) return "var(--color-text-muted)";
  const range = max - min;
  if (range === 0) return "var(--color-text-primary)";
  const t = (value - min) / range;
  if (t > 0.66) return "var(--color-accent-green)";
  if (t > 0.33) return "var(--color-accent-yellow)";
  return "var(--color-accent-red)";
}

export function ParameterHeatmap({ result }: HeatmapProps) {
  const [hovered, setHovered] = useState<Sweep2DCell | null>(null);

  const allValues = result.cells.flat().map((c) => c.value).filter((v): v is number => v !== null);
  const min = allValues.length ? Math.min(...allValues) : 0;
  const max = allValues.length ? Math.max(...allValues) : 1;

  // Find best cell
  const bestCell = result.cells.flat().reduce<Sweep2DCell | null>((best, cell) => {
    if (cell.value === null) return best;
    if (!best || cell.value > (best.value ?? -Infinity)) return cell;
    return best;
  }, null);

  const metricLabel = result.metric.replace(/_/g, " ").replace(/\bpct\b/, "%");

  const cellSize = Math.max(44, Math.min(72, Math.floor(600 / Math.max(result.values_x.length, result.values_y.length))));

  return (
    <div>
      {/* Legend + info bar */}
      <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
        <div>
          <p className="section-label mb-1">
            {result.param_x} (x) × {result.param_y} (y) — metric: {metricLabel}
          </p>
          {bestCell && (
            <p className="text-xs text-text-secondary">
              Best: <span className="font-mono text-accent-green font-semibold">{String(bestCell.value?.toFixed(3))}</span>
              {" "}at {result.param_x}={bestCell.x}, {result.param_y}={bestCell.y}
            </p>
          )}
        </div>
        {/* Color scale */}
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-text-muted font-mono">{min.toFixed(2)}</span>
          <div
            className="w-28 h-3 rounded"
            style={{
              background: "linear-gradient(to right, rgba(220,40,60,0.7), rgba(255,187,51,0.7), rgba(0,212,170,0.8))",
            }}
          />
          <span className="text-[10px] text-text-muted font-mono">{max.toFixed(2)}</span>
        </div>
      </div>

      {/* Grid */}
      <div className="overflow-x-auto">
        <div
          className="inline-grid gap-px"
          style={{
            gridTemplateColumns: `auto repeat(${result.values_y.length}, ${cellSize}px)`,
            background: "var(--color-border)",
          }}
        >
          {/* Top-left corner */}
          <div
            className="flex items-end justify-end p-1.5"
            style={{ background: "var(--color-bg-primary)", minWidth: 56 }}
          >
            <span className="section-label text-[9px]">{result.param_x} \ {result.param_y}</span>
          </div>

          {/* Column headers (param_y values) */}
          {result.values_y.map((vy) => (
            <div
              key={vy}
              className="flex items-center justify-center p-1"
              style={{
                background: "var(--color-bg-secondary)",
                height: 28,
                fontSize: 10,
                fontFamily: "var(--font-mono)",
                color: "var(--color-text-muted)",
              }}
            >
              {vy}
            </div>
          ))}

          {/* Rows */}
          {result.cells.map((row, xi) => (
            <>
              {/* Row header (param_x value) */}
              <div
                key={`row-header-${xi}`}
                className="flex items-center justify-end pr-2"
                style={{
                  background: "var(--color-bg-secondary)",
                  fontSize: 10,
                  fontFamily: "var(--font-mono)",
                  color: "var(--color-text-muted)",
                  height: cellSize,
                }}
              >
                {result.values_x[xi]}
              </div>

              {/* Cells */}
              {row.map((cell, yi) => {
                const isBest = bestCell && cell.x === bestCell.x && cell.y === bestCell.y;
                return (
                  <div
                    key={`${xi}-${yi}`}
                    className="relative flex flex-col items-center justify-center transition-all duration-100"
                    style={{
                      background: metricColor(cell.value, min, max),
                      height: cellSize,
                      cursor: "pointer",
                      outline: isBest ? "2px solid rgba(0,212,170,0.8)" : "none",
                      outlineOffset: "-1px",
                    }}
                    onMouseEnter={() => setHovered(cell)}
                    onMouseLeave={() => setHovered(null)}
                  >
                    {cell.value !== null ? (
                      <span
                        className="font-mono font-semibold tabular-nums"
                        style={{
                          fontSize: cellSize > 56 ? 11 : 9,
                          color: metricTextColor(cell.value, min, max),
                        }}
                      >
                        {cell.value.toFixed(2)}
                      </span>
                    ) : (
                      <span className="text-[9px]" style={{ color: "var(--color-text-muted)" }}>
                        err
                      </span>
                    )}
                    {isBest && (
                      <span
                        className="absolute -top-1 -right-1 text-[8px] font-bold rounded-full w-3.5 h-3.5 flex items-center justify-center"
                        style={{ background: "var(--color-accent-green)", color: "var(--color-bg-primary)" }}
                      >
                        ★
                      </span>
                    )}
                  </div>
                );
              })}
            </>
          ))}
        </div>
      </div>

      {/* Tooltip */}
      {hovered && (
        <div
          className="mt-3 rounded p-3 text-xs"
          style={{
            background: "var(--color-bg-secondary)",
            border: "1px solid var(--color-border-strong)",
          }}
        >
          <span className="font-mono">
            {result.param_x}={hovered.x}, {result.param_y}={hovered.y}
          </span>
          <span className="text-text-muted mx-2">|</span>
          <span className="font-mono" style={{ color: metricTextColor(hovered.value, min, max) }}>
            {metricLabel}: {hovered.value?.toFixed(4) ?? "error"}
          </span>
          {hovered.total_return_pct != null && (
            <>
              <span className="text-text-muted mx-2">|</span>
              <span className="font-mono">
                Return: {hovered.total_return_pct >= 0 ? "+" : ""}{hovered.total_return_pct.toFixed(2)}%
              </span>
            </>
          )}
          {hovered.max_drawdown_pct != null && (
            <>
              <span className="text-text-muted mx-2">|</span>
              <span className="font-mono text-accent-red">
                MaxDD: {hovered.max_drawdown_pct.toFixed(2)}%
              </span>
            </>
          )}
        </div>
      )}
    </div>
  );
}
