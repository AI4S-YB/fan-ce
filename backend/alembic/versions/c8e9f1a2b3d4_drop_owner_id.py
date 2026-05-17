"""drop owner_id from dataset_registry

Revision ID: c8e9f1a2b3d4
Revises: b5f7c3d9e210
Create Date: 2026-05-17
"""
from alembic import op
import sqlalchemy as sa

revision = 'c8e9f1a2b3d4'
down_revision = 'b5f7c3d9e210'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.drop_column('dataset_registry', 'owner_id')

def downgrade() -> None:
    op.add_column('dataset_registry', sa.Column('owner_id', sa.Integer()))
