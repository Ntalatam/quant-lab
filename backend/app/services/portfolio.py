"""
Portfolio state manager.

Tracks cash, positions, equity, and trade history with support for both
long-only and long/short books. Long positions use positive shares and short
positions use negative shares.
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
    accrued_borrow_cost: float = 0.0
    accrued_locate_fee: float = 0.0

    @property
    def is_short(self) -> bool:
        return self.shares < 0

    @property
    def direction(self) -> str:
        return "SHORT" if self.is_short else "LONG"

    @property
    def market_value(self) -> float:
        return self.shares * self.current_price

    @property
    def gross_market_value(self) -> float:
        return abs(self.market_value)

    @property
    def unrealized_pnl(self) -> float:
        if self.is_short:
            return (self.avg_cost - self.current_price) * abs(self.shares)
        return (self.current_price - self.avg_cost) * self.shares

    @property
    def unrealized_pnl_pct(self) -> float:
        if self.avg_cost == 0:
            return 0.0
        if self.is_short:
            return ((self.avg_cost - self.current_price) / self.avg_cost) * 100
        return ((self.current_price - self.avg_cost) / self.avg_cost) * 100


@dataclass
class TradeEntry:
    ticker: str
    side: str
    position_direction: str
    entry_date: date
    entry_price: float
    exit_date: date | None = None
    exit_price: float | None = None
    shares: int = 0
    pnl: float | None = None
    pnl_pct: float | None = None
    commission: float = 0.0
    slippage: float = 0.0
    borrow_cost: float = 0.0
    locate_fee: float = 0.0
    requested_shares: int = 0
    unfilled_shares: int = 0
    spread_cost: float = 0.0
    market_impact_cost: float = 0.0
    timing_cost: float = 0.0
    opportunity_cost: float = 0.0
    participation_rate_pct: float = 0.0
    implementation_shortfall: float = 0.0
    risk_event: str | None = None


@dataclass
class PortfolioTransactionResult:
    executed_shares: int = 0
    requested_shares: int = 0
    unfilled_shares: int = 0
    commission: float = 0.0
    slippage: float = 0.0
    borrow_cost: float = 0.0
    locate_fee: float = 0.0
    spread_cost: float = 0.0
    market_impact_cost: float = 0.0
    timing_cost: float = 0.0
    opportunity_cost: float = 0.0
    participation_rate_pct: float = 0.0
    implementation_shortfall: float = 0.0

    def merge(self, other: "PortfolioTransactionResult"):
        self.executed_shares += other.executed_shares
        self.requested_shares += other.requested_shares
        self.unfilled_shares += other.unfilled_shares
        self.commission += other.commission
        self.slippage += other.slippage
        self.borrow_cost += other.borrow_cost
        self.locate_fee += other.locate_fee
        self.spread_cost += other.spread_cost
        self.market_impact_cost += other.market_impact_cost
        self.timing_cost += other.timing_cost
        self.opportunity_cost += other.opportunity_cost
        self.implementation_shortfall += other.implementation_shortfall
        if self.executed_shares > 0:
            self.participation_rate_pct = (
                (self.participation_rate_pct * max(self.executed_shares - other.executed_shares, 0))
                + (other.participation_rate_pct * other.executed_shares)
            ) / self.executed_shares


@dataclass
class Portfolio:
    initial_capital: float
    cash: float = 0.0
    positions: dict[str, Position] = field(default_factory=dict)
    equity_history: list[dict] = field(default_factory=list)
    trade_log: list[TradeEntry] = field(default_factory=list)
    total_borrow_cost_paid: float = 0.0
    total_locate_fees_paid: float = 0.0
    last_borrow_accrual_date: date | None = None

    def __post_init__(self):
        if self.cash == 0.0:
            self.cash = self.initial_capital

    @property
    def market_value(self) -> float:
        return sum(position.market_value for position in self.positions.values())

    @property
    def gross_market_value(self) -> float:
        return sum(position.gross_market_value for position in self.positions.values())

    @property
    def long_market_value(self) -> float:
        return sum(
            position.market_value for position in self.positions.values() if position.shares > 0
        )

    @property
    def short_market_value(self) -> float:
        return sum(
            -position.market_value for position in self.positions.values() if position.shares < 0
        )

    @property
    def total_equity(self) -> float:
        return self.cash + self.market_value

    @property
    def exposure_pct(self) -> float:
        return self.gross_exposure_pct

    @property
    def gross_exposure_pct(self) -> float:
        base = abs(self.total_equity)
        if base <= 1e-10:
            return 0.0
        return (self.gross_market_value / base) * 100

    @property
    def net_exposure_pct(self) -> float:
        base = abs(self.total_equity)
        if base <= 1e-10:
            return 0.0
        return (self.market_value / base) * 100

    def available_cash(self, short_margin_requirement_pct: float = 50.0) -> float:
        required_short_collateral = self.short_market_value * (
            1 + short_margin_requirement_pct / 100
        )
        return self.cash - required_short_collateral

    def get_short_squeeze_candidates(
        self, prices: dict[str, float], short_squeeze_threshold_pct: float
    ) -> list[str]:
        candidates: list[str] = []
        threshold = short_squeeze_threshold_pct / 100
        for ticker, position in self.positions.items():
            if position.shares >= 0 or position.current_price <= 0:
                continue
            next_price = prices.get(ticker)
            if next_price is None:
                continue
            adverse_move = (next_price / position.current_price) - 1
            if adverse_move >= threshold:
                candidates.append(ticker)
        return candidates

    def update_prices(
        self,
        prices: dict[str, float],
        current_date: date,
        short_borrow_rate_bps: float = 0.0,
    ):
        """Mark all positions to market and accrue short borrow where applicable."""
        self._accrue_short_borrow(current_date, short_borrow_rate_bps)

        for ticker, price in prices.items():
            if ticker in self.positions:
                self.positions[ticker].current_price = price

        self.equity_history.append(
            {
                "date": current_date.isoformat(),
                "equity": self.total_equity,
                "cash": self.cash,
                "market_value": self.market_value,
                "long_market_value": self.long_market_value,
                "short_market_value": self.short_market_value,
                "gross_market_value": self.gross_market_value,
                "exposure_pct": self.gross_exposure_pct,
                "gross_exposure_pct": self.gross_exposure_pct,
                "net_exposure_pct": self.net_exposure_pct,
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
    ) -> int:
        result = self.apply_transaction(
            ticker=ticker,
            side="BUY",
            shares=shares,
            fill_price=fill_price,
            commission=commission,
            slippage_cost=slippage_cost,
            trade_date=trade_date,
        )
        return result.executed_shares

    def execute_sell(
        self,
        ticker: str,
        shares: int,
        fill_price: float,
        commission: float,
        slippage_cost: float,
        trade_date: date,
    ) -> int:
        result = self.apply_transaction(
            ticker=ticker,
            side="SELL",
            shares=shares,
            fill_price=fill_price,
            commission=commission,
            slippage_cost=slippage_cost,
            trade_date=trade_date,
            allow_short_selling=False,
        )
        return result.executed_shares

    def apply_transaction(
        self,
        ticker: str,
        side: str,
        shares: int,
        fill_price: float,
        commission: float,
        slippage_cost: float,
        trade_date: date,
        requested_shares: int | None = None,
        spread_cost: float = 0.0,
        market_impact_cost: float = 0.0,
        timing_cost: float = 0.0,
        opportunity_cost: float = 0.0,
        participation_rate_pct: float = 0.0,
        allow_short_selling: bool = False,
        short_margin_requirement_pct: float = 50.0,
        short_locate_fee_bps: float = 0.0,
        risk_event: str | None = None,
    ) -> PortfolioTransactionResult:
        result = PortfolioTransactionResult()
        if shares <= 0:
            return result

        requested_shares = requested_shares or shares
        commission_per_share = commission / shares if shares else 0.0
        slippage_per_share = slippage_cost / shares if shares else 0.0
        spread_per_share = spread_cost / shares if shares else 0.0
        market_impact_per_share = market_impact_cost / shares if shares else 0.0
        timing_per_share = timing_cost / shares if shares else 0.0
        opportunity_per_share = opportunity_cost / max(requested_shares, 1)
        participation_per_share = participation_rate_pct / shares if shares else 0.0
        existing = self.positions.get(ticker)

        if side == "BUY":
            if existing and existing.shares < 0:
                cover_shares = min(shares, abs(existing.shares))
                result.merge(
                    self._cover_short(
                        ticker=ticker,
                        requested_shares=min(requested_shares, cover_shares),
                        shares=cover_shares,
                        fill_price=fill_price,
                        commission_per_share=commission_per_share,
                        slippage_per_share=slippage_per_share,
                        spread_per_share=spread_per_share,
                        market_impact_per_share=market_impact_per_share,
                        timing_per_share=timing_per_share,
                        opportunity_per_share=opportunity_per_share,
                        participation_per_share=participation_per_share,
                        trade_date=trade_date,
                        risk_event=risk_event,
                    )
                )
                shares -= cover_shares
                requested_shares = max(requested_shares - cover_shares, 0)

            if shares > 0:
                result.merge(
                    self._open_or_add_long(
                        ticker=ticker,
                        requested_shares=requested_shares,
                        shares=shares,
                        fill_price=fill_price,
                        commission_per_share=commission_per_share,
                        slippage_per_share=slippage_per_share,
                        spread_per_share=spread_per_share,
                        market_impact_per_share=market_impact_per_share,
                        timing_per_share=timing_per_share,
                        opportunity_per_share=opportunity_per_share,
                        participation_per_share=participation_per_share,
                        trade_date=trade_date,
                        short_margin_requirement_pct=short_margin_requirement_pct,
                    )
                )
            return result

        if existing and existing.shares > 0:
            long_shares = min(shares, existing.shares)
            result.merge(
                self._reduce_or_close_long(
                    ticker=ticker,
                    requested_shares=min(requested_shares, long_shares),
                    shares=long_shares,
                    fill_price=fill_price,
                    commission_per_share=commission_per_share,
                    slippage_per_share=slippage_per_share,
                    spread_per_share=spread_per_share,
                    market_impact_per_share=market_impact_per_share,
                    timing_per_share=timing_per_share,
                    opportunity_per_share=opportunity_per_share,
                    participation_per_share=participation_per_share,
                    trade_date=trade_date,
                    risk_event=risk_event,
                )
            )
            shares -= long_shares
            requested_shares = max(requested_shares - long_shares, 0)

        if shares > 0 and allow_short_selling:
            result.merge(
                self._open_or_add_short(
                    ticker=ticker,
                    requested_shares=requested_shares,
                    shares=shares,
                    fill_price=fill_price,
                    commission_per_share=commission_per_share,
                    slippage_per_share=slippage_per_share,
                    spread_per_share=spread_per_share,
                    market_impact_per_share=market_impact_per_share,
                    timing_per_share=timing_per_share,
                    opportunity_per_share=opportunity_per_share,
                    participation_per_share=participation_per_share,
                    trade_date=trade_date,
                    short_margin_requirement_pct=short_margin_requirement_pct,
                    short_locate_fee_bps=short_locate_fee_bps,
                )
            )

        return result

    def _accrue_short_borrow(self, current_date: date, short_borrow_rate_bps: float) -> None:
        if self.last_borrow_accrual_date is None:
            self.last_borrow_accrual_date = current_date
            return

        day_count = (current_date - self.last_borrow_accrual_date).days
        if day_count <= 0:
            return

        if short_borrow_rate_bps > 0:
            rate = (short_borrow_rate_bps / 10_000) * (day_count / 365)
            for position in self.positions.values():
                if position.shares >= 0 or position.current_price <= 0:
                    continue
                borrow_cost = abs(position.shares) * position.current_price * rate
                position.accrued_borrow_cost += borrow_cost
                self.total_borrow_cost_paid += borrow_cost
                self.cash -= borrow_cost

        self.last_borrow_accrual_date = current_date

    def _open_or_add_long(
        self,
        ticker: str,
        requested_shares: int,
        shares: int,
        fill_price: float,
        commission_per_share: float,
        slippage_per_share: float,
        spread_per_share: float,
        market_impact_per_share: float,
        timing_per_share: float,
        opportunity_per_share: float,
        participation_per_share: float,
        trade_date: date,
        short_margin_requirement_pct: float,
    ) -> PortfolioTransactionResult:
        result = PortfolioTransactionResult()
        cost_per_share = fill_price + commission_per_share + slippage_per_share
        if cost_per_share <= 0:
            return result

        affordable = min(
            shares,
            int(max(self.available_cash(short_margin_requirement_pct), 0) / cost_per_share),
        )
        if affordable <= 0:
            return result

        commission = commission_per_share * affordable
        slippage = slippage_per_share * affordable
        spread_cost = spread_per_share * affordable
        market_impact_cost = market_impact_per_share * affordable
        timing_cost = timing_per_share * affordable
        opportunity_cost = opportunity_per_share * max(requested_shares - affordable, 0)
        participation_rate_pct = participation_per_share * affordable
        total_cost = (fill_price * affordable) + commission + slippage
        self.cash -= total_cost

        if ticker in self.positions and self.positions[ticker].shares > 0:
            position = self.positions[ticker]
            total_shares = position.shares + affordable
            position.avg_cost = (
                (position.avg_cost * position.shares) + (fill_price * affordable)
            ) / total_shares
            position.shares = total_shares
            position.current_price = fill_price
        else:
            self.positions[ticker] = Position(
                ticker=ticker,
                shares=affordable,
                avg_cost=fill_price,
                entry_date=trade_date,
                current_price=fill_price,
            )

        self.trade_log.append(
            TradeEntry(
                ticker=ticker,
                side="BUY",
                position_direction="LONG",
                entry_date=trade_date,
                entry_price=fill_price,
                shares=affordable,
                commission=commission,
                slippage=slippage,
                requested_shares=requested_shares,
                unfilled_shares=max(requested_shares - affordable, 0),
                spread_cost=spread_cost,
                market_impact_cost=market_impact_cost,
                timing_cost=timing_cost,
                opportunity_cost=opportunity_cost,
                participation_rate_pct=participation_rate_pct,
                implementation_shortfall=(
                    commission + spread_cost + market_impact_cost + timing_cost + opportunity_cost
                ),
            )
        )
        result.executed_shares = affordable
        result.requested_shares = requested_shares
        result.unfilled_shares = max(requested_shares - affordable, 0)
        result.commission = commission
        result.slippage = slippage
        result.spread_cost = spread_cost
        result.market_impact_cost = market_impact_cost
        result.timing_cost = timing_cost
        result.opportunity_cost = opportunity_cost
        result.participation_rate_pct = participation_rate_pct
        result.implementation_shortfall = (
            commission + spread_cost + market_impact_cost + timing_cost + opportunity_cost
        )
        return result

    def _reduce_or_close_long(
        self,
        ticker: str,
        requested_shares: int,
        shares: int,
        fill_price: float,
        commission_per_share: float,
        slippage_per_share: float,
        spread_per_share: float,
        market_impact_per_share: float,
        timing_per_share: float,
        opportunity_per_share: float,
        participation_per_share: float,
        trade_date: date,
        risk_event: str | None,
    ) -> PortfolioTransactionResult:
        result = PortfolioTransactionResult()
        position = self.positions.get(ticker)
        if not position or position.shares <= 0:
            return result

        shares = min(shares, position.shares)
        if shares <= 0:
            return result

        commission = commission_per_share * shares
        slippage = slippage_per_share * shares
        spread_cost = spread_per_share * shares
        market_impact_cost = market_impact_per_share * shares
        timing_cost = timing_per_share * shares
        opportunity_cost = opportunity_per_share * max(requested_shares - shares, 0)
        participation_rate_pct = participation_per_share * shares
        proceeds = (fill_price * shares) - commission - slippage
        self.cash += proceeds

        pnl = (fill_price - position.avg_cost) * shares - commission - slippage
        pnl_pct = (
            ((fill_price - position.avg_cost) / position.avg_cost) * 100
            if position.avg_cost > 0
            else 0.0
        )
        self.trade_log.append(
            TradeEntry(
                ticker=ticker,
                side="SELL",
                position_direction="LONG",
                entry_date=position.entry_date,
                entry_price=position.avg_cost,
                exit_date=trade_date,
                exit_price=fill_price,
                shares=shares,
                pnl=pnl,
                pnl_pct=pnl_pct,
                commission=commission,
                slippage=slippage,
                requested_shares=requested_shares,
                unfilled_shares=max(requested_shares - shares, 0),
                spread_cost=spread_cost,
                market_impact_cost=market_impact_cost,
                timing_cost=timing_cost,
                opportunity_cost=opportunity_cost,
                participation_rate_pct=participation_rate_pct,
                implementation_shortfall=(
                    commission + spread_cost + market_impact_cost + timing_cost + opportunity_cost
                ),
                risk_event=risk_event,
            )
        )

        position.shares -= shares
        if position.shares <= 0:
            del self.positions[ticker]

        result.executed_shares = shares
        result.requested_shares = requested_shares
        result.unfilled_shares = max(requested_shares - shares, 0)
        result.commission = commission
        result.slippage = slippage
        result.spread_cost = spread_cost
        result.market_impact_cost = market_impact_cost
        result.timing_cost = timing_cost
        result.opportunity_cost = opportunity_cost
        result.participation_rate_pct = participation_rate_pct
        result.implementation_shortfall = (
            commission + spread_cost + market_impact_cost + timing_cost + opportunity_cost
        )
        return result

    def _open_or_add_short(
        self,
        ticker: str,
        requested_shares: int,
        shares: int,
        fill_price: float,
        commission_per_share: float,
        slippage_per_share: float,
        spread_per_share: float,
        market_impact_per_share: float,
        timing_per_share: float,
        opportunity_per_share: float,
        participation_per_share: float,
        trade_date: date,
        short_margin_requirement_pct: float,
        short_locate_fee_bps: float,
    ) -> PortfolioTransactionResult:
        result = PortfolioTransactionResult()
        margin_fraction = short_margin_requirement_pct / 100
        locate_fee_per_share = fill_price * short_locate_fee_bps / 10_000
        cost_per_share = (
            (fill_price * margin_fraction)
            + commission_per_share
            + slippage_per_share
            + locate_fee_per_share
        )
        if cost_per_share <= 0:
            return result

        affordable = min(
            shares,
            int(max(self.available_cash(short_margin_requirement_pct), 0) / cost_per_share),
        )
        if affordable <= 0:
            return result

        commission = commission_per_share * affordable
        slippage = slippage_per_share * affordable
        locate_fee = locate_fee_per_share * affordable
        spread_cost = spread_per_share * affordable
        market_impact_cost = market_impact_per_share * affordable
        timing_cost = timing_per_share * affordable
        opportunity_cost = opportunity_per_share * max(requested_shares - affordable, 0)
        participation_rate_pct = participation_per_share * affordable
        proceeds = (fill_price * affordable) - commission - slippage - locate_fee
        self.cash += proceeds
        self.total_locate_fees_paid += locate_fee

        if ticker in self.positions and self.positions[ticker].shares < 0:
            position = self.positions[ticker]
            existing_shares = abs(position.shares)
            total_shares = existing_shares + affordable
            position.avg_cost = (
                (position.avg_cost * existing_shares) + (fill_price * affordable)
            ) / total_shares
            position.shares = -total_shares
            position.current_price = fill_price
            position.accrued_locate_fee += locate_fee
        else:
            self.positions[ticker] = Position(
                ticker=ticker,
                shares=-affordable,
                avg_cost=fill_price,
                entry_date=trade_date,
                current_price=fill_price,
                accrued_locate_fee=locate_fee,
            )

        self.trade_log.append(
            TradeEntry(
                ticker=ticker,
                side="SELL",
                position_direction="SHORT",
                entry_date=trade_date,
                entry_price=fill_price,
                shares=affordable,
                commission=commission,
                slippage=slippage,
                locate_fee=locate_fee,
                requested_shares=requested_shares,
                unfilled_shares=max(requested_shares - affordable, 0),
                spread_cost=spread_cost,
                market_impact_cost=market_impact_cost,
                timing_cost=timing_cost,
                opportunity_cost=opportunity_cost,
                participation_rate_pct=participation_rate_pct,
                implementation_shortfall=(
                    commission + spread_cost + market_impact_cost + timing_cost + opportunity_cost
                ),
            )
        )
        result.executed_shares = affordable
        result.requested_shares = requested_shares
        result.unfilled_shares = max(requested_shares - affordable, 0)
        result.commission = commission
        result.slippage = slippage
        result.locate_fee = locate_fee
        result.spread_cost = spread_cost
        result.market_impact_cost = market_impact_cost
        result.timing_cost = timing_cost
        result.opportunity_cost = opportunity_cost
        result.participation_rate_pct = participation_rate_pct
        result.implementation_shortfall = (
            commission + spread_cost + market_impact_cost + timing_cost + opportunity_cost
        )
        return result

    def _cover_short(
        self,
        ticker: str,
        requested_shares: int,
        shares: int,
        fill_price: float,
        commission_per_share: float,
        slippage_per_share: float,
        spread_per_share: float,
        market_impact_per_share: float,
        timing_per_share: float,
        opportunity_per_share: float,
        participation_per_share: float,
        trade_date: date,
        risk_event: str | None,
    ) -> PortfolioTransactionResult:
        result = PortfolioTransactionResult()
        position = self.positions.get(ticker)
        if not position or position.shares >= 0:
            return result

        shares = min(shares, abs(position.shares))
        if shares <= 0:
            return result

        commission = commission_per_share * shares
        slippage = slippage_per_share * shares
        spread_cost = spread_per_share * shares
        market_impact_cost = market_impact_per_share * shares
        timing_cost = timing_per_share * shares
        opportunity_cost = opportunity_per_share * max(requested_shares - shares, 0)
        participation_rate_pct = participation_per_share * shares
        total_cost = (fill_price * shares) + commission + slippage
        self.cash -= total_cost

        total_short_shares = abs(position.shares)
        borrow_cost = (
            position.accrued_borrow_cost * shares / total_short_shares
            if total_short_shares > 0
            else 0.0
        )
        locate_fee = (
            position.accrued_locate_fee * shares / total_short_shares
            if total_short_shares > 0
            else 0.0
        )
        pnl = (
            (position.avg_cost - fill_price) * shares
            - commission
            - slippage
            - borrow_cost
            - locate_fee
        )
        pnl_pct = (
            ((position.avg_cost - fill_price) / position.avg_cost) * 100
            if position.avg_cost > 0
            else 0.0
        )
        self.trade_log.append(
            TradeEntry(
                ticker=ticker,
                side="BUY",
                position_direction="SHORT",
                entry_date=position.entry_date,
                entry_price=position.avg_cost,
                exit_date=trade_date,
                exit_price=fill_price,
                shares=shares,
                pnl=pnl,
                pnl_pct=pnl_pct,
                commission=commission,
                slippage=slippage,
                borrow_cost=borrow_cost,
                locate_fee=locate_fee,
                requested_shares=requested_shares,
                unfilled_shares=max(requested_shares - shares, 0),
                spread_cost=spread_cost,
                market_impact_cost=market_impact_cost,
                timing_cost=timing_cost,
                opportunity_cost=opportunity_cost,
                participation_rate_pct=participation_rate_pct,
                implementation_shortfall=(
                    commission + spread_cost + market_impact_cost + timing_cost + opportunity_cost
                ),
                risk_event=risk_event,
            )
        )

        position.shares += shares
        position.accrued_borrow_cost = max(position.accrued_borrow_cost - borrow_cost, 0.0)
        position.accrued_locate_fee = max(position.accrued_locate_fee - locate_fee, 0.0)
        if position.shares >= 0:
            del self.positions[ticker]

        result.executed_shares = shares
        result.requested_shares = requested_shares
        result.unfilled_shares = max(requested_shares - shares, 0)
        result.commission = commission
        result.slippage = slippage
        result.borrow_cost = borrow_cost
        result.locate_fee = locate_fee
        result.spread_cost = spread_cost
        result.market_impact_cost = market_impact_cost
        result.timing_cost = timing_cost
        result.opportunity_cost = opportunity_cost
        result.participation_rate_pct = participation_rate_pct
        result.implementation_shortfall = (
            commission + spread_cost + market_impact_cost + timing_cost + opportunity_cost
        )
        return result
