from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.router import api_router
from app.config import settings
from app.database import async_session, engine, init_db
from app.observability import (
    bind_request_context,
    clear_request_context,
    configure_logging,
    elapsed_ms,
    get_logger,
)
from app.schemas.system import DependencyHealth, HealthResponse
from app.services.paper_trading import PaperTradingManager

configure_logging(
    service_name=settings.APP_NAME,
    environment=settings.APP_ENV,
    log_level=settings.LOG_LEVEL,
    json_logs=settings.LOG_JSON,
)
logger = get_logger(__name__)

OPENAPI_TAGS = [
    {
        "name": "system",
        "description": "Readiness probes and operational health endpoints.",
    },
    {
        "name": "data",
        "description": "Market-data loading and chart-ready OHLCV retrieval.",
    },
    {
        "name": "backtest",
        "description": "Historical simulation, parameter sweeps, and optimization workflows.",
    },
    {
        "name": "analytics",
        "description": "Post-trade analytics, comparison, attribution, and portfolio blending.",
    },
    {
        "name": "paper-trading",
        "description": "Persistent live paper-trading sessions and real-time monitoring.",
    },
    {
        "name": "options",
        "description": "Black-Scholes pricing, Greeks, implied volatility, and volatility surface analytics.",
    },
    {
        "name": "strategies",
        "description": "Strategy metadata, parameter schemas, and discoverability helpers.",
    },
    {
        "name": "demo",
        "description": "Workspace seeding helpers for the demo and onboarding flows.",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.started_at = time.monotonic()
    logger.info("app.startup.started")
    await init_db()
    manager = PaperTradingManager(async_session)
    app.state.paper_trading_manager = manager
    await manager.resume_active_sessions()
    logger.info("app.startup.completed")
    try:
        yield
    finally:
        await manager.shutdown()
        logger.info("app.shutdown.completed")


def create_app() -> FastAPI:
    app = FastAPI(
        title="QuantLab API",
        summary="API for QuantLab's quantitative research, backtesting, and paper-trading platform.",
        description=(
            "QuantLab exposes historical simulation, analytics, data-ingestion, and "
            "paper-trading endpoints for the frontend research workstation.\n\n"
            "Use these docs to inspect request and response contracts, replay sample "
            "payloads, and understand how backtests, analytics, and live paper sessions "
            "flow through the system."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_tags=OPENAPI_TAGS,
        swagger_ui_parameters={
            "displayRequestDuration": True,
            "docExpansion": "list",
            "defaultModelsExpandDepth": 1,
        },
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or f"req_{uuid.uuid4().hex[:12]}"
        request.state.request_id = request_id
        bind_request_context(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        start_time = time.perf_counter()
        log = logger.bind(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = elapsed_ms(start_time)
            log.exception(
                "http.request.failed",
                duration_ms=duration_ms,
                query=str(request.url.query),
                client=request.client.host if request.client else None,
            )
            clear_request_context()
            raise

        duration_ms = elapsed_ms(start_time)
        level = (
            "warning"
            if duration_ms >= settings.SLOW_REQUEST_THRESHOLD_MS
            else "info"
        )
        getattr(log, level)(
            "http.request.completed",
            duration_ms=duration_ms,
            status_code=response.status_code,
            query=str(request.url.query),
            client=request.client.host if request.client else None,
        )
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"
        clear_request_context()
        return response

    @app.get(
        "/health",
        response_model=HealthResponse,
        tags=["system"],
        summary="Readiness and liveness probe",
        description=(
            "Checks API readiness, database connectivity, and the paper-trading "
            "runtime manager. Returns HTTP 503 when a critical dependency is degraded."
        ),
    )
    async def health_check(request: Request):
        dependencies: dict[str, DependencyHealth] = {}
        overall_status = "ok"

        db_start = time.perf_counter()
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            dependencies["database"] = DependencyHealth(
                status="ok",
                latency_ms=elapsed_ms(db_start),
                details={"engine": "sqlalchemy-async"},
            )
        except Exception as exc:
            overall_status = "degraded"
            dependencies["database"] = DependencyHealth(
                status="degraded",
                latency_ms=elapsed_ms(db_start),
                details={"error": str(exc)},
            )

        paper_manager = getattr(request.app.state, "paper_trading_manager", None)
        if paper_manager is None:
            overall_status = "degraded"
            dependencies["paper_trading"] = DependencyHealth(
                status="degraded",
                details={"error": "paper trading manager not initialized"},
            )
        else:
            dependencies["paper_trading"] = DependencyHealth(
                status="ok",
                details=paper_manager.health_summary(),
            )

        payload = HealthResponse(
            status=overall_status,
            service=settings.APP_NAME,
            environment=settings.APP_ENV,
            version=app.version,
            timestamp=datetime.now(timezone.utc),
            uptime_seconds=round(
                time.monotonic() - request.app.state.started_at,
                2,
            ),
            request_id=getattr(request.state, "request_id", None),
            dependencies=dependencies,
        )
        logger.info(
            "system.health_checked",
            status=overall_status,
            database_status=dependencies["database"].status,
        )
        return JSONResponse(
            status_code=200 if overall_status == "ok" else 503,
            content=payload.model_dump(mode="json"),
        )

    app.include_router(api_router, prefix="/api")
    return app


app = create_app()
