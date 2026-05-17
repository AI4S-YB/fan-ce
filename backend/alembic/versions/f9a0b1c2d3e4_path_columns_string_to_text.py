"""widen path columns from String(1024) to Text

Revision ID: f9a0b1c2d3e4
Revises: e7f8a9b0c1d2
Create Date: 2026-05-17
"""
from alembic import op

revision = 'f9a0b1c2d3e4'
down_revision = 'e7f8a9b0c1d2'
branch_labels = None
depends_on = None

COLUMNS = {
    'dataset_scan_root': ['root_path'],
    'dataset_staging_file': ['storage_uri', 'local_path', 'relative_path'],
    'asset_file': ['storage_uri', 'local_path'],
    'dataset_version': ['file_path'],
    'phn_import_run': ['source_file_path'],
}


def upgrade() -> None:
    for table, columns in COLUMNS.items():
        for column in columns:
            op.execute(f'ALTER TABLE {table} ALTER COLUMN {column} TYPE TEXT')


def downgrade() -> None:
    for table, columns in COLUMNS.items():
        for column in columns:
            op.execute(f'ALTER TABLE {table} ALTER COLUMN {column} TYPE VARCHAR(1024)')
