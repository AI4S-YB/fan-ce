"""Drop legacy database_id columns after bridge removal."""
from alembic import op

revision = 'drop_legacy_database_id'
down_revision = 'consolidate_init_tables'
branch_labels = None
depends_on = None

TABLES = [
    'dataset_registry',
    'dataset_version',
    'dataset_asset',
    'asset_file',
    'dataset_lineage_edge',
    'dataset_workflow_task',
    'dataset_publish_record',
    'dataset_version_publish_record',
]


def upgrade():
    for table in TABLES:
        op.drop_column(table, 'database_id')


def downgrade():
    for table in TABLES:
        op.add_column(table, sa.Column('database_id', sa.Integer(), index=True))
