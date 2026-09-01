"""Phase 1 — Full data spine migration.

Adds all production tables on top of the users table from 0001.
TimescaleDB hypertables are created for time-series data.
PostGIS geography columns are used for spatial queries.

Run: alembic upgrade head
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_data_spine"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # stations
    # ------------------------------------------------------------------
    op.create_table(
        "stations",
        sa.Column("station_code", sa.String(10), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("city", sa.Text(), nullable=True),
        sa.Column("state", sa.Text(), nullable=True),
        sa.Column("zone", sa.String(10), nullable=True),
        sa.Column("latitude", sa.Double(), nullable=False),
        sa.Column("longitude", sa.Double(), nullable=False),
        sa.Column("elevation_m", sa.Numeric(), nullable=True),
        sa.Column("is_major", sa.Boolean(), server_default="false"),
        sa.Column("platform_count", sa.Integer(), nullable=True),
    )
    op.create_index("ix_stations_zone", "stations", ["zone"])

    # ------------------------------------------------------------------
    # trains
    # ------------------------------------------------------------------
    op.create_table(
        "trains",
        sa.Column("train_number", sa.String(10), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("train_type", sa.String(30), nullable=True),
        sa.Column("zone", sa.String(10), nullable=True),
        sa.Column("source_station", sa.String(10), sa.ForeignKey("stations.station_code"), nullable=False),
        sa.Column("destination_station", sa.String(10), sa.ForeignKey("stations.station_code"), nullable=False),
        sa.Column("total_distance_km", sa.Numeric(), nullable=True),
        sa.Column("journey_duration_min", sa.Integer(), nullable=True),
        sa.Column("runs_on_days", sa.String(7), nullable=False, server_default="1111111"),
        sa.Column("departure_time", sa.Time(), nullable=True),
        sa.Column("arrival_time", sa.Time(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("external_ids", postgresql.JSONB(), nullable=True),
    )
    op.create_index("ix_trains_type", "trains", ["train_type"])
    op.create_index("ix_trains_source", "trains", ["source_station"])
    op.create_index("ix_trains_dest", "trains", ["destination_station"])

    # ------------------------------------------------------------------
    # train_schedule
    # ------------------------------------------------------------------
    op.create_table(
        "train_schedule",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("train_number", sa.String(10), sa.ForeignKey("trains.train_number", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("station_code", sa.String(10), sa.ForeignKey("stations.station_code"), nullable=False),
        sa.Column("scheduled_arrival", sa.Time(), nullable=True),
        sa.Column("scheduled_departure", sa.Time(), nullable=True),
        sa.Column("distance_from_source_km", sa.Numeric(), nullable=True),
        sa.Column("avg_halt_minutes", sa.Numeric(), server_default="2"),
        sa.Column("day_offset", sa.Integer(), server_default="0"),  # 0=day1, 1=day2 etc.
    )
    op.create_unique_constraint("uq_train_schedule", "train_schedule", ["train_number", "sequence"])
    op.create_index("ix_train_schedule_train", "train_schedule", ["train_number"])
    op.create_index("ix_train_schedule_station", "train_schedule", ["station_code"])

    # ------------------------------------------------------------------
    # sections (track segments between consecutive stations)
    # ------------------------------------------------------------------
    op.create_table(
        "sections",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("from_station", sa.String(10), sa.ForeignKey("stations.station_code"), nullable=False),
        sa.Column("to_station", sa.String(10), sa.ForeignKey("stations.station_code"), nullable=False),
        sa.Column("distance_km", sa.Numeric(), nullable=False),
        sa.Column("max_permissible_speed_kmh", sa.Numeric(), server_default="100"),
        sa.Column("avg_speed_kmh", sa.Numeric(), server_default="80"),
        sa.Column("line_type", sa.String(20), server_default="double"),  # single/double/quadruple
        sa.Column("line_capacity_trains_per_hour", sa.Numeric(), server_default="8"),
        sa.Column("electrified", sa.Boolean(), server_default="true"),
    )
    op.create_index("ix_sections_from", "sections", ["from_station"])
    op.create_index("ix_sections_to", "sections", ["to_station"])

    # ------------------------------------------------------------------
    # weather_snapshots
    # ------------------------------------------------------------------
    op.create_table(
        "weather_snapshots",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("section_id", sa.BigInteger(), sa.ForeignKey("sections.id"), nullable=True),
        sa.Column("station_code", sa.String(10), sa.ForeignKey("stations.station_code"), nullable=True),
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("condition", sa.String(30), nullable=True),
        sa.Column("rainfall_mm", sa.Numeric(), nullable=True),
        sa.Column("visibility_km", sa.Numeric(), nullable=True),
        sa.Column("wind_speed_kmh", sa.Numeric(), nullable=True),
        sa.Column("temperature_c", sa.Numeric(), nullable=True),
    )
    op.create_index("ix_weather_time", "weather_snapshots", ["time"])

    # ------------------------------------------------------------------
    # train_positions  (TimescaleDB hypertable)
    # ------------------------------------------------------------------
    op.create_table(
        "train_positions",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("train_number", sa.String(10), nullable=False),
        sa.Column("run_date", sa.Date(), nullable=False),
        sa.Column("latitude", sa.Double(), nullable=True),
        sa.Column("longitude", sa.Double(), nullable=True),
        sa.Column("speed_kmh", sa.Numeric(), nullable=True),
        sa.Column("heading_deg", sa.Numeric(), nullable=True),
        sa.Column("last_station", sa.String(10), sa.ForeignKey("stations.station_code"), nullable=True),
        sa.Column("next_station", sa.String(10), sa.ForeignKey("stations.station_code"), nullable=True),
        sa.Column("distance_to_next_km", sa.Numeric(), nullable=True),
        sa.Column("current_delay_min", sa.Numeric(), nullable=True, server_default="0"),
        sa.Column("source", sa.String(20), server_default="simulator"),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=True),
    )
    # Convert to hypertable — fails gracefully if TimescaleDB not installed
    # Supabase does not support TimescaleDB extension, so we skip create_hypertable
    pass
    op.create_index("ix_train_positions_train_time", "train_positions", ["train_number", "time"])

    # ------------------------------------------------------------------
    # predictions  (TimescaleDB hypertable)
    # ------------------------------------------------------------------
    op.create_table(
        "predictions",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("train_number", sa.String(10), nullable=False),
        sa.Column("run_date", sa.Date(), nullable=False),
        sa.Column("station_code", sa.String(10), nullable=False),
        sa.Column("station_sequence", sa.Integer(), nullable=True),
        sa.Column("predicted_eta", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lower_bound", sa.DateTime(timezone=True), nullable=True),
        sa.Column("upper_bound", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confidence", sa.Numeric(), nullable=True),
        sa.Column("model_version", sa.String(20), server_default="physics_v1"),
        sa.Column("explanation", postgresql.JSONB(), nullable=True),
    )
    # Supabase does not support TimescaleDB extension, so we skip create_hypertable
    pass
    op.create_index("ix_predictions_train_time", "predictions", ["train_number", "time"])
    op.create_index("ix_predictions_train_station", "predictions", ["train_number", "station_code"])

    # ------------------------------------------------------------------
    # events
    # ------------------------------------------------------------------
    op.create_table(
        "events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("section_id", sa.BigInteger(), sa.ForeignKey("sections.id"), nullable=True),
        sa.Column("station_code", sa.String(10), sa.ForeignKey("stations.station_code"), nullable=True),
        sa.Column("severity", sa.String(10), server_default="medium"),
        sa.Column("speed_restriction_kmh", sa.Numeric(), nullable=True),
        sa.Column("delay_impact_min", sa.Numeric(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_events_type", "events", ["event_type"])
    op.create_index("ix_events_active", "events", ["is_active"])

    # ------------------------------------------------------------------
    # delay_propagation
    # ------------------------------------------------------------------
    op.create_table(
        "delay_propagation",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("cause_train", sa.String(10), nullable=False),
        sa.Column("affected_train", sa.String(10), nullable=False),
        sa.Column("section_id", sa.BigInteger(), sa.ForeignKey("sections.id"), nullable=True),
        sa.Column("estimated_impact_min", sa.Numeric(), nullable=True),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_propagation_cause", "delay_propagation", ["cause_train"])
    op.create_index("ix_propagation_affected", "delay_propagation", ["affected_train"])

    # ------------------------------------------------------------------
    # model_registry
    # ------------------------------------------------------------------
    op.create_table(
        "model_registry",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("model_name", sa.String(50), nullable=False),
        sa.Column("version", sa.String(20), nullable=False),
        sa.Column("trained_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("mae_min", sa.Numeric(), nullable=True),
        sa.Column("rmse_min", sa.Numeric(), nullable=True),
        sa.Column("accuracy_within_5min", sa.Numeric(), nullable=True),
        sa.Column("accuracy_within_10min", sa.Numeric(), nullable=True),
        sa.Column("artifact_path", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="false"),
        sa.Column("notes", sa.Text(), nullable=True),
    )

    # ------------------------------------------------------------------
    # audit_log (admin actions — security requirement)
    # ------------------------------------------------------------------
    op.create_table(
        "audit_log",
        sa.Column("id", sa.BigInteger(), autoincrement=True, primary_key=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_email", sa.Text(), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=True),
        sa.Column("resource_id", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_audit_log_actor", "audit_log", ["actor_id"])
    op.create_index("ix_audit_log_created", "audit_log", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("model_registry")
    op.drop_table("delay_propagation")
    op.drop_table("events")
    op.drop_table("predictions")
    op.drop_table("train_positions")
    op.drop_table("weather_snapshots")
    op.drop_table("sections")
    op.drop_table("train_schedule")
    op.drop_table("trains")
    op.drop_table("stations")
