import type {
  AuthSession,
  CurrentSession,
  BacktestConfig,
  BacktestResult,
  BacktestSummary,
  BayesOptParamSpec,
  BayesOptResult,
  CapacityResult,
  ComparisonResult,
  CustomStrategyDetail,
  CustomStrategySummary,
  EconomicIndicatorCatalogEntry,
  EconomicIndicatorsResponse,
  EarningsOverview,
  CorrelationResult,
  FactorExposureResult,
  ImpliedVolResult,
  LineageResult,
  LineageSummary,
  MonteCarloResult,
  OptionPriceResult,
  OptionsChainEntry,
  PaperTradingSessionCreate,
  PaperTradingSessionDetail,
  PaperTradingSessionSummary,
  NewsSentimentResult,
  PnlScenarioResult,
  PortfolioBlendResult,
  RegimeAnalysisResult,
  RiskBudgetResult,
  ResearchJob,
  SpreadResult,
  StrategyInfo,
  StrategyEditorSpec,
  StrategyValidationResult,
  SweepResult,
  Sweep2DResult,
  TransactionCostAnalysisResult,
  VolSurfaceResult,
  WalkForwardResult,
} from "./types";
import { buildApiUrl, getApiBaseUrl } from "./network";

const API_BASE = getApiBaseUrl();
export const AUTH_TOKEN_STORAGE_KEY = "quantlab.access_token";

class ApiClient {
  private accessToken: string | null = null;
  private refreshPromise: Promise<string | null> | null = null;

  setAccessToken(token: string | null) {
    this.accessToken = token;
  }

  getAccessToken() {
    return this.accessToken;
  }

  private isAuthPath(path: string): boolean {
    return path.startsWith("/auth/login") || path.startsWith("/auth/register");
  }

  private async parseError(response: Response): Promise<string> {
    const error = await response
      .json()
      .catch(() => ({ detail: "Unknown error" }));
    return error.detail || `API error: ${response.status}`;
  }

  private async refreshAccessToken(): Promise<string | null> {
    if (this.refreshPromise) {
      return this.refreshPromise;
    }

    this.refreshPromise = (async () => {
      const response = await fetch(buildApiUrl("/auth/refresh", API_BASE), {
        method: "POST",
        credentials: "include",
        headers: {
          Accept: "application/json",
        },
      });

      if (!response.ok) {
        this.accessToken = null;
        return null;
      }

      const payload = (await response.json()) as AuthSession;
      this.accessToken = payload.access_token;
      return payload.access_token;
    })().finally(() => {
      this.refreshPromise = null;
    });

    return this.refreshPromise;
  }

  private async request<T>(
    path: string,
    options?: RequestInit,
    allowRefresh: boolean = true,
  ): Promise<T> {
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

    if (this.accessToken && !headers.has("Authorization")) {
      headers.set("Authorization", `Bearer ${this.accessToken}`);
    }

    const response = await fetch(buildApiUrl(path, API_BASE), {
      credentials: "include",
      headers,
      ...options,
    });
    if (response.status === 401 && allowRefresh && !this.isAuthPath(path)) {
      const refreshedToken = await this.refreshAccessToken();
      if (refreshedToken) {
        return this.request(path, options, false);
      }
    }
    if (!response.ok) {
      throw new Error(await this.parseError(response));
    }
    return response.json();
  }

  async register(payload: {
    email: string;
    password: string;
    display_name?: string | null;
  }): Promise<AuthSession> {
    const response = await this.request<AuthSession>("/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    this.accessToken = response.access_token;
    return response;
  }

  async login(payload: {
    email: string;
    password: string;
  }): Promise<AuthSession> {
    const response = await this.request<AuthSession>("/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    this.accessToken = response.access_token;
    return response;
  }

  async refreshSession(): Promise<AuthSession> {
    const response = await this.request<AuthSession>(
      "/auth/refresh",
      { method: "POST" },
      false,
    );
    this.accessToken = response.access_token;
    return response;
  }

  async logout(): Promise<{ status: string; message?: string }> {
    const response = await this.request<{ status: string; message?: string }>(
      "/auth/logout",
      { method: "POST" },
      false,
    );
    this.accessToken = null;
    return response;
  }

  async getCurrentSession(): Promise<CurrentSession> {
    return this.request("/auth/me");
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
      `/data/ohlcv?ticker=${ticker}&start_date=${startDate}&end_date=${endDate}`,
    );
  }

  async getEconomicIndicatorCatalog(): Promise<
    EconomicIndicatorCatalogEntry[]
  > {
    return this.request("/data/economic-indicators/catalog");
  }

  async getEconomicIndicators(
    seriesIds: string[],
    startDate: string,
    endDate: string,
  ): Promise<EconomicIndicatorsResponse> {
    const params = new URLSearchParams({
      start_date: startDate,
      end_date: endDate,
    });
    seriesIds.forEach((seriesId) => params.append("series_ids", seriesId));
    return this.request(`/data/economic-indicators?${params.toString()}`);
  }

  async getEarningsOverview(ticker: string): Promise<EarningsOverview> {
    return this.request(`/data/earnings?ticker=${encodeURIComponent(ticker)}`);
  }

  async getNewsSentiment(
    ticker: string,
    lookbackDays: number = 30,
    limit: number = 10,
  ): Promise<NewsSentimentResult> {
    const params = new URLSearchParams({
      ticker,
      lookback_days: String(lookbackDays),
      limit: String(limit),
    });
    return this.request(`/data/news-sentiment?${params.toString()}`);
  }

  // Backtest
  async runBacktest(config: BacktestConfig): Promise<ResearchJob> {
    return this.request("/backtest/run", {
      method: "POST",
      body: JSON.stringify(config),
    });
  }

  async getResearchJob<T = Record<string, unknown> | null>(
    id: string,
  ): Promise<ResearchJob<T>> {
    return this.request(`/jobs/${id}`);
  }

  async getBacktestResult(id: string): Promise<BacktestResult> {
    return this.request(`/backtest/${id}`);
  }

  async listBacktests(): Promise<BacktestSummary[]> {
    const res = await this.request<
      { items: BacktestSummary[]; total: number } | BacktestSummary[]
    >("/backtest/list?limit=500");
    // Handle both new paginated and old flat array responses
    return Array.isArray(res) ? res : res.items;
  }

  async deleteBacktest(id: string): Promise<void> {
    return this.request(`/backtest/${id}`, { method: "DELETE" });
  }

  async updateNotes(
    id: string,
    notes: string,
  ): Promise<{ id: string; notes: string }> {
    return this.request(`/backtest/${id}/notes`, {
      method: "PATCH",
      body: JSON.stringify({ notes }),
    });
  }

  // Versioning / lineage
  async setLineageTag(
    backtestId: string,
    lineageTag: string,
    parentId?: string,
  ): Promise<{
    id: string;
    lineage_tag: string;
    version: number;
    parent_id: string | null;
  }> {
    return this.request(`/backtest/${backtestId}/lineage`, {
      method: "PATCH",
      body: JSON.stringify({
        lineage_tag: lineageTag,
        parent_id: parentId || null,
      }),
    });
  }

  async getLineage(tag: string): Promise<LineageResult> {
    return this.request(`/backtest/lineage/${encodeURIComponent(tag)}`);
  }

  async listLineages(): Promise<{ lineages: LineageSummary[] }> {
    return this.request("/backtest/lineages");
  }

  // Paper trading
  async listPaperSessions(): Promise<PaperTradingSessionSummary[]> {
    return this.request("/paper/sessions");
  }

  async createPaperSession(
    payload: PaperTradingSessionCreate,
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

  async getStrategyParams(strategyId: string): Promise<{
    id: string;
    name: string;
    source_type?: "builtin" | "custom";
    params: StrategyInfo["params"];
    defaults: Record<string, number | string | boolean>;
  }> {
    return this.request(`/strategies/${strategyId}/params`);
  }

  async getStrategyEditorSpec(): Promise<StrategyEditorSpec> {
    return this.request("/strategies/custom/editor-spec");
  }

  async validateCustomStrategy(
    code: string,
  ): Promise<StrategyValidationResult> {
    return this.request("/strategies/custom/validate", {
      method: "POST",
      body: JSON.stringify({ code }),
    });
  }

  async listCustomStrategies(): Promise<CustomStrategySummary[]> {
    return this.request("/strategies/custom");
  }

  async getCustomStrategy(id: string): Promise<CustomStrategyDetail> {
    return this.request(`/strategies/custom/${id}`);
  }

  async createCustomStrategy(code: string): Promise<CustomStrategyDetail> {
    return this.request("/strategies/custom", {
      method: "POST",
      body: JSON.stringify({ code }),
    });
  }

  async updateCustomStrategy(
    id: string,
    code: string,
  ): Promise<CustomStrategyDetail> {
    return this.request(`/strategies/custom/${id}`, {
      method: "PUT",
      body: JSON.stringify({ code }),
    });
  }

  async deleteCustomStrategy(
    id: string,
  ): Promise<{ deleted: boolean; id: string }> {
    return this.request(`/strategies/custom/${id}`, { method: "DELETE" });
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
    nDays: number = 252,
  ): Promise<MonteCarloResult> {
    return this.request(
      `/analytics/monte-carlo/${backtestId}?n_simulations=${nSimulations}&n_days=${nDays}`,
      { method: "POST" },
    );
  }

  async runSweep(
    baseConfig: BacktestConfig,
    sweepParam: string,
    sweepValues: (number | string)[],
  ): Promise<ResearchJob<SweepResult>> {
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
    trainPct: number,
  ): Promise<ResearchJob<WalkForwardResult>> {
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
    metric: string = "sharpe_ratio",
  ): Promise<ResearchJob<Sweep2DResult>> {
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
    return this.request(`/analytics/factor-exposure/${backtestId}`, {
      method: "POST",
    });
  }

  async getRegimeAnalysis(backtestId: string): Promise<RegimeAnalysisResult> {
    return this.request(`/analytics/regime-analysis/${backtestId}`, {
      method: "POST",
    });
  }

  async getCapacityAnalysis(backtestId: string): Promise<CapacityResult> {
    return this.request(`/analytics/capacity/${backtestId}`, {
      method: "POST",
    });
  }

  async getRiskBudgetAnalysis(
    backtestId: string,
    lookbackDays: number = 63,
  ): Promise<RiskBudgetResult> {
    return this.request(
      `/analytics/risk-budget/${backtestId}?lookback_days=${lookbackDays}`,
      { method: "POST" },
    );
  }

  async getTransactionCostAnalysis(
    backtestId: string,
  ): Promise<TransactionCostAnalysisResult> {
    return this.request(`/analytics/tca/${backtestId}`, { method: "POST" });
  }

  async portfolioBlend(
    backtestIds: string[],
    weights: number[],
    optimize: "custom" | "equal" | "max_sharpe" | "min_dd" = "custom",
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
    nTrials: number,
  ): Promise<ResearchJob<BayesOptResult>> {
    // Fetch the original backtest to get base_config
    const result = await this.getBacktestResult(backtestId);
    return this.request("/backtest/optimize", {
      method: "POST",
      body: JSON.stringify({
        base_config: result.config,
        param_specs: paramSpecs,
        metric,
        n_trials: nTrials,
        maximize: ![
          "max_drawdown_pct",
          "annualized_volatility_pct",
          "var_95_pct",
          "cvar_95_pct",
        ].includes(metric),
      }),
    });
  }

  // Correlation & cointegration
  async getCorrelationAnalysis(
    tickers: string[],
    startDate: string,
    endDate: string,
    rollingWindow: number = 63,
    maxPairs: number = 10,
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
    lookback: number = 63,
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

  // Options analytics
  async priceOption(params: {
    spot: number;
    strike: number;
    days_to_expiry: number;
    risk_free_rate: number;
    volatility: number;
    option_type: "call" | "put";
  }): Promise<OptionPriceResult> {
    return this.request("/options/price", {
      method: "POST",
      body: JSON.stringify(params),
    });
  }

  async solveImpliedVol(params: {
    market_price: number;
    spot: number;
    strike: number;
    days_to_expiry: number;
    risk_free_rate: number;
    option_type: "call" | "put";
  }): Promise<ImpliedVolResult> {
    return this.request("/options/implied-vol", {
      method: "POST",
      body: JSON.stringify(params),
    });
  }

  async getOptionsChain(params: {
    spot: number;
    risk_free_rate?: number;
    volatility?: number;
    days_to_expiry?: number[];
    n_strikes?: number;
  }): Promise<{ spot: number; chain: OptionsChainEntry[] }> {
    return this.request("/options/chain", {
      method: "POST",
      body: JSON.stringify(params),
    });
  }

  async getVolSurface(params: {
    spot: number;
    risk_free_rate?: number;
    base_volatility?: number;
    days_to_expiry?: number[];
    n_strikes?: number;
  }): Promise<VolSurfaceResult> {
    return this.request("/options/vol-surface", {
      method: "POST",
      body: JSON.stringify(params),
    });
  }

  async getPnlScenario(params: {
    spot: number;
    strike: number;
    days_to_expiry: number;
    risk_free_rate?: number;
    volatility?: number;
    option_type: "call" | "put";
    position: 1 | -1;
  }): Promise<PnlScenarioResult> {
    return this.request("/options/pnl-scenario", {
      method: "POST",
      body: JSON.stringify(params),
    });
  }

  getExportUrl(backtestId: string, format: "csv" = "csv"): string {
    const params = new URLSearchParams({ format });
    if (this.accessToken) {
      params.set("access_token", this.accessToken);
    }
    return `${API_BASE}/analytics/export/${backtestId}?${params.toString()}`;
  }
}

export const api = new ApiClient();
