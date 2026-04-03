import { act, screen } from "@testing-library/react";
import { vi } from "vitest";

import { renderWithProviders } from "@/test/test-utils";

import { DrawdownChart } from "./DrawdownChart";

const areaSeriesSetData = vi.fn();
const lineSeriesSetData = vi.fn();
const addSeries = vi.fn();
const subscribeCrosshairMove = vi.fn();

let areaSeriesRef: { setData: typeof areaSeriesSetData } | null = null;
let crosshairHandler:
  | ((param: { seriesData?: Map<unknown, { value: number }> }) => void)
  | null = null;

vi.mock("./LightweightChartWrapper", async () => {
  const React = await import("react");

  return {
    AreaSeries: "AreaSeries",
    LineSeries: "LineSeries",
    toTime: (value: string) => value,
    LightweightChart: ({
      onInit,
      height,
    }: {
      onInit: (chart: unknown, container: HTMLDivElement) => void;
      height?: number;
    }) => {
      React.useEffect(() => {
        areaSeriesSetData.mockReset();
        lineSeriesSetData.mockReset();
        addSeries.mockReset();
        subscribeCrosshairMove.mockReset();

        const areaSeries = { setData: areaSeriesSetData };
        const lineSeries = { setData: lineSeriesSetData };
        areaSeriesRef = areaSeries;

        addSeries.mockImplementation((seriesType: string) =>
          seriesType === "AreaSeries" ? areaSeries : lineSeries
        );
        subscribeCrosshairMove.mockImplementation(
          (handler: (param: { seriesData?: Map<unknown, { value: number }> }) => void) => {
            crosshairHandler = handler;
          }
        );

        const chart = {
          addSeries,
          subscribeCrosshairMove,
        };

        onInit(chart, document.createElement("div"));
      }, [onInit]);

      return <div data-testid="mock-drawdown-chart" data-height={height} />;
    },
  };
});

describe("DrawdownChart", () => {
  afterEach(() => {
    crosshairHandler = null;
    areaSeriesRef = null;
  });

  it("initializes the area chart data and renders the latest drawdown in the legend", () => {
    renderWithProviders(
      <DrawdownChart
        data={[
          { date: "2024-01-02", value: -1.25 },
          { date: "2024-01-03", value: -4.5 },
          { date: "2024-01-04", value: -7.5 },
        ]}
        height={240}
      />
    );

    expect(screen.getByTestId("mock-drawdown-chart")).toHaveAttribute(
      "data-height",
      "240"
    );
    expect(areaSeriesSetData).toHaveBeenCalledWith([
      { time: "2024-01-02", value: -1.25 },
      { time: "2024-01-03", value: -4.5 },
      { time: "2024-01-04", value: -7.5 },
    ]);
    expect(lineSeriesSetData).toHaveBeenCalledWith([
      { time: "2024-01-02", value: 0 },
      { time: "2024-01-04", value: 0 },
    ]);
    expect(screen.getByText("-7.50%")).toBeInTheDocument();
  });

  it("updates the legend when the crosshair moves across the chart", () => {
    renderWithProviders(
      <DrawdownChart
        data={[
          { date: "2024-01-02", value: -1.25 },
          { date: "2024-01-03", value: -4.5 },
          { date: "2024-01-04", value: -7.5 },
        ]}
      />
    );

    expect(crosshairHandler).not.toBeNull();
    expect(areaSeriesRef).not.toBeNull();

    act(() => {
      crosshairHandler?.({
        seriesData: new Map([[areaSeriesRef, { value: -2.25 }]]),
      });
    });

    expect(screen.getByText("-2.25%")).toBeInTheDocument();
  });
});
