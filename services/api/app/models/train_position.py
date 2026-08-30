from datetime import datetime, date
from sqlalchemy import String, Numeric, DateTime, Date, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TrainPosition(Base):
    """Real-time position ping for a train run — TimescaleDB hypertable."""
    __tablename__ = "train_positions"

    # Composite primary key: (time, train_number, run_date) for hypertable
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    train_number: Mapped[str] = mapped_column(String(10), primary_key=True)
    run_date: Mapped[date] = mapped_column(Date(), primary_key=True)

    latitude: Mapped[float | None] = mapped_column(Numeric(), nullable=True)
    longitude: Mapped[float | None] = mapped_column(Numeric(), nullable=True)
    speed_kmh: Mapped[float | None] = mapped_column(Numeric(), nullable=True)
    heading_deg: Mapped[float | None] = mapped_column(Numeric(), nullable=True)
    last_station: Mapped[str | None] = mapped_column(String(10), ForeignKey("stations.station_code"), nullable=True)
    next_station: Mapped[str | None] = mapped_column(String(10), ForeignKey("stations.station_code"), nullable=True)
    distance_to_next_km: Mapped[float | None] = mapped_column(Numeric(), nullable=True)
    current_delay_min: Mapped[float] = mapped_column(Numeric(), default=0)
    source: Mapped[str] = mapped_column(String(20), default="simulator")
    raw_payload: Mapped[dict | None] = mapped_column(JSONB(), nullable=True)

    def __repr__(self) -> str:
        return f"<TrainPosition {self.train_number} @ {self.time}>"
