"""add partial unique
  index for movie watch history

Revision ID: 16b1ac384f3d
Revises: 9afc76d62278
Create Date: 2026-06-07 11:48:52.651276

"""

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "16b1ac384f3d"
down_revision: Union[str, Sequence[str], None] = "9afc76d62278"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        DELETE FROM watch_history
        WHERE id IN (
            SELECT id FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY user_id, media_id
                           ORDER BY
                               CASE status
                                   WHEN 'WATCHED' THEN 1
                                   WHEN 'DROPPED' THEN 2
                                   WHEN 'WATCHING' THEN 3
                                   WHEN 'PLANNED' THEN 4
                               END,
                               watched_at DESC NULLS LAST,
                               id DESC
                       ) AS rn
                FROM watch_history
                WHERE episode_id IS NULL
            ) sub
            WHERE rn > 1
        )
        """
    )
    op.create_index(
        "uq_watch_history_user_media_no_episode",
        "watch_history",
        ["user_id", "media_id"],
        unique=True,
        postgresql_where=sa.text("episode_id IS NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "uq_watch_history_user_media_no_episode",
        table_name="watch_history",
        postgresql_where=sa.text("episode_id IS NULL"),
    )
