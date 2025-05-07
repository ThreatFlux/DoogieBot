"""Merge multiple heads

Revision ID: 98bf9371c8e5
Revises: 202505051000, 890a69efd645
Create Date: 2025-05-05 15:55:52.242690

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '98bf9371c8e5'
down_revision = ('202505051000', '890a69efd645')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass