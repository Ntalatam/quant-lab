import { fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { renderWithProviders } from "@/test/test-utils";
import { useStrategies } from "@/hooks/useAnalytics";
import { useBacktestStore } from "@/store/backtest-store";

import { StrategyForm } from "./StrategyForm";

vi.mock("@/hooks/useAnalytics", () => ({
  useStrategies: vi.fn(),
}));

const mockedUseStrategies = vi.mocked(useStrategies);

const mockStrategies = [
  {
    id: "sma_crossover",
    name: "SMA Crossover",
    description: "Trend-following crossover strategy.",
    signal_mode: "long_only" as const,
    requires_short_selling: false,
    category: "trend_following" as const,
    params: [
      {
        name: "short_window",
        label: "Short Window",
        type: "int" as const,
        default: 20,
        min: 5,
        max: 50,
        step: 1,
        description: "Fast moving average lookback.",
      },
    ],
  },
  {
    id: "market_neutral_momentum",
    name: "Market Neutral Momentum",
    description: "Balanced long/short momentum basket.",
    signal_mode: "long_short" as const,
    requires_short_selling: true,
    category: "momentum" as const,
    params: [
      {
        name: "long_n",
        label: "Long Basket Size",
        type: "int" as const,
        default: 3,
        min: 1,
        max: 10,
        step: 1,
        description: "Number of long names to hold.",
      },
    ],
  },
];

const initialState = useBacktestStore.getState();

describe("StrategyForm", () => {
  beforeEach(() => {
    mockedUseStrategies.mockReturnValue({
      data: mockStrategies,
      isLoading: false,
    } as ReturnType<typeof useStrategies>);

    useBacktestStore.setState(
      {
        ...initialState,
        config: {
          ...initialState.config,
          strategy_id: "sma_crossover",
          params: {},
          allow_short_selling: false,
          tickers: ["AAPL"],
        },
      },
      true,
    );
  });

  afterEach(() => {
    useBacktestStore.setState(initialState, true);
  });

  it("loads strategy defaults and enables shorting for short-required strategies", async () => {
    const user = userEvent.setup();
    renderWithProviders(<StrategyForm />);

    await user.selectOptions(
      screen.getByLabelText("Strategy"),
      "market_neutral_momentum",
    );

    expect(
      screen.getByText("Balanced long/short momentum basket."),
    ).toBeInTheDocument();
    expect(screen.getByText("Requires short selling")).toBeInTheDocument();

    await waitFor(() => {
      const config = useBacktestStore.getState().config;
      expect(config.allow_short_selling).toBe(true);
      expect(config.params?.long_n).toBe(3);
    });
  });

  it("normalizes comma-separated tickers into uppercase symbols", async () => {
    renderWithProviders(<StrategyForm />);

    const tickerInput = screen.getByLabelText(/Tickers \(comma-separated\)/i);
    fireEvent.change(tickerInput, {
      target: { value: "aapl, msft, spy" },
    });

    await waitFor(() => {
      expect(useBacktestStore.getState().config.tickers).toEqual([
        "AAPL",
        "MSFT",
        "SPY",
      ]);
    });
  });

  it("does not reset tuned params when optional short selling is toggled", async () => {
    const user = userEvent.setup();
    renderWithProviders(<StrategyForm />);

    await waitFor(() => {
      expect(useBacktestStore.getState().config.params?.short_window).toBe(20);
    });

    useBacktestStore.getState().setConfig({
      params: { short_window: 35 },
    });

    await user.click(screen.getByRole("checkbox"));

    await waitFor(() => {
      const config = useBacktestStore.getState().config;
      expect(config.allow_short_selling).toBe(true);
      expect(config.params?.short_window).toBe(35);
    });
  });
});
