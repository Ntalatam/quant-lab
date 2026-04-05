"use client";

interface MetricsCardProps {
  label: string;
  value: string;
  benchmark?: string;
  positive?: boolean;
  description?: string;
  size?: "sm" | "md";
  /** 0–1 percentile rank among all stored runs (1 = best) */
  percentile?: number;
}

export function MetricsCard({
  label,
  value,
  benchmark,
  positive,
  description,
  size = "md",
  percentile,
}: MetricsCardProps) {
  const accentColor =
    positive === undefined
      ? "var(--color-accent-blue)"
      : positive
        ? "var(--color-accent-green)"
        : "var(--color-accent-red)";

  const valueColor =
    positive === undefined
      ? "text-text-primary"
      : positive
        ? "text-accent-green"
        : "text-accent-red";

  // Benchmark delta — show arrow + color if provided
  const hasBench =
    benchmark !== undefined && benchmark !== null && benchmark !== "";

  return (
    <div
      className="panel-soft relative overflow-hidden transition-all duration-200 hover:-translate-y-0.5 hover:bg-bg-hover"
      style={{
        borderColor: "rgba(111,130,166,0.14)",
      }}
      title={description}
    >
      <div
        className="absolute inset-x-0 top-0 h-[3px]"
        style={{
          background: `linear-gradient(90deg, ${accentColor}, transparent)`,
          opacity: 0.9,
        }}
      />
      <div
        className="absolute -right-10 top-0 h-24 w-24 rounded-full blur-2xl"
        style={{ background: `${accentColor}26` }}
      />

      <div className={size === "sm" ? "px-3 py-3.5" : "px-4 py-4"}>
        <div className="mb-2 flex items-start justify-between gap-3">
          <p className="section-label">{label}</p>
          {percentile !== undefined && (
            <span
              className="rounded-full px-2 py-1 text-[9px] font-mono"
              style={{
                color:
                  percentile >= 0.67
                    ? "var(--color-accent-green)"
                    : percentile >= 0.33
                      ? "var(--color-accent-yellow)"
                      : "var(--color-accent-red)",
                background: "rgba(255,255,255,0.03)",
                border: "1px solid rgba(111,130,166,0.12)",
              }}
            >
              top {Math.max(1, Math.round((1 - percentile) * 100))}%
            </span>
          )}
        </div>

        <p
          className={`font-mono tabular-nums font-semibold ${valueColor} ${
            size === "sm" ? "text-base" : "text-xl"
          }`}
        >
          {value ?? "—"}
        </p>

        {hasBench && (
          <p className="text-[10px] text-text-muted mt-1 font-mono tabular-nums">
            <span className="text-text-muted/60">Bench</span> {benchmark}
          </p>
        )}

        {description && (
          <p className="mt-2 max-w-[20ch] text-[11px] leading-relaxed text-text-muted">
            {description}
          </p>
        )}
      </div>
    </div>
  );
}
