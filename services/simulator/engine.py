"""Physics-informed train simulator — digital twin engine.

Each TrainRun tracks one train's journey for a given date.
The engine advances all runs every TICK_INTERVAL_SECONDS and POSTs
position pings to the ingestion API.

Physics model:
- Position is interpolated linearly between stations based on elapsed time
- Speed is capped at section max_permissible_speed with gaussian jitter (±10%)
- Delay accumulates from events; partial recovery applies at station halts
- When a train reaches its terminus, the run is marked complete

Designed so the real-feed adapter (Phase 3+) is a drop-in replacement:
it produces the same PositionPing format, posts to the same endpoint.
"""

from __future__ import annotations

import asyncio
import logging
import math
import random
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta, timezone
from typing import Any

import httpx

from events import maybe_generate_event, ActiveEvent

logger = logging.getLogger(__name__)

TICK_INTERVAL_SECONDS = 30
API_BASE = "http://api:8000"         # internal Docker network address
INTERNAL_API_KEY = ""                 # set from env at startup


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _interpolate_position(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
    fraction: float,
) -> tuple[float, float]:
    """Linear interpolation between two lat/lon points."""
    frac = max(0.0, min(1.0, fraction))
    return lat1 + (lat2 - lat1) * frac, lon1 + (lon2 - lon1) * frac


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class StationStop:
    sequence: int
    station_code: str
    station_name: str
    latitude: float
    longitude: float
    scheduled_arrival: datetime | None
    scheduled_departure: datetime | None
    distance_from_source_km: float
    avg_halt_minutes: float
    day_offset: int
    section_max_speed_kmh: float = 100.0
    section_avg_speed_kmh: float = 80.0


@dataclass
class TrainRun:
    train_number: str
    run_date: date
    stops: list[StationStop]
    current_stop_idx: int = 0          # index of the stop we just departed from
    current_delay_min: float = 0.0
    active_events: list[ActiveEvent] = field(default_factory=list)
    is_complete: bool = False
    departed_at: datetime | None = None  # actual departure time from current stop

    @property
    def last_stop(self) -> StationStop:
        return self.stops[self.current_stop_idx]

    @property
    def next_stop(self) -> StationStop | None:
        idx = self.current_stop_idx + 1
        return self.stops[idx] if idx < len(self.stops) else None

    def advance_to_next_stop(self) -> None:
        self.current_stop_idx += 1
        if self.current_stop_idx >= len(self.stops) - 1:
            self.is_complete = True


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class SimulatorEngine:
    def __init__(self, api_base: str, internal_key: str) -> None:
        self.api_base = api_base
        self.internal_key = internal_key
        self._runs: dict[str, TrainRun] = {}
        self._client: httpx.AsyncClient | None = None

    async def startup(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=self.api_base,
            headers={"X-Internal-Key": self.internal_key},
            timeout=10.0,
        )
        # Load schedule from API
        await self._load_runs()

    async def shutdown(self) -> None:
        if self._client:
            await self._client.aclose()

    async def _load_runs(self) -> None:
        """Fetch all active trains + schedules from the API and initialise runs."""
        try:
            resp = await self._client.get("/api/v1/trains?page_size=100")
            resp.raise_for_status()
            trains_data = resp.json().get("trains", [])
        except Exception as exc:
            logger.warning("Could not load trains from API: %s", exc)
            return

        today = date.today()
        for t in trains_data:
            tn = t["train_number"]
            if tn in self._runs:
                continue
            try:
                detail_resp = await self._client.get(f"/api/v1/trains/{tn}")
                detail_resp.raise_for_status()
            except Exception:
                continue

            # We need the schedule — fetch from a dedicated endpoint
            try:
                sched_resp = await self._client.get(f"/api/v1/trains/{tn}/schedule")
                sched_resp.raise_for_status()
                stops_raw = sched_resp.json().get("stops", [])
            except Exception:
                stops_raw = []

            if len(stops_raw) < 2:
                continue

            stops = [self._build_stop(s, today) for s in stops_raw]
            run = TrainRun(
                train_number=tn,
                run_date=today,
                stops=stops,
                current_delay_min=random.uniform(0, 5),   # realistic starting scatter
            )
            # Set starting position: find the stop nearest to the current time
            run.current_stop_idx = self._estimate_current_stop_idx(run)
            run.departed_at = datetime.now(timezone.utc)
            self._runs[tn] = run
            logger.info("Loaded run for %s (%s)", tn, t.get("name", ""))

        logger.info("Simulator loaded %d train runs", len(self._runs))

    def _build_stop(self, raw: dict, run_date: date) -> StationStop:
        def parse_dt(t_str: str | None, offset: int) -> datetime | None:
            if not t_str:
                return None
            try:
                h, m = int(t_str[:2]), int(t_str[3:5])
                base = datetime(run_date.year, run_date.month, run_date.day,
                                h % 24, m, tzinfo=timezone.utc)
                return base + timedelta(days=offset)
            except Exception:
                return None

        offset = raw.get("day_offset", 0)
        return StationStop(
            sequence=raw["sequence"],
            station_code=raw["station_code"],
            station_name=raw.get("station_name", raw["station_code"]),
            latitude=float(raw.get("latitude", 0)),
            longitude=float(raw.get("longitude", 0)),
            scheduled_arrival=parse_dt(raw.get("scheduled_arrival"), offset),
            scheduled_departure=parse_dt(raw.get("scheduled_departure"), offset),
            distance_from_source_km=float(raw.get("distance_from_source_km", 0)),
            avg_halt_minutes=float(raw.get("avg_halt_minutes", 2)),
            day_offset=offset,
        )

    def _estimate_current_stop_idx(self, run: TrainRun) -> int:
        """Find the stop we should be at based on the current wall-clock time."""
        now = datetime.now(timezone.utc)
        for i, stop in enumerate(run.stops[:-1]):
            dep = stop.scheduled_departure
            if dep and dep > now:
                return max(i - 1, 0)
        return max(len(run.stops) - 2, 0)

    async def tick(self) -> None:
        """Advance all runs by one tick and POST position pings."""
        now = datetime.now(timezone.utc)
        for tn, run in list(self._runs.items()):
            if run.is_complete:
                continue
            try:
                ping = self._compute_ping(run, now)
                if ping:
                    await self._post_ping(ping)
            except Exception as exc:
                logger.error("Error processing run %s: %s", tn, exc)

    def _compute_ping(self, run: TrainRun, now: datetime) -> dict | None:
        last_stop = run.last_stop
        next_stop = run.next_stop
        if next_stop is None:
            run.is_complete = True
            return None

        # Process active events
        run.active_events = [e for e in run.active_events if e.is_active]
        new_event = maybe_generate_event(now)
        if new_event:
            run.current_delay_min += new_event.delay_impact_min
            run.active_events.append(new_event)
            logger.info("Event on %s: %s (+%.1f min delay)", run.train_number,
                        new_event.event_type, new_event.delay_impact_min)

        # Initialise departure time if not set
        if run.departed_at is None:
            run.departed_at = now

        section_dist = max(next_stop.distance_from_source_km - last_stop.distance_from_source_km, 1.0)

        # Check if train is currently halted at station
        if now < run.departed_at:
            return {
                "train_number": run.train_number,
                "run_date": str(run.run_date),
                "timestamp": now.isoformat(),
                "latitude": round(last_stop.latitude, 6),
                "longitude": round(last_stop.longitude, 6),
                "speed_kmh": 0.0,
                "last_station": last_stop.station_code,
                "next_station": next_stop.station_code,
                "distance_to_next_km": round(section_dist, 2),
                "current_delay_min": round(run.current_delay_min, 1),
                "source": "simulator",
            }

        # Determine section cruising speed based on track limits & events
        max_speed = max(min(last_stop.section_max_speed_kmh, 130.0), 30.0)
        avg_speed = max(min(last_stop.section_avg_speed_kmh, max_speed), 25.0)
        target_speed_kmh = avg_speed * random.gauss(1.0, 0.03)

        for event in run.active_events:
            if event.speed_restriction_kmh:
                target_speed_kmh = min(target_speed_kmh, event.speed_restriction_kmh)
        target_speed_kmh = max(min(target_speed_kmh, max_speed), 15.0)

        # Calculate progress between stations
        elapsed_min = (now - run.departed_at).total_seconds() / 60.0
        travel_time_min = (section_dist / target_speed_kmh) * 60.0
        fraction = min(max(elapsed_min / travel_time_min, 0.0), 1.0) if travel_time_min > 0 else 1.0

        # Model realistic instantaneous speed profile (acceleration / cruise / deceleration)
        if fraction < 0.12:
            # Accelerating out of last station
            current_speed = max(10.0, target_speed_kmh * (fraction / 0.12))
        elif fraction > 0.88:
            # Decelerating on approach to next station
            current_speed = max(12.0, target_speed_kmh * ((1.0 - fraction) / 0.12))
        else:
            # Cruising at target section speed
            current_speed = target_speed_kmh

        lat, lon = _interpolate_position(
            last_stop.latitude, last_stop.longitude,
            next_stop.latitude, next_stop.longitude,
            fraction,
        )
        distance_remaining = max(0.0, section_dist * (1.0 - fraction))

        # Check if train arrived at next stop
        if fraction >= 1.0:
            # Apply partial delay recovery at stations
            recovery = min(run.current_delay_min * 0.1, 3.0)
            run.current_delay_min = max(0.0, run.current_delay_min - recovery)

            # Halt at the station
            halt_end = now + timedelta(minutes=next_stop.avg_halt_minutes)
            run.advance_to_next_stop()
            run.departed_at = halt_end

            lat, lon = next_stop.latitude, next_stop.longitude
            distance_remaining = 0.0
            current_speed = 0.0

        return {
            "train_number": run.train_number,
            "run_date": str(run.run_date),
            "timestamp": now.isoformat(),
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "speed_kmh": round(current_speed, 1),
            "last_station": run.last_stop.station_code,
            "next_station": (run.next_stop.station_code if run.next_stop else run.last_stop.station_code),
            "distance_to_next_km": round(distance_remaining, 2),
            "current_delay_min": round(run.current_delay_min, 1),
            "source": "simulator",
        }

    async def _post_ping(self, ping: dict) -> None:
        assert self._client is not None
        try:
            resp = await self._client.post("/ingest/position", json=ping)
            if resp.status_code not in (200, 202):
                logger.warning("Ingest returned %d for %s", resp.status_code, ping["train_number"])
        except httpx.ConnectError:
            logger.debug("API not yet ready — will retry next tick")
        except Exception as exc:
            logger.error("POST /ingest/position failed: %s", exc)
