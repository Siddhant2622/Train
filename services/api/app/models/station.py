from sqlalchemy import String, Text, Boolean, Numeric, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.train import Train
    from app.models.train_schedule import TrainSchedule


class Station(Base):
    __tablename__ = "stations"

    station_code: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(Text(), nullable=False)
    city: Mapped[str | None] = mapped_column(Text(), nullable=True)
    state: Mapped[str | None] = mapped_column(Text(), nullable=True)
    zone: Mapped[str | None] = mapped_column(String(10), nullable=True)
    latitude: Mapped[float] = mapped_column(nullable=False)
    longitude: Mapped[float] = mapped_column(nullable=False)
    elevation_m: Mapped[float | None] = mapped_column(Numeric(), nullable=True)
    is_major: Mapped[bool] = mapped_column(Boolean(), default=False)
    platform_count: Mapped[int | None] = mapped_column(Integer(), nullable=True)

    def __repr__(self) -> str:
        return f"<Station {self.station_code} — {self.name}>"
