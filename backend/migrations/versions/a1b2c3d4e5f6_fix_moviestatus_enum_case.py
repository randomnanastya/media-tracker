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


def upgrade() -> None:
    op.execute("ALTER TYPE moviestatus RENAME VALUE 'rumored' TO 'RUMORED'")
    op.execute("ALTER TYPE moviestatus RENAME VALUE 'announced' TO 'ANNOUNCED'")
    op.execute("ALTER TYPE moviestatus RENAME VALUE 'in_production' TO 'IN_PRODUCTION'")
    op.execute("ALTER TYPE moviestatus RENAME VALUE 'post_production' TO 'POST_PRODUCTION'")
    op.execute("ALTER TYPE moviestatus RENAME VALUE 'in_cinemas' TO 'IN_CINEMAS'")
    op.execute("ALTER TYPE moviestatus RENAME VALUE 'released' TO 'RELEASED'")
    op.execute("ALTER TYPE moviestatus RENAME VALUE 'canceled' TO 'CANCELED'")


def downgrade() -> None:
    op.execute("ALTER TYPE moviestatus RENAME VALUE 'RUMORED' TO 'rumored'")
    op.execute("ALTER TYPE moviestatus RENAME VALUE 'ANNOUNCED' TO 'announced'")
    op.execute("ALTER TYPE moviestatus RENAME VALUE 'IN_PRODUCTION' TO 'in_production'")
    op.execute("ALTER TYPE moviestatus RENAME VALUE 'POST_PRODUCTION' TO 'post_production'")
    op.execute("ALTER TYPE moviestatus RENAME VALUE 'IN_CINEMAS' TO 'in_cinemas'")
    op.execute("ALTER TYPE moviestatus RENAME VALUE 'RELEASED' TO 'released'")
    op.execute("ALTER TYPE moviestatus RENAME VALUE 'CANCELED' TO 'canceled'")
