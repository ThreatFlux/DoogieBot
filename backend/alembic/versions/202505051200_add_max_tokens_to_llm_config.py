"""add max_tokens to llm_config

Revision ID: 202505051200
Revises: 202505050000
Create Date: 2025-05-05 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = '202505051200'
down_revision: Union[str, None] = '202505050000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add max_tokens column to llm_config if it doesn't exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('llm_config')]
    
    # Only add the column if it doesn't already exist
    if 'max_tokens' not in columns:
        with op.batch_alter_table('llm_config', schema=None) as batch_op:
            batch_op.add_column(sa.Column('max_tokens', sa.Integer(), nullable=True))
    
    # Log the operation
    print("Added max_tokens column to llm_config table")


def downgrade() -> None:
    # Remove the max_tokens column from llm_config table
    with op.batch_alter_table('llm_config', schema=None) as batch_op:
        batch_op.drop_column('max_tokens')