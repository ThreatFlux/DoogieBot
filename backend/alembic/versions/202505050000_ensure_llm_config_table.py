"""Ensure llm_config table exists

Revision ID: 202505050000
Revises: 202505042032
Create Date: 2025-05-05 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.sqlite import JSON

# revision identifiers, used by Alembic.
revision: str = '202505050000'
down_revision: Union[str, None] = '202505042032'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create llm_config table if it doesn't exist."""
    # Create llm_config table if it doesn't exist
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    if 'llm_config' not in inspector.get_table_names():
        op.create_table(
            'llm_config',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('provider', sa.String(), nullable=False),
            sa.Column('chat_provider', sa.String(), nullable=False),
            sa.Column('embedding_provider', sa.String(), nullable=False),
            sa.Column('model', sa.String(), nullable=False),
            sa.Column('embedding_model', sa.String(), nullable=False),
            sa.Column('system_prompt', sa.String(), nullable=False),
            sa.Column('api_key', sa.String(), nullable=True),
            sa.Column('base_url', sa.String(), nullable=True),
            sa.Column('temperature', sa.Float(), nullable=True),
            sa.Column('max_tokens', sa.Integer(), nullable=True),  # Added for test compatibility
            sa.Column('is_active', sa.Boolean(), default=False),
            sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
            sa.Column('reranked_top_n', sa.Integer(), nullable=True),
            sa.Column('config', JSON(), nullable=True),
        )


def downgrade() -> None:
    """Drop llm_config table."""
    op.drop_table('llm_config')