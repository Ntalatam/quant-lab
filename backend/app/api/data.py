"""
Data API endpoints.

GET  /api/data/tickers    — List all tickers with loaded data
POST /api/data/load       — Load data for a ticker + date range
GET  /api/data/ohlcv      — Get OHLCV data for charting
"""

from datetime import date

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.price_data import PriceData
from app.schemas.price_data import LoadDataRequest
from app.services.data_ingestion import ensure_data_loaded, get_price_dataframe

router = APIRouter(prefix="/data", tags=["data"])


@router.get("/tickers")
async def list_tickers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(distinct(PriceData.ticker)).order_by(PriceData.ticker)
    )
    return [row[0] for row in result.fetchall()]


@router.post("/load")
async def load_data(request: LoadDataRequest, db: AsyncSession = Depends(get_db)):
    success = await ensure_data_loaded(
        db,
        request.ticker.upper(),
        date.fromisoformat(request.start_date),
        date.fromisoformat(request.end_date),
    )
    if not success:
        raise HTTPException(400, f"Could not load data for {request.ticker}")
    return {"status": "ok", "ticker": request.ticker.upper()}


@router.get("/ohlcv")
async def get_ohlcv(
    ticker: str = Query(...),
    start_date: str = Query(...),
    end_date: str = Query(...),
    max_points: int = Query(default=500, ge=50, le=5000),
    db: AsyncSession = Depends(get_db),
):
    df = await get_price_dataframe(
        db,
        ticker.upper(),
        date.fromisoformat(start_date),
        date.fromisoformat(end_date),
    )
    if df.empty:
        raise HTTPException(404, f"No data for {ticker}")

    # Downsample to max_points using uniform sampling — preserves chart shape
    # while preventing Recharts from rendering thousands of DOM nodes
    original_rows = len(df)
    if len(df) > max_points:
        step = len(df) / max_points
        indices = [int(i * step) for i in range(max_points)]
        # Always include the last point so the chart ends at the right date
        if indices[-1] != len(df) - 1:
            indices[-1] = len(df) - 1
        df = df.iloc[indices]

    return {
        "ticker": ticker.upper(),
        "original_rows": original_rows,
        "returned_rows": len(df),
        "data": [
            {
                "date": idx.date().isoformat(),
                "open": round(row["open"], 2),
                "high": round(row["high"], 2),
                "low": round(row["low"], 2),
                "close": round(row["close"], 2),
                "volume": int(row["volume"]),
            }
            for idx, row in df.iterrows()
        ],
    }
