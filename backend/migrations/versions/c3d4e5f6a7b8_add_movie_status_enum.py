"""add MovieStatus enum for movies.status

Revision ID: c3d4e5f6a7b8
Revises: aedcba8d6c2c
Create Date: 2026-05-10 00:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "aedcba8d6c2c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

movie_status_enum = postgresql.ENUM(
    "RUMORED",
    "ANNOUNCED",
    "IN_PRODUCTION",
    "POST_PRODUCTION",
    "IN_CINEMAS",
    "RELEASED",
    "CANCELED",
    name="moviestatus",
)


def upgrade() -> None:
    movie_status_enum.create(op.get_bind(), checkfirst=True)

    # Normalize existing string values to the new enum values
    op.execute(
        """
        UPDATE movies SET status = CASE
            WHEN status IN ('announced', 'tba', 'Planned') THEN 'ANNOUNCED'
            WHEN status = 'inCinemas' THEN 'IN_CINEMAS'
            WHEN status IN ('released', 'Released') THEN 'RELEASED'
            WHEN status IN ('deleted', 'Canceled') THEN 'CANCELED'
            WHEN status = 'Rumored' THEN 'RUMORED'
            WHEN status = 'In Production' THEN 'IN_PRODUCTION'
            WHEN status = 'Post Production' THEN 'POST_PRODUCTION'
            ELSE NULL
        END
    """
    )

    op.alter_column(
        "movies",
        "status",
        existing_type=sa.String(),
        type_=movie_status_enum,
        existing_nullable=True,
        postgresql_using="status::moviestatus",
    )


def downgrade() -> None:
    op.alter_column(
        "movies",
        "status",
        existing_type=movie_status_enum,
        type_=sa.String(),
        existing_nullable=True,
        postgresql_using="status::text",
    )
    movie_status_enum.drop(op.get_bind(), checkfirst=True)
