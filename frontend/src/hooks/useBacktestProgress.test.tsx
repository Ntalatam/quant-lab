import { fireEvent, waitFor } from "@testing-library/react";

import { useBacktestProgress } from "@/hooks/useBacktestProgress";
import { api } from "@/lib/api";
import { renderWithProviders } from "@/test/test-utils";

const CONFIG = {
  strategy_id: "sma_crossover",
  params: { short_window: 20, long_window: 60 },
  tickers: ["AAPL", "MSFT"],
  benchmark: "SPY",
  start_date: "2024-01-01",
  end_date: "2024-05-01",
  initial_capital: 100000,
  slippage_bps: 5,
  commission_per_share: 0.005,
  market_impact_model: "almgren_chriss" as const,
  max_volume_participation_pct: 5,
  position_sizing: "equal_weight" as const,
  portfolio_construction_model: "equal_weight" as const,
  portfolio_lookback_days: 63,
  max_position_pct: 25,
  max_gross_exposure_pct: 150,
  turnover_limit_pct: 100,
  max_sector_exposure_pct: 100,
  allow_short_selling: false,
  max_short_position_pct: 25,
  short_margin_requirement_pct: 50,
  short_borrow_rate_bps: 200,
  short_locate_fee_bps: 10,
  short_squeeze_threshold_pct: 15,
  rebalance_frequency: "daily" as const,
};

function ProgressProbe() {
  const { progress, run } = useBacktestProgress();

  return (
    <div>
      <button onClick={() => void run(CONFIG)}>Run</button>
      <span data-testid="status">{progress.status}</span>
      <span data-testid="message">
        {"message" in progress ? progress.message : ""}
      </span>
      <span data-testid="pct">{"pct" in progress ? progress.pct : 0}</span>
      <span data-testid="backtest-id">
        {"id" in progress ? progress.id : ""}
      </span>
    </div>
  );
}

describe("useBacktestProgress", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("polls queued jobs through completion", async () => {
    vi.spyOn(api, "runBacktest").mockResolvedValue({
      id: "job_1",
      kind: "backtest_run",
      status: "queued",
      progress_pct: 0,
      progress_current: 0,
      progress_total: 0,
      progress_message: "Queued backtest run.",
      progress_date: null,
      progress_equity: null,
      logs: [],
      attempt_count: 0,
      max_attempts: 1,
      result_backtest_run_id: null,
      result: null,
      error_message: null,
      queued_at: "2026-04-05T12:00:00Z",
      started_at: null,
      completed_at: null,
      failed_at: null,
      updated_at: "2026-04-05T12:00:00Z",
    });

    vi.spyOn(api, "getResearchJob")
      .mockResolvedValueOnce({
        id: "job_1",
        kind: "backtest_run",
        status: "running",
        progress_pct: 0.25,
        progress_current: 25,
        progress_total: 100,
        progress_message: "Simulating 25 of 100 bars",
        progress_date: "2024-02-01",
        progress_equity: 103250,
        logs: [],
        attempt_count: 1,
        max_attempts: 1,
        result_backtest_run_id: null,
        result: null,
        error_message: null,
        queued_at: "2026-04-05T12:00:00Z",
        started_at: "2026-04-05T12:00:01Z",
        completed_at: null,
        failed_at: null,
        updated_at: "2026-04-05T12:00:02Z",
      })
      .mockResolvedValueOnce({
        id: "job_1",
        kind: "backtest_run",
        status: "completed",
        progress_pct: 1,
        progress_current: 100,
        progress_total: 100,
        progress_message: "Backtest ready.",
        progress_date: "2024-05-01",
        progress_equity: 118400,
        logs: [],
        attempt_count: 1,
        max_attempts: 1,
        result_backtest_run_id: "bt_1",
        result: { backtest_run_id: "bt_1" },
        error_message: null,
        queued_at: "2026-04-05T12:00:00Z",
        started_at: "2026-04-05T12:00:01Z",
        completed_at: "2026-04-05T12:00:03Z",
        failed_at: null,
        updated_at: "2026-04-05T12:00:03Z",
      });

    const { getByRole, getByTestId } = renderWithProviders(<ProgressProbe />);

    fireEvent.click(getByRole("button", { name: "Run" }));

    await waitFor(() => {
      expect(getByTestId("status").textContent).toBe("queued");
    });

    await waitFor(
      () => {
        expect(getByTestId("status").textContent).toBe("running");
        expect(getByTestId("pct").textContent).toBe("0.25");
      },
      { timeout: 2000 },
    );

    await waitFor(
      () => {
        expect(getByTestId("status").textContent).toBe("complete");
        expect(getByTestId("backtest-id").textContent).toBe("bt_1");
      },
      { timeout: 3000 },
    );
  });
});
