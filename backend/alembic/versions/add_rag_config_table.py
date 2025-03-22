"""Add RAG config table

Revision ID: add_rag_config_table
Revises: add_llm_config_table
Create Date: 2025-03-21 17:34:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = 'add_rag_config_table'
down_revision = 'add_llm_config_table'
branch_labels = None
depends_on = None


def upgrade():
    # Create RAG config table
    op.create_table(
        'rag_config',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('bm25_enabled', sa.Boolean(), nullable=True, default=True),
        sa.Column('faiss_enabled', sa.Boolean(), nullable=True, default=True),
        sa.Column('graph_enabled', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('config', sqlite.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Insert default configuration
    op.execute(
        """
        INSERT INTO rag_config (id, bm25_enabled, faiss_enabled, graph_enabled, created_at, updated_at)
        VALUES (
            'default',
            1,
            1,
            1,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        )
        """
    )


def downgrade():
    # Drop RAG config table
    op.drop_table('rag_config')