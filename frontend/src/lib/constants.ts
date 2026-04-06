export const BENCHMARKS = ["SPY", "QQQ", "IWM", "DIA", "TLT"] as const;

export const POSITION_SIZING_OPTIONS = [
  { value: "equal_weight", label: "Equal Weight" },
  { value: "risk_parity", label: "Risk Parity" },
  { value: "mean_variance", label: "Mean-Variance" },
  { value: "black_litterman", label: "Black-Litterman" },
] as const;

export const REBALANCE_OPTIONS = [
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
  { value: "monthly", label: "Monthly" },
] as const;

export const PAPER_INTERVAL_OPTIONS = [
  { value: "1m", label: "1 Minute" },
  { value: "5m", label: "5 Minutes" },
  { value: "15m", label: "15 Minutes" },
  { value: "1h", label: "1 Hour" },
  { value: "1d", label: "1 Day" },
] as const;

export const PAPER_EXECUTION_MODE_OPTIONS = [
  {
    value: "simulated_paper",
    broker_adapter: "paper",
    label: "Simulated Paper",
    description:
      "QuantLab simulates fills locally with slippage, commission, and risk controls.",
  },
  {
    value: "broker_paper",
    broker_adapter: "alpaca",
    label: "Broker Paper",
    description:
      "QuantLab submits paper orders to Alpaca and syncs positions, fills, and open orders back in.",
  },
] as const;

export const PAPER_EXECUTION_MODE_LABELS = {
  simulated_paper: "Simulated Paper",
  broker_paper: "Broker Paper",
  broker_live: "Broker Live",
} as const;

export const MARKET_IMPACT_MODEL_OPTIONS = [
  { value: "almgren_chriss", label: "Almgren-Chriss" },
  { value: "constant", label: "Constant Slippage" },
] as const;

export const CATEGORY_LABELS: Record<string, string> = {
  trend_following: "Trend Following",
  mean_reversion: "Mean Reversion",
  momentum: "Momentum",
  statistical_arbitrage: "Statistical Arbitrage",
  risk_management: "Risk Management",
  custom: "Custom",
};

export const CHART_COLORS = {
  strategy: "#00d4aa",
  benchmark: "#555577",
  positive: "#00d4aa",
  negative: "#ff4466",
  grid: "#1e1e2a",
  axis: "#555566",
  tooltip: "#16161f",
  blue: "#4488ff",
  yellow: "#ffbb33",
  purple: "#8855ff",
} as const;

export const MONTH_LABELS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
] as const;
