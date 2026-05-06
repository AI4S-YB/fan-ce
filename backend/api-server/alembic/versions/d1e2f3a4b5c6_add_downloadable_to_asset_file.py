"""add is_downloadable to asset_file

Revision ID: d1e2f3a4b5c6
Revises: c3d4e5f6a7b8
Create Date: 2026-05-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'd1e2f3a4b5c6'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('asset_file', sa.Column('is_downloadable', sa.Boolean(), nullable=True, server_default=sa.text('false'), comment='是否允许公开下载'))


def downgrade() -> None:
    op.drop_column('asset_file', 'is_downloadable')
