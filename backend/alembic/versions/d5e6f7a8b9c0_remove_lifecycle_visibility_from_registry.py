"""remove lifecycle_state and visibility from dataset_registry

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-05-18
"""
from alembic import op
import sqlalchemy as sa

revision = 'd5e6f7a8b9c0'
down_revision = 'c4d5e6f7a8b9'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.drop_column('dataset_registry', 'visibility')
    op.drop_column('dataset_registry', 'lifecycle_state')

def downgrade() -> None:
    op.add_column('dataset_registry', sa.Column('lifecycle_state', sa.String(64), server_default='draft'))
    op.add_column('dataset_registry', sa.Column('visibility', sa.String(32), server_default='private'))
