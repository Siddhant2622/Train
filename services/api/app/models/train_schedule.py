from datetime import time
from sqlalchemy import String, Integer, Numeric, Time, ForeignKey, UniqueConstraint, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TrainSchedule(Base):
    __tablename__ = "train_schedule"
    __table_args__ = (
        UniqueConstraint("train_number", "sequence", name="uq_train_schedule"),
    )

    id: Mapped[int] = mapped_column(BigInteger(), autoincrement=True, primary_key=True)
    train_number: Mapped[str] = mapped_column(String(10), ForeignKey("trains.train_number", ondelete="CASCADE"), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer(), nullable=False)
    station_code: Mapped[str] = mapped_column(String(10), ForeignKey("stations.station_code"), nullable=False)
    scheduled_arrival: Mapped[time | None] = mapped_column(Time(), nullable=True)
    scheduled_departure: Mapped[time | None] = mapped_column(Time(), nullable=True)
    distance_from_source_km: Mapped[float | None] = mapped_column(Numeric(), nullable=True)
    avg_halt_minutes: Mapped[float] = mapped_column(Numeric(), default=2)
    day_offset: Mapped[int] = mapped_column(Integer(), default=0)

    def __repr__(self) -> str:
        return f"<TrainSchedule {self.train_number} seq={self.sequence} {self.station_code}>"
