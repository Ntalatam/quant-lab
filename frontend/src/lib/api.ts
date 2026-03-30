import type {
  BacktestConfig,
  BacktestResult,
  BacktestSummary,
  ComparisonResult,
  MonteCarloResult,
  StrategyInfo,
  SweepResult,
  Sweep2DResult,
  WalkForwardResult,
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

class ApiClient {
  private async request<T>(path: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE}${path}`, {
      headers: { "Content-Type": "application/json" },
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
    return this.request("/backtest/list");
  }

  async deleteBacktest(id: string): Promise<void> {
    return this.request(`/backtest/${id}`, { method: "DELETE" });
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

  getExportUrl(backtestId: string, format: "csv" = "csv"): string {
    return `${API_BASE}/analytics/export/${backtestId}?format=${format}`;
  }
}

export const api = new ApiClient();
