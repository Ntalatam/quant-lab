from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db, async_session
from app.api.router import api_router
from app.services.paper_trading import PaperTradingManager


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    manager = PaperTradingManager(async_session)
    app.state.paper_trading_manager = manager
    await manager.resume_active_sessions()
    yield
    await manager.shutdown()


def create_app() -> FastAPI:
    app = FastAPI(
        title="QuantLab API",
        description="Quantitative research and backtesting platform",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api")
    return app


app = create_app()
