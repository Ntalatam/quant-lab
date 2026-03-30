"use client";

interface MetricsCardProps {
  label: string;
  value: string;
  benchmark?: string;
  positive?: boolean;
  description?: string;
}

export function MetricsCard({
  label,
  value,
  benchmark,
  positive,
  description,
}: MetricsCardProps) {
  const valueColor =
    positive === undefined
      ? "text-text-primary"
      : positive
        ? "text-accent-green"
        : "text-accent-red";

  return (
    <div
      className="bg-bg-card border border-border rounded p-4 hover:border-text-muted/30 transition-colors"
      title={description}
    >
      <p className="text-xs text-text-muted uppercase tracking-wider mb-1">
        {label}
      </p>
      <p className={`text-xl font-mono tabular-nums font-semibold ${valueColor}`}>
        {value}
      </p>
      {benchmark && (
        <p className="text-xs text-text-muted mt-1 font-mono tabular-nums">
          Bench: {benchmark}
        </p>
      )}
    </div>
  );
}
