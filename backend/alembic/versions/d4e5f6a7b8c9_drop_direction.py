"""drop direction from dataset_lineage_edge

Revision ID: d4e5f6a7b8c9
Revises: c8e9f1a2b3d4
Create Date: 2026-05-17
"""
from alembic import op
import sqlalchemy as sa

revision = 'd4e5f6a7b8c9'
down_revision = 'c8e9f1a2b3d4'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.drop_column('dataset_lineage_edge', 'direction')

def downgrade() -> None:
    op.add_column('dataset_lineage_edge', sa.Column('direction', sa.String(16), server_default='forward'))
