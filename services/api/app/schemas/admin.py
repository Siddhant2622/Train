"""Pydantic schemas for admin endpoints."""

from datetime import datetime
from pydantic import BaseModel, Field


class FleetSummary(BaseModel):
    total_active: int
    on_time: int
    delayed: int
    severely_delayed: int
    avg_delay_min: float
    max_delay_min: float
    on_time_percentage: float
    generated_at: datetime


class EventCreate(BaseModel):
    event_type: str = Field(..., pattern="^(signal_failure|speed_restriction|weather|maintenance|track_block)$")
    station_code: str | None = None
    severity: str = Field("medium", pattern="^(low|medium|high|critical)$")
    speed_restriction_kmh: float | None = None
    delay_impact_min: float | None = None
    notes: str | None = None


class EventResponse(BaseModel):
    id: int
    event_type: str
    station_code: str | None
    severity: str
    started_at: datetime
    is_active: bool
    delay_impact_min: float | None
