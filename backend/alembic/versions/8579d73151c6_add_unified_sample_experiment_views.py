"""add_unified_sample_experiment_views

Revision ID: 8579d73151c6
Revises: 24075ad57ea3
Create Date: 2026-04-28 19:41:23.395896

"""
from alembic import op

# revision identifiers
revision = '8579d73151c6'
down_revision = '24075ad57ea3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    from modules.datasets.unified_sample import BIOLOGICAL_SAMPLE_VIEW_DDL, SEQUENCING_EXPERIMENT_VIEW_DDL
    op.execute(BIOLOGICAL_SAMPLE_VIEW_DDL)
    op.execute(SEQUENCING_EXPERIMENT_VIEW_DDL)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS biological_sample_view")
    op.execute("DROP VIEW IF EXISTS sequencing_experiment_view")
