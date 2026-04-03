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
  signal_mode: "long_only" | "long_short";
  requires_short_selling: boolean;
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
  allow_short_selling: boolean;
  max_short_position_pct: number;
  short_margin_requirement_pct: number;
  short_borrow_rate_bps: number;
  short_locate_fee_bps: number;
  short_squeeze_threshold_pct: number;
  rebalance_frequency: "daily" | "weekly" | "monthly";
}

// ---- Backtest Results ----
export interface BacktestResult {
  id: string;
  config: BacktestConfig;
  created_at: string;
  notes?: string;
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
  avg_net_exposure_pct: number;
  max_net_exposure_pct: number;
  avg_short_exposure_pct: number;
  max_short_exposure_pct: number;
  alpha: number;
  beta: number;
  correlation: number;
  tracking_error_pct: number;
  // Transaction cost metrics
  total_commission: number;
  total_slippage: number;
  total_borrow_cost: number;
  total_locate_fees: number;
  total_cost: number;
  cost_drag_bps: number;
  cost_drag_pct: number;
}

export interface Trade {
  id: string;
  ticker: string;
  side: "BUY" | "SELL";
  position_direction: "LONG" | "SHORT";
  entry_date: string;
  entry_price: number;
  exit_date: string | null;
  exit_price: number | null;
  shares: number;
  pnl: number | null;
  pnl_pct: number | null;
  commission: number;
  slippage: number;
  borrow_cost: number;
  locate_fee: number;
  risk_event: string | null;
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

// ---- Paper Trading ----
export type PaperSessionStatus =
  | "draft"
  | "active"
  | "paused"
  | "stopped"
  | "error";

export type PaperBarInterval = "1m" | "5m" | "15m" | "1h" | "1d";

export interface PaperTradingSessionCreate {
  name: string;
  strategy_id: string;
  params: Record<string, number | string | boolean>;
  tickers: string[];
  benchmark: string;
  initial_capital: number;
  slippage_bps: number;
  commission_per_share: number;
  max_position_pct: number;
  allow_short_selling: boolean;
  max_short_position_pct: number;
  short_margin_requirement_pct: number;
  short_borrow_rate_bps: number;
  short_locate_fee_bps: number;
  short_squeeze_threshold_pct: number;
  bar_interval: PaperBarInterval;
  polling_interval_seconds: number;
  start_immediately: boolean;
}

export interface PaperTradingSessionSummary {
  id: string;
  name: string;
  status: PaperSessionStatus;
  strategy_id: string;
  tickers: string[];
  bar_interval: PaperBarInterval;
  polling_interval_seconds: number;
  initial_capital: number;
  cash: number;
  market_value: number;
  total_equity: number;
  total_return_pct: number;
  created_at: string;
  started_at: string | null;
  stopped_at: string | null;
  last_price_at: string | null;
  last_heartbeat_at: string | null;
  last_error: string | null;
}

export interface PaperTradingPosition {
  ticker: string;
  shares: number;
  avg_cost: number;
  entry_date: string | null;
  current_price: number;
  market_value: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  accrued_borrow_cost: number;
  accrued_locate_fee: number;
  updated_at: string | null;
}

export interface PaperTradingEvent {
  id: string;
  timestamp: string;
  event_type: "status" | "signal" | "fill" | "error";
  ticker: string | null;
  action: string;
  signal: number | null;
  shares: number | null;
  fill_price: number | null;
  status: string;
  message: string;
}

export interface PaperTradingEquityPoint {
  timestamp: string;
  equity: number;
  cash: number;
  market_value: number;
}

export interface PaperTradingSessionDetail extends PaperTradingSessionSummary {
  benchmark: string;
  strategy_params: Record<string, number | string | boolean>;
  slippage_bps: number;
  commission_per_share: number;
  max_position_pct: number;
  allow_short_selling: boolean;
  max_short_position_pct: number;
  short_margin_requirement_pct: number;
  short_borrow_rate_bps: number;
  short_locate_fee_bps: number;
  short_squeeze_threshold_pct: number;
  positions: PaperTradingPosition[];
  recent_events: PaperTradingEvent[];
  equity_curve: PaperTradingEquityPoint[];
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

// ---- Capacity Analysis ----
export interface CapacityResult {
  initial_capital: number;
  n_trades: number;
  max_adv_participation_pct: number;
  avg_adv_participation_pct: number;
  p90_adv_participation_pct: number;
  capacity_estimates: {
    adv_threshold_pct: number;
    capacity_aum: number | null;
    label: string;
  }[];
  trade_adv_stats: {
    ticker: string;
    side: string;
    date: string;
    shares: number;
    notional: number;
    adv: number;
    adv_participation_pct: number;
  }[];
  message?: string;
}

// ---- Regime Analysis ----
export interface RegimeStat {
  regime: string;
  color: string;
  days: number;
  pct_of_period: number;
  ann_return_pct: number;
  ann_volatility_pct: number;
  sharpe: number;
}

export interface RegimeAnalysisResult {
  timeline: { date: string; regime: string; return: number }[];
  regime_stats: RegimeStat[];
  description: string;
}

// ---- Factor Exposure ----
export interface FactorExposureResult {
  alpha_annualized: number;
  r_squared: number;
  n_obs: number;
  factors: {
    name: string;
    beta: number;
    t_stat: number;
    p_value: number;
    significant: boolean;
  }[];
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

// ---- Bayesian Optimization ----
export interface BayesOptParamSpec {
  name: string;
  type: "int" | "float";
  low: number;
  high: number;
  step?: number | null;
}

export interface BayesOptTrial {
  trial: number;
  params: Record<string, number>;
  value: number;
}

export interface BayesOptResult {
  best_params: Record<string, number | string | boolean>;
  best_value: number;
  metric: string;
  n_trials: number;
  trials: BayesOptTrial[];
  param_specs: BayesOptParamSpec[];
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
