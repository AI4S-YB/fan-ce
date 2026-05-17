"""p1p2_field_audit_fixes: normalize boolean types, rename columns, remove redundant registry fields

Revision ID: 1b4e82a4770f
Revises: drop_legacy_database_id
Create Date: 2026-05-17 17:07:26.543311
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '1b4e82a4770f'
down_revision = 'drop_legacy_database_id'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── P2.1: Rename timestamp columns to _time suffix ──
    op.alter_column('dataset_scan_job', 'started_at', new_column_name='start_time')
    op.alter_column('dataset_scan_job', 'finished_at', new_column_name='finish_time')
    op.alter_column('dataset_staging_file', 'discovered_at', new_column_name='discover_time')
    op.alter_column('dataset_staging_file', 'last_seen_at', new_column_name='last_seen_time')

    # ── P2.2: Rename extra_json -> meta_json on registry + version ──
    op.alter_column('dataset_registry', 'extra_json', new_column_name='meta_json')
    op.alter_column('dataset_version', 'extra_json', new_column_name='meta_json')

    # ── P2.3: Rename status columns ──
    op.alter_column('dataset_staging_file', 'stage_status', new_column_name='status')
    op.alter_column('dataset_workflow_task', 'task_status', new_column_name='status')
    op.alter_column('dataset_workflow_task', 'from_state', new_column_name='from_lifecycle_state')
    op.alter_column('dataset_workflow_task', 'to_state', new_column_name='to_lifecycle_state')

    # ── P1.2: Unify boolean storage (Integer -> Boolean) ──
    _int_to_bool('dataset_kind_registry', 'is_system', False)
    _int_to_bool('dataset_kind_registry', 'is_active', True)
    _int_to_bool('asset_type_registry', 'is_system', False)
    _int_to_bool('asset_type_registry', 'is_active', True)
    _int_to_bool('asset_file_type_registry', 'is_system', False)
    _int_to_bool('asset_file_type_registry', 'is_active', True)
    _int_to_bool('dataset_scan_root', 'scan_recursive', True)
    _int_to_bool('dataset_scan_root', 'include_hidden', False)
    _int_to_bool('dataset_scan_root', 'is_active', True)
    _int_to_bool('dataset_version', 'is_current', False)
    _int_to_bool('dataset_version', 'is_default_public', False)
    _int_to_bool('dataset_asset', 'is_required', True)
    _int_to_bool('dataset_asset', 'is_query_entry', False)
    _int_to_bool('dataset_registration_candidate_file', 'is_primary', False)
    _int_to_bool('dataset_registration_candidate_file', 'is_required', True)
    _int_to_bool('phn_observation', 'is_missing', False)

    # ── P1.1: Remove redundant columns from dataset_registry ──
    op.drop_column('dataset_registry', 'version')
    op.drop_column('dataset_registry', 'file_format')
    op.drop_column('dataset_registry', 'query_engine')

    # ── P1.3: Remove redundant PK id indexes (PK already creates btree index) ──
    _drop_index_if_exists('ix_asset_file_id')
    _drop_index_if_exists('ix_asset_file_type_registry_id')
    _drop_index_if_exists('ix_asset_type_registry_id')
    _drop_index_if_exists('ix_dataset_asset_id')
    _drop_index_if_exists('ix_dataset_kind_registry_id')
    _drop_index_if_exists('ix_dataset_lineage_edge_id')
    _drop_index_if_exists('ix_dataset_publish_record_id')
    _drop_index_if_exists('ix_dataset_registration_candidate_id')
    _drop_index_if_exists('ix_dataset_registration_candidate_file_id')
    _drop_index_if_exists('ix_dataset_registry_id')
    _drop_index_if_exists('ix_dataset_scan_job_id')
    _drop_index_if_exists('ix_dataset_scan_root_id')
    _drop_index_if_exists('ix_dataset_staging_file_id')
    _drop_index_if_exists('ix_dataset_version_id')
    _drop_index_if_exists('ix_dataset_version_publish_record_id')
    _drop_index_if_exists('ix_dataset_workflow_task_id')


def downgrade() -> None:
    # ── P1.3: Restore redundant PK id indexes ──
    _create_index_if_not_exists('ix_asset_file_id', 'asset_file', ['id'])
    _create_index_if_not_exists('ix_asset_file_type_registry_id', 'asset_file_type_registry', ['id'])
    _create_index_if_not_exists('ix_asset_type_registry_id', 'asset_type_registry', ['id'])
    _create_index_if_not_exists('ix_dataset_asset_id', 'dataset_asset', ['id'])
    _create_index_if_not_exists('ix_dataset_kind_registry_id', 'dataset_kind_registry', ['id'])
    _create_index_if_not_exists('ix_dataset_lineage_edge_id', 'dataset_lineage_edge', ['id'])
    _create_index_if_not_exists('ix_dataset_publish_record_id', 'dataset_publish_record', ['id'])
    _create_index_if_not_exists('ix_dataset_registration_candidate_id', 'dataset_registration_candidate', ['id'])
    _create_index_if_not_exists('ix_dataset_registration_candidate_file_id', 'dataset_registration_candidate_file', ['id'])
    _create_index_if_not_exists('ix_dataset_registry_id', 'dataset_registry', ['id'])
    _create_index_if_not_exists('ix_dataset_scan_job_id', 'dataset_scan_job', ['id'])
    _create_index_if_not_exists('ix_dataset_scan_root_id', 'dataset_scan_root', ['id'])
    _create_index_if_not_exists('ix_dataset_staging_file_id', 'dataset_staging_file', ['id'])
    _create_index_if_not_exists('ix_dataset_version_id', 'dataset_version', ['id'])
    _create_index_if_not_exists('ix_dataset_version_publish_record_id', 'dataset_version_publish_record', ['id'])
    _create_index_if_not_exists('ix_dataset_workflow_task_id', 'dataset_workflow_task', ['id'])

    # ── P1.1: Restore redundant columns on dataset_registry ──
    op.add_column('dataset_registry', sa.Column('query_engine', sa.String(128)))
    op.add_column('dataset_registry', sa.Column('file_format', sa.String(128)))
    op.add_column('dataset_registry', sa.Column('version', sa.String(64), server_default='v1'))

    # ── P1.2: Revert boolean -> Integer ──
    _bool_to_int('phn_observation', 'is_missing', 0)
    _bool_to_int('dataset_registration_candidate_file', 'is_required', 1)
    _bool_to_int('dataset_registration_candidate_file', 'is_primary', 0)
    _bool_to_int('dataset_asset', 'is_query_entry', 0)
    _bool_to_int('dataset_asset', 'is_required', 1)
    _bool_to_int('dataset_version', 'is_default_public', 0)
    _bool_to_int('dataset_version', 'is_current', 0)
    _bool_to_int('dataset_scan_root', 'is_active', 1)
    _bool_to_int('dataset_scan_root', 'include_hidden', 0)
    _bool_to_int('dataset_scan_root', 'scan_recursive', 1)
    _bool_to_int('asset_file_type_registry', 'is_active', 1)
    _bool_to_int('asset_file_type_registry', 'is_system', 0)
    _bool_to_int('asset_type_registry', 'is_active', 1)
    _bool_to_int('asset_type_registry', 'is_system', 0)
    _bool_to_int('dataset_kind_registry', 'is_active', 1)
    _bool_to_int('dataset_kind_registry', 'is_system', 0)

    # ── P2.3: Revert status column renames ──
    op.alter_column('dataset_workflow_task', 'to_lifecycle_state', new_column_name='to_state')
    op.alter_column('dataset_workflow_task', 'from_lifecycle_state', new_column_name='from_state')
    op.alter_column('dataset_workflow_task', 'status', new_column_name='task_status')
    op.alter_column('dataset_staging_file', 'status', new_column_name='stage_status')

    # ── P2.2: Revert extra_json rename ──
    op.alter_column('dataset_version', 'meta_json', new_column_name='extra_json')
    op.alter_column('dataset_registry', 'meta_json', new_column_name='extra_json')

    # ── P2.1: Revert timestamp column renames ──
    op.alter_column('dataset_staging_file', 'last_seen_time', new_column_name='last_seen_at')
    op.alter_column('dataset_staging_file', 'discover_time', new_column_name='discovered_at')
    op.alter_column('dataset_scan_job', 'finish_time', new_column_name='finished_at')
    op.alter_column('dataset_scan_job', 'start_time', new_column_name='started_at')


def _int_to_bool(table, column, default):
    """Convert an Integer 0/1 column to Boolean."""
    op.execute(
        f'ALTER TABLE {table} ALTER COLUMN {column} TYPE BOOLEAN USING ({column}::int != 0)'
    )
    if default is True:
        op.execute(f"ALTER TABLE {table} ALTER COLUMN {column} SET DEFAULT TRUE")
    elif default is False:
        op.execute(f"ALTER TABLE {table} ALTER COLUMN {column} SET DEFAULT FALSE")


def _bool_to_int(table, column, default):
    """Convert a Boolean column back to Integer 0/1."""
    op.execute(
        f'ALTER TABLE {table} ALTER COLUMN {column} TYPE INTEGER USING (CASE WHEN {column} THEN 1 ELSE 0 END)'
    )
    op.execute(f"ALTER TABLE {table} ALTER COLUMN {column} SET DEFAULT {default}")


def _drop_index_if_exists(idx):
    """Drop an index if it exists (ignore error if not found)."""
    op.execute(f'DROP INDEX IF EXISTS {idx}')


def _create_index_if_not_exists(idx, table, columns):
    """Create an index if it does not already exist."""
    col_str = ', '.join(columns)
    op.execute(f'CREATE INDEX IF NOT EXISTS {idx} ON {table} ({col_str})')
