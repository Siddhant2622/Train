"""Re-export all ORM models so Alembic autogenerate can detect them.

Import this module in db/migrations/env.py to ensure all tables are tracked.
"""

from app.models.user import User
from app.models.station import Station
from app.models.train import Train
from app.models.train_schedule import TrainSchedule
from app.models.section import Section
from app.models.train_position import TrainPosition
from app.models.prediction import Prediction
from app.models.propagation import Propagation
from app.models.event import Event

__all__ = [
    "User",
    "Station",
    "Train",
    "TrainSchedule",
    "Section",
    "TrainPosition",
    "Prediction",
    "Propagation",
    "Event",
]
