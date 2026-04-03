import { screen } from "@testing-library/react";

import { renderWithProviders } from "@/test/test-utils";

import { MetricsCard } from "./MetricsCard";

describe("MetricsCard", () => {
  it("renders benchmark context and percentile rank", () => {
    renderWithProviders(
      <MetricsCard
        label="Sharpe Ratio"
        value="1.42"
        benchmark="0.91"
        positive={true}
        percentile={0.75}
      />
    );

    expect(screen.getByText("Sharpe Ratio")).toBeInTheDocument();
    expect(screen.getByText("1.42")).toHaveClass("text-accent-green");
    expect(screen.getByText((content) => content.includes("Bench"))).toBeInTheDocument();
    expect(screen.getByText("0.91")).toBeInTheDocument();
    expect(screen.getByText(/top 25%/i)).toBeInTheDocument();
  });

  it("uses the description as a hover title and renders negative values distinctly", () => {
    renderWithProviders(
      <MetricsCard
        label="Max Drawdown"
        value="-12.40%"
        positive={false}
        description="Worst peak-to-trough decline"
      />
    );

    expect(screen.getByTitle("Worst peak-to-trough decline")).toBeInTheDocument();
    expect(screen.getByText("-12.40%")).toHaveClass("text-accent-red");
  });
});
