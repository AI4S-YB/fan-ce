"""drop legacy databases tables

Revision ID: d7f2a3c4e5b6
Revises: 189f59068f3b
Create Date: 2026-05-03 23:55:00.000000

"""
from alembic import op


revision = 'd7f2a3c4e5b6'
down_revision = '189f59068f3b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop FK-dependent tables first, then the parent
    op.drop_table('databases_metadata')
    op.drop_table('databases_file')
    op.drop_table('project_database')
    op.drop_table('experiment_databases_link')
    op.drop_table('databases')


def downgrade() -> None:
    # Not reversible — these tables are legacy and data has been migrated
    pass
