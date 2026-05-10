"""fix moviestatus enum values to uppercase

Revision ID: a1b2c3d4e5f6
Revises: f1a2b3c4d5e6
Create Date: 2026-05-10 10:10:00.000000

"""

from collections.abc import Sequence
from typing import Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _rename_if_exists(old: str, new: str) -> None:
    op.execute(
        f"""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM pg_enum
                       WHERE enumlabel = '{old}'
                       AND enumtypid = 'moviestatus'::regtype) THEN
                ALTER TYPE moviestatus RENAME VALUE '{old}' TO '{new}';
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    _rename_if_exists("rumored", "RUMORED")
    _rename_if_exists("announced", "ANNOUNCED")
    _rename_if_exists("in_production", "IN_PRODUCTION")
    _rename_if_exists("post_production", "POST_PRODUCTION")
    _rename_if_exists("in_cinemas", "IN_CINEMAS")
    _rename_if_exists("released", "RELEASED")
    _rename_if_exists("canceled", "CANCELED")


def downgrade() -> None:
    _rename_if_exists("RUMORED", "rumored")
    _rename_if_exists("ANNOUNCED", "announced")
    _rename_if_exists("IN_PRODUCTION", "in_production")
    _rename_if_exists("POST_PRODUCTION", "post_production")
    _rename_if_exists("IN_CINEMAS", "in_cinemas")
    _rename_if_exists("RELEASED", "released")
    _rename_if_exists("CANCELED", "canceled")
