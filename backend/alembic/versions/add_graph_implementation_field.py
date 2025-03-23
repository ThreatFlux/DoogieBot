"""Add graph_implementation field to rag_config table

Revision ID: add_graph_implementation_field
Revises: add_rag_config_table
Create Date: 2025-03-23 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_graph_implementation_field'
down_revision = 'add_rag_config_table'
branch_labels = None
depends_on = None


def upgrade():
    # Add graph_implementation column to rag_config table
    op.add_column('rag_config', sa.Column('graph_implementation', sa.String(), nullable=True))
    
    # Set default value for existing rows
    op.execute("UPDATE rag_config SET graph_implementation = 'networkx' WHERE graph_implementation IS NULL")


def downgrade():
    # Remove graph_implementation column from rag_config table
    op.drop_column('rag_config', 'graph_implementation')