from datetime import datetime, date
from sqlalchemy import String, Numeric, DateTime, Date, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Prediction(Base):
    """ETA prediction for a train at a future station — TimescaleDB hypertable."""
    __tablename__ = "predictions"

    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    train_number: Mapped[str] = mapped_column(String(10), primary_key=True)
    run_date: Mapped[date] = mapped_column(Date(), primary_key=True)
    station_code: Mapped[str] = mapped_column(String(10), primary_key=True)

    station_sequence: Mapped[int | None] = mapped_column(Integer(), nullable=True)
    predicted_eta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    lower_bound: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    upper_bound: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Numeric(), nullable=True)
    model_version: Mapped[str] = mapped_column(String(20), default="physics_v1")
    explanation: Mapped[dict | None] = mapped_column(JSONB(), nullable=True)

    def __repr__(self) -> str:
        return f"<Prediction {self.train_number}→{self.station_code} @ {self.predicted_eta}>"
