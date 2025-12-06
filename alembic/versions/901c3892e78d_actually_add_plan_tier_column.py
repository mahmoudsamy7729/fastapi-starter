"""actually add plan tier column

Revision ID: 901c3892e78d
Revises: d511d819de27
Create Date: 2025-12-05 20:30:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "901c3892e78d"
down_revision: Union[str, Sequence[str], None] = "d511d819de27"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    plantier_enum = sa.Enum("FREE", "PRO", "VIP", name="plantier")
    plantier_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "plans",
        sa.Column(
            "tier",
            plantier_enum,
            nullable=False,
            server_default="FREE",  # set existing rows to FREE
        ),
    )


def downgrade() -> None:
    op.drop_column("plans", "tier")
    plantier_enum = sa.Enum(name="plantier")
    plantier_enum.drop(op.get_bind(), checkfirst=True)
