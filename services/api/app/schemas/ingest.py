"""Pydantic schemas for the ingestion endpoint (internal service communication)."""

from datetime import datetime, date
from pydantic import BaseModel, Field


class PositionPing(BaseModel):
    """A single real-time position update from the simulator or real feed adapter.
    
    This is the contract between any data source (simulator, real feed, manual entry)
    and the ingestion endpoint. Nothing downstream cares where the ping came from.
    """
    train_number: str = Field(..., min_length=4, max_length=10)
    run_date: date
    timestamp: datetime
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    speed_kmh: float = Field(..., ge=0, le=200)
    heading_deg: float | None = Field(None, ge=0, le=360)
    last_station: str = Field(..., max_length=10)
    next_station: str = Field(..., max_length=10)
    distance_to_next_km: float = Field(..., ge=0)
    current_delay_min: float = Field(0.0, ge=-60, le=600)
    source: str = Field("simulator", pattern="^(simulator|real_feed|manual)$")


class IngestResponse(BaseModel):
    status: str = "accepted"
    train_number: str
    timestamp: datetime
    predictions_computed: int
