from datetime import time
from sqlalchemy import String, Text, Boolean, Numeric, Integer, Time, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Train(Base):
    __tablename__ = "trains"

    train_number: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(Text(), nullable=False)
    train_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    zone: Mapped[str | None] = mapped_column(String(10), nullable=True)
    source_station: Mapped[str] = mapped_column(String(10), ForeignKey("stations.station_code"), nullable=False)
    destination_station: Mapped[str] = mapped_column(String(10), ForeignKey("stations.station_code"), nullable=False)
    total_distance_km: Mapped[float | None] = mapped_column(Numeric(), nullable=True)
    journey_duration_min: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    runs_on_days: Mapped[str] = mapped_column(String(7), default="1111111")
    departure_time: Mapped[time | None] = mapped_column(Time(), nullable=True)
    arrival_time: Mapped[time | None] = mapped_column(Time(), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean(), default=True)
    external_ids: Mapped[dict | None] = mapped_column(JSONB(), nullable=True)

    def __repr__(self) -> str:
        return f"<Train {self.train_number} — {self.name}>"
