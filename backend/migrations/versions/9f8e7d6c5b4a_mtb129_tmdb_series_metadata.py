"""MTB-129 tmdb series metadata

Revision ID: 9f8e7d6c5b4a
Revises: a1b2c3d4e5f6
Create Date: 2026-05-11 12:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "9f8e7d6c5b4a"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # --- New columns: series ---
    op.add_column("series", sa.Column("original_name", sa.String(), nullable=True))
    op.add_column("series", sa.Column("overview", sa.String(), nullable=True))
    op.add_column("series", sa.Column("backdrop_path", sa.String(), nullable=True))
    op.add_column("series", sa.Column("first_air_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("series", sa.Column("last_air_date", sa.DateTime(timezone=True), nullable=True))
    op.add_column("series", sa.Column("number_of_seasons", sa.Integer(), nullable=True))
    op.add_column("series", sa.Column("number_of_episodes", sa.Integer(), nullable=True))
    op.add_column(
        "series",
        sa.Column("tmdb_metadata_fetched_at", sa.DateTime(timezone=True), nullable=True),
    )

    # --- New columns: seasons ---
    op.add_column("seasons", sa.Column("tmdb_id", sa.Integer(), nullable=True))
    op.add_column("seasons", sa.Column("overview", sa.String(), nullable=True))
    op.add_column("seasons", sa.Column("poster_url", sa.String(), nullable=True))
    op.add_column("seasons", sa.Column("vote_average", sa.Float(), nullable=True))
    op.create_unique_constraint("uq_seasons_tmdb_id", "seasons", ["tmdb_id"])

    # --- New columns: episodes ---
    op.add_column("episodes", sa.Column("tmdb_id", sa.Integer(), nullable=True))
    op.add_column("episodes", sa.Column("episode_type", sa.String(), nullable=True))
    op.add_column("episodes", sa.Column("still_url", sa.String(), nullable=True))
    op.add_column("episodes", sa.Column("vote_average", sa.Float(), nullable=True))
    op.create_unique_constraint("uq_episodes_tmdb_id", "episodes", ["tmdb_id"])

    # --- Convert series.status String -> Enum(SeriesStatus) ---
    seriesstatus = postgresql.ENUM(
        "continuing",
        "in_production",
        "planned",
        "ended",
        "canceled",
        "deleted",
        name="seriesstatus",
    )
    seriesstatus.create(op.get_bind(), checkfirst=True)

    # Normalize existing string values before type conversion
    op.execute(
        """
        UPDATE series SET status = CASE
            WHEN status IN ('continuing', 'Continuing') THEN 'continuing'
            WHEN status IN ('upcoming', 'Unreleased') THEN 'in_production'
            WHEN status IN ('ended', 'Ended') THEN 'ended'
            WHEN status = 'deleted' THEN 'deleted'
            WHEN status IN ('canceled', 'Canceled') THEN 'canceled'
            WHEN status = 'planned' THEN 'planned'
            ELSE NULL
        END
    """
    )

    op.alter_column(
        "series",
        "status",
        existing_type=sa.String(),
        type_=postgresql.ENUM(
            "continuing",
            "in_production",
            "planned",
            "ended",
            "canceled",
            "deleted",
            name="seriesstatus",
            create_type=False,
        ),
        existing_nullable=True,
        postgresql_using="status::text::seriesstatus",
    )

    # --- Rename SyncJobType enum value ---
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_enum
                WHERE enumtypid = 'syncjobtype'::regtype
                  AND enumlabel = 'tmdb_movies_metadata_update'
            ) THEN
                ALTER TYPE syncjobtype RENAME VALUE 'tmdb_movies_metadata_update' TO 'tmdb_metadata_update';
            END IF;
        END$$;
    """
    )


def downgrade() -> None:
    """Downgrade schema."""
    # --- Rename SyncJobType value back ---
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_enum
                WHERE enumtypid = 'syncjobtype'::regtype
                  AND enumlabel = 'tmdb_metadata_update'
            ) THEN
                ALTER TYPE syncjobtype RENAME VALUE 'tmdb_metadata_update' TO 'tmdb_movies_metadata_update';
            END IF;
        END$$;
    """
    )

    # --- Revert series.status Enum -> String ---
    op.alter_column(
        "series",
        "status",
        existing_type=postgresql.ENUM(
            "continuing",
            "in_production",
            "planned",
            "ended",
            "canceled",
            "deleted",
            name="seriesstatus",
            create_type=False,
        ),
        type_=sa.String(),
        existing_nullable=True,
    )
    seriesstatus = postgresql.ENUM(name="seriesstatus")
    seriesstatus.drop(op.get_bind(), checkfirst=True)

    # --- Drop new columns: seasons ---
    op.drop_constraint("uq_seasons_tmdb_id", "seasons", type_="unique")
    op.drop_column("seasons", "vote_average")
    op.drop_column("seasons", "poster_url")
    op.drop_column("seasons", "overview")
    op.drop_column("seasons", "tmdb_id")

    # --- Drop new columns: episodes ---
    op.drop_constraint("uq_episodes_tmdb_id", "episodes", type_="unique")
    op.drop_column("episodes", "vote_average")
    op.drop_column("episodes", "still_url")
    op.drop_column("episodes", "episode_type")
    op.drop_column("episodes", "tmdb_id")

    # --- Drop new columns: series ---
    op.drop_column("series", "tmdb_metadata_fetched_at")
    op.drop_column("series", "number_of_episodes")
    op.drop_column("series", "number_of_seasons")
    op.drop_column("series", "last_air_date")
    op.drop_column("series", "first_air_date")
    op.drop_column("series", "backdrop_path")
    op.drop_column("series", "overview")
    op.drop_column("series", "original_name")
