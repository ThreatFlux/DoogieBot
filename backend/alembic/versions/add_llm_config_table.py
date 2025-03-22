"""add_llm_config_table

Revision ID: add_llm_config_table
Revises: 340bb28f6d8c
Create Date: 2025-03-18 14:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = 'add_llm_config_table'
down_revision = '340bb28f6d8c'
branch_labels = None
depends_on = None


def upgrade():
    # Create llm_config table
    op.create_table(
        'llm_config',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('provider', sa.String(), nullable=False),
        sa.Column('model', sa.String(), nullable=False),
        sa.Column('embedding_model', sa.String(), nullable=False),
        sa.Column('system_prompt', sa.String(), nullable=False),
        sa.Column('api_key', sa.String(), nullable=True),
        sa.Column('base_url', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('config', sqlite.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index on is_active for faster queries
    op.create_index(op.f('ix_llm_config_is_active'), 'llm_config', ['is_active'], unique=False)


def downgrade():
    # Drop index
    op.drop_index(op.f('ix_llm_config_is_active'), table_name='llm_config')
    
    # Drop table
    op.drop_table('llm_config')