from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, cast

import pandas as pd
import yfinance as yf
from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.paper import (
    PaperTradingEquityPoint,
    PaperTradingEvent,
    PaperTradingExecution,
    PaperTradingOrder,
    PaperTradingPosition,
    PaperTradingSession,
)
from app.observability import elapsed_ms, get_logger
from app.schemas.paper import (
    BarInterval,
    PaperSessionStatus,
    PaperTradingEquityPointView,
    PaperTradingEventView,
    PaperTradingExecutionView,
    PaperTradingOrderView,
    PaperTradingPositionView,
    PaperTradingSessionCreate,
    PaperTradingSessionDetail,
    PaperTradingSessionSummary,
)
from app.services.brokers.factory import build_broker_adapter, build_broker_adapter_for_session
from app.services.brokers.types import BrokerExecutionRecord, BrokerOrderRecord, BrokerSyncResult
from app.services.portfolio import Portfolio
from app.services.portfolio_optimizer import (
    PortfolioConstructionRequest,
    construct_target_weights,
)
from app.services.strategy_registry import build_strategy_instance
from app.strategies.base import BaseStrategy
from app.utils.datetime import utc_now_naive

NO_MARKET_DATA_ERROR = "No live market data was returned."
logger = get_logger(__name__)


@dataclass
class PaperSessionRuntime:
    session_id: str
    strategy: BaseStrategy | None = None
    portfolio: Portfolio | None = None
    adapter: Any | None = None
    task: asyncio.Task | None = None
    latest_frames: dict[str, pd.DataFrame] = field(default_factory=dict)
    last_processed_bar: pd.Timestamp | None = None


def _history_period_for_interval(interval: str) -> str:
    if interval == "1m":
        return "7d"
    if interval in {"5m", "15m"}:
        return "60d"
    if interval == "1h":
        return "730d"
    return "10y"


def _normalize_history(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    rename_map = {
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Adj Close": "adj_close",
        "Volume": "volume",
    }
    df = df.rename(columns=rename_map)
    if "adj_close" not in df.columns:
        df["adj_close"] = df["close"]

    df = df[["open", "high", "low", "close", "adj_close", "volume"]].dropna(subset=["close"])
    df.index = pd.to_datetime(df.index)
    if getattr(df.index, "tz", None) is not None:
        df.index = df.index.tz_convert(None)
    return df.sort_index()


def _latest_common_timestamp(
    price_frames: dict[str, pd.DataFrame],
) -> pd.Timestamp | None:
    candidates = [df.index[-1] for df in price_frames.values() if not df.empty]
    if not candidates:
        return None
    return min(candidates)


class PaperTradingManager:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory
        self._runtimes: dict[str, PaperSessionRuntime] = {}
        self._subscribers: dict[str, set[WebSocket]] = {}

    async def resume_active_sessions(self):
        logger.info("paper_trading.resume_active_sessions.started")
        async with self._session_factory() as db:
            result = await db.execute(
                select(PaperTradingSession).where(PaperTradingSession.status == "active")
            )
            sessions = result.scalars().all()

        for session in sessions:
            try:
                await self.start_session(session.id, emit_status=False)
            except Exception as exc:
                logger.exception(
                    "paper_trading.resume_active_sessions.failed",
                    session_id=session.id,
                    error=str(exc),
                )
        logger.info(
            "paper_trading.resume_active_sessions.completed",
            resumed_sessions=len(sessions),
        )

    async def shutdown(self):
        logger.info(
            "paper_trading.shutdown.started",
            active_runtimes=len(self._runtimes),
        )
        for session_id in list(self._runtimes.keys()):
            await self._cancel_task(session_id)
        logger.info("paper_trading.shutdown.completed")

    async def create_session(
        self,
        payload: PaperTradingSessionCreate,
        *,
        workspace_id: str,
        created_by_user_id: str,
    ) -> PaperTradingSessionDetail:
        log = logger.bind(
            session_name=payload.name,
            strategy_id=payload.strategy_id,
            tickers=payload.tickers,
        )
        log.info("paper_trading.session_create.started")
        session_id = str(uuid.uuid4())
        created_at = utc_now_naive()

        async with self._session_factory() as db:
            strategy = await build_strategy_instance(
                db,
                payload.strategy_id,
                payload.params,
                workspace_id=workspace_id,
            )
            adapter = build_broker_adapter(
                execution_mode=payload.execution_mode,
                broker_adapter=payload.broker_adapter,
            )
            if strategy.requires_short_selling and not payload.allow_short_selling:
                raise ValueError(f"{strategy.name} requires short selling to be enabled.")
            session = PaperTradingSession(
                id=session_id,
                workspace_id=workspace_id,
                created_by_user_id=created_by_user_id,
                name=payload.name,
                status="draft",
                execution_mode=payload.execution_mode,
                broker_adapter=payload.broker_adapter,
                broker_account_label=adapter.default_account_label(),
                open_order_count=0,
                strategy_id=payload.strategy_id,
                strategy_params=payload.params,
                tickers=payload.tickers,
                benchmark=payload.benchmark,
                bar_interval=payload.bar_interval,
                polling_interval_seconds=payload.polling_interval_seconds,
                initial_capital=payload.initial_capital,
                slippage_bps=payload.slippage_bps,
                commission_per_share=payload.commission_per_share,
                market_impact_model=payload.market_impact_model,
                max_volume_participation_pct=payload.max_volume_participation_pct,
                portfolio_construction_model=payload.portfolio_construction_model,
                portfolio_lookback_days=payload.portfolio_lookback_days,
                max_position_pct=payload.max_position_pct,
                max_gross_exposure_pct=payload.max_gross_exposure_pct,
                turnover_limit_pct=payload.turnover_limit_pct,
                max_sector_exposure_pct=payload.max_sector_exposure_pct,
                allow_short_selling=payload.allow_short_selling,
                max_short_position_pct=payload.max_short_position_pct,
                short_margin_requirement_pct=payload.short_margin_requirement_pct,
                short_borrow_rate_bps=payload.short_borrow_rate_bps,
                short_locate_fee_bps=payload.short_locate_fee_bps,
                short_squeeze_threshold_pct=payload.short_squeeze_threshold_pct,
                cash=payload.initial_capital,
                market_value=0.0,
                total_equity=payload.initial_capital,
                total_return_pct=0.0,
                created_at=created_at,
            )
            db.add(session)
            db.add(
                PaperTradingEquityPoint(
                    session_id=session_id,
                    timestamp=created_at,
                    equity=payload.initial_capital,
                    cash=payload.initial_capital,
                    market_value=0.0,
                )
            )
            db.add(
                PaperTradingEvent(
                    id=str(uuid.uuid4()),
                    session_id=session_id,
                    timestamp=created_at,
                    event_type="status",
                    action="created",
                    status="info",
                    message="Paper trading session created.",
                )
            )
            await db.commit()

        if payload.start_immediately:
            await self.start_session(session_id, workspace_id=workspace_id)

        log.info("paper_trading.session_create.completed", session_id=session_id)
        return await self.get_session_detail(session_id, workspace_id=workspace_id)

    async def list_sessions(self, *, workspace_id: str) -> list[PaperTradingSessionSummary]:
        async with self._session_factory() as db:
            result = await db.execute(
                select(PaperTradingSession)
                .where(PaperTradingSession.workspace_id == workspace_id)
                .order_by(PaperTradingSession.created_at.desc())
            )
            sessions = result.scalars().all()
            return [self._session_to_summary(session) for session in sessions]

    async def get_session_detail(
        self,
        session_id: str,
        *,
        workspace_id: str | None = None,
    ) -> PaperTradingSessionDetail:
        async with self._session_factory() as db:
            return await self._load_detail(db, session_id, workspace_id=workspace_id)

    async def start_session(
        self,
        session_id: str,
        *,
        emit_status: bool = True,
        workspace_id: str | None = None,
    ):
        logger.info("paper_trading.session_start.started", session_id=session_id)
        async with self._session_factory() as db:
            session = await self._get_session(db, session_id, workspace_id=workspace_id)
            if not session:
                raise ValueError("Paper trading session not found")
            build_broker_adapter_for_session(session)
            strategy = await build_strategy_instance(
                db,
                session.strategy_id,
                session.strategy_params,
                workspace_id=session.workspace_id,
            )
            if strategy.requires_short_selling and not session.allow_short_selling:
                raise ValueError(f"{strategy.name} requires short selling to be enabled.")

            status_changed = session.status != "active"
            session.status = "active"
            session.last_error = None
            session.stopped_at = None
            if session.started_at is None:
                session.started_at = utc_now_naive()

            if emit_status and status_changed:
                db.add(
                    PaperTradingEvent(
                        id=str(uuid.uuid4()),
                        session_id=session_id,
                        timestamp=utc_now_naive(),
                        event_type="status",
                        action="started",
                        status="info",
                        message="Live paper trading started.",
                    )
                )
            await db.commit()

        await self._ensure_runtime_task(session_id)
        await self.broadcast_snapshot(session_id)
        logger.info("paper_trading.session_start.completed", session_id=session_id)

    async def pause_session(self, session_id: str, *, workspace_id: str | None = None):
        logger.info("paper_trading.session_pause.started", session_id=session_id)
        async with self._session_factory() as db:
            session = await self._get_session(db, session_id, workspace_id=workspace_id)
            if not session:
                raise ValueError("Paper trading session not found")
            runtime = await self._load_runtime(session_id)
            if runtime.adapter is not None:
                cancelled_orders = await runtime.adapter.cancel_open_orders(
                    session,
                    runtime,
                    reason="Session paused; open broker orders were cancelled.",
                    db=db,
                )
                if cancelled_orders:
                    await self._persist_broker_activity(
                        db,
                        session_id,
                        BrokerSyncResult(
                            orders=cancelled_orders,
                            account_label=session.broker_account_label,
                            open_order_count=0,
                        ),
                        snapshot_time=utc_now_naive(),
                    )
            status_changed = session.status != "paused"
            session.status = "paused"
            session.open_order_count = 0
            if status_changed:
                db.add(
                    PaperTradingEvent(
                        id=str(uuid.uuid4()),
                        session_id=session_id,
                        timestamp=utc_now_naive(),
                        event_type="status",
                        action="paused",
                        status="info",
                        message="Paper trading paused.",
                    )
                )
            await db.commit()

        await self._cancel_task(session_id)
        await self.broadcast_snapshot(session_id)
        logger.info("paper_trading.session_pause.completed", session_id=session_id)

    async def stop_session(self, session_id: str, *, workspace_id: str | None = None):
        logger.info("paper_trading.session_stop.started", session_id=session_id)
        async with self._session_factory() as db:
            session = await self._get_session(db, session_id, workspace_id=workspace_id)
            if not session:
                raise ValueError("Paper trading session not found")
            runtime = await self._load_runtime(session_id)
            if runtime.adapter is not None:
                cancelled_orders = await runtime.adapter.cancel_open_orders(
                    session,
                    runtime,
                    reason="Session stopped; open broker orders were cancelled.",
                    db=db,
                )
                if cancelled_orders:
                    await self._persist_broker_activity(
                        db,
                        session_id,
                        BrokerSyncResult(
                            orders=cancelled_orders,
                            account_label=session.broker_account_label,
                            open_order_count=0,
                        ),
                        snapshot_time=utc_now_naive(),
                    )
            status_changed = session.status != "stopped"
            session.status = "stopped"
            session.open_order_count = 0
            if status_changed:
                session.stopped_at = utc_now_naive()
                db.add(
                    PaperTradingEvent(
                        id=str(uuid.uuid4()),
                        session_id=session_id,
                        timestamp=utc_now_naive(),
                        event_type="status",
                        action="stopped",
                        status="info",
                        message="Paper trading stopped.",
                    )
                )
            await db.commit()

        await self._cancel_task(session_id)
        await self.broadcast_snapshot(session_id)
        logger.info("paper_trading.session_stop.completed", session_id=session_id)

    async def subscribe(self, session_id: str, websocket: WebSocket):
        self._subscribers.setdefault(session_id, set()).add(websocket)

    async def unsubscribe(self, session_id: str, websocket: WebSocket):
        if session_id in self._subscribers:
            self._subscribers[session_id].discard(websocket)
            if not self._subscribers[session_id]:
                del self._subscribers[session_id]

    async def broadcast_snapshot(self, session_id: str):
        subscribers = self._subscribers.get(session_id, set())
        if not subscribers:
            return

        try:
            detail = await self.get_session_detail(session_id)
        except Exception:
            return

        payload = {"type": "snapshot", "session": jsonable_encoder(detail)}
        stale: list[WebSocket] = []
        for websocket in subscribers:
            try:
                await websocket.send_json(payload)
            except Exception:
                stale.append(websocket)
        for websocket in stale:
            await self.unsubscribe(session_id, websocket)

    async def _ensure_runtime_task(self, session_id: str):
        runtime = await self._load_runtime(session_id)
        if runtime.task and not runtime.task.done():
            return
        runtime.task = asyncio.create_task(self._run_session(session_id))

    async def _cancel_task(self, session_id: str):
        runtime = self._runtimes.get(session_id)
        if not runtime or not runtime.task:
            return
        runtime.task.cancel()
        try:
            await runtime.task
        except asyncio.CancelledError:
            pass
        runtime.task = None

    async def _load_runtime(self, session_id: str) -> PaperSessionRuntime:
        runtime = self._runtimes.get(session_id)
        if runtime is None:
            runtime = PaperSessionRuntime(session_id=session_id)
            self._runtimes[session_id] = runtime

        if (
            runtime.strategy is not None
            and runtime.portfolio is not None
            and runtime.adapter is not None
        ):
            return runtime

        async with self._session_factory() as db:
            session = await db.get(PaperTradingSession, session_id)
            if not session:
                raise ValueError("Paper trading session not found")

            runtime.strategy = await build_strategy_instance(
                db,
                session.strategy_id,
                session.strategy_params,
                workspace_id=session.workspace_id,
            )
            runtime.adapter = build_broker_adapter_for_session(session)
            await runtime.adapter.load_portfolio(session, runtime, db)
            if session.last_price_at is not None:
                runtime.last_processed_bar = pd.Timestamp(session.last_price_at)

        return runtime

    async def _run_session(self, session_id: str):
        runtime = await self._load_runtime(session_id)
        log = logger.bind(session_id=session_id)

        while True:
            try:
                async with self._session_factory() as db:
                    poll_start = time.perf_counter()
                    session = await db.get(PaperTradingSession, session_id)
                    if not session or session.status != "active":
                        return

                    price_frames = await self._fetch_price_frames(
                        session.tickers, session.bar_interval
                    )
                    runtime.latest_frames = price_frames
                    current_ts = _latest_common_timestamp(price_frames)

                    if current_ts is None:
                        session.last_heartbeat_at = utc_now_naive()
                        if session.last_error != NO_MARKET_DATA_ERROR:
                            session.last_error = NO_MARKET_DATA_ERROR
                            db.add(
                                PaperTradingEvent(
                                    id=str(uuid.uuid4()),
                                    session_id=session_id,
                                    timestamp=utc_now_naive(),
                                    event_type="error",
                                    action="market_data",
                                    status="warning",
                                    message="No live market data was returned for the active symbols.",
                                )
                            )
                        await db.commit()
                        await self.broadcast_snapshot(session_id)
                        log.warning(
                            "paper_trading.poll.no_market_data",
                            duration_ms=elapsed_ms(poll_start),
                            tickers=session.tickers,
                            interval=session.bar_interval,
                        )
                        await asyncio.sleep(session.polling_interval_seconds)
                        continue

                    current_dt = current_ts.to_pydatetime()
                    current_prices: dict[str, float] = {}
                    signal_windows: dict[str, pd.DataFrame] = {}
                    execution_bars: dict[str, pd.Series] = {}

                    for ticker, df in price_frames.items():
                        window = df[df.index <= current_ts]
                        if window.empty:
                            continue
                        latest_bar = window.iloc[-1]
                        latest_price = float(latest_bar["adj_close"])
                        current_prices[ticker] = latest_price
                        signal_windows[ticker] = window
                        execution_bars[ticker] = pd.Series(
                            {
                                "open": latest_price,
                                "high": latest_price,
                                "low": latest_price,
                                "close": latest_price,
                                "volume": max(int(latest_bar["volume"]), 1),
                            }
                        )

                    if runtime.portfolio is None or runtime.strategy is None:
                        raise RuntimeError("Paper trading runtime was not initialized.")
                    if runtime.adapter is None:
                        raise RuntimeError("Paper trading broker adapter was not initialized.")

                    latest_sync = await runtime.adapter.sync_account_state(
                        session,
                        runtime,
                        current_prices=current_prices,
                        snapshot_time=current_dt,
                        db=db,
                    )
                    await self._persist_broker_activity(
                        db,
                        session_id,
                        latest_sync,
                        snapshot_time=current_dt,
                    )
                    if session.last_error == NO_MARKET_DATA_ERROR:
                        session.last_error = None
                        db.add(
                            PaperTradingEvent(
                                id=str(uuid.uuid4()),
                                session_id=session_id,
                                timestamp=utc_now_naive(),
                                event_type="status",
                                action="market_data_recovered",
                                status="info",
                                message="Live market data recovered.",
                            )
                        )

                    market_open = await runtime.adapter.is_market_open(
                        session,
                        snapshot_time=current_dt,
                    )
                    forced_cover_tickers = (
                        runtime.portfolio.get_short_squeeze_candidates(
                            current_prices, session.short_squeeze_threshold_pct
                        )
                        if session.allow_short_selling
                        else []
                    )

                    if market_open and forced_cover_tickers:
                        latest_sync = await runtime.adapter.force_cover_positions(
                            session,
                            runtime,
                            tickers=forced_cover_tickers,
                            current_bars=execution_bars,
                            current_prices=current_prices,
                            snapshot_time=current_dt,
                            db=db,
                            reason="Forced buy-to-cover after the short squeeze threshold was breached.",
                        )
                        await self._persist_broker_activity(
                            db,
                            session_id,
                            latest_sync,
                            snapshot_time=current_dt,
                        )

                    if market_open and (
                        runtime.last_processed_bar is None
                        or current_ts > runtime.last_processed_bar
                    ):
                        try:
                            signals = runtime.strategy.generate_signals(signal_windows, current_ts)
                        except Exception:
                            log.exception(
                                "paper_trading.strategy_error",
                                timestamp=current_ts.isoformat(),
                            )
                            raise
                        for ticker in forced_cover_tickers:
                            if ticker in signals:
                                signals[ticker] = 0.0
                        construction = await construct_target_weights(
                            PortfolioConstructionRequest(
                                raw_signals=signals,
                                data_window=signal_windows,
                                current_prices=current_prices,
                                portfolio=runtime.portfolio,
                                signal_mode=runtime.strategy.signal_mode,
                                construction_model=session.portfolio_construction_model,
                                lookback_days=session.portfolio_lookback_days,
                                max_position_pct=session.max_position_pct,
                                max_short_position_pct=session.max_short_position_pct,
                                max_gross_exposure_pct=session.max_gross_exposure_pct,
                                turnover_limit_pct=session.turnover_limit_pct,
                                max_sector_exposure_pct=session.max_sector_exposure_pct,
                                allow_short_selling=session.allow_short_selling,
                            )
                        )
                        latest_sync = await runtime.adapter.execute_target_weights(
                            session,
                            runtime,
                            target_weights=construction.target_weights,
                            current_bars=execution_bars,
                            current_prices=current_prices,
                            snapshot_time=current_dt,
                            db=db,
                        )
                        await self._persist_broker_activity(
                            db,
                            session_id,
                            latest_sync,
                            snapshot_time=current_dt,
                        )
                        runtime.last_processed_bar = current_ts
                        session.last_signal_at = utc_now_naive()

                    await self._sync_session_state(
                        db,
                        session=session,
                        portfolio=runtime.portfolio,
                        snapshot_time=current_dt,
                        latest_bar_ts=current_dt,
                        account_label=latest_sync.account_label,
                        open_order_count=latest_sync.open_order_count,
                    )
                    await db.commit()

                    log.info(
                        "paper_trading.poll.completed",
                        duration_ms=elapsed_ms(poll_start),
                        tickers=len(session.tickers),
                        positions=len(runtime.portfolio.positions),
                        total_equity=round(runtime.portfolio.total_equity, 2),
                    )
                    await self.broadcast_snapshot(session_id)
                    await asyncio.sleep(session.polling_interval_seconds)

            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log.exception("paper_trading.runtime_failed", error=str(exc))
                async with self._session_factory() as db:
                    session = await db.get(PaperTradingSession, session_id)
                    if session:
                        session.status = "error"
                        session.last_error = str(exc)
                        session.last_heartbeat_at = utc_now_naive()
                        db.add(
                            PaperTradingEvent(
                                id=str(uuid.uuid4()),
                                session_id=session_id,
                                timestamp=utc_now_naive(),
                                event_type="error",
                                action="runtime",
                                status="error",
                                message=f"Paper trading session crashed: {exc}",
                            )
                        )
                        await db.commit()
                await self.broadcast_snapshot(session_id)
                return

    async def _fetch_price_frames(
        self, tickers: list[str], interval: str
    ) -> dict[str, pd.DataFrame]:
        start_time = time.perf_counter()
        results = await asyncio.gather(
            *[
                asyncio.to_thread(self._download_ticker_history, ticker, interval)
                for ticker in tickers
            ]
        )
        logger.debug(
            "paper_trading.market_data_loaded",
            tickers=tickers,
            interval=interval,
            duration_ms=elapsed_ms(start_time),
        )
        return dict(zip(tickers, results, strict=True))

    def _download_ticker_history(self, ticker: str, interval: str) -> pd.DataFrame:
        df = yf.download(
            ticker,
            period=_history_period_for_interval(interval),
            interval=interval,
            auto_adjust=False,
            progress=False,
            prepost=False,
        )
        return _normalize_history(df)

    def health_summary(self) -> dict[str, int]:
        adapter_counts: dict[str, int] = {}
        for runtime in self._runtimes.values():
            adapter_key = getattr(runtime.adapter, "adapter_key", "paper")
            adapter_counts[f"{adapter_key}_sessions"] = (
                adapter_counts.get(f"{adapter_key}_sessions", 0) + 1
            )
        return {
            "runtime_sessions": len(self._runtimes),
            "subscriber_channels": len(self._subscribers),
            **adapter_counts,
        }

    async def _persist_broker_activity(
        self,
        db: AsyncSession,
        session_id: str,
        broker_result: BrokerSyncResult,
        *,
        snapshot_time: datetime,
    ):
        changed_orders: list[BrokerOrderRecord] = []
        inserted_executions: list[BrokerExecutionRecord] = []

        for order in broker_result.orders:
            order_row = await db.get(PaperTradingOrder, order.id)
            if order_row is None and order.broker_order_id:
                existing_result = await db.execute(
                    select(PaperTradingOrder).where(
                        PaperTradingOrder.session_id == session_id,
                        PaperTradingOrder.broker_order_id == order.broker_order_id,
                    )
                )
                order_row = existing_result.scalar_one_or_none()

            previous_status = order_row.status if order_row is not None else None
            previous_filled = order_row.filled_shares if order_row is not None else None

            if order_row is None:
                order_row = PaperTradingOrder(
                    id=order.id,
                    session_id=session_id,
                    broker_order_id=order.broker_order_id,
                    client_order_id=order.client_order_id,
                    ticker=order.ticker,
                    side=order.side,
                    order_type=order.order_type,
                    time_in_force=order.time_in_force,
                    requested_shares=order.requested_shares,
                    filled_shares=order.filled_shares,
                    status=order.status,
                    avg_fill_price=order.avg_fill_price,
                    submitted_at=order.submitted_at,
                    updated_at=order.updated_at,
                    message=order.message,
                    metadata_json=order.metadata,
                )
                db.add(order_row)
                changed_orders.append(order)
                continue

            order_row.client_order_id = order.client_order_id
            order_row.ticker = order.ticker
            order_row.side = order.side
            order_row.order_type = order.order_type
            order_row.time_in_force = order.time_in_force
            order_row.requested_shares = order.requested_shares
            order_row.filled_shares = order.filled_shares
            order_row.status = order.status
            order_row.avg_fill_price = order.avg_fill_price
            order_row.submitted_at = order.submitted_at
            order_row.updated_at = order.updated_at
            order_row.message = order.message
            order_row.metadata_json = order.metadata

            if previous_status != order.status or previous_filled != order.filled_shares:
                changed_orders.append(order)

        for execution in broker_result.executions:
            execution_row = await db.get(PaperTradingExecution, execution.id)
            if execution_row is None and execution.broker_execution_id:
                execution_result = await db.execute(
                    select(PaperTradingExecution).where(
                        PaperTradingExecution.session_id == session_id,
                        PaperTradingExecution.broker_execution_id == execution.broker_execution_id,
                    )
                )
                execution_row = execution_result.scalar_one_or_none()

            if execution_row is not None:
                continue

            db.add(
                PaperTradingExecution(
                    id=execution.id,
                    session_id=session_id,
                    order_id=execution.order_id,
                    broker_execution_id=execution.broker_execution_id,
                    ticker=execution.ticker,
                    side=execution.side,
                    shares=execution.shares,
                    fill_price=execution.fill_price,
                    commission=execution.commission,
                    slippage_cost=execution.slippage_cost,
                    borrow_cost=execution.borrow_cost,
                    locate_fee=execution.locate_fee,
                    spread_cost=execution.spread_cost,
                    market_impact_cost=execution.market_impact_cost,
                    timing_cost=execution.timing_cost,
                    opportunity_cost=execution.opportunity_cost,
                    participation_rate_pct=execution.participation_rate_pct,
                    status=execution.status,
                    risk_event=execution.risk_event,
                    executed_at=execution.executed_at,
                    message=execution.message,
                    metadata_json=execution.metadata,
                )
            )
            inserted_executions.append(execution)

        self._emit_broker_events(
            db,
            session_id=session_id,
            orders=changed_orders,
            executions=inserted_executions,
            snapshot_time=snapshot_time,
        )

    def _emit_broker_events(
        self,
        db: AsyncSession,
        *,
        session_id: str,
        orders: list[BrokerOrderRecord],
        executions: list[BrokerExecutionRecord],
        snapshot_time: datetime,
    ):
        execution_order_ids = {execution.order_id for execution in executions if execution.order_id}
        for order in orders:
            if order.order_type and order.id in execution_order_ids:
                continue
            event_type = "error" if order.status in {"rejected"} else "signal"
            event_status = "warning" if order.status in {"canceled", "cancelled"} else order.status
            db.add(
                PaperTradingEvent(
                    id=str(uuid.uuid4()),
                    session_id=session_id,
                    timestamp=snapshot_time,
                    event_type=event_type,
                    ticker=order.ticker,
                    action=order.side,
                    shares=order.filled_shares or order.requested_shares,
                    fill_price=order.avg_fill_price,
                    status=event_status,
                    message=order.message or f"{order.side.upper()} order {order.status}.",
                )
            )

        for execution in executions:
            db.add(
                PaperTradingEvent(
                    id=str(uuid.uuid4()),
                    session_id=session_id,
                    timestamp=execution.executed_at,
                    event_type="fill",
                    ticker=execution.ticker,
                    action=execution.side,
                    shares=execution.shares,
                    fill_price=execution.fill_price,
                    status=execution.status,
                    message=execution.message or "Execution recorded.",
                )
            )

    async def _sync_session_state(
        self,
        db: AsyncSession,
        session: PaperTradingSession,
        portfolio: Portfolio,
        snapshot_time: datetime,
        latest_bar_ts: datetime,
        account_label: str | None = None,
        open_order_count: int = 0,
    ):
        previous_price_at = session.last_price_at
        session.cash = round(portfolio.cash, 2)
        session.market_value = round(portfolio.market_value, 2)
        session.total_equity = round(portfolio.total_equity, 2)
        session.total_return_pct = round(
            ((portfolio.total_equity / session.initial_capital) - 1) * 100, 3
        )
        session.last_price_at = latest_bar_ts
        session.last_heartbeat_at = utc_now_naive()
        session.broker_account_label = account_label or session.broker_account_label
        session.open_order_count = open_order_count

        if previous_price_at is None or pd.Timestamp(latest_bar_ts) > pd.Timestamp(
            previous_price_at
        ):
            db.add(
                PaperTradingEquityPoint(
                    session_id=session.id,
                    timestamp=latest_bar_ts,
                    equity=round(portfolio.total_equity, 2),
                    cash=round(portfolio.cash, 2),
                    market_value=round(portfolio.market_value, 2),
                )
            )

        existing_positions_result = await db.execute(
            select(PaperTradingPosition).where(PaperTradingPosition.session_id == session.id)
        )
        existing_positions = {row.ticker: row for row in existing_positions_result.scalars().all()}

        live_tickers = set(portfolio.positions.keys())
        for ticker, row in list(existing_positions.items()):
            if ticker not in live_tickers:
                await db.delete(row)

        for ticker, position in portfolio.positions.items():
            position_row = existing_positions.get(ticker)
            if position_row is None:
                position_row = PaperTradingPosition(
                    id=str(uuid.uuid4()),
                    session_id=session.id,
                    ticker=ticker,
                    shares=position.shares,
                    avg_cost=position.avg_cost,
                    entry_date=datetime.combine(position.entry_date, datetime.min.time()),
                    current_price=position.current_price,
                    market_value=position.market_value,
                    unrealized_pnl=position.unrealized_pnl,
                    unrealized_pnl_pct=position.unrealized_pnl_pct,
                    accrued_borrow_cost=position.accrued_borrow_cost,
                    accrued_locate_fee=position.accrued_locate_fee,
                )
                db.add(position_row)
                continue

            position_row.shares = position.shares
            position_row.avg_cost = position.avg_cost
            position_row.current_price = position.current_price
            position_row.market_value = position.market_value
            position_row.unrealized_pnl = position.unrealized_pnl
            position_row.unrealized_pnl_pct = position.unrealized_pnl_pct
            position_row.accrued_borrow_cost = position.accrued_borrow_cost
            position_row.accrued_locate_fee = position.accrued_locate_fee
            position_row.updated_at = utc_now_naive()

    async def _load_detail(
        self,
        db: AsyncSession,
        session_id: str,
        *,
        workspace_id: str | None = None,
    ) -> PaperTradingSessionDetail:
        session = await self._get_session(db, session_id, workspace_id=workspace_id)
        if not session:
            raise ValueError("Paper trading session not found")

        positions_result = await db.execute(
            select(PaperTradingPosition)
            .where(PaperTradingPosition.session_id == session_id)
            .order_by(PaperTradingPosition.ticker)
        )
        events_result = await db.execute(
            select(PaperTradingEvent)
            .where(PaperTradingEvent.session_id == session_id)
            .order_by(PaperTradingEvent.timestamp.desc())
            .limit(100)
        )
        equity_result = await db.execute(
            select(PaperTradingEquityPoint)
            .where(PaperTradingEquityPoint.session_id == session_id)
            .order_by(PaperTradingEquityPoint.timestamp.asc())
        )
        order_result = await db.execute(
            select(PaperTradingOrder)
            .where(PaperTradingOrder.session_id == session_id)
            .order_by(PaperTradingOrder.submitted_at.desc())
            .limit(50)
        )
        execution_result = await db.execute(
            select(PaperTradingExecution)
            .where(PaperTradingExecution.session_id == session_id)
            .order_by(PaperTradingExecution.executed_at.desc())
            .limit(50)
        )

        positions = positions_result.scalars().all()
        events = list(reversed(events_result.scalars().all()))
        equity_points = equity_result.scalars().all()
        orders = list(reversed(order_result.scalars().all()))
        executions = list(reversed(execution_result.scalars().all()))

        return PaperTradingSessionDetail(
            **self._session_to_summary(session).model_dump(),
            benchmark=session.benchmark,
            strategy_params=session.strategy_params,
            slippage_bps=session.slippage_bps,
            commission_per_share=session.commission_per_share,
            market_impact_model=session.market_impact_model,
            max_volume_participation_pct=session.max_volume_participation_pct,
            portfolio_construction_model=session.portfolio_construction_model,
            portfolio_lookback_days=session.portfolio_lookback_days,
            max_position_pct=session.max_position_pct,
            max_gross_exposure_pct=session.max_gross_exposure_pct,
            turnover_limit_pct=session.turnover_limit_pct,
            max_sector_exposure_pct=session.max_sector_exposure_pct,
            allow_short_selling=session.allow_short_selling,
            max_short_position_pct=session.max_short_position_pct,
            short_margin_requirement_pct=session.short_margin_requirement_pct,
            short_borrow_rate_bps=session.short_borrow_rate_bps,
            short_locate_fee_bps=session.short_locate_fee_bps,
            short_squeeze_threshold_pct=session.short_squeeze_threshold_pct,
            positions=[
                PaperTradingPositionView(
                    ticker=row.ticker,
                    shares=row.shares,
                    avg_cost=row.avg_cost,
                    entry_date=row.entry_date,
                    current_price=row.current_price,
                    market_value=row.market_value,
                    unrealized_pnl=row.unrealized_pnl,
                    unrealized_pnl_pct=row.unrealized_pnl_pct,
                    accrued_borrow_cost=row.accrued_borrow_cost,
                    accrued_locate_fee=row.accrued_locate_fee,
                    updated_at=row.updated_at,
                )
                for row in positions
            ],
            recent_events=[
                PaperTradingEventView(
                    id=row.id,
                    timestamp=row.timestamp,
                    event_type=cast(Any, row.event_type),
                    ticker=row.ticker,
                    action=row.action,
                    signal=row.signal,
                    shares=row.shares,
                    fill_price=row.fill_price,
                    status=row.status,
                    message=row.message,
                )
                for row in events
            ],
            recent_orders=[
                PaperTradingOrderView(
                    id=row.id,
                    broker_order_id=row.broker_order_id,
                    client_order_id=row.client_order_id,
                    submitted_at=row.submitted_at,
                    updated_at=row.updated_at,
                    ticker=row.ticker,
                    side=row.side,
                    order_type=row.order_type,
                    time_in_force=row.time_in_force,
                    requested_shares=row.requested_shares,
                    filled_shares=row.filled_shares,
                    status=row.status,
                    avg_fill_price=row.avg_fill_price,
                    message=row.message,
                )
                for row in orders
            ],
            recent_executions=[
                PaperTradingExecutionView(
                    id=row.id,
                    order_id=row.order_id,
                    broker_execution_id=row.broker_execution_id,
                    executed_at=row.executed_at,
                    ticker=row.ticker,
                    side=row.side,
                    shares=row.shares,
                    fill_price=row.fill_price,
                    commission=row.commission,
                    slippage_cost=row.slippage_cost,
                    borrow_cost=row.borrow_cost,
                    locate_fee=row.locate_fee,
                    spread_cost=row.spread_cost,
                    market_impact_cost=row.market_impact_cost,
                    timing_cost=row.timing_cost,
                    opportunity_cost=row.opportunity_cost,
                    participation_rate_pct=row.participation_rate_pct,
                    status=row.status,
                    risk_event=row.risk_event,
                    message=row.message,
                )
                for row in executions
            ],
            equity_curve=[
                PaperTradingEquityPointView(
                    timestamp=row.timestamp,
                    equity=row.equity,
                    cash=row.cash,
                    market_value=row.market_value,
                )
                for row in equity_points
            ],
        )

    async def _get_session(
        self,
        db: AsyncSession,
        session_id: str,
        *,
        workspace_id: str | None = None,
    ) -> PaperTradingSession | None:
        if workspace_id is None:
            return await db.get(PaperTradingSession, session_id)
        result = await db.execute(
            select(PaperTradingSession).where(
                PaperTradingSession.id == session_id,
                PaperTradingSession.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    def _session_to_summary(self, session: PaperTradingSession) -> PaperTradingSessionSummary:
        return PaperTradingSessionSummary(
            id=session.id,
            name=session.name,
            status=cast(PaperSessionStatus, session.status),
            execution_mode=cast(Any, session.execution_mode),
            broker_adapter=cast(Any, session.broker_adapter),
            broker_account_label=session.broker_account_label,
            strategy_id=session.strategy_id,
            tickers=session.tickers,
            bar_interval=cast(BarInterval, session.bar_interval),
            polling_interval_seconds=session.polling_interval_seconds,
            initial_capital=session.initial_capital,
            cash=session.cash,
            market_value=session.market_value,
            total_equity=session.total_equity,
            total_return_pct=session.total_return_pct,
            created_at=session.created_at,
            started_at=session.started_at,
            stopped_at=session.stopped_at,
            last_price_at=session.last_price_at,
            last_heartbeat_at=session.last_heartbeat_at,
            last_error=session.last_error,
            open_order_count=session.open_order_count,
        )
