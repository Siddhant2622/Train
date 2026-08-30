"""RailPredict AI — FastAPI application entry point.

Phase 0: health endpoints, auth, CORS, Sentry, rate limiting.
No train/ML/realtime logic yet — that's Phase 1+.
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
from app.routers import auth

logger = logging.getLogger(__name__)

settings = get_settings()


# ---------------------------------------------------------------------------
# Sentry — initialise before app creation so it captures startup errors too
# ---------------------------------------------------------------------------

if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        traces_sample_rate=0.2,   # capture 20% of transactions for perf
        profiles_sample_rate=0.1,
    )
    logger.info("Sentry initialised")
else:
    logger.info("SENTRY_DSN not set — error monitoring disabled")


# ---------------------------------------------------------------------------
# Rate limiter (slowapi)
# ---------------------------------------------------------------------------

limiter = Limiter(key_func=get_remote_address)


# ---------------------------------------------------------------------------
# App lifespan — startup / shutdown hooks
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("RailPredict API starting up…")
    # Future phases: warm model cache, start background tasks, etc.
    yield
    logger.info("RailPredict API shutting down…")


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(
    title="RailPredict AI",
    description="Dynamic ETA forecasting for Indian coaching trains (SIH26028)",
    version="0.1.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

# ---- Middleware ----

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
# Health endpoints (required by Render/Fly load balancers and CI smoke tests)
# ---------------------------------------------------------------------------

@app.get("/healthz", tags=["health"], summary="Liveness probe")
@limiter.limit("60/minute")
async def healthz(request: Request):
    """Returns 200 OK if the process is running. Used by load balancers."""
    return {"status": "ok", "version": app.version}


@app.get("/readyz", tags=["health"], summary="Readiness probe")
@limiter.limit("30/minute")
async def readyz(request: Request):
    """Returns 200 OK only if the database is reachable.
    
    Returns 503 if the DB is down so the load balancer stops sending traffic.
    """
    db_ok = await check_db_connection()
    if not db_ok:
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "db": "unreachable"},
        )
    return {"status": "ok", "db": "connected"}


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(auth.router)

# Phase 1+ routers (uncomment as they are built):
# from app.routers import trains, stations, realtime
# app.include_router(trains.router)
# app.include_router(stations.router)
# app.include_router(realtime.router)
