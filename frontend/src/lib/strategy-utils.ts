import type { StrategyInfo } from "@/lib/types";

export function buildStrategyParamDefaults(
  strategy: StrategyInfo | undefined,
): Record<string, number | string | boolean> {
  const defaults: Record<string, number | string | boolean> = {};
  strategy?.params.forEach((param) => {
    defaults[param.name] = param.default;
  });
  return defaults;
}

export function parseTickerList(value: string): string[] {
  return value
    .split(",")
    .map((ticker) => ticker.trim().toUpperCase())
    .filter(Boolean);
}
