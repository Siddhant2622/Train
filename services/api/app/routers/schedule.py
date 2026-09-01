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
        # Check if train exists and synthesize schedule from source/destination stations
        t_row = await db.execute(
            text("SELECT train_number, name, source_station, destination_station, total_distance_km, journey_duration_min FROM trains WHERE train_number = :n"),
            {"n": train_number}
        )
        train_info = t_row.mappings().first()
        src = (train_info["source_station"] if train_info else "NDLS") or "NDLS"
        dst = (train_info["destination_station"] if train_info else "HWH") or "HWH"
        dist = float(train_info["total_distance_km"]) if (train_info and train_info["total_distance_km"]) else 450.0

        # Ensure stations exist
        for code in (src, dst):
            await db.execute(
                text("""
                    INSERT INTO stations (station_code, name, latitude, longitude, is_major)
                    VALUES (:c, :c, :lat, :lon, true)
                    ON CONFLICT (station_code) DO NOTHING
                """),
                {"c": code, "lat": 28.6139 if code == "NDLS" else 22.5833, "lon": 77.2090 if code == "NDLS" else 88.3433}
            )

        # Insert 2-stop schedule
        await db.execute(
            text("""
                INSERT INTO train_schedule (train_number, sequence, station_code, scheduled_arrival, scheduled_departure, distance_from_source_km, avg_halt_minutes, day_offset)
                VALUES 
                    (:n, 1, :src, NULL, '08:00', 0.0, 0.0, 0),
                    (:n, 2, :dst, '20:00', NULL, :dist, 0.0, 0)
                ON CONFLICT ON CONSTRAINT uq_train_schedule DO NOTHING
            """),
            {"n": train_number, "src": src, "dst": dst, "dist": dist}
        )
        await db.commit()

        # Re-fetch
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
