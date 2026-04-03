"use client";

import { useState } from "react";
import type { Trade } from "@/lib/types";
import { formatCurrency, formatDate } from "@/lib/formatters";

interface TradeLogProps {
  trades: Trade[];
}

type SortField = "entry_date" | "pnl" | "pnl_pct" | "ticker";
type SortDir = "asc" | "desc";

function tradeLabel(trade: Trade) {
  if (trade.position_direction === "SHORT") {
    return trade.side === "SELL" ? "SHORT" : "COVER";
  }
  return trade.side;
}

function tradeTone(trade: Trade) {
  if (trade.position_direction === "SHORT") {
    return trade.side === "SELL" ? "text-accent-yellow" : "text-accent-blue";
  }
  return trade.side === "BUY" ? "text-accent-green" : "text-accent-red";
}

export function TradeLog({ trades }: TradeLogProps) {
  const [sortField, setSortField] = useState<SortField>("entry_date");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const sorted = [...trades].sort((a, b) => {
    let cmp = 0;
    if (sortField === "entry_date") {
      cmp = (a.entry_date || "").localeCompare(b.entry_date || "");
    } else if (sortField === "pnl") {
      cmp = (a.pnl || 0) - (b.pnl || 0);
    } else if (sortField === "pnl_pct") {
      cmp = (a.pnl_pct || 0) - (b.pnl_pct || 0);
    } else if (sortField === "ticker") {
      cmp = a.ticker.localeCompare(b.ticker);
    }
    return sortDir === "asc" ? cmp : -cmp;
  });

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortField(field);
      setSortDir("desc");
    }
  };

  const headerClass =
    "text-left text-xs text-text-muted font-normal py-2 px-2 cursor-pointer hover:text-text-secondary select-none";

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs font-mono tabular-nums">
        <thead>
          <tr className="border-b border-border">
            <th className={headerClass} onClick={() => toggleSort("ticker")}>
              Ticker
            </th>
            <th className={headerClass}>Side</th>
            <th className={headerClass} onClick={() => toggleSort("entry_date")}>
              Entry Date
            </th>
            <th className={headerClass}>Entry Price</th>
            <th className={headerClass}>Exit Date</th>
            <th className={headerClass}>Exit Price</th>
            <th className={headerClass}>Shares</th>
            <th className={headerClass} onClick={() => toggleSort("pnl")}>
              P&L
            </th>
            <th className={headerClass} onClick={() => toggleSort("pnl_pct")}>
              P&L %
            </th>
            <th className={headerClass}>Cost</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((trade) => (
            <tr
              key={trade.id}
              className="border-b border-border/50 hover:bg-bg-hover transition-colors"
            >
              <td className="py-1.5 px-2 text-text-primary">{trade.ticker}</td>
              <td className="py-1.5 px-2">
                <span className={tradeTone(trade)}>{tradeLabel(trade)}</span>
                {trade.risk_event && (
                  <div className="text-[10px] text-accent-yellow mt-0.5">
                    {trade.risk_event.replace(/_/g, " ")}
                  </div>
                )}
              </td>
              <td className="py-1.5 px-2 text-text-secondary">
                {trade.entry_date ? formatDate(trade.entry_date) : "-"}
              </td>
              <td className="py-1.5 px-2 text-text-primary">
                ${trade.entry_price.toFixed(2)}
              </td>
              <td className="py-1.5 px-2 text-text-secondary">
                {trade.exit_date ? formatDate(trade.exit_date) : "-"}
              </td>
              <td className="py-1.5 px-2 text-text-primary">
                {trade.exit_price ? `$${trade.exit_price.toFixed(2)}` : "-"}
              </td>
              <td className="py-1.5 px-2 text-text-primary">{trade.shares}</td>
              <td
                className={`py-1.5 px-2 ${
                  trade.pnl !== null
                    ? trade.pnl >= 0
                      ? "text-accent-green"
                      : "text-accent-red"
                    : "text-text-muted"
                }`}
              >
                {trade.pnl !== null ? formatCurrency(trade.pnl) : "-"}
              </td>
              <td
                className={`py-1.5 px-2 ${
                  trade.pnl_pct !== null
                    ? trade.pnl_pct >= 0
                      ? "text-accent-green"
                      : "text-accent-red"
                    : "text-text-muted"
                }`}
              >
                {trade.pnl_pct !== null
                  ? `${trade.pnl_pct >= 0 ? "+" : ""}${trade.pnl_pct.toFixed(2)}%`
                  : "-"}
              </td>
              <td className="py-1.5 px-2 text-text-muted">
                $
                {(
                  trade.commission +
                  trade.slippage +
                  trade.borrow_cost +
                  trade.locate_fee
                ).toFixed(2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {trades.length === 0 && (
        <p className="text-center text-text-muted py-8 text-sm">
          No trades recorded
        </p>
      )}
    </div>
  );
}
