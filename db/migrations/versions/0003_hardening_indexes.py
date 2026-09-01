"""hardening_indexes

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-31 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0003_hardening_indexes'
down_revision: Union[str, None] = '0002_data_spine'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # We add an index to optimize the `GET /api/v1/trains` DISTINCT ON (train_number) query
    op.create_index(
        "ix_train_positions_latest",
        "train_positions",
        ["run_date", "train_number", sa.text("time DESC")]
    )


def downgrade() -> None:
    op.drop_index("ix_train_positions_latest", table_name="train_positions")
