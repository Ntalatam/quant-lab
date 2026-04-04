"""
Data API endpoints.

GET  /api/data/tickers    — List all tickers with loaded data
POST /api/data/load       — Load data for a ticker + date range
GET  /api/data/ohlcv      — Get OHLCV data for charting
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.price_data import PriceData
from app.schemas.alternative_data import (
    EarningsOverviewResponse,
    EconomicIndicatorCatalogEntry,
    EconomicIndicatorsResponse,
    NewsSentimentResponse,
)
from app.schemas.common import ErrorResponse
from app.schemas.price_data import LoadDataRequest, LoadDataResponse, OHLCVResponse
from app.services.alternative_data import (
    get_earnings_overview,
    get_economic_indicators,
    get_news_sentiment,
    list_economic_indicator_catalog,
)
from app.services.data_ingestion import ensure_data_loaded, get_price_dataframe

router = APIRouter(prefix="/data", tags=["data"])


@router.get(
    "/tickers",
    response_model=list[str],
    summary="List cached tickers",
    description="Returns every ticker symbol currently cached in the local market-data store.",
)
async def list_tickers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(distinct(PriceData.ticker)).order_by(PriceData.ticker))
    return [row[0] for row in result.fetchall()]


@router.post(
    "/load",
    response_model=LoadDataResponse,
    summary="Load market data for a ticker",
    description=(
        "Fetches historical OHLCV data for the requested ticker and date range, "
        "then persists it in the local price-data table."
    ),
    responses={400: {"model": ErrorResponse, "description": "Data load failed."}},
)
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


@router.get(
    "/ohlcv",
    response_model=OHLCVResponse,
    summary="Read chart-ready OHLCV data",
    description=(
        "Returns cached OHLCV candles for the requested period. Results are "
        "uniformly downsampled when needed to keep chart payloads lightweight."
    ),
    responses={404: {"model": ErrorResponse, "description": "No cached data found."}},
)
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


@router.get(
    "/economic-indicators/catalog",
    response_model=list[EconomicIndicatorCatalogEntry],
    summary="List supported macro indicators",
    description=(
        "Returns the curated catalog of FRED series that QuantLab exposes in the "
        "alternative-data workspace."
    ),
)
async def get_indicator_catalog():
    return list_economic_indicator_catalog()


@router.get(
    "/economic-indicators",
    response_model=EconomicIndicatorsResponse,
    summary="Read macro indicators from FRED",
    description=(
        "Loads chart-ready macro time series from FRED, with latest-value "
        "summaries and recent directional changes."
    ),
)
async def read_economic_indicators(
    series_ids: list[str] | None = Query(default=None),
    start_date: str = Query(...),
    end_date: str = Query(...),
):
    series = await get_economic_indicators(
        series_ids=series_ids,
        start_date=date.fromisoformat(start_date),
        end_date=date.fromisoformat(end_date),
    )
    return {"series": series}


@router.get(
    "/earnings",
    response_model=EarningsOverviewResponse,
    summary="Read earnings events for a ticker",
    description=(
        "Returns recent reported earnings plus the next scheduled earnings date "
        "for the requested ticker."
    ),
)
async def read_earnings_overview(ticker: str = Query(...)):
    return await get_earnings_overview(ticker.upper())


@router.get(
    "/news-sentiment",
    response_model=NewsSentimentResponse,
    summary="Read news sentiment for a ticker",
    description=(
        "Scores recent ticker-linked news with a finance-aware lexical model, "
        "then aggregates the articles into a rolling sentiment signal."
    ),
)
async def read_news_sentiment(
    ticker: str = Query(...),
    lookback_days: int = Query(default=30, ge=3, le=180),
    limit: int = Query(default=10, ge=3, le=25),
):
    return await get_news_sentiment(
        ticker.upper(),
        lookback_days=lookback_days,
        limit=limit,
    )
