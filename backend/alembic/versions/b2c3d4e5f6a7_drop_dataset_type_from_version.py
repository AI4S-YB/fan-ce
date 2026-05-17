"""drop dataset_type from dataset_version

Revision ID: b2c3d4e5f6a7
Revises: f6a7b8c9d0e1
Create Date: 2026-05-17
"""
from alembic import op
import sqlalchemy as sa

revision = 'b2c3d4e5f6a7'
down_revision = 'f6a7b8c9d0e1'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.drop_column('dataset_version', 'dataset_type')

def downgrade() -> None:
    op.add_column('dataset_version', sa.Column('dataset_type', sa.String(128)))
