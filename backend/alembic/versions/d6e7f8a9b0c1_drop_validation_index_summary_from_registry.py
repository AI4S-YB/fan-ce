"""drop validation_summary and index_summary from dataset_registry

Revision ID: d6e7f8a9b0c1
Revises: b2c3d4e5f6a7
Create Date: 2026-05-17
"""
from alembic import op
import sqlalchemy as sa

revision = 'd6e7f8a9b0c1'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.drop_column('dataset_registry', 'index_summary')
    op.drop_column('dataset_registry', 'validation_summary')

def downgrade() -> None:
    op.add_column('dataset_registry', sa.Column('validation_summary', sa.Text()))
    op.add_column('dataset_registry', sa.Column('index_summary', sa.Text()))
