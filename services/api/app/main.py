"""RailPredict AI — FastAPI application entry point.

Phase 2: all production routes wired — trains, stations, admin, ingest, WebSocket.
"""

import logging
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import get_settings
from app.core.database import check_db_connection
from app.realtime.manager import manager
from app.routers import auth, trains, stations, admin, ingest, realtime, schedule

logger = logging.getLogger(__name__)
settings = get_settings()

# ---------------------------------------------------------------------------
# Sentry
# ---------------------------------------------------------------------------
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        traces_sample_rate=0.2,
        profiles_sample_rate=0.1,
    )

# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------
limiter = Limiter(key_func=get_remote_address)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("RailPredict API starting up…")
    await manager.startup(settings.redis_url)
    yield
    logger.info("RailPredict API shutting down…")
    await manager.shutdown()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="RailPredict AI",
    description="Dynamic ETA forecasting for Indian coaching trains (SIH26028 / Production)",
    version="0.2.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# ---------------------------------------------------------------------------
# Health endpoints
# ---------------------------------------------------------------------------
@app.get("/healthz", tags=["health"])
@limiter.limit("60/minute")
async def healthz(request: Request):
    return {"status": "ok", "version": app.version}


@app.get("/readyz", tags=["health"])
@limiter.limit("30/minute")
async def readyz(request: Request):
    db_ok = await check_db_connection()
    if not db_ok:
        return JSONResponse(status_code=503, content={"status": "unavailable", "db": "unreachable"})
    return {"status": "ok", "db": "connected"}


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(auth.router)
app.include_router(trains.router)
app.include_router(stations.router)
app.include_router(admin.router)
app.include_router(ingest.router)
app.include_router(realtime.router)
app.include_router(schedule.router)

