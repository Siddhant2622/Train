from datetime import datetime
from sqlalchemy import BigInteger, String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Propagation(Base):
    __tablename__ = "delay_propagation"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    cause_train: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    affected_train: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    section_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("sections.id"), nullable=True)
    estimated_impact_min: Mapped[float | None] = mapped_column(Numeric(), nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<Propagation {self.cause_train} -> {self.affected_train} ({self.estimated_impact_min} min)>"
