"""Pydantic schemas for train endpoints."""

from datetime import datetime, date
from pydantic import BaseModel


class StopEta(BaseModel):
    station_code: str
    station_name: str
    sequence: int
    scheduled_arrival: datetime | None = None
    scheduled_departure: datetime | None = None
    predicted_eta: datetime
    lower_bound: datetime
    upper_bound: datetime
    confidence: float = 0.9
    delay_min: float = 0.0
    platform: str | None = None
    distance_km: float | None = None
    is_halt: bool = True
    status: str = "upcoming"  # "departed" | "at-station" | "arrived" | "upcoming"
    explanation: dict | None = None


class LivePosition(BaseModel):
    latitude: float | None = None
    longitude: float | None = None
    speed_kmh: float | None = None
    last_station: str | None = None
    next_station: str | None = None
    distance_to_next_km: float | None = None
    current_delay_min: float = 0.0
    updated_at: datetime
    source: str = "real_feed"
    status: str | None = None          # "running" | "at-station" | "not-started" | "completed"
    status_message: str | None = None
    distance_covered_km: float | None = None
    total_distance_km: float | None = None
    is_halted: bool = False


class TrainSummary(BaseModel):
    train_number: str
    name: str
    train_type: str | None = None
    source_station: str
    destination_station: str
    current_delay_min: float
    status: str             # "on_time" | "delayed" | "severely_delayed" | "unknown"
    latitude: float | None = None
    longitude: float | None = None
    speed_kmh: float | None = None
    next_station: str | None = None
    last_updated: datetime | None = None


class TrainDetail(BaseModel):
    train_number: str
    name: str
    train_type: str | None = None
    zone: str | None = None
    source_station: str
    destination_station: str
    total_distance_km: float | None = None
    run_date: date | None = None
    position: LivePosition | None = None
    upcoming_stops: list[StopEta] = []
    model_version: str = "railradar_live_v1"
    coach_position: str | None = None
    status: str | None = "running"
    total_halts: int | None = None
    avg_speed_kmh: float | None = None


class TrainListResponse(BaseModel):
    trains: list[TrainSummary]
    total: int
    page: int
    page_size: int
