import type {
  BacktestConfig,
  BacktestResult,
  BacktestSummary,
  BayesOptParamSpec,
  BayesOptResult,
  CapacityResult,
  ComparisonResult,
  CorrelationResult,
  FactorExposureResult,
  MonteCarloResult,
  PaperTradingSessionCreate,
  PaperTradingSessionDetail,
  PaperTradingSessionSummary,
  PortfolioBlendResult,
  RegimeAnalysisResult,
  SpreadResult,
  StrategyInfo,
  SweepResult,
  Sweep2DResult,
  TransactionCostAnalysisResult,
  WalkForwardResult,
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

class ApiClient {
  private async request<T>(path: string, options?: RequestInit): Promise<T> {
    const headers = new Headers(options?.headers);

    if (
      options?.body &&
      !(options.body instanceof FormData) &&
      !headers.has("Content-Type")
    ) {
      headers.set("Content-Type", "application/json");
    }

    if (!headers.has("Accept")) {
      headers.set("Accept", "application/json");
    }

    const response = await fetch(`${API_BASE}${path}`, {
      headers,
      ...options,
    });
    if (!response.ok) {
      const error = await response
        .json()
        .catch(() => ({ detail: "Unknown error" }));
      throw new Error(error.detail || `API error: ${response.status}`);
    }
    return response.json();
  }

  // Data
  async getAvailableTickers(): Promise<string[]> {
    return this.request("/data/tickers");
  }

  async loadTickerData(ticker: string, startDate: string, endDate: string) {
    return this.request<{ status: string; ticker: string }>("/data/load", {
      method: "POST",
      body: JSON.stringify({
        ticker,
        start_date: startDate,
        end_date: endDate,
      }),
    });
  }

  async getOHLCV(ticker: string, startDate: string, endDate: string) {
    return this.request<{
      ticker: string;
      original_rows: number;
      returned_rows: number;
      data: {
        date: string;
        open: number;
        high: number;
        low: number;
        close: number;
        volume: number;
      }[];
    }>(
      `/data/ohlcv?ticker=${ticker}&start_date=${startDate}&end_date=${endDate}`
    );
  }

  // Backtest
  async runBacktest(config: BacktestConfig): Promise<BacktestResult> {
    return this.request("/backtest/run", {
      method: "POST",
      body: JSON.stringify(config),
    });
  }

  async getBacktestResult(id: string): Promise<BacktestResult> {
    return this.request(`/backtest/${id}`);
  }

  async listBacktests(): Promise<BacktestSummary[]> {
    const res = await this.request<{ items: BacktestSummary[]; total: number } | BacktestSummary[]>(
      "/backtest/list?limit=500"
    );
    // Handle both new paginated and old flat array responses
    return Array.isArray(res) ? res : res.items;
  }

  async deleteBacktest(id: string): Promise<void> {
    return this.request(`/backtest/${id}`, { method: "DELETE" });
  }

  async updateNotes(id: string, notes: string): Promise<{ id: string; notes: string }> {
    return this.request(`/backtest/${id}/notes`, {
      method: "PATCH",
      body: JSON.stringify({ notes }),
    });
  }

  // Paper trading
  async listPaperSessions(): Promise<PaperTradingSessionSummary[]> {
    return this.request("/paper/sessions");
  }

  async createPaperSession(
    payload: PaperTradingSessionCreate
  ): Promise<PaperTradingSessionDetail> {
    return this.request("/paper/sessions", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  async getPaperSession(id: string): Promise<PaperTradingSessionDetail> {
    return this.request(`/paper/sessions/${id}`);
  }

  async startPaperSession(id: string): Promise<PaperTradingSessionDetail> {
    return this.request(`/paper/sessions/${id}/start`, { method: "POST" });
  }

  async pausePaperSession(id: string): Promise<PaperTradingSessionDetail> {
    return this.request(`/paper/sessions/${id}/pause`, { method: "POST" });
  }

  async stopPaperSession(id: string): Promise<PaperTradingSessionDetail> {
    return this.request(`/paper/sessions/${id}/stop`, { method: "POST" });
  }

  // Strategies
  async getStrategies(): Promise<StrategyInfo[]> {
    return this.request("/strategies/list");
  }

  async getStrategyParams(
    strategyId: string
  ): Promise<{
    id: string;
    name: string;
    params: StrategyInfo["params"];
    defaults: Record<string, number | string | boolean>;
  }> {
    return this.request(`/strategies/${strategyId}/params`);
  }

  // Analytics
  async compareBacktests(ids: string[]): Promise<ComparisonResult> {
    return this.request("/analytics/compare", {
      method: "POST",
      body: JSON.stringify({ backtest_ids: ids }),
    });
  }

  async runMonteCarlo(
    backtestId: string,
    nSimulations: number = 1000,
    nDays: number = 252
  ): Promise<MonteCarloResult> {
    return this.request(
      `/analytics/monte-carlo/${backtestId}?n_simulations=${nSimulations}&n_days=${nDays}`,
      { method: "POST" }
    );
  }

  async runSweep(
    baseConfig: BacktestConfig,
    sweepParam: string,
    sweepValues: (number | string)[]
  ): Promise<SweepResult> {
    return this.request("/backtest/sweep", {
      method: "POST",
      body: JSON.stringify({
        base_config: baseConfig,
        sweep_param: sweepParam,
        sweep_values: sweepValues,
      }),
    });
  }

  async runWalkForward(
    config: BacktestConfig,
    nFolds: number,
    trainPct: number
  ): Promise<WalkForwardResult> {
    return this.request("/backtest/walk-forward", {
      method: "POST",
      body: JSON.stringify({ config, n_folds: nFolds, train_pct: trainPct }),
    });
  }

  async runSweep2D(
    baseConfig: BacktestConfig,
    paramX: string,
    valuesX: number[],
    paramY: string,
    valuesY: number[],
    metric: string = "sharpe_ratio"
  ): Promise<Sweep2DResult> {
    return this.request("/backtest/sweep2d", {
      method: "POST",
      body: JSON.stringify({
        base_config: baseConfig,
        param_x: paramX,
        values_x: valuesX,
        param_y: paramY,
        values_y: valuesY,
        metric,
      }),
    });
  }

  async getFactorExposure(backtestId: string): Promise<FactorExposureResult> {
    return this.request(`/analytics/factor-exposure/${backtestId}`, { method: "POST" });
  }

  async getRegimeAnalysis(backtestId: string): Promise<RegimeAnalysisResult> {
    return this.request(`/analytics/regime-analysis/${backtestId}`, { method: "POST" });
  }

  async getCapacityAnalysis(backtestId: string): Promise<CapacityResult> {
    return this.request(`/analytics/capacity/${backtestId}`, { method: "POST" });
  }

  async getTransactionCostAnalysis(
    backtestId: string
  ): Promise<TransactionCostAnalysisResult> {
    return this.request(`/analytics/tca/${backtestId}`, { method: "POST" });
  }

  async portfolioBlend(
    backtestIds: string[],
    weights: number[],
    optimize: "custom" | "equal" | "max_sharpe" | "min_dd" = "custom"
  ): Promise<PortfolioBlendResult> {
    return this.request("/analytics/portfolio-blend", {
      method: "POST",
      body: JSON.stringify({ backtest_ids: backtestIds, weights, optimize }),
    });
  }

  async runBayesOpt(
    backtestId: string,
    paramSpecs: BayesOptParamSpec[],
    metric: string,
    nTrials: number
  ): Promise<BayesOptResult> {
    // Fetch the original backtest to get base_config
    const result = await this.getBacktestResult(backtestId);
    return this.request("/backtest/optimize", {
      method: "POST",
      body: JSON.stringify({
        base_config: result.config,
        param_specs: paramSpecs,
        metric,
        n_trials: nTrials,
        maximize: !["max_drawdown_pct", "annualized_volatility_pct", "var_95_pct", "cvar_95_pct"].includes(metric),
      }),
    });
  }

  // Correlation & cointegration
  async getCorrelationAnalysis(
    tickers: string[],
    startDate: string,
    endDate: string,
    rollingWindow: number = 63,
    maxPairs: number = 10
  ): Promise<CorrelationResult> {
    return this.request("/analytics/correlation", {
      method: "POST",
      body: JSON.stringify({
        tickers,
        start_date: startDate,
        end_date: endDate,
        rolling_window: rollingWindow,
        max_pairs: maxPairs,
      }),
    });
  }

  async getSpreadAnalysis(
    tickerA: string,
    tickerB: string,
    startDate: string,
    endDate: string,
    lookback: number = 63
  ): Promise<SpreadResult> {
    return this.request("/analytics/spread", {
      method: "POST",
      body: JSON.stringify({
        ticker_a: tickerA,
        ticker_b: tickerB,
        start_date: startDate,
        end_date: endDate,
        lookback,
      }),
    });
  }

  getExportUrl(backtestId: string, format: "csv" = "csv"): string {
    return `${API_BASE}/analytics/export/${backtestId}?format=${format}`;
  }
}

export const api = new ApiClient();
