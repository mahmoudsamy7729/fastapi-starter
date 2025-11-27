"""add plans table and subscriptions table

Revision ID: 4f13070ec20a
Revises: 5f0d227cfb77
Create Date: 2025-11-24 21:39:16.200209

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4f13070ec20a'
down_revision: Union[str, Sequence[str], None] = '5f0d227cfb77'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
