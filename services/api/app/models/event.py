from datetime import datetime
from sqlalchemy import BigInteger, String, Numeric, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    section_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("sections.id"), nullable=True)
    station_code: Mapped[str | None] = mapped_column(String(10), ForeignKey("stations.station_code"), nullable=True)
    severity: Mapped[str] = mapped_column(String(10), server_default="medium")
    speed_restriction_kmh: Mapped[float | None] = mapped_column(Numeric(), nullable=True)
    delay_impact_min: Mapped[float | None] = mapped_column(Numeric(), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean(), server_default="true", index=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB(), nullable=True)
    created_by: Mapped[str | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    def __repr__(self) -> str:
        return f"<Event {self.id} — {self.event_type} at {self.station_code or self.section_id}>"
