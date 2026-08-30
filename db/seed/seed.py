"""Idempotent database seeder.

Seeds stations, trains, and their schedules from the JSON files in this directory.
Safe to re-run — uses INSERT ... ON CONFLICT DO NOTHING for all records.

Usage (run from services/api/):
    python -m db.seed.seed
    # or inside Docker:
    docker compose exec api python -m db.seed.seed
"""

import asyncio
import json
import sys
from datetime import datetime, time
from pathlib import Path

# Allow running from the services/api directory
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "services" / "api"))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
import os

SEED_DIR = Path(__file__).parent

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://railpredict:dev_password_change_me@localhost:5432/railpredict",
)


def parse_time(t_str: str | None) -> time | None:
    if not t_str:
        return None
    try:
        h, m = t_str.split(":")[:2]
        return time(int(h) % 24, int(m))
    except Exception:
        return None


async def seed() -> None:
    engine = create_async_engine(DATABASE_URL, echo=False)
    Session = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with Session() as db:
        # ----------------------------------------------------------------
        # Stations
        # ----------------------------------------------------------------
        stations_data = json.loads((SEED_DIR / "stations.json").read_text())
        inserted_stations = 0
        for s in stations_data:
            result = await db.execute(
                text("""
                    INSERT INTO stations
                        (station_code, name, city, state, zone, latitude, longitude, is_major, platform_count)
                    VALUES
                        (:station_code, :name, :city, :state, :zone, :latitude, :longitude, :is_major, :platform_count)
                    ON CONFLICT (station_code) DO NOTHING
                """),
                {
                    "station_code": s["station_code"],
                    "name": s["name"],
                    "city": s.get("city"),
                    "state": s.get("state"),
                    "zone": s.get("zone"),
                    "latitude": s["latitude"],
                    "longitude": s["longitude"],
                    "is_major": s.get("is_major", False),
                    "platform_count": s.get("platform_count"),
                },
            )
            if result.rowcount:
                inserted_stations += 1
        await db.commit()
        print(f"✓ Stations: {inserted_stations} inserted ({len(stations_data)} total in seed file)")

        # ----------------------------------------------------------------
        # Trains + Schedules
        # ----------------------------------------------------------------
        trains_data = json.loads((SEED_DIR / "trains.json").read_text())
        inserted_trains = 0
        inserted_schedules = 0

        for t in trains_data:
            dep_time = parse_time(t.get("departure_time", "").replace(":00", "")[:5])
            arr_time = parse_time(t.get("arrival_time", "").replace(":00", "")[:5])

            result = await db.execute(
                text("""
                    INSERT INTO trains
                        (train_number, name, train_type, zone, source_station, destination_station,
                         total_distance_km, journey_duration_min, runs_on_days, departure_time, arrival_time)
                    VALUES
                        (:train_number, :name, :train_type, :zone, :source_station, :destination_station,
                         :total_distance_km, :journey_duration_min, :runs_on_days, :departure_time, :arrival_time)
                    ON CONFLICT (train_number) DO NOTHING
                """),
                {
                    "train_number": t["train_number"],
                    "name": t["name"],
                    "train_type": t.get("train_type"),
                    "zone": t.get("zone"),
                    "source_station": t["source_station"],
                    "destination_station": t["destination_station"],
                    "total_distance_km": t.get("total_distance_km"),
                    "journey_duration_min": t.get("journey_duration_min"),
                    "runs_on_days": t.get("runs_on_days", "1111111"),
                    "departure_time": dep_time,
                    "arrival_time": arr_time,
                },
            )
            if result.rowcount:
                inserted_trains += 1

            # Insert schedule stops
            for stop in t.get("schedule", []):
                arr = parse_time(stop.get("arrival"))
                dep = parse_time(stop.get("departure"))
                res2 = await db.execute(
                    text("""
                        INSERT INTO train_schedule
                            (train_number, sequence, station_code, scheduled_arrival, scheduled_departure,
                             distance_from_source_km, avg_halt_minutes, day_offset)
                        VALUES
                            (:train_number, :sequence, :station_code, :scheduled_arrival, :scheduled_departure,
                             :distance_from_source_km, :avg_halt_minutes, :day_offset)
                        ON CONFLICT ON CONSTRAINT uq_train_schedule DO NOTHING
                    """),
                    {
                        "train_number": t["train_number"],
                        "sequence": stop["sequence"],
                        "station_code": stop["station_code"],
                        "scheduled_arrival": arr,
                        "scheduled_departure": dep,
                        "distance_from_source_km": stop.get("distance_km"),
                        "avg_halt_minutes": stop.get("halt_min", 2),
                        "day_offset": stop.get("day", 0),
                    },
                )
                if res2.rowcount:
                    inserted_schedules += 1

        await db.commit()
        print(f"✓ Trains: {inserted_trains} inserted ({len(trains_data)} total in seed file)")
        print(f"✓ Schedule stops: {inserted_schedules} inserted")

        # ----------------------------------------------------------------
        # Seed a default admin user (idempotent)
        # ----------------------------------------------------------------
        # Import here to avoid circular imports at module level
        import sys, os
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "services" / "api"))
        
        admin_email = os.getenv("SEED_ADMIN_EMAIL", "admin@railpredict.dev")
        admin_password = os.getenv("SEED_ADMIN_PASSWORD", "ChangeMe123!")

        try:
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            hashed = pwd_context.hash(admin_password)
            await db.execute(
                text("""
                    INSERT INTO users (email, password_hash, role)
                    VALUES (:email, :password_hash, 'admin')
                    ON CONFLICT (email) DO NOTHING
                """),
                {"email": admin_email, "password_hash": hashed},
            )
            await db.commit()
            print(f"✓ Admin user: {admin_email} (seeded if not present)")
        except ImportError:
            print("⚠  passlib not available — skipping admin user seed")

        print("\n✅ Seeding complete.")
        print(f"   Admin login: {admin_email} / {admin_password}")
        print("   Change the password immediately after first login in production.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
