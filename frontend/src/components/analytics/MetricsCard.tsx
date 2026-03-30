"use client";

interface MetricsCardProps {
  label: string;
  value: string;
  benchmark?: string;
  positive?: boolean;
  description?: string;
  size?: "sm" | "md";
}

export function MetricsCard({
  label,
  value,
  benchmark,
  positive,
  description,
  size = "md",
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
  const hasBench = benchmark !== undefined && benchmark !== null && benchmark !== "";

  return (
    <div
      className="relative overflow-hidden rounded-[5px] hover:bg-bg-hover transition-colors duration-150"
      style={{
        background: "var(--color-bg-card)",
        border: "1px solid var(--color-border)",
        boxShadow: "0 1px 3px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.02)",
      }}
      title={description}
    >
      {/* Accent bar — 2px strip at top, color-coded */}
      <div
        className="absolute top-0 left-0 right-0 h-[2px] rounded-t-[5px]"
        style={{ background: accentColor, opacity: 0.7 }}
      />

      <div className={size === "sm" ? "px-3 py-2.5 pt-3.5" : "px-4 py-3 pt-4"}>
        {/* Label */}
        <p className="section-label mb-1.5">{label}</p>

        {/* Value */}
        <p
          className={`font-mono tabular-nums font-semibold ${valueColor} ${
            size === "sm" ? "text-base" : "text-xl"
          }`}
        >
          {value ?? "—"}
        </p>

        {/* Benchmark */}
        {hasBench && (
          <p className="text-[10px] text-text-muted mt-1 font-mono tabular-nums">
            <span className="text-text-muted/60">Bench</span>{" "}
            {benchmark}
          </p>
        )}
      </div>
    </div>
  );
}
