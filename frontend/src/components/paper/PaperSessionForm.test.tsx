import { fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { useStrategies } from "@/hooks/useAnalytics";
import { useCreatePaperSession } from "@/hooks/usePaperTrading";
import { renderWithProviders } from "@/test/test-utils";

import { PaperSessionForm } from "./PaperSessionForm";

const pushMock = vi.fn();
const mutateAsyncMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: pushMock,
  }),
}));

vi.mock("@/hooks/useAnalytics", () => ({
  useStrategies: vi.fn(),
}));

vi.mock("@/hooks/usePaperTrading", () => ({
  useCreatePaperSession: vi.fn(),
}));

const mockedUseStrategies = vi.mocked(useStrategies);
const mockedUseCreatePaperSession = vi.mocked(useCreatePaperSession);

describe("PaperSessionForm", () => {
  beforeEach(() => {
    pushMock.mockReset();
    mutateAsyncMock.mockReset();
    mutateAsyncMock.mockResolvedValue({ id: "paper-session-1" });

    mockedUseStrategies.mockReturnValue({
      data: [
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
      ],
      isLoading: false,
      error: null,
    } as ReturnType<typeof useStrategies>);

    mockedUseCreatePaperSession.mockReturnValue({
      mutateAsync: mutateAsyncMock,
      isPending: false,
      error: null,
    } as unknown as ReturnType<typeof useCreatePaperSession>);
  });

  it("submits normalized payloads and preserves required short selling", async () => {
    const user = userEvent.setup();

    renderWithProviders(
      <PaperSessionForm
        prefillConfig={{
          strategy_id: "market_neutral_momentum",
          params: { long_n: 5 },
          tickers: ["msft"],
          benchmark: "QQQ",
          initial_capital: 150_000,
        }}
      />,
    );

    await waitFor(() => {
      expect(
        screen.getByDisplayValue("Market Neutral Momentum Live Session"),
      ).toBeInTheDocument();
    });

    const shortSellingToggle = screen.getByLabelText("Enable Short Selling");
    expect(shortSellingToggle).toBeChecked();
    expect(shortSellingToggle).toBeDisabled();

    fireEvent.change(screen.getByPlaceholderText("AAPL, MSFT, NVDA"), {
      target: { value: "tsla, spy" },
    });
    await user.click(
      screen.getByRole("button", { name: "Create Simulated Session" }),
    );

    await waitFor(() => {
      expect(mutateAsyncMock).toHaveBeenCalledWith(
        expect.objectContaining({
          execution_mode: "simulated_paper",
          broker_adapter: "paper",
          strategy_id: "market_neutral_momentum",
          tickers: ["TSLA", "SPY"],
          benchmark: "QQQ",
          allow_short_selling: true,
          params: { long_n: 5 },
        }),
      );
      expect(pushMock).toHaveBeenCalledWith("/paper/paper-session-1");
    });
  });

  it("switches into broker paper mode with Alpaca", async () => {
    const user = userEvent.setup();

    renderWithProviders(<PaperSessionForm />);

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: "Create Simulated Session" }),
      ).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /Broker Paper/ }));
    await user.click(
      screen.getByRole("button", { name: "Create Broker Paper Session" }),
    );

    await waitFor(() => {
      expect(mutateAsyncMock).toHaveBeenCalledWith(
        expect.objectContaining({
          execution_mode: "broker_paper",
          broker_adapter: "alpaca",
        }),
      );
    });
  });
});
