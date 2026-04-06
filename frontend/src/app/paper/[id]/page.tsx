"use client";

import { use } from "react";
import Link from "next/link";
import { ArrowLeft, Pause, Play, RadioTower, Square } from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { PageLoading } from "@/components/shared/LoadingSpinner";
import {
  usePaperSession,
  usePaperSessionStream,
  usePausePaperSession,
  useStartPaperSession,
  useStopPaperSession,
} from "@/hooks/usePaperTrading";
import { formatCurrency, formatDate, formatPercent } from "@/lib/formatters";
import { PAPER_EXECUTION_MODE_LABELS } from "@/lib/constants";

function formatTimestamp(value: string | null | undefined) {
  if (!value) return "—";
  const date = new Date(value);
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function statusAccent(status: string) {
  switch (status) {
    case "active":
      return "var(--color-accent-green)";
    case "paused":
      return "var(--color-accent-yellow)";
    case "error":
      return "var(--color-accent-red)";
    default:
      return "var(--color-accent-blue)";
  }
}

export default function PaperTradingSessionPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);

  const detailQuery = usePaperSession(id);
  const startMutation = useStartPaperSession();
  const pauseMutation = usePausePaperSession();
  const stopMutation = useStopPaperSession();
  const { session, connection } = usePaperSessionStream(id, detailQuery.data);

  if (detailQuery.isLoading) return <PageLoading />;
  if (detailQuery.error || !session) {
    return (
      <div className="text-accent-red text-sm">
        {detailQuery.error?.message ?? "Paper trading session not found"}
      </div>
    );
  }

  const actionPending =
    startMutation.isPending ||
    pauseMutation.isPending ||
    stopMutation.isPending;

  const equityChart = session.equity_curve.map((point) => ({
    timestamp: point.timestamp,
    timeLabel: formatTimestamp(point.timestamp),
    equity: point.equity,
    cash: point.cash,
    market_value: point.market_value,
  }));

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <Link
          href="/paper"
          className="text-text-muted hover:text-text-primary transition-colors"
        >
          <ArrowLeft size={18} />
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-xl font-bold text-text-primary tracking-tight">
              {session.name}
            </h1>
            <span
              className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full border"
              style={{
                color: statusAccent(session.status),
                borderColor: `${statusAccent(session.status)}55`,
                background: `${statusAccent(session.status)}12`,
              }}
            >
              {session.status}
            </span>
            <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full border border-border text-text-secondary">
              {PAPER_EXECUTION_MODE_LABELS[session.execution_mode]}
            </span>
          </div>
          <p className="text-xs text-text-muted">
            {session.strategy_id} · {session.tickers.join(", ")} ·{" "}
            {session.bar_interval} bars · {session.id.slice(0, 8)}
          </p>
          {session.broker_account_label && (
            <p className="text-[11px] text-text-muted mt-1">
              Account: {session.broker_account_label}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span
            className="flex items-center gap-1.5 text-[11px] px-3 py-1.5 rounded border"
            style={{
              color:
                connection === "connected"
                  ? "var(--color-accent-green)"
                  : connection === "error"
                    ? "var(--color-accent-red)"
                    : "var(--color-accent-blue)",
              borderColor:
                connection === "connected"
                  ? "rgba(0,212,170,0.3)"
                  : connection === "error"
                    ? "rgba(255,68,102,0.3)"
                    : "rgba(68,136,255,0.3)",
            }}
          >
            <RadioTower size={12} />
            {connection === "connected"
              ? "Live stream connected"
              : connection === "error"
                ? "Live stream error"
                : "Connecting…"}
          </span>
          <button
            onClick={() => startMutation.mutate(id)}
            disabled={actionPending || session.status === "active"}
            className="flex items-center gap-1.5 text-xs px-3 py-2 rounded disabled:opacity-40"
            style={{
              background: "rgba(0,212,170,0.12)",
              border: "1px solid rgba(0,212,170,0.22)",
              color: "var(--color-accent-green)",
            }}
          >
            <Play size={12} />
            Start
          </button>
          <button
            onClick={() => pauseMutation.mutate(id)}
            disabled={actionPending || session.status !== "active"}
            className="flex items-center gap-1.5 text-xs px-3 py-2 rounded disabled:opacity-40"
            style={{
              background: "rgba(255,187,51,0.12)",
              border: "1px solid rgba(255,187,51,0.22)",
              color: "var(--color-accent-yellow)",
            }}
          >
            <Pause size={12} />
            Pause
          </button>
          <button
            onClick={() => stopMutation.mutate(id)}
            disabled={actionPending || session.status === "stopped"}
            className="flex items-center gap-1.5 text-xs px-3 py-2 rounded disabled:opacity-40"
            style={{
              background: "rgba(255,68,102,0.12)",
              border: "1px solid rgba(255,68,102,0.22)",
              color: "var(--color-accent-red)",
            }}
          >
            <Square size={12} />
            Stop
          </button>
        </div>
      </div>

      {session.last_error && (
        <div className="rounded-md p-3 mb-5 bg-accent-red/10 border border-accent-red/20 text-accent-red text-sm">
          {session.last_error}
        </div>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-7 gap-3 mb-6">
        {[
          {
            label: "Total Equity",
            value: formatCurrency(session.total_equity),
            tone: "text-text-primary",
          },
          {
            label: "Live Return",
            value: formatPercent(session.total_return_pct),
            tone:
              session.total_return_pct >= 0
                ? "text-accent-green"
                : "text-accent-red",
          },
          {
            label: "Cash",
            value: formatCurrency(session.cash),
            tone: "text-text-secondary",
          },
          {
            label: "Market Value",
            value: formatCurrency(session.market_value),
            tone: "text-text-secondary",
          },
          {
            label: "Open Positions",
            value: String(session.positions.length),
            tone: "text-text-primary",
          },
          {
            label: "Open Orders",
            value: String(session.open_order_count),
            tone: "text-text-primary",
          },
          {
            label: "Last Tick",
            value: formatTimestamp(session.last_price_at),
            tone: "text-text-secondary",
          },
        ].map((metric) => (
          <div
            key={metric.label}
            className="rounded-md p-4"
            style={{
              background: "var(--color-bg-card)",
              border: "1px solid var(--color-border)",
            }}
          >
            <p className="section-label mb-1.5">{metric.label}</p>
            <p className={`font-mono text-sm font-semibold ${metric.tone}`}>
              {metric.value}
            </p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1.6fr_0.8fr] gap-6 mb-6">
        <div
          className="rounded-md overflow-hidden"
          style={{
            background: "var(--color-bg-card)",
            border: "1px solid var(--color-border)",
            boxShadow: "0 1px 3px rgba(0,0,0,0.4)",
          }}
        >
          <div
            className="px-5 py-3"
            style={{ borderBottom: "1px solid var(--color-border)" }}
          >
            <h3 className="text-sm font-semibold text-text-primary">
              Live Equity Curve
            </h3>
            <p className="text-[10px] text-text-muted mt-0.5">
              Minute-by-minute mark-to-market portfolio equity
            </p>
          </div>
          <div className="p-4">
            {equityChart.length <= 1 ? (
              <div className="h-72 flex items-center justify-center text-sm text-text-muted">
                Waiting for live market data…
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={320}>
                <AreaChart data={equityChart}>
                  <defs>
                    <linearGradient
                      id="paperEquity"
                      x1="0"
                      y1="0"
                      x2="0"
                      y2="1"
                    >
                      <stop
                        offset="5%"
                        stopColor="#00d4aa"
                        stopOpacity={0.32}
                      />
                      <stop
                        offset="95%"
                        stopColor="#00d4aa"
                        stopOpacity={0.03}
                      />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e1e2a" />
                  <XAxis
                    dataKey="timeLabel"
                    tick={{ fontSize: 11 }}
                    stroke="#555566"
                    minTickGap={36}
                  />
                  <YAxis
                    tick={{ fontSize: 11 }}
                    stroke="#555566"
                    width={70}
                    tickFormatter={(value) => `$${Math.round(value / 1000)}k`}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#16161f",
                      border: "1px solid #252535",
                      borderRadius: 6,
                      fontSize: 12,
                    }}
                    formatter={(value, key) => [
                      formatCurrency(Number(value ?? 0)),
                      key === "equity"
                        ? "Equity"
                        : key === "cash"
                          ? "Cash"
                          : "Market Value",
                    ]}
                    labelFormatter={(label) => String(label)}
                  />
                  <Area
                    type="monotone"
                    dataKey="equity"
                    stroke="#00d4aa"
                    fill="url(#paperEquity)"
                    strokeWidth={2}
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div
          className="rounded-md p-5"
          style={{
            background: "var(--color-bg-card)",
            border: "1px solid var(--color-border)",
            boxShadow: "0 1px 3px rgba(0,0,0,0.4)",
          }}
        >
          <h3 className="text-sm font-semibold text-text-primary mb-4">
            Session Configuration
          </h3>
          <div className="space-y-2">
            {[
              ["Strategy", session.strategy_id],
              ["Mode", PAPER_EXECUTION_MODE_LABELS[session.execution_mode]],
              ["Broker", session.broker_adapter],
              ["Account", session.broker_account_label ?? "—"],
              ["Tickers", session.tickers.join(", ")],
              ["Benchmark", session.benchmark],
              ["Interval", session.bar_interval],
              ["Polling", `${session.polling_interval_seconds}s`],
              ["Capital", formatCurrency(session.initial_capital)],
              ["Slippage", `${session.slippage_bps} bps`],
              ["Commission", `$${session.commission_per_share}/share`],
              ["Impact", session.market_impact_model],
              ["Max Vol", `${session.max_volume_participation_pct}%`],
              [
                "Construction",
                session.portfolio_construction_model ?? "equal_weight",
              ],
              ["Risk Lookback", `${session.portfolio_lookback_days} days`],
              ["Max Position", `${session.max_position_pct}%`],
              ["Max Gross", `${session.max_gross_exposure_pct}%`],
              ["Turnover", `${session.turnover_limit_pct}%`],
              ["Sector Cap", `${session.max_sector_exposure_pct}% gross`],
              [
                "Shorting",
                session.allow_short_selling ? "Enabled" : "Disabled",
              ],
              ...(session.allow_short_selling
                ? [
                    ["Max Short", `${session.max_short_position_pct}%`],
                    ["Margin", `${session.short_margin_requirement_pct}%`],
                    ["Borrow", `${session.short_borrow_rate_bps} bps/year`],
                    ["Locate", `${session.short_locate_fee_bps} bps/entry`],
                    [
                      "Squeeze",
                      `${session.short_squeeze_threshold_pct}% adverse move`,
                    ],
                  ]
                : []),
              ["Created", formatDate(session.created_at)],
              ["Started", formatTimestamp(session.started_at)],
              ["Heartbeat", formatTimestamp(session.last_heartbeat_at)],
            ].map(([label, value]) => (
              <div
                key={label}
                className="flex justify-between text-xs py-1.5"
                style={{ borderBottom: "1px solid rgba(37,37,53,0.5)" }}
              >
                <span className="text-text-muted">{label}</span>
                <span className="text-text-primary font-mono text-right max-w-[55%]">
                  {value}
                </span>
              </div>
            ))}
          </div>

          <div className="mt-5">
            <p className="section-label mb-2">Strategy Params</p>
            <div className="space-y-1.5">
              {Object.entries(session.strategy_params).map(([key, value]) => (
                <div key={key} className="flex justify-between text-xs">
                  <span className="text-text-muted">{key}</span>
                  <span className="font-mono text-text-primary">
                    {String(value)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <div
          className="rounded-md overflow-hidden"
          style={{
            background: "var(--color-bg-card)",
            border: "1px solid var(--color-border)",
            boxShadow: "0 1px 3px rgba(0,0,0,0.4)",
          }}
        >
          <div
            className="px-5 py-3"
            style={{ borderBottom: "1px solid var(--color-border)" }}
          >
            <h3 className="text-sm font-semibold text-text-primary">
              Open Positions
            </h3>
            <p className="text-[10px] text-text-muted mt-0.5">
              Live holdings with mark-to-market P&L
            </p>
          </div>
          <div className="p-4 overflow-x-auto">
            {session.positions.length === 0 ? (
              <div className="h-56 flex items-center justify-center text-sm text-text-muted">
                No open positions yet
              </div>
            ) : (
              <table className="w-full text-xs font-mono">
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
                    {[
                      "Ticker",
                      "Side",
                      "Shares",
                      "Avg",
                      "Last",
                      "Value",
                      "Unrealized",
                    ].map((header, index) => (
                      <th
                        key={header}
                        className={`section-label py-2 px-2 font-normal ${
                          index === 0 ? "text-left" : "text-right"
                        }`}
                      >
                        {header}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {session.positions.map((position) => (
                    <tr
                      key={position.ticker}
                      style={{
                        borderBottom: "1px solid rgba(37,37,53,0.5)",
                      }}
                    >
                      <td className="py-2 px-2 text-text-secondary">
                        {position.ticker}
                      </td>
                      <td
                        className={`py-2 px-2 text-right ${
                          position.shares < 0
                            ? "text-accent-yellow"
                            : "text-accent-green"
                        }`}
                      >
                        {position.shares < 0 ? "SHORT" : "LONG"}
                      </td>
                      <td className="py-2 px-2 text-right text-text-primary">
                        {Math.abs(position.shares)}
                      </td>
                      <td className="py-2 px-2 text-right text-text-primary">
                        ${position.avg_cost.toFixed(2)}
                      </td>
                      <td className="py-2 px-2 text-right text-text-primary">
                        ${position.current_price.toFixed(2)}
                      </td>
                      <td className="py-2 px-2 text-right text-text-primary">
                        {formatCurrency(position.market_value)}
                      </td>
                      <td
                        className={`py-2 px-2 text-right ${
                          position.unrealized_pnl >= 0
                            ? "text-accent-green"
                            : "text-accent-red"
                        }`}
                      >
                        {formatCurrency(position.unrealized_pnl)}
                        <div className="text-[10px] opacity-80">
                          {formatPercent(position.unrealized_pnl_pct)}
                        </div>
                        {(position.accrued_borrow_cost > 0 ||
                          position.accrued_locate_fee > 0) && (
                          <div className="text-[10px] opacity-70">
                            Carry $
                            {(
                              position.accrued_borrow_cost +
                              position.accrued_locate_fee
                            ).toFixed(2)}
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        <div
          className="rounded-md overflow-hidden"
          style={{
            background: "var(--color-bg-card)",
            border: "1px solid var(--color-border)",
            boxShadow: "0 1px 3px rgba(0,0,0,0.4)",
          }}
        >
          <div
            className="px-5 py-3"
            style={{ borderBottom: "1px solid var(--color-border)" }}
          >
            <h3 className="text-sm font-semibold text-text-primary">
              Signal Log
            </h3>
            <p className="text-[10px] text-text-muted mt-0.5">
              Status changes, generated signals, and filled paper orders
            </p>
          </div>
          <div className="p-4 overflow-x-auto">
            {session.recent_events.length === 0 ? (
              <div className="h-56 flex items-center justify-center text-sm text-text-muted">
                No events recorded yet
              </div>
            ) : (
              <table className="w-full text-xs font-mono">
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
                    {["Time", "Type", "Ticker", "Action", "Details"].map(
                      (header, index) => (
                        <th
                          key={header}
                          className={`section-label py-2 px-2 font-normal ${
                            index === 4 ? "text-left" : "text-right"
                          }`}
                        >
                          {header}
                        </th>
                      ),
                    )}
                  </tr>
                </thead>
                <tbody>
                  {session.recent_events.map((event) => (
                    <tr
                      key={event.id}
                      style={{
                        borderBottom: "1px solid rgba(37,37,53,0.5)",
                      }}
                    >
                      <td className="py-2 px-2 text-right text-text-muted">
                        {formatTimestamp(event.timestamp)}
                      </td>
                      <td className="py-2 px-2 text-right text-text-secondary">
                        {event.event_type}
                      </td>
                      <td className="py-2 px-2 text-right text-text-primary">
                        {event.ticker ?? "—"}
                      </td>
                      <td className="py-2 px-2 text-right text-text-primary">
                        {event.action}
                      </td>
                      <td className="py-2 px-2 text-left text-text-muted">
                        <span>{event.message}</span>
                        {(event.fill_price || event.shares) && (
                          <span className="block text-[10px] mt-0.5">
                            {event.shares ? `${event.shares} sh` : ""}
                            {event.fill_price
                              ? ` @ $${event.fill_price.toFixed(2)}`
                              : ""}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 mt-6">
        <div
          className="rounded-md overflow-hidden"
          style={{
            background: "var(--color-bg-card)",
            border: "1px solid var(--color-border)",
            boxShadow: "0 1px 3px rgba(0,0,0,0.4)",
          }}
        >
          <div
            className="px-5 py-3"
            style={{ borderBottom: "1px solid var(--color-border)" }}
          >
            <h3 className="text-sm font-semibold text-text-primary">
              Recent Orders
            </h3>
            <p className="text-[10px] text-text-muted mt-0.5">
              Persisted broker and simulator order intent for this session
            </p>
          </div>
          <div className="p-4 overflow-x-auto">
            {session.recent_orders.length === 0 ? (
              <div className="h-48 flex items-center justify-center text-sm text-text-muted">
                No orders recorded yet
              </div>
            ) : (
              <table className="w-full text-xs font-mono">
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
                    {["Time", "Ticker", "Side", "Qty", "Status", "Fill"].map(
                      (header, index) => (
                        <th
                          key={header}
                          className={`section-label py-2 px-2 font-normal ${
                            index === 0 ? "text-left" : "text-right"
                          }`}
                        >
                          {header}
                        </th>
                      ),
                    )}
                  </tr>
                </thead>
                <tbody>
                  {session.recent_orders.map((order) => (
                    <tr
                      key={order.id}
                      style={{
                        borderBottom: "1px solid rgba(37,37,53,0.5)",
                      }}
                    >
                      <td className="py-2 px-2 text-left text-text-muted">
                        {formatTimestamp(order.submitted_at)}
                      </td>
                      <td className="py-2 px-2 text-right text-text-primary">
                        {order.ticker}
                      </td>
                      <td className="py-2 px-2 text-right text-text-secondary uppercase">
                        {order.side}
                      </td>
                      <td className="py-2 px-2 text-right text-text-primary">
                        {order.filled_shares}/{order.requested_shares}
                      </td>
                      <td className="py-2 px-2 text-right text-text-primary">
                        {order.status}
                      </td>
                      <td className="py-2 px-2 text-right text-text-muted">
                        {order.avg_fill_price !== null
                          ? `$${order.avg_fill_price.toFixed(2)}`
                          : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>

        <div
          className="rounded-md overflow-hidden"
          style={{
            background: "var(--color-bg-card)",
            border: "1px solid var(--color-border)",
            boxShadow: "0 1px 3px rgba(0,0,0,0.4)",
          }}
        >
          <div
            className="px-5 py-3"
            style={{ borderBottom: "1px solid var(--color-border)" }}
          >
            <h3 className="text-sm font-semibold text-text-primary">
              Recent Executions
            </h3>
            <p className="text-[10px] text-text-muted mt-0.5">
              Fills captured from the simulator or broker paper account
            </p>
          </div>
          <div className="p-4 overflow-x-auto">
            {session.recent_executions.length === 0 ? (
              <div className="h-48 flex items-center justify-center text-sm text-text-muted">
                No executions recorded yet
              </div>
            ) : (
              <table className="w-full text-xs font-mono">
                <thead>
                  <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
                    {["Time", "Ticker", "Side", "Shares", "Price", "Costs"].map(
                      (header, index) => (
                        <th
                          key={header}
                          className={`section-label py-2 px-2 font-normal ${
                            index === 0 ? "text-left" : "text-right"
                          }`}
                        >
                          {header}
                        </th>
                      ),
                    )}
                  </tr>
                </thead>
                <tbody>
                  {session.recent_executions.map((execution) => (
                    <tr
                      key={execution.id}
                      style={{
                        borderBottom: "1px solid rgba(37,37,53,0.5)",
                      }}
                    >
                      <td className="py-2 px-2 text-left text-text-muted">
                        {formatTimestamp(execution.executed_at)}
                      </td>
                      <td className="py-2 px-2 text-right text-text-primary">
                        {execution.ticker}
                      </td>
                      <td className="py-2 px-2 text-right text-text-secondary uppercase">
                        {execution.side}
                      </td>
                      <td className="py-2 px-2 text-right text-text-primary">
                        {execution.shares}
                      </td>
                      <td className="py-2 px-2 text-right text-text-primary">
                        ${execution.fill_price.toFixed(2)}
                      </td>
                      <td className="py-2 px-2 text-right text-text-muted">
                        {formatCurrency(
                          execution.commission +
                            execution.slippage_cost +
                            execution.borrow_cost +
                            execution.locate_fee,
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
