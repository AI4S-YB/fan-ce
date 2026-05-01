"""remove_team_tables_and_columns

Revision ID: a1b2c3d4e5f6
Revises: 8579d73151c6
Create Date: 2026-05-01 00:00:00.000000

"""
from alembic import op

# revision identifiers
revision = 'a1b2c3d4e5f6'
down_revision = '8579d73151c6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop team_id columns from existing tables
    op.drop_column('databases', 'team_id')
    op.drop_column('gene_set', 'team_id')
    op.drop_column('pf_news', 'team_id')

    # Drop team-related tables
    op.drop_table('system_team_user')
    op.drop_table('system_team_project')
    op.drop_table('system_team_role')
    op.drop_table('system_team')


def downgrade() -> None:
    # Community edition: no rollback for breaking change
    pass
