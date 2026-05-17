"""drop_assembly_column: remove assembly from registration_candidate and legacy table

Revision ID: ae08f2974c0f
Revises: 1b4e82a4770f
Create Date: 2026-05-17 17:45:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = 'ae08f2974c0f'
down_revision = '1b4e82a4770f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column('dataset_registration_candidate', 'assembly')


def downgrade() -> None:
    op.add_column('dataset_registration_candidate', sa.Column('assembly', sa.String(255)))
