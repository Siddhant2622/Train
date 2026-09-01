"""Ingestion router — receives position pings from the simulator and real feed adapter.

This endpoint is the single point of ingress for all position data.
It:
  1. Validates the ping (Pydantic)
  2. Writes to train_positions (TimescaleDB)
  3. Fetches the upcoming schedule and section speeds
  4. Computes physics ETA for all remaining stops
  5. Writes predictions to DB
  6. Publishes to Redis → WebSocket gateway relays to connected clients

Rate limited and requires an internal API key — not exposed publicly.
"""

import logging
import json
from datetime import datetime, timezone, date as date_type

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.eta.baseline import compute_eta
from app.realtime.manager import manager
from app.schemas.ingest import IngestResponse, PositionPing

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ingest", tags=["ingest"])


async def verify_internal_key(request: Request) -> None:
    """Simple API key auth for internal service-to-service calls."""
    settings = get_settings()
    key = request.headers.get("X-Internal-Key", "")
    if not key or key != settings.internal_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing internal API key",
        )


@router.post("/position", response_model=IngestResponse, status_code=202)
async def ingest_position(
    ping: PositionPing,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(verify_internal_key),
) -> IngestResponse:
    """Accept a position ping and compute ETAs.

    This is an internal endpoint — requires X-Internal-Key header.
    The simulator and real-feed adapter both POST here.
    """
    now = ping.timestamp.replace(tzinfo=timezone.utc) if ping.timestamp.tzinfo is None else ping.timestamp

    # ------------------------------------------------------------------
    # 1. Write position to TimescaleDB
    # ------------------------------------------------------------------
    await db.execute(
        text("""
            INSERT INTO train_positions
                (time, train_number, run_date, latitude, longitude, speed_kmh,
                 heading_deg, last_station, next_station, distance_to_next_km,
                 current_delay_min, source)
            VALUES
                (:time, :train_number, :run_date, :latitude, :longitude, :speed_kmh,
                 :heading_deg, :last_station, :next_station, :distance_to_next_km,
                 :current_delay_min, :source)
            ON CONFLICT DO NOTHING
        """),
        {
            "time": now,
            "train_number": ping.train_number,
            "run_date": ping.run_date,
            "latitude": ping.latitude,
            "longitude": ping.longitude,
            "speed_kmh": ping.speed_kmh,
            "heading_deg": ping.heading_deg,
            "last_station": ping.last_station,
            "next_station": ping.next_station,
            "distance_to_next_km": ping.distance_to_next_km,
            "current_delay_min": ping.current_delay_min,
            "source": ping.source,
        },
    )
    await db.commit()

    # ------------------------------------------------------------------
    # 2. Fetch upcoming schedule stops
    # ------------------------------------------------------------------
    sched_rows = await db.execute(
        text("""
            SELECT ts.sequence, ts.station_code, s.name as station_name,
                   ts.scheduled_arrival, ts.scheduled_departure,
                   ts.distance_from_source_km, ts.avg_halt_minutes, ts.day_offset,
                   st.latitude, st.longitude
            FROM train_schedule ts
            JOIN stations st ON ts.station_code = st.station_code
            JOIN stations s ON ts.station_code = s.station_code
            WHERE ts.train_number = :train_number
              AND ts.station_code != :last_station
            ORDER BY ts.sequence
        """),
        {"train_number": ping.train_number, "last_station": ping.last_station},
    )
    schedule = sched_rows.mappings().all()

    if not schedule:
        return IngestResponse(
            status="accepted_no_schedule",
            train_number=ping.train_number,
            timestamp=now,
            predictions_computed=0,
        )

    # ------------------------------------------------------------------
    # 3. Build station lookup and section speed lookup
    # ------------------------------------------------------------------
    station_lookup = {
        row["station_code"]: {"name": row["station_name"], "latitude": row["latitude"], "longitude": row["longitude"]}
        for row in schedule
    }

    section_rows = await db.execute(
        text("SELECT from_station, to_station, avg_speed_kmh FROM sections")
    )
    section_speeds = {
        (r["from_station"], r["to_station"]): float(r["avg_speed_kmh"])
        for r in section_rows.mappings().all()
    }

    # Build upcoming stops list — only future stops (sequence > last_station's sequence)
    last_seq_row = await db.execute(
        text("""
            SELECT sequence FROM train_schedule
            WHERE train_number = :train_number AND station_code = :station_code
            LIMIT 1
        """),
        {"train_number": ping.train_number, "station_code": ping.last_station},
    )
    last_seq = (last_seq_row.scalar() or 0)

    upcoming = [
        {
            "sequence": r["sequence"],
            "station_code": r["station_code"],
            "station_name": r["station_name"],
            "scheduled_arrival": _combine_time(ping.run_date, r["scheduled_arrival"], r["day_offset"]),
            "avg_halt_minutes": float(r["avg_halt_minutes"]),
            "distance_from_source_km": float(r["distance_from_source_km"] or 0),
        }
        for r in schedule
        if r["sequence"] > last_seq
    ]

    if not upcoming:
        return IngestResponse(
            status="accepted_terminus_reached",
            train_number=ping.train_number,
            timestamp=now,
            predictions_computed=0,
        )

    # ------------------------------------------------------------------
    # 4. Compute physics ETA and apply ML layer
    # ------------------------------------------------------------------
    eta_result = compute_eta(
        train_number=ping.train_number,
        run_date=str(ping.run_date),
        now=now,
        current_delay_min=ping.current_delay_min,
        current_speed_kmph=ping.speed_kmh,
        distance_to_next_km=ping.distance_to_next_km,
        last_station_code=ping.last_station,
        next_station_code=ping.next_station,
        upcoming_stops=upcoming,
        station_lookup=station_lookup,
        section_speeds=section_speeds,
    )

    from app.eta.ml_xgboost import apply_ml_layer
    from app.eta.ml_sequence import apply_sequence_layer
    from app.eta.kalman import apply_kalman_filter
    from app.eta.propagation import detect_propagation, apply_propagation_layer
    from app.eta.events import fetch_active_events, apply_event_layer

    # Phase 5: Detect cross-train propagation first
    await detect_propagation(
        db=db,
        cause_train=ping.train_number,
        current_delay_min=ping.current_delay_min,
        next_station=ping.next_station,
        now=now,
    )
    
    # Fetch active control room events (Phase 6)
    active_events = await fetch_active_events(db)

    # Layer 2: XGBoost Residuals
    eta_result = apply_ml_layer(
        eta_result=eta_result,
        current_speed_kmph=ping.speed_kmh,
        time_of_day_hour=now.hour,
        day_of_week=now.weekday()
    )
    
    # Layer 3: GRU Sequence Modeling
    eta_result = apply_sequence_layer(
        eta_result=eta_result,
        time_of_day_hour=now.hour
    )
    
    # Layer 4: Kalman Filter Smoothing
    eta_result = apply_kalman_filter(
        eta_result=eta_result
    )

    # Layer 5: Network Delay Cascade Propagation
    eta_result = await apply_propagation_layer(
        db=db,
        eta_result=eta_result
    )
    
    # Layer 6: Control Room Events (Overrides everything else)
    eta_result = apply_event_layer(
        eta_result=eta_result,
        active_events=active_events
    )

    # ------------------------------------------------------------------
    # 5. Write predictions to DB
    # ------------------------------------------------------------------
    for stop in eta_result.stops:
        await db.execute(
            text("""
                INSERT INTO predictions
                    (time, train_number, run_date, station_code, station_sequence,
                     predicted_eta, lower_bound, upper_bound, confidence,
                     model_version, explanation)
                VALUES
                    (:time, :train_number, :run_date, :station_code, :station_sequence,
                     :predicted_eta, :lower_bound, :upper_bound, :confidence,
                     :model_version, :explanation)
                ON CONFLICT DO NOTHING
            """),
            {
                "time": now,
                "train_number": ping.train_number,
                "run_date": ping.run_date,
                "station_code": stop.station_code,
                "station_sequence": stop.sequence,
                "predicted_eta": stop.predicted_eta,
                "lower_bound": stop.lower_bound,
                "upper_bound": stop.upper_bound,
                "confidence": stop.confidence,
                "model_version": eta_result.model_version[:20],
                "explanation": json.dumps(stop.explanation),
            },
        )
    await db.commit()

    # ------------------------------------------------------------------
    # 6. Publish to Redis → WebSocket clients
    # ------------------------------------------------------------------
    ws_payload = {
        "event": "position_update",
        "train_number": ping.train_number,
        "run_date": str(ping.run_date),
        "timestamp": now.isoformat(),
        "latitude": ping.latitude,
        "longitude": ping.longitude,
        "speed_kmh": ping.speed_kmh,
        "current_delay_min": ping.current_delay_min,
        "last_station": ping.last_station,
        "next_station": ping.next_station,
        "distance_to_next_km": ping.distance_to_next_km,
        "upcoming_stops": [
            {
                "station_code": s.station_code,
                "station_name": s.station_name,
                "predicted_eta": s.predicted_eta.isoformat(),
                "lower_bound": s.lower_bound.isoformat(),
                "upper_bound": s.upper_bound.isoformat(),
                "delay_min": s.delay_at_stop_min,
                "explanation": s.explanation,
            }
            for s in eta_result.stops[:5]  # send first 5 for WS efficiency
        ],
    }
    await manager.publish(ping.train_number, ws_payload)

    return IngestResponse(
        status="accepted",
        train_number=ping.train_number,
        timestamp=now,
        predictions_computed=len(eta_result.stops),
    )


def _combine_time(run_date: date_type, t, day_offset: int) -> datetime | None:
    """Combine a schedule time with the run date and day offset."""
    if t is None:
        return None
    from datetime import datetime, timedelta, timezone
    base = datetime(run_date.year, run_date.month, run_date.day,
                    t.hour, t.minute, 0, tzinfo=timezone.utc)
    return base + timedelta(days=day_offset)
