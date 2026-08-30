"""Train schedule endpoint — used by the simulator to bootstrap run data."""

from datetime import datetime, timezone, date as date_type, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

router = APIRouter(prefix="/api/v1/trains", tags=["schedule"])


@router.get("/{train_number}/schedule")
async def get_train_schedule(train_number: str, db: AsyncSession = Depends(get_db)):
    """Return the full stop sequence for a train — used by the simulator."""
    rows = await db.execute(
        text("""
            SELECT ts.sequence, ts.station_code, s.name as station_name,
                   s.latitude, s.longitude,
                   ts.scheduled_arrival, ts.scheduled_departure,
                   ts.distance_from_source_km, ts.avg_halt_minutes, ts.day_offset,
                   COALESCE(sec.avg_speed_kmh, 80) as section_avg_speed,
                   COALESCE(sec.max_permissible_speed_kmh, 100) as section_max_speed
            FROM train_schedule ts
            JOIN stations s ON ts.station_code = s.station_code
            LEFT JOIN sections sec ON sec.from_station = ts.station_code
            WHERE ts.train_number = :n
            ORDER BY ts.sequence
        """),
        {"n": train_number},
    )
    stops = rows.mappings().all()
    if not stops:
        raise HTTPException(status_code=404, detail=f"No schedule for train {train_number}")

    def fmt_time(t) -> str | None:
        if t is None:
            return None
        return f"{t.hour:02d}:{t.minute:02d}"

    return {
        "train_number": train_number,
        "stops": [
            {
                "sequence": s["sequence"],
                "station_code": s["station_code"],
                "station_name": s["station_name"],
                "latitude": float(s["latitude"]),
                "longitude": float(s["longitude"]),
                "scheduled_arrival": fmt_time(s["scheduled_arrival"]),
                "scheduled_departure": fmt_time(s["scheduled_departure"]),
                "distance_from_source_km": float(s["distance_from_source_km"] or 0),
                "avg_halt_minutes": float(s["avg_halt_minutes"]),
                "day_offset": s["day_offset"],
                "section_avg_speed_kmh": float(s["section_avg_speed"]),
                "section_max_speed_kmh": float(s["section_max_speed"]),
            }
            for s in stops
        ],
    }
