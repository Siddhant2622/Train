"""Fast-forward data generator for ML training.

Connects directly to the DB, fetches schedules, and simulates train runs
over the past 90 days. Generates a CSV dataset for XGBoost training.
"""

import asyncio
import csv
import logging
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_URL = "postgresql+asyncpg://railpredict:dev_password_change_me@postgres:5432/railpredict"
OUTPUT_FILE = "/app/ml/train_data.csv"
DAYS_TO_SIMULATE = 90
MAX_ROWS = 10000

# Physics engine logic replicated for data generation
def _travel_minutes(dist: float, speed: float) -> float:
    return (dist / max(speed, 10)) * 60.0

async def generate_data() -> None:
    engine = create_async_engine(DB_URL)
    
    # 1. Load active trains and schedules
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT train_number, name, train_type FROM trains WHERE is_active = true"))
        trains = [dict(r) for r in res.mappings()]
        
        logger.info(f"Loaded {len(trains)} trains.")
        
        dataset = []
        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=DAYS_TO_SIMULATE)
        
        for t in trains:
            tn = t["train_number"]
            s_res = await conn.execute(
                text("""
                    SELECT ts.sequence, ts.station_code, ts.distance_from_source_km, 
                           ts.avg_halt_minutes, COALESCE(sec.avg_speed_kmh, 80) as section_speed
                    FROM train_schedule ts
                    LEFT JOIN sections sec ON sec.from_station = ts.station_code
                    WHERE ts.train_number = :n
                    ORDER BY ts.sequence
                """),
                {"n": tn}
            )
            schedule = [dict(r) for r in s_res.mappings()]
            if len(schedule) < 2:
                continue
                
            # Simulate runs for each day
            for day_offset in range(DAYS_TO_SIMULATE):
                if len(dataset) >= MAX_ROWS:
                    break
                    
                run_date = start_date + timedelta(days=day_offset)
                current_delay = random.uniform(0, 15)  # initial delay
                
                for i in range(len(schedule) - 1):
                    current_stop = schedule[i]
                    next_stop = schedule[i+1]
                    
                    dist = float(next_stop["distance_from_source_km"] or 0) - float(current_stop["distance_from_source_km"] or 0)
                    dist = max(dist, 1.0)
                    speed = float(current_stop["section_speed"])
                    
                    # Physics ETA
                    physics_travel_time = _travel_minutes(dist, speed)
                    physics_delay = current_delay
                    
                    # Actual simulated travel time with stochastic events (weather, congestion, etc.)
                    event_modifier = 1.0
                    if random.random() < 0.1:  # 10% chance of a minor event
                        event_modifier = random.uniform(1.1, 1.5)
                        current_delay += random.uniform(5, 20)
                    elif random.random() < 0.02: # 2% chance of major event
                        event_modifier = random.uniform(1.5, 2.5)
                        current_delay += random.uniform(30, 90)
                    else:
                        # Natural recovery
                        recovery = min(current_delay * 0.1, 5.0)
                        current_delay = max(0, current_delay - recovery)
                        
                    actual_travel_time = _travel_minutes(dist, speed / event_modifier)
                    
                    # Features
                    target_residual = (actual_travel_time - physics_travel_time) + (current_delay - physics_delay)
                    
                    dataset.append({
                        "train_number": tn,
                        "train_type": t["train_type"] or "Express",
                        "station_code": current_stop["station_code"],
                        "distance_to_next_km": round(dist, 2),
                        "section_speed_kmh": round(speed, 1),
                        "current_delay_min": round(physics_delay, 1),
                        "time_of_day_hour": run_date.hour,
                        "day_of_week": run_date.weekday(),
                        "delay_residual": round(target_residual, 2) # TARGET
                    })
                    
        logger.info(f"Generated {len(dataset)} rows of training data.")
        
        # Save to CSV
        with open(OUTPUT_FILE, 'w', newline='') as f:
            if dataset:
                writer = csv.DictWriter(f, fieldnames=dataset[0].keys())
                writer.writeheader()
                writer.writerows(dataset)
                logger.info(f"Saved to {OUTPUT_FILE}")
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(generate_data())
