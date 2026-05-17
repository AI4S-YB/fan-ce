"""migrate all Integer timestamp columns to TIMESTAMPTZ

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
Create Date: 2026-05-17
"""
from alembic import op

revision = 'e7f8a9b0c1d2'
down_revision = 'd6e7f8a9b0c1'
branch_labels = None
depends_on = None

TABLES_AND_COLUMNS = {
    'abd_experiment': ['create_time', 'update_time'],
    'abd_experiment_meta': ['create_time'],
    'abd_sample': ['create_time', 'update_time'],
    'abd_sample_meta': ['create_time'],
    'asset_file': ['create_time', 'update_time'],
    'asset_file_type_registry': ['create_time', 'update_time'],
    'asset_type_registry': ['create_time', 'update_time'],
    'brd_analysis_job': ['started_at', 'finished_at'],
    'dataset_asset': ['create_time', 'update_time'],
    'dataset_kind_registry': ['create_time', 'update_time'],
    'dataset_lineage_edge': ['create_time'],
    'dataset_publish_record': ['create_time'],
    'dataset_registry': ['create_time', 'update_time'],
    'dataset_scan_job': ['create_time', 'update_time', 'start_time', 'finish_time'],
    'dataset_scan_root': ['create_time', 'update_time', 'last_scan_time'],
    'dataset_staging_file': ['create_time', 'update_time', 'discover_time', 'last_seen_time'],
    'dataset_version': ['create_time', 'update_time'],
    'dataset_version_publish_record': ['create_time'],
    'dataset_workflow_task': ['create_time', 'finish_time'],
    'functional_gene': ['create_time', 'update_time'],
    'functional_term': ['create_time', 'update_time'],
    'functional_term_assignment': ['create_time'],
    'gene_set': ['create_time'],
    'gene_set_link': ['create_time'],
    'pf_model_api_setting': ['create_time', 'update_time'],
    'pf_news': ['create_time'],
    'pf_site_setting': ['create_time', 'update_time'],
    'phn_import_run': ['create_time', 'update_time'],
    'phn_observation': ['create_time'],
    'phn_plot': ['create_time', 'update_time'],
    'phn_source_column': ['create_time'],
    'phn_subject': ['create_time', 'update_time'],
    'phn_trait': ['create_time', 'update_time'],
    'phn_trial': ['create_time', 'update_time'],
    'system_dict_data': ['create_time', 'update_time'],
    'system_dict_field': ['create_time'],
    'system_log': ['create_time'],
    'system_menu': ['create_time'],
    'system_permission': ['create_time'],
    'system_role': ['create_time'],
    'system_users': ['create_time', 'update_time'],
}


def upgrade() -> None:
    for table, columns in TABLES_AND_COLUMNS.items():
        for column in columns:
            op.execute(
                f"""ALTER TABLE {table}
                ALTER COLUMN {column} TYPE TIMESTAMPTZ
                USING CASE
                    WHEN {column} IS NULL THEN NULL
                    WHEN {column} = 0 THEN NULL
                    ELSE to_timestamp({column})
                END"""
            )


def downgrade() -> None:
    for table, columns in TABLES_AND_COLUMNS.items():
        for column in columns:
            op.execute(
                f"""ALTER TABLE {table}
                ALTER COLUMN {column} TYPE INTEGER
                USING CASE
                    WHEN {column} IS NULL THEN 0
                    ELSE extract(epoch FROM {column})::int
                END"""
            )
