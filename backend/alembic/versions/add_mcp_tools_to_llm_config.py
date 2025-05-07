"""Add MCP tools fields to LLM config

Revision ID: add_mcp_tools_to_llm_config
Revises: 202505060000_add_tool_calls_to_message
Create Date: 2023-05-06 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite


# revision identifiers, used by Alembic.
revision = 'add_mcp_tools_to_llm_config'
down_revision = '202505060000_add_tool_calls_to_message'
branch_labels = None
depends_on = None


def upgrade():
    # Add the global_mcp_tools_enabled and global_allowed_mcp_tool_server_ids columns
    with op.batch_alter_table('llm_config') as batch_op:
        batch_op.add_column(sa.Column('global_mcp_tools_enabled', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('global_allowed_mcp_tool_server_ids', sqlite.JSON(), nullable=True))
    
    # Set default values for existing rows
    conn = op.get_bind()
    conn.execute(sa.text('UPDATE llm_config SET global_mcp_tools_enabled = false'))


def downgrade():
    # Remove the columns
    with op.batch_alter_table('llm_config') as batch_op:
        batch_op.drop_column('global_allowed_mcp_tool_server_ids')
        batch_op.drop_column('global_mcp_tools_enabled')