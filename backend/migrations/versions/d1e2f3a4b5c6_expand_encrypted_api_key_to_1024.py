"""expand encrypted_api_key column to 1024

Revision ID: d1e2f3a4b5c6
Revises: 318c76f4e023
Create Date: 2026-03-21 11:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, Sequence[str], None] = "318c76f4e023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "service_configs",
        "encrypted_api_key",
        existing_type=sa.String(length=500),
        type_=sa.String(length=1024),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "service_configs",
        "encrypted_api_key",
        existing_type=sa.String(length=1024),
        type_=sa.String(length=500),
        existing_nullable=False,
    )
