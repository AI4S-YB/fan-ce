"""drop_system_project

Revision ID: f5347d1ec742
Revises: 1b007813bced
Create Date: 2026-05-02 01:43:29.914904

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = 'f5347d1ec742'
down_revision = '1b007813bced'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop system_project and system_project_meta tables
    op.drop_table('system_project_meta')
    op.drop_table('system_project')

    # Drop dataset.project_id column
    op.drop_column('dataset', 'project_id')


def downgrade() -> None:
    # Community edition: no rollback for breaking change
    pass
