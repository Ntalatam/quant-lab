from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.analytics import RiskBudgetResponse
from app.services.analytics_backtests import load_backtest_run_or_404, load_backtest_trades
from app.services.risk_budget import build_risk_budget_report


async def build_risk_budget_response(
    db: AsyncSession,
    backtest_id: str,
    workspace_id: str,
    *,
    lookback_days: int,
) -> RiskBudgetResponse:
    run = await load_backtest_run_or_404(db, backtest_id, workspace_id)
    trades = await load_backtest_trades(
        db,
        backtest_id,
        workspace_id=workspace_id,
    )
    return RiskBudgetResponse.model_validate(
        await build_risk_budget_report(
            db=db,
            run=run,
            trades=trades,
            lookback_days=lookback_days,
        )
    )
