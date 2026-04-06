"""
Analytics API composition.

Groups analytics routes by domain while preserving the existing /api/analytics/*
surface for the frontend.
"""

from fastapi import APIRouter

from app.api.analytics_compare import router as compare_router
from app.api.analytics_execution import router as execution_router
from app.api.analytics_factor_regime import router as factor_regime_router
from app.api.analytics_market import router as market_router
from app.api.analytics_risk import router as risk_router
from app.database import get_db

router = APIRouter(prefix="/analytics")
router.include_router(compare_router, tags=["analytics"])
router.include_router(risk_router, tags=["analytics"])
router.include_router(execution_router, tags=["analytics"])
router.include_router(factor_regime_router, tags=["analytics"])
router.include_router(market_router, tags=["analytics"])

__all__ = ["router", "get_db"]
