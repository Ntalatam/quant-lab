import { render } from "@testing-library/react";
import { vi } from "vitest";
import type { LogicalRange } from "lightweight-charts";

import { LightweightChart } from "./LightweightChartWrapper";

type FakeChart = {
  applyOptions: ReturnType<typeof vi.fn>;
  remove: ReturnType<typeof vi.fn>;
  subscribeCrosshairMove: ReturnType<typeof vi.fn>;
  unsubscribeCrosshairMove: ReturnType<typeof vi.fn>;
  timeScaleApi: {
    fitContent: ReturnType<typeof vi.fn>;
    subscribeVisibleLogicalRangeChange: ReturnType<typeof vi.fn>;
    unsubscribeVisibleLogicalRangeChange: ReturnType<typeof vi.fn>;
    setVisibleLogicalRange: ReturnType<typeof vi.fn>;
  };
};

const { createdCharts, createChart } = vi.hoisted(() => {
  const charts: FakeChart[] = [];
  const createChartMock = vi.fn(() => {
    const timeScaleApi = {
      fitContent: vi.fn(),
      subscribeVisibleLogicalRangeChange: vi.fn(),
      unsubscribeVisibleLogicalRangeChange: vi.fn(),
      setVisibleLogicalRange: vi.fn(),
    };
    const chart = {
      applyOptions: vi.fn(),
      remove: vi.fn(),
      subscribeCrosshairMove: vi.fn(),
      unsubscribeCrosshairMove: vi.fn(),
      timeScale: vi.fn(() => timeScaleApi),
    };
    charts.push({
      applyOptions: chart.applyOptions,
      remove: chart.remove,
      subscribeCrosshairMove: chart.subscribeCrosshairMove,
      unsubscribeCrosshairMove: chart.unsubscribeCrosshairMove,
      timeScaleApi,
    });
    return chart;
  });
  return {
    createdCharts: charts,
    createChart: createChartMock,
  };
});

vi.mock("lightweight-charts", () => ({
  createChart,
  createSeriesMarkers: vi.fn(),
  CandlestickSeries: "CandlestickSeries",
  LineSeries: "LineSeries",
  AreaSeries: "AreaSeries",
  HistogramSeries: "HistogramSeries",
  ColorType: { Solid: "solid" },
  CrosshairMode: { Normal: 0 },
}));

describe("LightweightChart", () => {
  beforeEach(() => {
    createdCharts.length = 0;
    createChart.mockClear();
  });

  it("recreates the chart when onInit changes and runs cleanup", () => {
    const cleanupA = vi.fn();
    const cleanupB = vi.fn();
    const onInitA = vi.fn(() => cleanupA);
    const onInitB = vi.fn(() => cleanupB);

    const { rerender, unmount } = render(<LightweightChart onInit={onInitA} />);

    expect(createChart).toHaveBeenCalledTimes(1);
    expect(onInitA).toHaveBeenCalledTimes(1);

    rerender(<LightweightChart onInit={onInitB} />);

    expect(cleanupA).toHaveBeenCalledTimes(1);
    expect(createdCharts[0].remove).toHaveBeenCalledTimes(1);
    expect(createChart).toHaveBeenCalledTimes(2);
    expect(onInitB).toHaveBeenCalledTimes(1);

    unmount();

    expect(cleanupB).toHaveBeenCalledTimes(1);
    expect(createdCharts[1].remove).toHaveBeenCalledTimes(1);
  });

  it("applies option updates and uses the latest event callbacks without remounting", () => {
    const onInit = vi.fn();
    const onCrosshairMoveA = vi.fn();
    const onCrosshairMoveB = vi.fn();
    const onVisibleRangeChangeA = vi.fn();
    const onVisibleRangeChangeB = vi.fn();
    const syncRange = {
      from: 10,
      to: 20,
    } as unknown as LogicalRange;

    const { rerender } = render(
      <LightweightChart
        onInit={onInit}
        height={220}
        options={{ rightPriceScale: { visible: false } }}
        onCrosshairMove={onCrosshairMoveA}
        onVisibleRangeChange={onVisibleRangeChangeA}
      />,
    );

    expect(createChart).toHaveBeenCalledTimes(1);
    expect(createdCharts[0].applyOptions).toHaveBeenLastCalledWith({
      rightPriceScale: { visible: false },
      height: 220,
    });

    const crosshairHandler =
      createdCharts[0].subscribeCrosshairMove.mock.calls[0][0];
    const visibleRangeHandler =
      createdCharts[0].timeScaleApi.subscribeVisibleLogicalRangeChange.mock
        .calls[0][0];

    rerender(
      <LightweightChart
        onInit={onInit}
        height={260}
        options={{ leftPriceScale: { visible: false } }}
        onCrosshairMove={onCrosshairMoveB}
        onVisibleRangeChange={onVisibleRangeChangeB}
        syncRange={syncRange}
      />,
    );

    expect(createChart).toHaveBeenCalledTimes(1);
    expect(createdCharts[0].applyOptions).toHaveBeenLastCalledWith({
      leftPriceScale: { visible: false },
      height: 260,
    });
    expect(
      createdCharts[0].timeScaleApi.setVisibleLogicalRange,
    ).toHaveBeenCalledWith(syncRange);

    crosshairHandler({ time: "2024-01-02" });
    visibleRangeHandler({ from: 2, to: 4 });

    expect(onCrosshairMoveA).not.toHaveBeenCalled();
    expect(onVisibleRangeChangeA).not.toHaveBeenCalled();
    expect(onCrosshairMoveB).toHaveBeenCalledWith({ time: "2024-01-02" });
    expect(onVisibleRangeChangeB).toHaveBeenCalledWith({ from: 2, to: 4 });
  });
});
