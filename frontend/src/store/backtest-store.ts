import { create } from "zustand";
import type { BacktestConfig, BacktestResult } from "@/lib/types";

interface BacktestStore {
  config: Partial<BacktestConfig>;
  setConfig: (config: Partial<BacktestConfig>) => void;
  resetConfig: () => void;
  lastResult: BacktestResult | null;
  setLastResult: (result: BacktestResult | null) => void;
  isRunning: boolean;
  setIsRunning: (running: boolean) => void;
  selectedBacktestIds: string[];
  toggleBacktestSelection: (id: string) => void;
  clearSelection: () => void;
}

const DEFAULT_CONFIG: Partial<BacktestConfig> = {
  strategy_id: "sma_crossover",
  params: {},
  tickers: ["AAPL"],
  benchmark: "SPY",
  start_date: "2019-01-01",
  end_date: "2024-01-01",
  initial_capital: 100_000,
  slippage_bps: 5.0,
  commission_per_share: 0.005,
  position_sizing: "equal_weight",
  portfolio_construction_model: "equal_weight",
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
  rebalance_frequency: "daily",
};

export const useBacktestStore = create<BacktestStore>((set) => ({
  config: DEFAULT_CONFIG,
  setConfig: (config) =>
    set((state) => ({ config: { ...state.config, ...config } })),
  resetConfig: () => set({ config: DEFAULT_CONFIG }),
  lastResult: null,
  setLastResult: (result) => set({ lastResult: result }),
  isRunning: false,
  setIsRunning: (running) => set({ isRunning: running }),
  selectedBacktestIds: [],
  toggleBacktestSelection: (id) =>
    set((state) => ({
      selectedBacktestIds: state.selectedBacktestIds.includes(id)
        ? state.selectedBacktestIds.filter((i) => i !== id)
        : [...state.selectedBacktestIds, id],
    })),
  clearSelection: () => set({ selectedBacktestIds: [] }),
}));
