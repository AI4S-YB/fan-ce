"""drop assembly column from dataset_registry

Revision ID: b7e8f9a0c1d2
Revises: d7f2a3c4e5b6
Create Date: 2026-05-04 01:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'b7e8f9a0c1d2'
down_revision = 'd7f2a3c4e5b6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column('dataset_registry', 'assembly')


def downgrade() -> None:
    op.add_column('dataset_registry', sa.Column('assembly', sa.VARCHAR(length=128), nullable=True, comment='组装版本'))
