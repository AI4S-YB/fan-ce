"""migrate meta_json from Text to JSONB

Revision ID: f6a7b8c9d0e1
Revises: d4e5f6a7b8c9
Create Date: 2026-05-17
"""
from alembic import op

revision = 'f6a7b8c9d0e1'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None

TABLES = [
    'abd_experiment', 'abd_sample',
    'asset_file', 'asset_file_type_registry', 'asset_type_registry',
    'brd_assay', 'brd_biosample', 'brd_data_file', 'brd_material',
    'brd_observation', 'brd_plot', 'brd_program', 'brd_trial',
    'dataset_asset', 'dataset_kind_registry', 'dataset_registry',
    'dataset_staging_file', 'dataset_version',
    'phn_observation', 'phn_plot', 'phn_source_column',
    'phn_subject', 'phn_trait', 'phn_trial',
]


def upgrade() -> None:
    for table in TABLES:
        op.execute(
            f"""ALTER TABLE {table}
            ALTER COLUMN meta_json TYPE JSONB
            USING CASE
                WHEN meta_json IS NULL THEN NULL
                WHEN meta_json = '' THEN NULL
                ELSE meta_json::jsonb
            END"""
        )


def downgrade() -> None:
    for table in TABLES:
        op.execute(
            f'ALTER TABLE {table} ALTER COLUMN meta_json TYPE TEXT USING meta_json::text'
        )
