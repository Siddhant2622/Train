from sqlalchemy import String, Numeric, Boolean, ForeignKey, BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Section(Base):
    """A track section between two consecutive stations."""
    __tablename__ = "sections"

    id: Mapped[int] = mapped_column(BigInteger(), autoincrement=True, primary_key=True)
    from_station: Mapped[str] = mapped_column(String(10), ForeignKey("stations.station_code"), nullable=False)
    to_station: Mapped[str] = mapped_column(String(10), ForeignKey("stations.station_code"), nullable=False)
    distance_km: Mapped[float] = mapped_column(Numeric(), nullable=False)
    max_permissible_speed_kmh: Mapped[float] = mapped_column(Numeric(), default=100)
    avg_speed_kmh: Mapped[float] = mapped_column(Numeric(), default=80)
    line_type: Mapped[str] = mapped_column(String(20), default="double")
    line_capacity_trains_per_hour: Mapped[float] = mapped_column(Numeric(), default=8)
    electrified: Mapped[bool] = mapped_column(Boolean(), default=True)

    def __repr__(self) -> str:
        return f"<Section {self.from_station}→{self.to_station} {self.distance_km}km>"
