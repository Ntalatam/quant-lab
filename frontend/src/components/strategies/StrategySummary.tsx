"use client";

import Link from "next/link";

import type { StrategyInfo } from "@/lib/types";

interface StrategySummaryProps {
  strategy: StrategyInfo;
}

export function StrategySummary({ strategy }: StrategySummaryProps) {
  return (
    <div className="mt-1 space-y-1">
      <p className="text-xs text-text-muted">{strategy.description}</p>
      <div className="flex items-center gap-2 text-[10px] uppercase tracking-wider">
        <span
          className="px-2 py-0.5 rounded border"
          style={{
            borderColor:
              strategy.signal_mode === "long_short"
                ? "rgba(255,187,51,0.25)"
                : "rgba(68,136,255,0.25)",
            color:
              strategy.signal_mode === "long_short"
                ? "var(--color-accent-yellow)"
                : "var(--color-accent-blue)",
            background:
              strategy.signal_mode === "long_short"
                ? "rgba(255,187,51,0.08)"
                : "rgba(68,136,255,0.08)",
          }}
        >
          {strategy.signal_mode === "long_short" ? "Long / Short" : "Long Only"}
        </span>
        {strategy.requires_short_selling && (
          <span className="text-accent-yellow">Requires short selling</span>
        )}
        {strategy.source_type === "custom" && (
          <Link
            href={`/strategies/custom?strategyId=${encodeURIComponent(strategy.id)}`}
            className="text-accent-purple hover:opacity-80 transition-opacity"
          >
            Edit in studio
          </Link>
        )}
      </div>
    </div>
  );
}
