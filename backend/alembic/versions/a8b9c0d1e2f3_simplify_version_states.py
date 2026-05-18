"""remove release_state and is_default_public from dataset_version

Revision ID: a8b9c0d1e2f3
Revises: f7a8b9c0d1e2
Create Date: 2026-05-18
"""
from alembic import op
import sqlalchemy as sa

revision = 'a8b9c0d1e2f3'
down_revision = 'f7a8b9c0d1e2'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.drop_column('dataset_version', 'is_default_public')
    op.drop_column('dataset_version', 'release_state')

def downgrade() -> None:
    op.add_column('dataset_version', sa.Column('release_state', sa.String(32), server_default='unreleased'))
    op.add_column('dataset_version', sa.Column('is_default_public', sa.Boolean(), server_default='false'))
