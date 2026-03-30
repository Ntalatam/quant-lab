// ---- Strategy Configuration ----
export interface StrategyParam {
  name: string;
  label: string;
  type: "int" | "float" | "select" | "bool";
  default: number | string | boolean;
  min?: number;
  max?: number;
  step?: number;
  options?: string[];
  description: string;
}

export interface StrategyInfo {
  id: string;
  name: string;
  description: string;
  category:
    | "trend_following"
    | "mean_reversion"
    | "momentum"
    | "statistical_arbitrage";
  params: StrategyParam[];
}

// ---- Backtest Configuration ----
export interface BacktestConfig {
  strategy_id: string;
  params: Record<string, number | string | boolean>;
  tickers: string[];
  benchmark: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  slippage_bps: number;
  commission_per_share: number;
  position_sizing: "equal_weight" | "risk_parity" | "kelly";
  max_position_pct: number;
  rebalance_frequency: "daily" | "weekly" | "monthly";
}

// ---- Backtest Results ----
export interface BacktestResult {
  id: string;
  config: BacktestConfig;
  created_at: string;
  equity_curve: TimeSeriesPoint[];
  clean_equity_curve: TimeSeriesPoint[];
  benchmark_curve: TimeSeriesPoint[];
  drawdown_series: TimeSeriesPoint[];
  rolling_sharpe: TimeSeriesPoint[];
  rolling_volatility: TimeSeriesPoint[];
  metrics: PerformanceMetrics;
  benchmark_metrics: PerformanceMetrics;
  trades: Trade[];
  monthly_returns: MonthlyReturn[];
}

export interface TimeSeriesPoint {
  date: string;
  value: number;
}

export interface PerformanceMetrics {
  total_return_pct: number;
  annualized_return_pct: number;
  cagr_pct: number;
  annualized_volatility_pct: number;
  max_drawdown_pct: number;
  max_drawdown_duration_days: number;
  current_drawdown_pct: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  calmar_ratio: number;
  information_ratio: number;
  var_95_pct: number;
  cvar_95_pct: number;
  skewness: number;
  kurtosis: number;
  total_trades: number;
  win_rate_pct: number;
  avg_win_pct: number;
  avg_loss_pct: number;
  profit_factor: number;
  avg_holding_period_days: number;
  best_trade_pct: number;
  worst_trade_pct: number;
  avg_exposure_pct: number;
  max_exposure_pct: number;
  alpha: number;
  beta: number;
  correlation: number;
  tracking_error_pct: number;
  // Transaction cost metrics
  total_commission: number;
  total_slippage: number;
  total_cost: number;
  cost_drag_bps: number;
  cost_drag_pct: number;
}

export interface Trade {
  id: string;
  ticker: string;
  side: "BUY" | "SELL";
  entry_date: string;
  entry_price: number;
  exit_date: string | null;
  exit_price: number | null;
  shares: number;
  pnl: number | null;
  pnl_pct: number | null;
  commission: number;
  slippage: number;
}

export interface MonthlyReturn {
  year: number;
  month: number;
  return_pct: number;
}

export interface BacktestSummary {
  id: string;
  strategy_name: string;
  tickers: string[];
  start_date: string;
  end_date: string;
  total_return_pct: number;
  sharpe_ratio: number;
  max_drawdown_pct: number;
  created_at: string;
}

// ---- Comparison ----
export interface ComparisonResult {
  backtests: {
    id: string;
    strategy_id: string;
    tickers: string[];
    metrics: PerformanceMetrics;
    equity_curve: TimeSeriesPoint[];
  }[];
  correlation_matrix: number[][];
}

// ---- Monte Carlo ----
export interface MonteCarloResult {
  percentiles: Record<string, number[]>;
  n_simulations: number;
  n_days: number;
  median_final_value: number;
  prob_loss: number;
}

// ---- Portfolio Blend ----
export interface PortfolioBlendResult {
  weights: number[];
  optimize: string;
  equity_curve: TimeSeriesPoint[];
  metrics: Partial<PerformanceMetrics>;
  asset_contributions: {
    id: string;
    strategy_id: string;
    tickers: string[];
    weight: number;
    asset_return_pct: number;
    contribution_pct: number;
  }[];
}

// ---- Sweep ----
export interface SweepResult {
  sweep_param: string;
  results: {
    param_value: number | string;
    sharpe_ratio?: number;
    total_return_pct?: number;
    max_drawdown_pct?: number;
    cagr_pct?: number;
    error?: string;
  }[];
}

// ---- Walk-Forward Analysis ----
export interface WalkForwardFold {
  fold: number;
  is_start: string;
  is_end: string;
  oos_start: string;
  oos_end: string;
  is_sharpe: number | null;
  is_return: number | null;
  oos_sharpe: number | null;
  oos_return: number | null;
  oos_max_dd: number | null;
  ok: boolean;
}

export interface WalkForwardResult {
  n_folds: number;
  train_pct: number;
  folds: WalkForwardFold[];
  oos_equity_curve: TimeSeriesPoint[];
  oos_metrics: Partial<PerformanceMetrics>;
  sharpe_efficiency: number | null;
}

// ---- 2D Sweep Heatmap ----
export interface Sweep2DCell {
  x: number;
  y: number;
  value: number | null;
  total_return_pct?: number;
  max_drawdown_pct?: number;
  error?: string;
}

export interface Sweep2DResult {
  param_x: string;
  param_y: string;
  metric: string;
  values_x: number[];
  values_y: number[];
  cells: Sweep2DCell[][];
}
