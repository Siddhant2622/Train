"""Admin router — controller/admin only endpoints."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.routers.auth import require_role
from app.schemas.admin import FleetSummary, EventCreate, EventResponse

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.get("/fleet-summary", response_model=FleetSummary)
async def fleet_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("controller", "admin")),
) -> FleetSummary:
    """Return real-time fleet KPIs — requires controller or admin role."""
    today = datetime.now(timezone.utc).date()

    row = await db.execute(
        text("""
            WITH latest AS (
                SELECT DISTINCT ON (train_number)
                    train_number, current_delay_min
                FROM train_positions
                WHERE run_date = :today
                ORDER BY train_number, time DESC
            )
            SELECT
                COUNT(*) as total_active,
                COUNT(*) FILTER (WHERE current_delay_min <= 5) as on_time,
                COUNT(*) FILTER (WHERE current_delay_min > 5 AND current_delay_min <= 30) as delayed,
                COUNT(*) FILTER (WHERE current_delay_min > 30) as severely_delayed,
                COALESCE(AVG(current_delay_min), 0) as avg_delay_min,
                COALESCE(MAX(current_delay_min), 0) as max_delay_min
            FROM latest
        """),
        {"today": today},
    )
    data = row.mappings().first()
    if not data or data["total_active"] == 0:
        return FleetSummary(
            total_active=0, on_time=0, delayed=0, severely_delayed=0,
            avg_delay_min=0, max_delay_min=0, on_time_percentage=0,
            generated_at=datetime.now(timezone.utc),
        )

    total = int(data["total_active"])
    on_time = int(data["on_time"])
    return FleetSummary(
        total_active=total,
        on_time=on_time,
        delayed=int(data["delayed"]),
        severely_delayed=int(data["severely_delayed"]),
        avg_delay_min=round(float(data["avg_delay_min"]), 1),
        max_delay_min=round(float(data["max_delay_min"]), 1),
        on_time_percentage=round((on_time / total * 100) if total else 0, 1),
        generated_at=datetime.now(timezone.utc),
    )


@router.post("/events", response_model=EventResponse, status_code=201)
async def create_event(
    body: EventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("controller", "admin")),
) -> EventResponse:
    """Inject a disruption event — controllers and admins only. Audited."""
    now = datetime.now(timezone.utc)

    # Write event
    result = await db.execute(
        text("""
            INSERT INTO events
                (event_type, station_code, severity, speed_restriction_kmh,
                 delay_impact_min, started_at, is_active, metadata, created_by)
            VALUES
                (:event_type, :station_code, :severity, :speed_restriction_kmh,
                 :delay_impact_min, :started_at, true,
                 :metadata, :created_by)
            RETURNING id
        """),
        {
            "event_type": body.event_type,
            "station_code": body.station_code,
            "severity": body.severity,
            "speed_restriction_kmh": body.speed_restriction_kmh,
            "delay_impact_min": body.delay_impact_min,
            "started_at": now,
            "metadata": {"notes": body.notes},
            "created_by": current_user.id,
        },
    )
    event_id = result.scalar()

    # Audit log
    await db.execute(
        text("""
            INSERT INTO audit_log (actor_id, actor_email, action, resource_type, resource_id, payload)
            VALUES (:actor_id, :actor_email, :action, :resource_type, :resource_id, :payload)
        """),
        {
            "actor_id": current_user.id,
            "actor_email": current_user.email,
            "action": "create_event",
            "resource_type": "event",
            "resource_id": str(event_id),
            "payload": body.model_dump(),
        },
    )
    await db.commit()

    return EventResponse(
        id=event_id,
        event_type=body.event_type,
        station_code=body.station_code,
        severity=body.severity,
        started_at=now,
        is_active=True,
        delay_impact_min=body.delay_impact_min,
    )
