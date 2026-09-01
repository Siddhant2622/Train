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
    engine = create_async_engine(
        DATABASE_URL, 
        echo=False,
        connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0}
    )
    Session = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with Session() as db:
        # ----------------------------------------------------------------
        # Stations
        # ----------------------------------------------------------------
        stations_data = json.loads((SEED_DIR / "stations.json").read_text())
        stations_map = {}
        for s in stations_data:
            code = str(s["station_code"])[:10].strip().upper()
            if not code:
                continue
            stations_map[code] = {
                "station_code": code,
                "name": s.get("name") or code,
                "city": s.get("city"),
                "state": s.get("state"),
                "zone": str(s.get("zone") or "")[:10] if s.get("zone") else None,
                "latitude": float(s.get("latitude") or 0.0),
                "longitude": float(s.get("longitude") or 0.0),
                "is_major": bool(s.get("is_major", False)),
                "platform_count": s.get("platform_count") or 1,
            }

        # ----------------------------------------------------------------
        # Trains + Schedules
        # ----------------------------------------------------------------
        trains_data = json.loads((SEED_DIR / "trains.json").read_text())
        trains_params = []
        schedule_params = []

        for t in trains_data:
            t_num = str(t["train_number"])[:10].strip()
            src = str(t.get("source_station") or "NDLS")[:10].strip().upper()
            dst = str(t.get("destination_station") or "HWH")[:10].strip().upper()
            
            # Ensure source and destination stations exist in stations_map
            for st_code in (src, dst):
                if st_code not in stations_map:
                    stations_map[st_code] = {
                        "station_code": st_code,
                        "name": st_code,
                        "city": None,
                        "state": None,
                        "zone": None,
                        "latitude": 28.6139 if st_code == "NDLS" else (22.5833 if st_code == "HWH" else 25.0),
                        "longitude": 77.2090 if st_code == "NDLS" else (88.3433 if st_code == "HWH" else 82.0),
                        "is_major": True,
                        "platform_count": 2,
                    }

            dep_time = parse_time(str(t.get("departure_time") or "08:00").replace(":00", "")[:5]) or time(8, 0)
            arr_time = parse_time(str(t.get("arrival_time") or "20:00").replace(":00", "")[:5]) or time(20, 0)
            dur = t.get("duration_minutes") or t.get("journey_duration_min") or 720
            dist = float(t.get("total_distance_km") or max(50, int(dur * 1.1)))

            trains_params.append({
                "train_number": t_num,
                "name": t.get("name") or f"Train {t_num}",
                "train_type": str(t.get("train_type") or t.get("type") or "Express")[:30],
                "zone": str(t.get("zone") or "")[:10] if t.get("zone") else None,
                "source_station": src,
                "destination_station": dst,
                "total_distance_km": dist,
                "journey_duration_min": dur,
                "runs_on_days": str(t.get("runs_on_days", "1111111"))[:7],
                "departure_time": dep_time,
                "arrival_time": arr_time,
            })

            # Check stops
            raw_stops = t.get("schedule", [])
            if raw_stops:
                for stop in raw_stops:
                    st_c = str(stop["station_code"])[:10].strip().upper()
                    if st_c not in stations_map:
                        stations_map[st_c] = {
                            "station_code": st_c,
                            "name": st_c,
                            "city": None,
                            "state": None,
                            "zone": None,
                            "latitude": 25.0,
                            "longitude": 82.0,
                            "is_major": False,
                            "platform_count": 1,
                        }
                    arr = parse_time(stop.get("arrival"))
                    dep = parse_time(stop.get("departure"))
                    schedule_params.append({
                        "train_number": t_num,
                        "sequence": stop["sequence"],
                        "station_code": st_c,
                        "scheduled_arrival": arr,
                        "scheduled_departure": dep,
                        "distance_from_source_km": stop.get("distance_km"),
                        "avg_halt_minutes": stop.get("halt_min", 2),
                        "day_offset": stop.get("day", 0),
                    })
            else:
                # Synthesize schedule with Origin and Terminus
                dep_h = dep_time.hour
                dep_m = dep_time.minute
                arr_h = (dep_h + int(dur // 60)) % 24
                arr_m = (dep_m + int(dur % 60)) % 60
                day_off = int(dur // 1440)

                schedule_params.append({
                    "train_number": t_num,
                    "sequence": 1,
                    "station_code": src,
                    "scheduled_arrival": None,
                    "scheduled_departure": dep_time,
                    "distance_from_source_km": 0.0,
                    "avg_halt_minutes": 0.0,
                    "day_offset": 0,
                })
                schedule_params.append({
                    "train_number": t_num,
                    "sequence": 2,
                    "station_code": dst,
                    "scheduled_arrival": time(arr_h, arr_m),
                    "scheduled_departure": None,
                    "distance_from_source_km": dist,
                    "avg_halt_minutes": 0.0,
                    "day_offset": day_off,
                })

        # Insert stations in batches
        stations_list = list(stations_map.values())
        batch_size = 5000
        for i in range(0, len(stations_list), batch_size):
            await db.execute(
                text("""
                    INSERT INTO stations
                        (station_code, name, city, state, zone, latitude, longitude, is_major, platform_count)
                    VALUES
                        (:station_code, :name, :city, :state, :zone, :latitude, :longitude, :is_major, :platform_count)
                    ON CONFLICT (station_code) DO NOTHING
                """),
                stations_list[i:i + batch_size]
            )
        await db.commit()
        print(f"✓ Stations: {len(stations_list)} inserted/verified")

        # Insert trains in batches
        for i in range(0, len(trains_params), batch_size):
            await db.execute(
                text("""
                    INSERT INTO trains
                        (train_number, name, train_type, zone, source_station, destination_station,
                         total_distance_km, journey_duration_min, runs_on_days, departure_time, arrival_time)
                    VALUES
                        (:train_number, :name, :train_type, :zone, :source_station, :destination_station,
                         :total_distance_km, :journey_duration_min, :runs_on_days, :departure_time, :arrival_time)
                    ON CONFLICT (train_number) DO UPDATE SET
                        source_station = EXCLUDED.source_station,
                        destination_station = EXCLUDED.destination_station,
                        total_distance_km = EXCLUDED.total_distance_km,
                        is_active = true
                """),
                trains_params[i:i + batch_size]
            )
        await db.commit()
        print(f"✓ Trains: {len(trains_params)} inserted/updated")

        # Insert schedules in batches
        for i in range(0, len(schedule_params), batch_size):
            await db.execute(
                text("""
                    INSERT INTO train_schedule
                        (train_number, sequence, station_code, scheduled_arrival, scheduled_departure,
                         distance_from_source_km, avg_halt_minutes, day_offset)
                    VALUES
                        (:train_number, :sequence, :station_code, :scheduled_arrival, :scheduled_departure,
                         :distance_from_source_km, :avg_halt_minutes, :day_offset)
                    ON CONFLICT ON CONSTRAINT uq_train_schedule DO UPDATE SET
                        station_code = EXCLUDED.station_code,
                        scheduled_arrival = EXCLUDED.scheduled_arrival,
                        scheduled_departure = EXCLUDED.scheduled_departure,
                        distance_from_source_km = EXCLUDED.distance_from_source_km
                """),
                schedule_params[i:i + batch_size]
            )
        await db.commit()
        print(f"✓ Schedule stops: {len(schedule_params)} inserted/updated")

        # ----------------------------------------------------------------
        # Seed a default admin user (idempotent)
        # ----------------------------------------------------------------
        # Import here to avoid circular imports at module level
        import sys, os
        sys.path.insert(0, str(Path(__file__).parent.parent.parent / "services" / "api"))
        
        admin_email = os.getenv("SEED_ADMIN_EMAIL", "admin@railpredict.dev")
        admin_password = os.getenv("SEED_ADMIN_PASSWORD", "ChangeMe123!")

        try:
            import bcrypt
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(admin_password.encode('utf-8'), salt).decode('utf-8')
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
