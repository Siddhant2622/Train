"""Delay Propagation Engine (Phase 5).

This module handles the cross-train delay cascade logic.
When a train experiences a significant delay, we detect other active trains
that share the same upcoming sections and propagate a delay penalty to them.
"""

import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import Any

from app.models.propagation import Propagation
from app.models.train_position import TrainPosition
from app.eta.baseline import EtaResult

logger = logging.getLogger(__name__)

PROPAGATION_THRESHOLD_MIN = 10.0


async def detect_propagation(
    db: AsyncSession,
    cause_train: str,
    current_delay_min: float,
    next_station: str,
    now: datetime
) -> None:
    """
    Detect if the current train's delay will cascade to other trains.
    Uses a simple 1-step lookahead heuristic: if cause_train is delayed by > 10m,
    any other train currently targeting the same `next_station` gets a cascade penalty.
    """
    if current_delay_min < PROPAGATION_THRESHOLD_MIN:
        # If train has recovered, we might want to resolve active propagations,
        # but for simplicity in this phase, we'll just not create new ones.
        return
        
    # Find other active trains heading to the same next station
    stmt = select(TrainPosition).where(
        TrainPosition.train_number != cause_train,
        TrainPosition.next_station == next_station
    )
    result = await db.execute(stmt)
    affected_positions = result.scalars().all()
    
    for pos in affected_positions:
        # Check if we already have an active propagation for this pair
        check_stmt = select(Propagation).where(
            Propagation.cause_train == cause_train,
            Propagation.affected_train == pos.train_number,
            Propagation.resolved_at.is_(None)
        )
        existing = (await db.execute(check_stmt)).scalars().first()
        
        if existing:
            # Update the estimated impact if the delay got worse
            if current_delay_min * 0.5 > float(existing.estimated_impact_min or 0):
                existing.estimated_impact_min = current_delay_min * 0.5
        else:
            # Create a new propagation event
            # We assume a 50% delay transfer for the heuristic
            impact = current_delay_min * 0.5
            new_prop = Propagation(
                cause_train=cause_train,
                affected_train=pos.train_number,
                estimated_impact_min=impact,
                detected_at=now,
            )
            db.add(new_prop)
            logger.info(f"Propagation detected: {cause_train} delaying {pos.train_number} by {impact:.1f}m at {next_station}")
            
    await db.commit()


async def apply_propagation_layer(
    db: AsyncSession,
    eta_result: EtaResult
) -> EtaResult:
    """
    Check if the current train is affected by any active propagations,
    and apply the cascaded delay penalty to the ETA predictions.
    """
    train_number = eta_result.train_number
    
    # Query active propagations where this train is the affected one
    stmt = select(Propagation).where(
        Propagation.affected_train == train_number,
        Propagation.resolved_at.is_(None)
    )
    result = await db.execute(stmt)
    active_props = result.scalars().all()
    
    if not active_props:
        return eta_result
        
    total_cascade_min = sum(float(p.estimated_impact_min or 0) for p in active_props)
    causes = [p.cause_train for p in active_props]
    
    if total_cascade_min <= 0:
        return eta_result
        
    # Apply the cascade penalty to the ETA bounds
    for stop in eta_result.stops:
        stop.predicted_eta += timedelta(minutes=total_cascade_min)
        stop.lower_bound += timedelta(minutes=total_cascade_min)
        stop.upper_bound += timedelta(minutes=total_cascade_min)
        stop.delay_at_stop_min += total_cascade_min
        
        stop.explanation["network_cascade_min"] = round(total_cascade_min, 1)
        stop.explanation["cascade_causes"] = causes
        stop.explanation["engine"] = "propagation_v1"
        
    eta_result.model_version += "+propagation"
    
    return eta_result
