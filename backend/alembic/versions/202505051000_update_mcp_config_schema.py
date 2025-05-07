"""Update MCP config schema

Revision ID: 202505051000
Revises: 202505051200
Create Date: 2025-05-05 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '202505051000'
down_revision = '202505051200'
branch_labels = None
depends_on = None


def upgrade():
    # Add and modify columns in MCP config table
    
    # Use batch mode for SQLite compatibility
    with op.batch_alter_table('mcp_config', schema=None) as batch_op:
        # First, make api_key nullable
        batch_op.alter_column('api_key', nullable=True)
        
        # Add new columns
        batch_op.add_column(sa.Column('transport_type', sa.String(), nullable=False, server_default='http'))
        batch_op.add_column(sa.Column('command', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('args', sqlite.JSON(), nullable=True))
        batch_op.add_column(sa.Column('working_directory', sa.String(), nullable=True))
        batch_op.add_column(sa.Column('environment', sqlite.JSON(), nullable=True))
        batch_op.add_column(sa.Column('capabilities_list', sqlite.JSON(), nullable=True))
        
        # Add unique constraint to name
        batch_op.create_unique_constraint('uq_mcp_config_name', ['name'])
        
        # Add index to is_active
        batch_op.create_index('ix_mcp_config_is_active', ['is_active'])


def downgrade():
    # Use batch mode for SQLite compatibility
    with op.batch_alter_table('mcp_config', schema=None) as batch_op:
        # Remove columns and constraints
        batch_op.drop_index('ix_mcp_config_is_active')
        batch_op.drop_constraint('uq_mcp_config_name', type_='unique')
        batch_op.drop_column('capabilities_list')
        batch_op.drop_column('environment')
        batch_op.drop_column('working_directory')
        batch_op.drop_column('args')
        batch_op.drop_column('command')
        batch_op.drop_column('transport_type')
        
        # Revert api_key to not nullable
        batch_op.alter_column('api_key', nullable=False)