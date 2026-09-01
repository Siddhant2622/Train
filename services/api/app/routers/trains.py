"""Trains REST Router — public read and live telemetry endpoints."""
import json
import logging
import os
import time
import httpx
from datetime import datetime, timezone, date as date_type, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.trains import TrainDetail, TrainListResponse, TrainSummary, LivePosition, StopEta
from app.core.rate_limit import limiter
from app.realtime.manager import manager
from app.eta.timing_engine import calculate_comprehensive_timings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/trains", tags=["trains"])

RAILRADAR_API_KEY = os.getenv("RAILRADAR_API_KEY", "rg_34e07a358bde431c8be60a796a7edd89")
RAPIDAPI_KEYS = [k.strip() for k in os.getenv("RAPIDAPI_KEYS", "").split(",") if k.strip()]

# In-memory short-lived cache for external API responses: {train_number: (timestamp, data_dict, source_type)}
_LIVE_DATA_CACHE: dict[str, tuple[float, dict, str]] = {}
CACHE_TTL_SECONDS = 45.0


def _delay_status(delay_min: float) -> str:
    if delay_min <= 5:
        return "on_time"
    if delay_min <= 30:
        return "delayed"
    return "severely_delayed"


def _parse_iso_time(val: str | None) -> datetime | None:
    if not val:
        return None
    try:
        # Handle ISO strings like 2026-09-01T17:00:00+05:30
        dt = datetime.fromisoformat(val)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _combine_scheduled(run_date: date_type, t, day_offset: int = 0) -> datetime | None:
    if t is None:
        return None
    try:
        if isinstance(t, str):
            parts = t.split(":")
            h, m = int(parts[0]), int(parts[1])
        else:
            h, m = t.hour, t.minute
        base = datetime(run_date.year, run_date.month, run_date.day, h, m, 0, tzinfo=timezone.utc)
        return base + timedelta(days=day_offset or 0)
    except Exception:
        return None


async def fetch_railradar_live(client: httpx.AsyncClient, train_number: str) -> dict | None:
    """Fetch real-time live train running status from RailRadar."""
    if not RAILRADAR_API_KEY:
        return None
    try:
        url = f"https://api.railradar.in/v1/trains/{train_number}/live"
        headers = {"Authorization": f"Bearer {RAILRADAR_API_KEY}"}
        resp = await client.get(url, headers=headers, timeout=8.0)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("success") and data.get("data"):
                return data["data"]
        else:
            logger.debug(f"RailRadar returned status {resp.status_code} for train {train_number}")
    except Exception as e:
        logger.debug(f"RailRadar error for {train_number}: {e}")
    return None


async def fetch_rapidapi_live(client: httpx.AsyncClient, train_number: str) -> dict | None:
    """Fallback: Fetch real-time live train status from RapidAPI IRCTC."""
    if not RAPIDAPI_KEYS:
        return None
    for key in RAPIDAPI_KEYS:
        for start_day in (0, 1):
            try:
                url = f"https://irctc1.p.rapidapi.com/api/v1/liveTrainStatus?trainNo={train_number}&startDay={start_day}"
                headers = {
                    "X-RapidAPI-Key": key,
                    "X-RapidAPI-Host": "irctc1.p.rapidapi.com"
                }
                resp = await client.get(url, headers=headers, timeout=8.0)
                if resp.status_code == 200:
                    data = resp.json()
                    d = data.get("data")
                    if d and (d.get("success") or d.get("train_number")):
                        return d
                elif resp.status_code in (403, 429):
                    break
            except Exception as e:
                logger.debug(f"RapidAPI IRCTC error with key {key[:6]}...: {e}")
    return None


async def get_live_train_feed(train_number: str) -> tuple[dict | None, str | None]:
    """Fetch live train data using cached or live API (Tier 1: RailRadar, Tier 2: RapidAPI)."""
    now = time.time()
    if train_number in _LIVE_DATA_CACHE:
        ts, cached_data, src = _LIVE_DATA_CACHE[train_number]
        if now - ts < CACHE_TTL_SECONDS:
            return cached_data, src

    async with httpx.AsyncClient(timeout=10.0) as client:
        # 1. RailRadar (Tier 1)
        rr_data = await fetch_railradar_live(client, train_number)
        if rr_data:
            _LIVE_DATA_CACHE[train_number] = (now, rr_data, "railradar")
            return rr_data, "railradar"

        # 2. RapidAPI (Tier 2)
        rapid_data = await fetch_rapidapi_live(client, train_number)
        if rapid_data:
            _LIVE_DATA_CACHE[train_number] = (now, rapid_data, "rapidapi")
            return rapid_data, "rapidapi"

    return None, None


@router.get("", response_model=TrainListResponse)
@limiter.limit("60/minute")
async def list_trains(
    request: Request,
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, pattern="^(on_time|delayed|severely_delayed)$"),
    zone: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> TrainListResponse:
    """Return all trains with their latest live position and delay status."""
    today = datetime.now(timezone.utc).date()
    offset = (page - 1) * page_size
    search_term = f"%{q}%" if q else None

    # Latest position per train for today's run
    rows = await db.execute(
        text("""
            WITH latest AS (
                SELECT DISTINCT ON (train_number)
                    train_number, latitude, longitude, speed_kmh, current_delay_min,
                    next_station, last_station, time as updated_at
                FROM train_positions
                WHERE run_date = :today
                ORDER BY train_number, time DESC
            )
            SELECT t.train_number, t.name, t.train_type, t.zone,
                   t.source_station, t.destination_station,
                   COALESCE(l.current_delay_min, 0) as current_delay_min,
                   l.latitude, l.longitude, l.speed_kmh, l.next_station, l.updated_at
            FROM trains t
            LEFT JOIN latest l ON t.train_number = l.train_number
            WHERE t.is_active = true
              AND (CAST(:zone AS VARCHAR) IS NULL OR t.zone = CAST(:zone AS VARCHAR))
              AND (CAST(:q AS VARCHAR) IS NULL OR t.train_number ILIKE CAST(:q AS VARCHAR) OR t.name ILIKE CAST(:q AS VARCHAR))
            ORDER BY COALESCE(l.current_delay_min, 0) DESC
            LIMIT :limit OFFSET :offset
        """),
        {"today": today, "zone": zone, "q": search_term, "limit": page_size, "offset": offset},
    )
    train_rows = rows.mappings().all()

    count_row = await db.execute(
        text("""
            SELECT count(*) FROM trains 
            WHERE is_active = true 
            AND (CAST(:zone AS VARCHAR) IS NULL OR zone = CAST(:zone AS VARCHAR))
            AND (CAST(:q AS VARCHAR) IS NULL OR train_number ILIKE CAST(:q AS VARCHAR) OR name ILIKE CAST(:q AS VARCHAR))
        """),
        {"zone": zone, "q": search_term},
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
            speed_kmh=float(r["speed_kmh"]) if r["speed_kmh"] is not None else None,
            next_station=r["next_station"],
            last_updated=r["updated_at"],
        )
        for r in train_rows
    ]

    if status:
        trains = [t for t in trains if t.status == status]

    return TrainListResponse(trains=trains, total=total, page=page, page_size=page_size)


@router.get("/{train_number}", response_model=TrainDetail)
@limiter.limit("120/minute")
async def get_train(
    request: Request,
    train_number: str,
    db: AsyncSession = Depends(get_db),
) -> TrainDetail:
    """Return full detail for a train — live real-time GPS position, platforms, and upcoming ETAs."""
    today = datetime.now(timezone.utc).date()
    now_utc = datetime.now(timezone.utc)

    # 1. Fetch from database or prepare placeholder
    train_row = await db.execute(
        text("SELECT * FROM trains WHERE train_number = :n"),
        {"n": train_number},
    )
    train = train_row.mappings().first()
    if not train:
        await db.execute(
            text("""
                INSERT INTO trains (train_number, name, train_type, zone, source_station, destination_station, is_active)
                VALUES (:n, :name, 'Express', 'NR', 'NDLS', 'HWH', true)
                ON CONFLICT (train_number) DO NOTHING
            """),
            {"n": train_number, "name": f"Train {train_number}"}
        )
        await db.commit()
        train_row = await db.execute(
            text("SELECT * FROM trains WHERE train_number = :n"),
            {"n": train_number},
        )
        train = train_row.mappings().first()

    # 2. Check cached live position age
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

    is_stale = True
    if pos:
        age_seconds = (now_utc - pos["time"]).total_seconds()
        if age_seconds < 45:
            is_stale = False

    live_feed_data, feed_source = await get_live_train_feed(train_number)

    # 3. Process Live Data if available
    if live_feed_data:
        try:
            if feed_source == "railradar":
                train_meta = live_feed_data.get("train", {})
                real_name = train_meta.get("name") or live_feed_data.get("trainName")
                src_obj = train_meta.get("source") or {}
                dst_obj = train_meta.get("destination") or {}
                real_src = str(src_obj.get("code") or train["source_station"] or "NDLS")[:10]
                real_dst = str(dst_obj.get("code") or train["destination_station"] or "HWH")[:10]
                total_dist = float(train_meta.get("distance") or train["total_distance_km"] or 500.0)
                train_type = train_meta.get("type") or "Express"
                coach_pos = train_meta.get("coachPosition")
                avg_speed = float(train_meta.get("avgSpeed") or 80.0)
                running_status = live_feed_data.get("status") or "running"
                delay_min = float(live_feed_data.get("delayMinutes") or 0.0)
                
                # First ensure source and destination stations exist in stations table (satisfies FK constraint)
                await db.execute(
                    text("""
                        INSERT INTO stations (station_code, name, latitude, longitude, is_major)
                        VALUES 
                            (:src, :src_name, :src_lat, :src_lon, true),
                            (:dst, :dst_name, :dst_lat, :dst_lon, true)
                        ON CONFLICT (station_code) DO NOTHING
                    """),
                    {
                        "src": real_src,
                        "src_name": src_obj.get("name") or real_src,
                        "src_lat": float(src_obj.get("lat") or 28.6419),
                        "src_lon": float(src_obj.get("lng") or 77.2217),
                        "dst": real_dst,
                        "dst_name": dst_obj.get("name") or real_dst,
                        "dst_lat": float(dst_obj.get("lat") or 28.6419),
                        "dst_lon": float(dst_obj.get("lng") or 77.2217),
                    }
                )

                # Update train record
                await db.execute(
                    text("""
                        UPDATE trains SET 
                            name = COALESCE(:name, name),
                            train_type = :ttype,
                            source_station = :src,
                            destination_station = :dst,
                            total_distance_km = :dist
                        WHERE train_number = :n
                    """),
                    {"n": train_number, "name": real_name, "ttype": train_type, "src": real_src, "dst": real_dst, "dist": total_dist}
                )

                # Process Route & Station coordinates
                route_items = live_feed_data.get("route", [])
                halt_items = [r for r in route_items if r.get("isHalt")]
                if not halt_items:
                    halt_items = route_items[:2]

                cur_loc = live_feed_data.get("currentLocation") or {}
                last_stn = cur_loc.get("stationCode") or real_src
                cur_seq = cur_loc.get("sequence") or 1
                loc_status = cur_loc.get("status") or "departed"
                is_halted = loc_status == "at-station" or running_status == "not-started"

                # Find next station in route
                next_stn = real_dst
                next_st_code = None
                for r_item in route_items:
                    if r_item.get("sequence") == cur_seq + 1:
                        next_st_code = r_item.get("stationCode")
                        break
                
                next_halt_obj = live_feed_data.get("nextHalt") or {}
                if next_halt_obj.get("stationCode"):
                    next_stn = next_halt_obj["stationCode"]

                relevant_codes = list(set(
                    [r.get("stationCode") for r in halt_items if r.get("stationCode")] +
                    [last_stn, next_st_code, next_stn, real_src, real_dst]
                ))
                relevant_codes = [c for c in relevant_codes if c]

                st_coords = {}
                if relevant_codes:
                    st_coord_q = await db.execute(
                        text("SELECT station_code, latitude, longitude FROM stations WHERE station_code = ANY(:codes)"),
                        {"codes": relevant_codes}
                    )
                    st_coords = {r["station_code"]: (float(r["latitude"]), float(r["longitude"])) for r in st_coord_q.mappings().all() if r["latitude"]}

                # If source or destination not in DB, insert with RailRadar coordinates
                if src_obj.get("code") and src_obj.get("lat") and src_obj["code"] not in st_coords:
                    await db.execute(
                        text("""
                            INSERT INTO stations (station_code, name, latitude, longitude, is_major)
                            VALUES (:c, :name, :lat, :lon, true)
                            ON CONFLICT (station_code) DO NOTHING
                        """),
                        {"c": src_obj["code"], "name": src_obj.get("name") or src_obj["code"], "lat": float(src_obj["lat"]), "lon": float(src_obj["lng"])}
                    )
                    st_coords[src_obj["code"]] = (float(src_obj["lat"]), float(src_obj["lng"]))

                if dst_obj.get("code") and dst_obj.get("lat") and dst_obj["code"] not in st_coords:
                    await db.execute(
                        text("""
                            INSERT INTO stations (station_code, name, latitude, longitude, is_major)
                            VALUES (:c, :name, :lat, :lon, true)
                            ON CONFLICT (station_code) DO NOTHING
                        """),
                        {"c": dst_obj["code"], "name": dst_obj.get("name") or dst_obj["code"], "lat": float(dst_obj["lat"]), "lon": float(dst_obj["lng"])}
                    )
                    st_coords[dst_obj["code"]] = (float(dst_obj["lat"]), float(dst_obj["lng"]))

                # Batch Ingest Scheduled Halts & Stations
                halt_items = [r for r in route_items if r.get("isHalt")]
                if not halt_items:
                    halt_items = route_items[:2]

                st_records = []
                sched_records = []
                seq_idx = 1

                for r_item in halt_items:
                    sc = str(r_item.get("stationCode") or "")[:10]
                    if not sc:
                        continue
                    sn = r_item.get("stationName") or sc
                    dist_km = float(r_item.get("distance") or 0.0)
                    lat_val, lng_val = st_coords.get(sc, (28.6419, 77.2217))
                    
                    st_records.append({"c": sc, "name": sn, "lat": lat_val, "lon": lng_val, "is_m": True})

                    sched_arr = _parse_iso_time(r_item.get("scheduledArrival"))
                    sched_dep = _parse_iso_time(r_item.get("scheduledDeparture"))
                    arr_time = sched_arr.time() if sched_arr else None
                    dep_time = sched_dep.time() if sched_dep else None
                    day_off = int(r_item.get("arrivalDay") or r_item.get("departureDay") or 1) - 1

                    sched_records.append({
                        "n": train_number,
                        "seq": seq_idx,
                        "c": sc,
                        "arr": arr_time,
                        "dep": dep_time,
                        "dist": dist_km,
                        "halt": 2.0,
                        "day": max(0, day_off)
                    })
                    seq_idx += 1

                if st_records:
                    await db.execute(
                        text("""
                            INSERT INTO stations (station_code, name, latitude, longitude, is_major)
                            VALUES (:c, :name, :lat, :lon, :is_m)
                            ON CONFLICT (station_code) DO NOTHING
                        """),
                        st_records
                    )

                if sched_records:
                    await db.execute(
                        text("""
                            INSERT INTO train_schedule
                                (train_number, sequence, station_code, scheduled_arrival, scheduled_departure,
                                 distance_from_source_km, avg_halt_minutes, day_offset)
                            VALUES
                                (:n, :seq, :c, :arr, :dep, :dist, :halt, :day)
                            ON CONFLICT ON CONSTRAINT uq_train_schedule DO UPDATE SET
                                station_code = EXCLUDED.station_code,
                                scheduled_arrival = EXCLUDED.scheduled_arrival,
                                scheduled_departure = EXCLUDED.scheduled_departure,
                                distance_from_source_km = EXCLUDED.distance_from_source_km,
                                day_offset = EXCLUDED.day_offset
                        """),
                        sched_records
                    )

                await db.commit()

                # Calculate Current Telemetry
                cur_loc = live_feed_data.get("currentLocation") or {}
                last_stn = cur_loc.get("stationCode") or real_src
                cur_seq = cur_loc.get("sequence") or 1
                loc_status = cur_loc.get("status") or "departed"
                is_halted = loc_status == "at-station" or running_status == "not-started"

                # Find next station in route
                next_stn = real_dst
                next_dist = 30.0
                next_st_code = None
                for r_item in route_items:
                    if r_item.get("sequence") == cur_seq + 1:
                        next_st_code = r_item.get("stationCode")
                        break
                
                next_halt_obj = live_feed_data.get("nextHalt") or {}
                if next_halt_obj.get("stationCode"):
                    next_stn = next_halt_obj["stationCode"]
                    next_dist = float(next_halt_obj.get("distance") or 30.0) - float(cur_loc.get("distanceFromOriginKm") or 0.0)
                    next_dist = max(1.0, next_dist)

                # Sub-kilometer GPS coordinate interpolation
                cur_coords = st_coords.get(last_stn)
                next_coords = st_coords.get(next_st_code) or st_coords.get(next_stn)
                
                if cur_coords and next_coords and loc_status == "departed":
                    prog = float(cur_loc.get("segmentProgress") or 0.2)
                    cur_lat = cur_coords[0] + (next_coords[0] - cur_coords[0]) * prog
                    cur_lng = cur_coords[1] + (next_coords[1] - cur_coords[1]) * prog
                elif cur_coords:
                    cur_lat, cur_lng = cur_coords
                else:
                    cur_lat, cur_lng = 28.6419, 77.2217

                speed_val = 0.0 if is_halted else round(avg_speed, 1)

                # Direct Ingestion to train_positions
                await db.execute(
                    text("""
                        INSERT INTO train_positions
                            (time, train_number, run_date, latitude, longitude, speed_kmh,
                             heading_deg, last_station, next_station, distance_to_next_km,
                             current_delay_min, source)
                        VALUES
                            (:time, :train_number, :run_date, :latitude, :longitude, :speed_kmh,
                             0.0, :last_station, :next_station, :distance_to_next_km,
                             :current_delay_min, 'railradar_live')
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "time": now_utc,
                        "train_number": train_number,
                        "run_date": today,
                        "latitude": round(cur_lat, 6),
                        "longitude": round(cur_lng, 6),
                        "speed_kmh": speed_val,
                        "last_station": last_stn,
                        "next_station": next_stn,
                        "distance_to_next_km": round(next_dist, 1),
                        "current_delay_min": round(delay_min, 1),
                    }
                )
                await db.commit()

                # Broadcast live position to connected WebSockets
                ping_payload = {
                    "train_number": train_number,
                    "latitude": round(cur_lat, 6),
                    "longitude": round(cur_lng, 6),
                    "speed_kmh": speed_val,
                    "last_station": last_stn,
                    "next_station": next_stn,
                    "distance_to_next_km": round(next_dist, 1),
                    "current_delay_min": round(delay_min, 1),
                    "timestamp": now_utc.isoformat(),
                    "source": "railradar_live"
                }
                await manager.publish(train_number, ping_payload)

            elif feed_source == "rapidapi":
                # Fallback to RapidAPI parsing
                real_name = live_feed_data.get("train_name")
                real_src = str(live_feed_data.get("source") or train["source_station"] or "NDLS")[:10]
                real_dst = str(live_feed_data.get("destination") or train["destination_station"] or "HWH")[:10]
                total_dist = float(live_feed_data.get("total_distance") or train["total_distance_km"] or 450.0)
                delay_min = float(live_feed_data.get("delay") or 0.0)
                cur_lat = float(live_feed_data.get("cur_stn_lat") or 28.6)
                cur_lng = float(live_feed_data.get("cur_stn_lng") or 77.2)
                last_stn = str(live_feed_data.get("current_station_code") or real_src)[:10]
                next_stn = real_dst
                next_dist = 40.0
                is_halted = bool(live_feed_data.get("at_src") or live_feed_data.get("at_dstn") or (live_feed_data.get("halt", 0) > 0))
                speed_val = 0.0 if is_halted else 80.0

                await db.execute(
                    text("""
                        INSERT INTO train_positions
                            (time, train_number, run_date, latitude, longitude, speed_kmh,
                             heading_deg, last_station, next_station, distance_to_next_km,
                             current_delay_min, source)
                        VALUES
                            (:time, :train_number, :run_date, :latitude, :longitude, :speed_kmh,
                             0.0, :last_station, :next_station, :distance_to_next_km,
                             :current_delay_min, 'rapidapi_live')
                        ON CONFLICT DO NOTHING
                    """),
                    {
                        "time": now_utc,
                        "train_number": train_number,
                        "run_date": today,
                        "latitude": round(cur_lat, 6),
                        "longitude": round(cur_lng, 6),
                        "speed_kmh": speed_val,
                        "last_station": last_stn,
                        "next_station": next_stn,
                        "distance_to_next_km": round(next_dist, 1),
                        "current_delay_min": round(delay_min, 1),
                    }
                )
                await db.commit()

        except Exception as e:
            logger.warning(f"Error persisting live feed telemetry for {train_number}: {e}", exc_info=True)

    # 4. Fetch latest position from DB
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

    # If position is still empty, bootstrap from schedule/stations
    if not pos:
        src = train["source_station"] or "NDLS"
        dst = train["destination_station"] or "HWH"
        st_q = await db.execute(
            text("SELECT latitude, longitude FROM stations WHERE station_code = :c"),
            {"c": src}
        )
        st_row = st_q.mappings().first()
        lat = float(st_row["latitude"]) if st_row and st_row["latitude"] else 28.6419
        lng = float(st_row["longitude"]) if st_row and st_row["longitude"] else 77.2217
        
        await db.execute(
            text("""
                INSERT INTO train_positions
                    (time, train_number, run_date, latitude, longitude, speed_kmh,
                     heading_deg, last_station, next_station, distance_to_next_km,
                     current_delay_min, source)
                VALUES
                    (:time, :train_number, :run_date, :latitude, :longitude, 0.0,
                     0.0, :last_station, :next_station, 50.0,
                     0.0, 'bootstrap')
                ON CONFLICT DO NOTHING
            """),
            {
                "time": now_utc,
                "train_number": train_number,
                "run_date": today,
                "latitude": lat,
                "longitude": lng,
                "last_station": src,
                "next_station": dst,
            }
        )
        await db.commit()

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
            speed_kmh=float(pos["speed_kmh"]) if pos["speed_kmh"] is not None else 0.0,
            last_station=pos["last_station"],
            next_station=pos["next_station"],
            distance_to_next_km=float(pos["distance_to_next_km"]) if pos["distance_to_next_km"] is not None else None,
            current_delay_min=float(pos["current_delay_min"]),
            updated_at=pos["time"],
            source=pos["source"],
            status="running" if (pos["speed_kmh"] or 0) > 2 else "at-station",
            status_message=f"Current delay: {int(pos['current_delay_min'])} mins" if pos["current_delay_min"] > 0 else "Operating on schedule",
            is_halted=(pos["speed_kmh"] or 0) <= 2,
        )

    # 5. Build Stop Itinerary with Comprehensive Multi-Factor Timing Engine
    sched_rows = await db.execute(
        text("""
            SELECT ts.sequence, ts.station_code, s.name as station_name,
                   ts.scheduled_arrival, ts.scheduled_departure,
                   ts.distance_from_source_km, ts.avg_halt_minutes, ts.day_offset
            FROM train_schedule ts
            JOIN stations s ON ts.station_code = s.station_code
            WHERE ts.train_number = :n
            ORDER BY ts.sequence
        """),
        {"n": train_number}
    )
    db_sched_all = [
        {
            "sequence": s["sequence"],
            "station_code": s["station_code"],
            "station_name": s["station_name"],
            "scheduled_arrival_dt": _combine_scheduled(today, s["scheduled_arrival"], s.get("day_offset", 0)),
            "scheduled_departure_dt": _combine_scheduled(today, s["scheduled_departure"], s.get("day_offset", 0)),
            "distance_from_source_km": float(s["distance_from_source_km"] or 0.0),
            "avg_halt_minutes": float(s["avg_halt_minutes"] or 2.0),
        }
        for s in sched_rows.mappings().all()
    ]

    upcoming_stops = calculate_comprehensive_timings(
        train_number=train_number,
        train_name=train["name"],
        train_type=train["train_type"],
        source_station=train["source_station"],
        destination_station=train["destination_station"],
        total_distance_km=float(train["total_distance_km"]) if train["total_distance_km"] else None,
        run_date=today,
        now_utc=now_utc,
        live_position=position,
        live_feed_data=live_feed_data,
        feed_source=feed_source,
        db_schedule_stops=db_sched_all,
    )

    # Re-fetch train to get updated metadata
    train_row = await db.execute(
        text("SELECT * FROM trains WHERE train_number = :n"),
        {"n": train_number},
    )
    train = train_row.mappings().first()

    coach_pos = None
    total_halts = len(upcoming_stops) if upcoming_stops else None
    avg_speed = 82.0
    status_str = "running"
    if live_feed_data and feed_source == "railradar":
        coach_pos = live_feed_data.get("train", {}).get("coachPosition")
        avg_speed = float(live_feed_data.get("train", {}).get("avgSpeed") or 82.0)
        status_str = live_feed_data.get("status") or "running"

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
        model_version="railradar_live_v1" if feed_source == "railradar" else "physics_v1",
        coach_position=coach_pos,
        status=status_str,
        total_halts=total_halts,
        avg_speed_kmh=avg_speed,
    )


@router.get("/{train_number}/history")
@limiter.limit("60/minute")
async def get_train_history(
    request: Request,
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
