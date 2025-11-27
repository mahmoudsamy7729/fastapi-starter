"""seed plans

Revision ID: 7248ef524515
Revises: 396164fe71fe
Create Date: 2025-11-24 22:09:40.902137

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session
from uuid import uuid4
from src.billing.models import Plan, BillingPeriod


# revision identifiers, used by Alembic.
revision: str = '7248ef524515'
down_revision: Union[str, Sequence[str], None] = '396164fe71fe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    bind = op.get_bind()
    session = Session(bind=bind)

    plans = [
        Plan(
            id=uuid4(),
            code="free",
            name="Free",
            price_cents=0,
            billing_period=BillingPeriod.MONTHLY,
        ),
        Plan(
            id=uuid4(),
            code="pro",
            name="Pro",
            price_cents=1900,
            billing_period=BillingPeriod.MONTHLY,
        ),
    ]

    for p in plans:
        session.add(p)

    session.commit()


def downgrade():
    bind = op.get_bind()
    session = Session(bind=bind)

    session.execute(sa.text("DELETE FROM plans WHERE code IN ('free','pro')"))
    session.commit()

