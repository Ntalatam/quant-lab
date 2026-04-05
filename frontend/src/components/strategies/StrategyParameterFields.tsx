"use client";

import type { StrategyInfo, StrategyParam } from "@/lib/types";

type ParamValue = number | string | boolean;

interface StrategyParameterFieldsProps {
  strategy: StrategyInfo;
  values: Record<string, ParamValue>;
  title: string;
  onChange: (name: string, value: ParamValue) => void;
}

function renderNumericControl(
  param: StrategyParam,
  value: number,
  onChange: (value: ParamValue) => void,
) {
  if (
    typeof param.min === "number" &&
    typeof param.max === "number" &&
    typeof param.step === "number"
  ) {
    return (
      <input
        type="range"
        min={param.min}
        max={param.max}
        step={param.step}
        value={value}
        onChange={(event) => {
          const nextValue =
            param.type === "int"
              ? Number.parseInt(event.target.value, 10)
              : Number.parseFloat(event.target.value);
          onChange(nextValue);
        }}
        className="w-full accent-accent-blue"
      />
    );
  }

  return (
    <input
      type="number"
      min={param.min}
      max={param.max}
      step={param.step ?? (param.type === "int" ? 1 : 0.1)}
      value={value}
      onChange={(event) => {
        const nextValue =
          param.type === "int"
            ? Number.parseInt(event.target.value, 10)
            : Number.parseFloat(event.target.value);
        if (!Number.isNaN(nextValue)) {
          onChange(nextValue);
        }
      }}
      className="w-full bg-bg-primary border border-border rounded px-3 py-2 text-sm text-text-primary"
    />
  );
}

export function StrategyParameterFields({
  strategy,
  values,
  title,
  onChange,
}: StrategyParameterFieldsProps) {
  if (strategy.params.length === 0) {
    return null;
  }

  return (
    <div>
      <p className="text-sm font-medium text-text-secondary mb-3">{title}</p>
      <div className="space-y-3">
        {strategy.params.map((param) => {
          const value = values[param.name] ?? param.default;
          return (
            <div key={param.name}>
              <div className="flex justify-between items-center mb-1">
                <label className="text-xs text-text-secondary">
                  {param.label}
                </label>
                <span className="text-xs font-mono text-text-primary">
                  {String(value)}
                </span>
              </div>

              {(param.type === "int" || param.type === "float") &&
                renderNumericControl(param, Number(value), (nextValue) =>
                  onChange(param.name, nextValue),
                )}

              {param.type === "bool" && (
                <label className="flex items-center gap-2 text-xs text-text-primary">
                  <input
                    type="checkbox"
                    checked={Boolean(value)}
                    onChange={(event) =>
                      onChange(param.name, event.target.checked)
                    }
                    className="accent-accent-blue"
                  />
                  Enable
                </label>
              )}

              {param.type === "select" && param.options && (
                <select
                  value={String(value)}
                  onChange={(event) => onChange(param.name, event.target.value)}
                  className="w-full bg-bg-primary border border-border rounded px-3 py-2 text-sm text-text-primary"
                >
                  {param.options.map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              )}

              <p className="text-[10px] text-text-muted mt-0.5">
                {param.description}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
