"""Stations REST router — public read endpoints."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.stations import StationBase, StationArrivalsResponse, ArrivalEntry, StationListResponse
from app.core.rate_limit import limiter

router = APIRouter(prefix="/api/v1/stations", tags=["stations"])


@router.get("", response_model=StationListResponse)
@limiter.limit("60/minute")
async def list_stations(
    request: Request,
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    zone: str | None = None,
    major_only: bool = False,
    db: AsyncSession = Depends(get_db),
) -> StationListResponse:
    """Return stations, optionally filtered by search query, zone, or major flag."""
    offset = (page - 1) * page_size
    
    # We use ILIKE for case-insensitive partial match
    search_term = f"%{q}%" if q else None

    rows = await db.execute(
        text("""
            SELECT station_code, name, city, state, zone, latitude, longitude,
                   is_major, platform_count
            FROM stations
            WHERE (CAST(:zone AS VARCHAR) IS NULL OR zone = CAST(:zone AS VARCHAR))
              AND (CAST(:major_only AS BOOLEAN) = false OR is_major = true)
              AND (CAST(:q AS VARCHAR) IS NULL OR name ILIKE CAST(:q AS VARCHAR) OR station_code ILIKE CAST(:q AS VARCHAR) OR city ILIKE CAST(:q AS VARCHAR))
            ORDER BY is_major DESC, name
            LIMIT :limit OFFSET :offset
        """),
        {"zone": zone, "major_only": major_only, "q": search_term, "limit": page_size, "offset": offset},
    )
    stations = [StationBase(**dict(r)) for r in rows.mappings().all()]
    
    count_row = await db.execute(
        text("""
            SELECT count(*) FROM stations 
            WHERE (CAST(:zone AS VARCHAR) IS NULL OR zone = CAST(:zone AS VARCHAR))
              AND (CAST(:major_only AS BOOLEAN) = false OR is_major = true)
              AND (CAST(:q AS VARCHAR) IS NULL OR name ILIKE CAST(:q AS VARCHAR) OR station_code ILIKE CAST(:q AS VARCHAR) OR city ILIKE CAST(:q AS VARCHAR))
        """),
        {"zone": zone, "major_only": major_only, "q": search_term},
    )
    total = count_row.scalar() or 0

    return StationListResponse(stations=stations, total=total, page=page, page_size=page_size)


@router.get("/{station_code}", response_model=StationBase)
@limiter.limit("60/minute")
async def get_station(request: Request, station_code: str, db: AsyncSession = Depends(get_db)) -> StationBase:
    row = await db.execute(
        text("SELECT * FROM stations WHERE station_code = :code"),
        {"code": station_code.upper()},
    )
    data = row.mappings().first()
    if not data:
        raise HTTPException(status_code=404, detail=f"Station {station_code} not found")
    return StationBase(**dict(data))


@router.get("/{station_code}/arrivals", response_model=StationArrivalsResponse)
@limiter.limit("60/minute")
async def station_arrivals(
    request: Request,
    station_code: str,
    limit: int = Query(20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> StationArrivalsResponse:
    """Upcoming arrivals at a station with ETA from predictions."""
    code = station_code.upper()

    station_row = await db.execute(
        text("SELECT name FROM stations WHERE station_code = :code"),
        {"code": code},
    )
    station = station_row.mappings().first()
    if not station:
        raise HTTPException(status_code=404, detail=f"Station {code} not found")

    today = datetime.now(timezone.utc).date()

    rows = await db.execute(
        text("""
            WITH latest_preds AS (
                SELECT DISTINCT ON (train_number, station_code)
                    train_number, station_code, predicted_eta, lower_bound, upper_bound
                FROM predictions
                WHERE station_code = :code AND run_date = :today
                  AND predicted_eta > now()
                ORDER BY train_number, station_code, time DESC
            )
            SELECT t.train_number, t.name, t.train_type,
                   t.source_station, t.destination_station,
                   ts.scheduled_arrival, ts.day_offset,
                   lp.predicted_eta,
                   COALESCE(pos.current_delay_min, 0) as current_delay_min,
                   pos.time as last_updated
            FROM train_schedule ts
            JOIN trains t ON ts.train_number = t.train_number
            LEFT JOIN latest_preds lp ON lp.train_number = ts.train_number
            LEFT JOIN (
                SELECT DISTINCT ON (train_number) train_number, current_delay_min, time
                FROM train_positions WHERE run_date = :today
                ORDER BY train_number, time DESC
            ) pos ON pos.train_number = t.train_number
            WHERE ts.station_code = :code AND t.is_active = true
            ORDER BY COALESCE(lp.predicted_eta, '9999-01-01'::timestamptz)
            LIMIT :limit
        """),
        {"code": code, "today": today, "limit": limit},
    )
    arrivals_data = rows.mappings().all()
    now = datetime.now(timezone.utc)

    arrivals = []
    for r in arrivals_data:
        delay = float(r["current_delay_min"])
        status = "on_time" if delay <= 5 else "delayed" if delay <= 30 else "severely_delayed"
        if not r["last_updated"]:
            status = "unknown"

        arrivals.append(
            ArrivalEntry(
                train_number=r["train_number"],
                train_name=r["name"],
                train_type=r["train_type"],
                scheduled_arrival=_combine_scheduled(today, r.get("scheduled_arrival"), r.get("day_offset", 0)),
                predicted_eta=r["predicted_eta"],
                delay_min=delay,
                status=status,
                source_station=r["source_station"],
                destination_station=r["destination_station"],
            )
        )

    return StationArrivalsResponse(
        station_code=code,
        station_name=station["name"],
        arrivals=arrivals,
        generated_at=now,
    )


def _combine_scheduled(run_date, t, day_offset: int):
    if t is None:
        return None
    from datetime import timedelta
    base = datetime(run_date.year, run_date.month, run_date.day,
                    t.hour, t.minute, 0, tzinfo=timezone.utc)
    return base + timedelta(days=day_offset or 0)
