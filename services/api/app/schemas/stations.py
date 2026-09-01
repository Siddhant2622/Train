"""Pydantic schemas for station endpoints."""

from datetime import datetime
from pydantic import BaseModel


class StationBase(BaseModel):
    station_code: str
    name: str
    city: str | None
    state: str | None
    zone: str | None
    latitude: float
    longitude: float
    is_major: bool
    platform_count: int | None


class ArrivalEntry(BaseModel):
    train_number: str
    train_name: str
    train_type: str | None
    scheduled_arrival: datetime | None
    predicted_eta: datetime | None
    delay_min: float
    status: str
    source_station: str
    destination_station: str


class StationArrivalsResponse(BaseModel):
    station_code: str
    station_name: str
    arrivals: list[ArrivalEntry]
    generated_at: datetime


class StationListResponse(BaseModel):
    stations: list[StationBase]
    total: int
    page: int
    page_size: int
