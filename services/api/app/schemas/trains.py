"""Pydantic schemas for train endpoints."""

from datetime import datetime, date
from pydantic import BaseModel


class StopEta(BaseModel):
    station_code: str
    station_name: str
    sequence: int
    scheduled_arrival: datetime | None
    predicted_eta: datetime
    lower_bound: datetime
    upper_bound: datetime
    confidence: float
    delay_min: float


class LivePosition(BaseModel):
    latitude: float | None
    longitude: float | None
    speed_kmh: float | None
    last_station: str | None
    next_station: str | None
    distance_to_next_km: float | None
    current_delay_min: float
    updated_at: datetime
    source: str


class TrainSummary(BaseModel):
    train_number: str
    name: str
    train_type: str | None
    source_station: str
    destination_station: str
    current_delay_min: float
    status: str             # "on_time" | "delayed" | "severely_delayed" | "unknown"
    latitude: float | None
    longitude: float | None
    next_station: str | None
    last_updated: datetime | None


class TrainDetail(BaseModel):
    train_number: str
    name: str
    train_type: str | None
    zone: str | None
    source_station: str
    destination_station: str
    total_distance_km: float | None
    run_date: date | None
    position: LivePosition | None
    upcoming_stops: list[StopEta]
    model_version: str


class TrainListResponse(BaseModel):
    trains: list[TrainSummary]
    total: int
    page: int
    page_size: int
