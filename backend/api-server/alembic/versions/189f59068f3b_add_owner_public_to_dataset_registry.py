"""add owner_id and is_public to dataset_registry, backfill from databases

Revision ID: 189f59068f3b
Revises: 7ac89a32eb98
Create Date: 2026-05-03 23:32:04.855864

"""
from alembic import op
import sqlalchemy as sa


revision = '189f59068f3b'
down_revision = '7ac89a32eb98'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('dataset_registry', sa.Column('owner_id', sa.Integer(), nullable=True, comment='所有者用户 ID'))
    op.add_column('dataset_registry', sa.Column('is_public', sa.Boolean(), nullable=True, comment='是否公开'))

    # Backfill owner_id and is_public from legacy databases table
    op.execute("""
        UPDATE dataset_registry dr
        SET owner_id = d.user_id,
            is_public = d.is_public
        FROM databases d
        WHERE dr.database_id = d.id
    """)


def downgrade() -> None:
    op.drop_column('dataset_registry', 'is_public')
    op.drop_column('dataset_registry', 'owner_id')
