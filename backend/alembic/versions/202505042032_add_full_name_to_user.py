"""Add full_name to user model

Revision ID: 202505042032
Revises: 202504300000
Create Date: 2025-05-04 20:32:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '202505042032'
down_revision = '202504300000'
branch_labels = None
depends_on = None


def upgrade():
    # Add full_name column to users table
    op.add_column('users', sa.Column('full_name', sa.String(), nullable=True))
    
    # Update existing users with default values
    op.execute("UPDATE users SET full_name = '' WHERE full_name IS NULL")


def downgrade():
    # Remove full_name column from users table
    op.drop_column('users', 'full_name')