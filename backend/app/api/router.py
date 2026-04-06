from fastapi import APIRouter, Depends

from app.api.analytics import router as analytics_router
from app.api.auth import router as auth_router
from app.api.backtest import router as backtest_router
from app.api.data import router as data_router
from app.api.demo import router as demo_router
from app.api.dependencies import get_current_user
from app.api.jobs import router as jobs_router
from app.api.options import router as options_router
from app.api.paper import router as paper_router
from app.api.strategies import router as strategies_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(data_router, dependencies=[Depends(get_current_user)])
api_router.include_router(backtest_router, dependencies=[Depends(get_current_user)])
api_router.include_router(jobs_router, dependencies=[Depends(get_current_user)])
api_router.include_router(strategies_router, dependencies=[Depends(get_current_user)])
api_router.include_router(analytics_router, dependencies=[Depends(get_current_user)])
api_router.include_router(demo_router, dependencies=[Depends(get_current_user)])
api_router.include_router(paper_router, dependencies=[Depends(get_current_user)])
api_router.include_router(options_router, dependencies=[Depends(get_current_user)])
