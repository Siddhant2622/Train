"""Disruption events that the simulator can inject into train runs.

Events are loaded from the DB (active events table) or can be triggered
programmatically. In Phase 6, the admin UI will call POST /api/v1/admin/events
and the simulator picks them up on the next tick.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class EventType(str, Enum):
    SIGNAL_FAILURE = "signal_failure"
    SPEED_RESTRICTION = "speed_restriction"
    UNSCHEDULED_HALT = "unscheduled_halt"
    WEATHER_DELAY = "weather"
    CONGESTION = "congestion"
    MAINTENANCE = "maintenance"


@dataclass
class ActiveEvent:
    event_type: EventType
    station_code: str | None
    severity: str  # low | medium | high | critical
    speed_restriction_kmh: float | None
    delay_impact_min: float
    started_at: datetime
    ended_at: datetime | None = None

    @property
    def is_active(self) -> bool:
        if self.ended_at is None:
            return True
        return datetime.utcnow() < self.ended_at.replace(tzinfo=None)


# ---------------------------------------------------------------------------
# Stochastic event generation for the simulator
# ---------------------------------------------------------------------------

# Probability per tick (30s) of a random event occurring per train
EVENT_PROBABILITY_PER_TICK = 0.003   # ~0.3% per tick ≈ 1 event every ~50 minutes per train

EVENT_TEMPLATES = [
    {
        "event_type": EventType.SIGNAL_FAILURE,
        "severity": "medium",
        "speed_restriction_kmh": None,
        "delay_min_range": (5, 25),
        "duration_min_range": (10, 45),
        "weight": 20,
    },
    {
        "event_type": EventType.SPEED_RESTRICTION,
        "severity": "low",
        "speed_restriction_kmh": 40,
        "delay_min_range": (3, 15),
        "duration_min_range": (15, 60),
        "weight": 30,
    },
    {
        "event_type": EventType.UNSCHEDULED_HALT,
        "severity": "low",
        "speed_restriction_kmh": None,
        "delay_min_range": (2, 10),
        "duration_min_range": (5, 20),
        "weight": 25,
    },
    {
        "event_type": EventType.CONGESTION,
        "severity": "medium",
        "speed_restriction_kmh": 60,
        "delay_min_range": (5, 20),
        "duration_min_range": (20, 60),
        "weight": 20,
    },
    {
        "event_type": EventType.MAINTENANCE,
        "severity": "high",
        "speed_restriction_kmh": 30,
        "delay_min_range": (15, 45),
        "duration_min_range": (30, 120),
        "weight": 5,
    },
]

_weights = [t["weight"] for t in EVENT_TEMPLATES]


def maybe_generate_event(now: datetime) -> ActiveEvent | None:
    """Roll the dice — return a new event or None."""
    if random.random() > EVENT_PROBABILITY_PER_TICK:
        return None

    template = random.choices(EVENT_TEMPLATES, weights=_weights, k=1)[0]
    delay = random.uniform(*template["delay_min_range"])
    duration = random.uniform(*template["duration_min_range"])

    from datetime import timedelta
    return ActiveEvent(
        event_type=template["event_type"],
        station_code=None,
        severity=template["severity"],
        speed_restriction_kmh=template["speed_restriction_kmh"],
        delay_impact_min=round(delay, 1),
        started_at=now,
        ended_at=now + timedelta(minutes=duration),
    )
