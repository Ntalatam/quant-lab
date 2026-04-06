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
  source_type?: "builtin" | "custom";
  signal_mode: "long_only" | "long_short";
  requires_short_selling: boolean;
  category:
    | "trend_following"
    | "mean_reversion"
    | "momentum"
    | "statistical_arbitrage"
    | "risk_management"
    | "custom"
    | string;
  params: StrategyParam[];
}

export interface StrategyEditorHelper {
  name: string;
  signature: string;
  description: string;
}

export interface StrategyEditorSpec {
  template: string;
  rules: string[];
  helpers: StrategyEditorHelper[];
}

export interface StrategyValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  extracted: {
    id: string;
    name: string;
    source_type: "custom";
    params: StrategyParam[];
    defaults: Record<string, number | string | boolean>;
  } | null;
  preview: StrategyInfo | null;
}

export interface CustomStrategySummary extends StrategyInfo {
  source_type: "custom";
  created_at: string;
  updated_at: string;
}

export interface CustomStrategyDetail extends CustomStrategySummary {
  defaults: Record<string, number | string | boolean>;
  code: string;
}

// ---- Auth / Session ----
export interface AuthUser {
  id: string;
  email: string;
  display_name: string | null;
  created_at: string;
}

export interface AuthWorkspace {
  id: string;
  name: string;
  is_personal: boolean;
  role: string;
}

export interface AuthSession {
  access_token: string;
  token_type: "bearer";
  expires_at: string;
  user: AuthUser;
  workspace: AuthWorkspace;
}

export interface CurrentSession {
  user: AuthUser;
  workspace: AuthWorkspace;
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
  market_impact_model: "constant" | "almgren_chriss";
  max_volume_participation_pct: number;
  position_sizing?:
    | "equal_weight"
    | "risk_parity"
    | "mean_variance"
    | "black_litterman"
    | "kelly";
  portfolio_construction_model:
    | "equal_weight"
    | "risk_parity"
    | "mean_variance"
    | "black_litterman"
    | "kelly";
  portfolio_lookback_days: number;
  max_position_pct: number;
  max_gross_exposure_pct: number;
  turnover_limit_pct: number;
  max_sector_exposure_pct: number;
  allow_short_selling: boolean;
  max_short_position_pct: number;
  short_margin_requirement_pct: number;
  short_borrow_rate_bps: number;
  short_locate_fee_bps: number;
  short_squeeze_threshold_pct: number;
  rebalance_frequency: "daily" | "weekly" | "monthly";
}

export type ResearchJobKind =
  | "backtest_run"
  | "backtest_sweep"
  | "backtest_sweep2d"
  | "backtest_walk_forward"
  | "backtest_optimize";

export type ResearchJobStatus = "queued" | "running" | "completed" | "failed";

export interface ResearchJobLogEntry {
  timestamp: string;
  message: string;
}

export interface ResearchJob<T = Record<string, unknown> | null> {
  id: string;
  kind: ResearchJobKind | string;
  status: ResearchJobStatus | string;
  progress_pct: number;
  progress_current: number;
  progress_total: number;
  progress_message: string | null;
  progress_date: string | null;
  progress_equity: number | null;
  logs: ResearchJobLogEntry[];
  attempt_count: number;
  max_attempts: number;
  result_backtest_run_id: string | null;
  result: T | null;
  error_message: string | null;
  queued_at: string;
  started_at: string | null;
  completed_at: string | null;
  failed_at: string | null;
  updated_at: string;
}

// ---- Backtest Results ----
export interface BacktestResult {
  id: string;
  config: BacktestConfig;
  created_at: string;
  notes?: string;
  lineage_tag?: string | null;
  version?: number | null;
  parent_id?: string | null;
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
  avg_turnover_pct: number;
  max_turnover_pct: number;
  alpha: number;
  beta: number;
  correlation: number;
  tracking_error_pct: number;
  // Transaction cost metrics
  total_commission: number;
  total_slippage: number;
  total_spread_cost: number;
  total_market_impact_cost: number;
  total_timing_cost: number;
  total_opportunity_cost: number;
  total_implementation_shortfall: number;
  avg_fill_rate_pct: number;
  avg_participation_rate_pct: number;
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
  requested_shares: number;
  unfilled_shares: number;
  pnl: number | null;
  pnl_pct: number | null;
  commission: number;
  slippage: number;
  spread_cost: number;
  market_impact_cost: number;
  timing_cost: number;
  opportunity_cost: number;
  participation_rate_pct: number;
  implementation_shortfall: number;
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
  lineage_tag?: string | null;
  version?: number | null;
}

// ---- Alternative Data ----
export interface EconomicIndicatorCatalogEntry {
  id: string;
  name: string;
  category: string;
  unit: string;
  frequency: string;
  description: string;
}

export interface EconomicIndicatorPoint {
  date: string;
  value: number;
}

export interface EconomicIndicatorSeries {
  id: string;
  name: string;
  category: string;
  unit: string;
  frequency: string;
  description: string;
  latest_date: string | null;
  latest_value: number | null;
  change_pct: number | null;
  change_direction: "up" | "down" | "flat" | null;
  points: EconomicIndicatorPoint[];
}

export interface EconomicIndicatorsResponse {
  series: EconomicIndicatorSeries[];
}

export interface EarningsEvent {
  date: string;
  event_type: "scheduled" | "reported";
  title: string;
  quarter_label: string | null;
  eps_actual: number | null;
  eps_estimate: number | null;
  eps_surprise_pct: number | null;
  revenue_estimate: number | null;
}

export interface EarningsOverview {
  ticker: string;
  next_earnings_date: string | null;
  events: EarningsEvent[];
}

export interface SentimentPoint {
  date: string;
  average_score: number;
  article_count: number;
}

export interface SentimentArticle {
  id: string;
  published_at: string;
  publisher: string;
  title: string;
  summary: string;
  url: string | null;
  content_type: string | null;
  sentiment_score: number;
  sentiment_label: "bullish" | "neutral" | "bearish";
}

export interface NewsSentimentResult {
  ticker: string;
  lookback_days: number;
  article_count: number;
  average_score: number;
  signal: "bullish" | "neutral" | "bearish";
  bullish_articles: number;
  neutral_articles: number;
  bearish_articles: number;
  rolling_series: SentimentPoint[];
  articles: SentimentArticle[];
}

// ---- Versioning / Lineage ----
export interface ParamDiff {
  key: string;
  old_value: number | string | boolean | null;
  new_value: number | string | boolean | null;
}

export interface LineageEntry {
  id: string;
  version: number | null;
  created_at: string | null;
  notes: string;
  strategy_id: string;
  tickers: string[];
  params: Record<string, number | string | boolean>;
  sharpe_ratio: number;
  total_return_pct: number;
  max_drawdown_pct: number;
  param_diffs: ParamDiff[];
}

export interface LineageResult {
  lineage_tag: string;
  entries: LineageEntry[];
}

export interface LineageSummary {
  tag: string;
  count: number;
  max_version: number;
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
  market_impact_model: "constant" | "almgren_chriss";
  max_volume_participation_pct: number;
  portfolio_construction_model:
    | "equal_weight"
    | "risk_parity"
    | "mean_variance"
    | "black_litterman"
    | "kelly";
  portfolio_lookback_days: number;
  max_position_pct: number;
  max_gross_exposure_pct: number;
  turnover_limit_pct: number;
  max_sector_exposure_pct: number;
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
  market_impact_model: "constant" | "almgren_chriss";
  max_volume_participation_pct: number;
  portfolio_construction_model:
    | "equal_weight"
    | "risk_parity"
    | "mean_variance"
    | "black_litterman"
    | "kelly";
  portfolio_lookback_days: number;
  max_position_pct: number;
  max_gross_exposure_pct: number;
  turnover_limit_pct: number;
  max_sector_exposure_pct: number;
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

// ---- Risk Budgeting ----
export interface RiskBudgetSummary {
  snapshot_date: string;
  lookback_days: number;
  total_equity: number;
  gross_exposure_pct: number;
  net_exposure_pct: number;
  daily_var_95_pct: number;
  daily_var_95_dollar: number;
  daily_cvar_95_pct: number;
  daily_cvar_95_dollar: number;
  diversification_ratio: number;
  average_pairwise_correlation: number | null;
}

export interface RiskBudgetPosition {
  ticker: string;
  sector: string | null;
  shares: number;
  price: number;
  market_value: number;
  weight_pct: number;
  daily_volatility_pct: number;
  beta_to_portfolio: number;
  var_contribution: number;
  var_contribution_pct: number;
  cvar_contribution: number;
  cvar_contribution_pct: number;
}

export interface StressPositionImpact {
  ticker: string;
  source_ticker: string;
  weight_pct: number;
  scenario_return_pct: number;
  pnl_impact: number;
}

export interface StressScenarioResult {
  id: string;
  name: string;
  description: string;
  start_date: string;
  end_date: string;
  portfolio_return_pct: number;
  pnl_impact: number;
  average_pairwise_correlation: number | null;
  correlation_shift: number | null;
  top_pair: string | null;
  top_pair_correlation: number | null;
  position_impacts: StressPositionImpact[];
}

export interface RiskBudgetResult {
  summary: RiskBudgetSummary | null;
  positions: RiskBudgetPosition[];
  scenarios: StressScenarioResult[];
  message?: string;
}

// ---- Transaction Cost Analysis ----
export interface TransactionCostAnalysisResult {
  model: {
    market_impact_model: string;
    max_volume_participation_pct: number;
    slippage_bps: number;
    commission_per_share: number;
  };
  summary: {
    total_trades: number;
    total_commission: number;
    total_spread_cost: number;
    total_market_impact_cost: number;
    total_timing_cost: number;
    total_opportunity_cost: number;
    total_borrow_cost: number;
    total_locate_fees: number;
    total_implementation_shortfall: number;
    avg_fill_rate_pct: number;
    avg_participation_rate_pct: number;
    p90_participation_rate_pct: number;
    cost_as_pct_of_initial_capital: number;
  };
  ticker_breakdown: {
    ticker: string;
    trades: number;
    total_commission: number;
    total_spread_cost: number;
    total_market_impact_cost: number;
    total_timing_cost: number;
    total_opportunity_cost: number;
    total_implementation_shortfall: number;
    avg_fill_rate_pct: number;
    avg_participation_rate_pct: number;
  }[];
  top_cost_trades: {
    id: string;
    ticker: string;
    side: string;
    position_direction: string;
    date: string;
    shares: number;
    requested_shares: number;
    unfilled_shares: number;
    commission: number;
    spread_cost: number;
    market_impact_cost: number;
    timing_cost: number;
    opportunity_cost: number;
    implementation_shortfall: number;
    fill_rate_pct: number;
    participation_rate_pct: number;
    risk_event?: string | null;
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

// ---- Correlation & Cointegration ----
export interface RollingCorrelationSeries {
  pair: string;
  ticker_a: string;
  ticker_b: string;
  series: TimeSeriesPoint[];
}

export interface PairTestResult {
  ticker_a: string;
  ticker_b: string;
  adf_statistic: number;
  adf_pvalue: number;
  cointegrated: boolean;
  beta: number;
  half_life_days: number | null;
  current_zscore: number | null;
  spread_std: number;
}

export interface CorrelationResult {
  tickers: string[];
  static_matrix: number[][];
  rolling_correlations: RollingCorrelationSeries[];
  discovered_pairs: PairTestResult[];
}

export interface SpreadResult {
  ticker_a: string;
  ticker_b: string;
  spread_series: TimeSeriesPoint[];
  zscore_series: TimeSeriesPoint[];
  half_life_days: number | null;
  current_zscore: number | null;
  spread_mean: number;
  spread_std: number;
  cointegration: PairTestResult;
}

// ---- Options Analytics ----
export interface OptionPriceResult {
  price: number;
  delta: number;
  gamma: number;
  theta: number;
  vega: number;
  rho: number;
  intrinsic: number;
  time_value: number;
  option_type: string;
  moneyness: number;
  moneyness_label: string;
}

export interface ImpliedVolResult {
  implied_volatility: number | null;
  implied_volatility_pct: number | null;
  market_price: number;
  theoretical_price: number | null;
  message: string;
}

export interface OptionsChainEntry {
  dte: number;
  strike: number;
  call_price: number;
  call_delta: number;
  call_gamma: number;
  call_theta: number;
  call_vega: number;
  put_price: number;
  put_delta: number;
  put_gamma: number;
  put_theta: number;
  put_vega: number;
  moneyness: number;
}

export interface VolSurfacePoint {
  dte: number;
  strike: number;
  moneyness: number;
  implied_vol: number;
}

export interface VolSurfaceResult {
  spot: number;
  base_vol: number;
  strikes: number[];
  expiries: number[];
  surface: VolSurfacePoint[];
}

export interface PnlPoint {
  spot: number;
  pnl: number;
}

export interface PnlCurve {
  dte: number;
  label: string;
  points: PnlPoint[];
}

export interface PnlScenarioResult {
  strike: number;
  entry_price: number;
  position: string;
  option_type: string;
  curves: PnlCurve[];
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
