"""Add tool_calls and tool_results to Message model

Revision ID: 202505060000
Revises: 202505051200
Create Date: 2025-05-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '202505060000'
down_revision = '202505051200'
branch_labels = None
depends_on = None


def upgrade():
    # Add tool_calls and tool_results columns to the messages table
    op.add_column('messages', sa.Column('tool_calls', sa.JSON(), nullable=True))
    op.add_column('messages', sa.Column('tool_results', sa.JSON(), nullable=True))


def downgrade():
    # Remove added columns
    op.drop_column('messages', 'tool_results')
    op.drop_column('messages', 'tool_calls')