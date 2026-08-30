"""Trains REST router — public read endpoints."""

from datetime import datetime, timezone, date as date_type
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.trains import TrainDetail, TrainListResponse, TrainSummary, LivePosition, StopEta

router = APIRouter(prefix="/api/v1/trains", tags=["trains"])


def _delay_status(delay_min: float) -> str:
    if delay_min <= 5:
        return "on_time"
    if delay_min <= 30:
        return "delayed"
    return "severely_delayed"


@router.get("", response_model=TrainListResponse)
async def list_trains(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, pattern="^(on_time|delayed|severely_delayed)$"),
    zone: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> TrainListResponse:
    """Return all currently active trains with their latest position and delay status."""
    today = datetime.now(timezone.utc).date()
    offset = (page - 1) * page_size

    # Latest position per train for today's run
    rows = await db.execute(
        text("""
            WITH latest AS (
                SELECT DISTINCT ON (train_number)
                    train_number, latitude, longitude, current_delay_min,
                    next_station, last_station, time as updated_at
                FROM train_positions
                WHERE run_date = :today
                ORDER BY train_number, time DESC
            )
            SELECT t.train_number, t.name, t.train_type, t.zone,
                   t.source_station, t.destination_station,
                   COALESCE(l.current_delay_min, 0) as current_delay_min,
                   l.latitude, l.longitude, l.next_station, l.updated_at
            FROM trains t
            LEFT JOIN latest l ON t.train_number = l.train_number
            WHERE t.is_active = true
              AND (:zone IS NULL OR t.zone = :zone)
            ORDER BY COALESCE(l.current_delay_min, 0) DESC
            LIMIT :limit OFFSET :offset
        """),
        {"today": today, "zone": zone, "limit": page_size, "offset": offset},
    )
    train_rows = rows.mappings().all()

    count_row = await db.execute(
        text("SELECT count(*) FROM trains WHERE is_active = true AND (:zone IS NULL OR zone = :zone)"),
        {"zone": zone},
    )
    total = count_row.scalar() or 0

    trains = [
        TrainSummary(
            train_number=r["train_number"],
            name=r["name"],
            train_type=r["train_type"],
            source_station=r["source_station"],
            destination_station=r["destination_station"],
            current_delay_min=float(r["current_delay_min"]),
            status=_delay_status(float(r["current_delay_min"])) if r["updated_at"] else "unknown",
            latitude=float(r["latitude"]) if r["latitude"] is not None else None,
            longitude=float(r["longitude"]) if r["longitude"] is not None else None,
            next_station=r["next_station"],
            last_updated=r["updated_at"],
        )
        for r in train_rows
    ]

    if status:
        trains = [t for t in trains if t.status == status]

    return TrainListResponse(trains=trains, total=total, page=page, page_size=page_size)


@router.get("/{train_number}", response_model=TrainDetail)
async def get_train(train_number: str, db: AsyncSession = Depends(get_db)) -> TrainDetail:
    """Return full detail for a train — current position + all upcoming ETAs."""
    train_row = await db.execute(
        text("SELECT * FROM trains WHERE train_number = :n"),
        {"n": train_number},
    )
    train = train_row.mappings().first()
    if not train:
        raise HTTPException(status_code=404, detail=f"Train {train_number} not found")

    today = datetime.now(timezone.utc).date()

    pos_row = await db.execute(
        text("""
            SELECT latitude, longitude, speed_kmh, last_station, next_station,
                   distance_to_next_km, current_delay_min, time, source
            FROM train_positions
            WHERE train_number = :n AND run_date = :today
            ORDER BY time DESC LIMIT 1
        """),
        {"n": train_number, "today": today},
    )
    pos = pos_row.mappings().first()

    position = None
    if pos:
        position = LivePosition(
            latitude=float(pos["latitude"]) if pos["latitude"] is not None else None,
            longitude=float(pos["longitude"]) if pos["longitude"] is not None else None,
            speed_kmh=float(pos["speed_kmh"]) if pos["speed_kmh"] is not None else None,
            last_station=pos["last_station"],
            next_station=pos["next_station"],
            distance_to_next_km=float(pos["distance_to_next_km"]) if pos["distance_to_next_km"] is not None else None,
            current_delay_min=float(pos["current_delay_min"]),
            updated_at=pos["time"],
            source=pos["source"],
        )

    # Latest predictions for upcoming stops
    pred_rows = await db.execute(
        text("""
            WITH latest_preds AS (
                SELECT DISTINCT ON (station_code)
                    station_code, station_sequence, predicted_eta,
                    lower_bound, upper_bound, confidence, model_version,
                    time as computed_at
                FROM predictions
                WHERE train_number = :n AND run_date = :today
                  AND predicted_eta > now()
                ORDER BY station_code, time DESC
            )
            SELECT lp.*, s.name as station_name,
                   ts.scheduled_arrival, ts.day_offset
            FROM latest_preds lp
            JOIN stations s ON lp.station_code = s.station_code
            LEFT JOIN train_schedule ts ON ts.train_number = :n
                AND ts.station_code = lp.station_code
            ORDER BY lp.station_sequence NULLS LAST
        """),
        {"n": train_number, "today": today},
    )
    preds = pred_rows.mappings().all()

    upcoming_stops = [
        StopEta(
            station_code=p["station_code"],
            station_name=p["station_name"],
            sequence=p["station_sequence"] or 0,
            scheduled_arrival=_combine_scheduled(today, p.get("scheduled_arrival"), p.get("day_offset", 0)),
            predicted_eta=p["predicted_eta"],
            lower_bound=p["lower_bound"],
            upper_bound=p["upper_bound"],
            confidence=float(p["confidence"]) if p["confidence"] else 0.7,
            delay_min=round((p["predicted_eta"] - _combine_scheduled(today, p.get("scheduled_arrival"), p.get("day_offset", 0))).total_seconds() / 60, 1)
            if p.get("scheduled_arrival") else 0.0,
        )
        for p in preds
    ]

    return TrainDetail(
        train_number=train["train_number"],
        name=train["name"],
        train_type=train["train_type"],
        zone=train["zone"],
        source_station=train["source_station"],
        destination_station=train["destination_station"],
        total_distance_km=float(train["total_distance_km"]) if train["total_distance_km"] else None,
        run_date=today,
        position=position,
        upcoming_stops=upcoming_stops,
        model_version="physics_v1",
    )


@router.get("/{train_number}/history")
async def get_train_history(
    train_number: str,
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Return today's position history for a train — for drawing the track on the map."""
    today = datetime.now(timezone.utc).date()
    rows = await db.execute(
        text("""
            SELECT time, latitude, longitude, speed_kmh, current_delay_min,
                   last_station, next_station
            FROM train_positions
            WHERE train_number = :n AND run_date = :today
            ORDER BY time DESC LIMIT :limit
        """),
        {"n": train_number, "today": today, "limit": limit},
    )
    data = rows.mappings().all()
    return {"train_number": train_number, "run_date": str(today), "positions": list(data)}


def _combine_scheduled(run_date: date_type, t, day_offset: int) -> datetime | None:
    if t is None:
        return None
    from datetime import timedelta
    base = datetime(run_date.year, run_date.month, run_date.day,
                    t.hour, t.minute, 0, tzinfo=timezone.utc)
    return base + timedelta(days=day_offset or 0)
