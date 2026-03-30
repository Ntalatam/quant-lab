from fastapi import APIRouter

from app.api.data import router as data_router
from app.api.backtest import router as backtest_router
from app.api.strategies import router as strategies_router
from app.api.analytics import router as analytics_router
from app.api.demo import router as demo_router

api_router = APIRouter()
api_router.include_router(data_router)
api_router.include_router(backtest_router)
api_router.include_router(strategies_router)
api_router.include_router(analytics_router)
api_router.include_router(demo_router)
