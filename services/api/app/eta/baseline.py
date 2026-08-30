"""Physics-based baseline ETA engine (Layer 1 of the ensemble).

Computes expected arrival times for all upcoming stops given:
- Current position (between two stations)
- Current speed and delay
- Section speed limits and distances
- Historical halt times from the schedule

This module is intentionally stateless — it takes data and returns predictions.
The ML layers (Phase 3+) will call this and add a residual on top.

Formula per stop:
    ETA = now
        + time_to_next_station (distance/speed)
        + sum of (section_travel_time + halt_time) for each subsequent stop
        + current_delay (applied uniformly — ML layer will model recovery)

Confidence interval: ±PHYSICS_TOLERANCE * travel_time (default 15%)
This is replaced by quantile regression in Phase 3.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

PHYSICS_TOLERANCE = 0.15  # ±15% — becomes calibrated conformal interval in Phase 3
MIN_SPEED_KMPH = 10.0      # clamp so we don't divide by ~0
DEFAULT_AVG_SPEED_KMPH = 80.0


@dataclass
class StopPrediction:
    station_code: str
    station_name: str
    sequence: int
    scheduled_arrival: datetime | None
    predicted_eta: datetime
    lower_bound: datetime
    upper_bound: datetime
    confidence: float          # 0–1 calibrated coverage (physics = 0.70 until Phase 3)
    delay_at_stop_min: float   # predicted delay at this stop
    explanation: dict[str, Any]


@dataclass
class EtaResult:
    train_number: str
    run_date: str
    computed_at: datetime
    current_delay_min: float
    stops: list[StopPrediction]
    model_version: str = "physics_v1"


def _clamp_speed(speed: float | None) -> float:
    return max(speed or DEFAULT_AVG_SPEED_KMPH, MIN_SPEED_KMPH)


def _travel_minutes(distance_km: float, speed_kmph: float) -> float:
    return (distance_km / speed_kmph) * 60.0


def compute_eta(
    *,
    train_number: str,
    run_date: str,
    now: datetime,
    current_delay_min: float,
    current_speed_kmph: float | None,
    distance_to_next_km: float,
    last_station_code: str,
    next_station_code: str,
    upcoming_stops: list[dict],      # ordered list of future schedule rows including next_station
    station_lookup: dict[str, dict], # station_code → {name, latitude, longitude}
    section_speeds: dict[tuple[str, str], float],  # (from, to) → avg_speed_kmph
) -> EtaResult:
    """Compute physics-based ETAs for all remaining stops.

    Args:
        upcoming_stops: list of dicts with keys:
            sequence, station_code, scheduled_arrival (datetime|None),
            distance_from_source_km, avg_halt_minutes, day_offset
        station_lookup: station_code → {name, ...}
        section_speeds: (from_code, to_code) → avg speed kmph
    """
    result_stops: list[StopPrediction] = []
    current_time = now
    cumulative_delay = current_delay_min

    # Time to reach the very next station
    effective_speed = _clamp_speed(current_speed_kmph)
    minutes_to_next = _travel_minutes(distance_to_next_km, effective_speed)
    current_time = current_time + timedelta(minutes=minutes_to_next)

    prev_code = last_station_code

    for stop in upcoming_stops:
        code: str = stop["station_code"]
        seq: int = stop["sequence"]
        sched_arr: datetime | None = stop.get("scheduled_arrival")
        halt_min: float = float(stop.get("avg_halt_minutes", 2))
        dist_from_src: float = float(stop.get("distance_from_source_km") or 0)

        station_info = station_lookup.get(code, {})
        station_name = station_info.get("name", code)

        # Section speed (fallback to current speed then default)
        section_speed = section_speeds.get(
            (prev_code, code),
            section_speeds.get((code, prev_code), effective_speed),
        )
        section_speed = _clamp_speed(section_speed)

        # Travel time from previous stop (or current position for first stop)
        if prev_code == last_station_code:
            # Already computed minutes_to_next for the very first stop
            travel_min = minutes_to_next
        else:
            # Compute from distance difference
            prev_dist = result_stops[-1].__dict__.get("_dist_from_src", 0) if result_stops else 0
            section_dist = max(dist_from_src - prev_dist, 1.0)
            travel_min = _travel_minutes(section_dist, section_speed)

        predicted_arrival = current_time
        lower = predicted_arrival - timedelta(minutes=travel_min * PHYSICS_TOLERANCE)
        upper = predicted_arrival + timedelta(minutes=travel_min * PHYSICS_TOLERANCE)

        # Delay at this stop
        if sched_arr:
            delay_at_stop = (predicted_arrival - sched_arr).total_seconds() / 60
        else:
            delay_at_stop = cumulative_delay

        explanation = {
            "engine": "physics_v1",
            "current_delay_min": round(current_delay_min, 1),
            "travel_time_min": round(travel_min, 1),
            "section_speed_kmph": round(section_speed, 1),
            "tolerance_pct": PHYSICS_TOLERANCE * 100,
        }

        sp = StopPrediction(
            station_code=code,
            station_name=station_name,
            sequence=seq,
            scheduled_arrival=sched_arr,
            predicted_eta=predicted_arrival,
            lower_bound=lower,
            upper_bound=upper,
            confidence=0.70,  # physics model coverage (→ calibrated in Phase 3)
            delay_at_stop_min=round(delay_at_stop, 1),
            explanation=explanation,
        )
        # Store dist for next iteration
        sp.__dict__["_dist_from_src"] = dist_from_src
        result_stops.append(sp)

        # Advance time past the halt
        current_time = predicted_arrival + timedelta(minutes=halt_min)
        prev_code = code

    return EtaResult(
        train_number=train_number,
        run_date=run_date,
        computed_at=now,
        current_delay_min=current_delay_min,
        stops=result_stops,
    )
