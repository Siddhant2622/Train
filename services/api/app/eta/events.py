"""Control Room Events ETA Layer (Phase 6).

This layer injects manual disruption events (e.g. station closures, track speed limits)
into the ETA predictions.
"""

from datetime import timedelta
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.models.event import Event
from app.eta.baseline import EtaResult

logger = logging.getLogger(__name__)


async def fetch_active_events(db: AsyncSession) -> List[Event]:
    """Fetch all currently active disruption events."""
    stmt = select(Event).where(Event.is_active == True)
    result = await db.execute(stmt)
    return list(result.scalars().all())


def apply_event_layer(eta_result: EtaResult, active_events: List[Event]) -> EtaResult:
    """
    Check if the train's upcoming route is affected by any active events.
    If so, inject the delay penalty and speed restrictions.
    """
    if not active_events:
        return eta_result

    # Map events by station code for quick lookup
    station_events = {e.station_code: e for e in active_events if e.station_code}
    
    total_event_delay_min = 0.0
    applied_events = []
    
    for stop in eta_result.stops:
        # If there's an event for this station, apply its delay
        event = station_events.get(stop.station_code)
        if event and event.delay_impact_min:
            delay = float(event.delay_impact_min)
            total_event_delay_min += delay
            applied_events.append(f"Event {event.id} ({event.severity}) at {event.station_code}")
            
        # Carry the accumulated event delay forward to all subsequent stops
        if total_event_delay_min > 0:
            stop.predicted_eta += timedelta(minutes=total_event_delay_min)
            stop.upper_bound += timedelta(minutes=total_event_delay_min)
            # We don't change lower bound as much because an event could be cleared
            stop.lower_bound += timedelta(minutes=total_event_delay_min * 0.5)
            stop.delay_at_stop_min += total_event_delay_min
            
            # Tag the explanation payload
            stop.explanation["control_room_event_min"] = round(total_event_delay_min, 1)
            stop.explanation["control_room_events"] = applied_events.copy()
            stop.explanation["engine"] = "events_v1"

    if total_event_delay_min > 0:
        eta_result.model_version += "+events"
        logger.debug(f"Applied {total_event_delay_min}m event delay to train {eta_result.train_number}")

    return eta_result
