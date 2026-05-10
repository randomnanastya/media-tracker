"""fix TMDB_MOVIES_METADATA_UPDATE enum case in syncjobtype

Revision ID: f1a2b3c4d5e6
Revises: c3d4e5f6a7b8
Create Date: 2026-05-10 10:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE syncjobtype ADD VALUE IF NOT EXISTS 'TMDB_MOVIES_METADATA_UPDATE'")


def downgrade() -> None:
    pass
