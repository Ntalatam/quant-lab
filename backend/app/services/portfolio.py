"""
Portfolio state manager.

Tracks cash, positions, equity, and trade history with realistic constraints:
- No negative cash (no margin/leverage)
- Whole shares only
- Mark-to-market at each bar's close
- All costs deducted from cash
"""

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Position:
    ticker: str
    shares: int
    avg_cost: float
    entry_date: date
    current_price: float = 0.0

    @property
    def market_value(self) -> float:
        return self.shares * self.current_price

    @property
    def unrealized_pnl(self) -> float:
        return (self.current_price - self.avg_cost) * self.shares

    @property
    def unrealized_pnl_pct(self) -> float:
        if self.avg_cost == 0:
            return 0.0
        return (self.current_price / self.avg_cost - 1) * 100


@dataclass
class TradeEntry:
    ticker: str
    side: str
    entry_date: date
    entry_price: float
    exit_date: date | None = None
    exit_price: float | None = None
    shares: int = 0
    pnl: float | None = None
    pnl_pct: float | None = None
    commission: float = 0.0
    slippage: float = 0.0


@dataclass
class Portfolio:
    initial_capital: float
    cash: float = 0.0
    positions: dict[str, Position] = field(default_factory=dict)
    equity_history: list[dict] = field(default_factory=list)
    trade_log: list[TradeEntry] = field(default_factory=list)

    def __post_init__(self):
        if self.cash == 0.0:
            self.cash = self.initial_capital

    @property
    def market_value(self) -> float:
        return sum(p.market_value for p in self.positions.values())

    @property
    def total_equity(self) -> float:
        return self.cash + self.market_value

    @property
    def exposure_pct(self) -> float:
        equity = self.total_equity
        if equity == 0:
            return 0.0
        return (self.market_value / equity) * 100

    def update_prices(self, prices: dict[str, float], current_date: date):
        """Mark all positions to market with current prices."""
        for ticker, price in prices.items():
            if ticker in self.positions:
                self.positions[ticker].current_price = price

        self.equity_history.append(
            {
                "date": current_date.isoformat(),
                "equity": self.total_equity,
                "cash": self.cash,
                "market_value": self.market_value,
                "exposure_pct": self.exposure_pct,
            }
        )

    def execute_buy(
        self,
        ticker: str,
        shares: int,
        fill_price: float,
        commission: float,
        slippage_cost: float,
        trade_date: date,
    ):
        """Execute a buy order. Deducts cost from cash, updates/creates position."""
        total_cost = (fill_price * shares) + commission + slippage_cost
        if total_cost > self.cash:
            affordable = int(
                (self.cash - commission)
                / (fill_price + slippage_cost / max(shares, 1))
            )
            if affordable <= 0:
                return
            shares = affordable
            total_cost = (fill_price * shares) + commission + slippage_cost

        self.cash -= total_cost

        if ticker in self.positions:
            pos = self.positions[ticker]
            total_shares = pos.shares + shares
            pos.avg_cost = (
                (pos.avg_cost * pos.shares) + (fill_price * shares)
            ) / total_shares
            pos.shares = total_shares
        else:
            self.positions[ticker] = Position(
                ticker=ticker,
                shares=shares,
                avg_cost=fill_price,
                entry_date=trade_date,
                current_price=fill_price,
            )

        self.trade_log.append(
            TradeEntry(
                ticker=ticker,
                side="BUY",
                entry_date=trade_date,
                entry_price=fill_price,
                shares=shares,
                commission=commission,
                slippage=slippage_cost,
            )
        )

    def execute_sell(
        self,
        ticker: str,
        shares: int,
        fill_price: float,
        commission: float,
        slippage_cost: float,
        trade_date: date,
    ):
        """Execute a sell order. Adds proceeds to cash, reduces/removes position."""
        if ticker not in self.positions:
            return
        pos = self.positions[ticker]
        shares = min(shares, pos.shares)
        if shares <= 0:
            return

        proceeds = (fill_price * shares) - commission - slippage_cost
        self.cash += proceeds

        pnl = (fill_price - pos.avg_cost) * shares - commission - slippage_cost
        pnl_pct = (
            ((fill_price / pos.avg_cost) - 1) * 100 if pos.avg_cost > 0 else 0.0
        )

        self.trade_log.append(
            TradeEntry(
                ticker=ticker,
                side="SELL",
                entry_date=pos.entry_date,
                entry_price=pos.avg_cost,
                exit_date=trade_date,
                exit_price=fill_price,
                shares=shares,
                pnl=pnl,
                pnl_pct=pnl_pct,
                commission=commission,
                slippage=slippage_cost,
            )
        )

        pos.shares -= shares
        if pos.shares <= 0:
            del self.positions[ticker]
