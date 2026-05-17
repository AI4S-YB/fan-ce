"""add foreign key constraints across dataset schema

Revision ID: a0b1c2d3e4f5
Revises: f9a0b1c2d3e4
Create Date: 2026-05-17
"""
from alembic import op

revision = 'a0b1c2d3e4f5'
down_revision = 'f9a0b1c2d3e4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Clean orphaned data before adding FKs
    op.execute("DELETE FROM dataset_version_publish_record WHERE dataset_version_id NOT IN (SELECT id FROM dataset_version)")

    # P0-1a: Core relationship chain
    op.execute("""ALTER TABLE asset_file ADD CONSTRAINT fk_asset_file_dataset_asset
        FOREIGN KEY (dataset_asset_id) REFERENCES dataset_asset(id) ON DELETE RESTRICT""")

    op.execute("""ALTER TABLE dataset_lineage_edge ADD CONSTRAINT fk_lineage_src_version
        FOREIGN KEY (src_dataset_version_id) REFERENCES dataset_version(id) ON DELETE RESTRICT""")
    op.execute("""ALTER TABLE dataset_lineage_edge ADD CONSTRAINT fk_lineage_dst_version
        FOREIGN KEY (dst_dataset_version_id) REFERENCES dataset_version(id) ON DELETE RESTRICT""")
    op.execute("""ALTER TABLE dataset_lineage_edge ADD CONSTRAINT fk_lineage_src_asset
        FOREIGN KEY (src_asset_id) REFERENCES dataset_asset(id) ON DELETE SET NULL""")
    op.execute("""ALTER TABLE dataset_lineage_edge ADD CONSTRAINT fk_lineage_dst_asset
        FOREIGN KEY (dst_asset_id) REFERENCES dataset_asset(id) ON DELETE SET NULL""")

    op.execute("""ALTER TABLE dataset_scan_job ADD CONSTRAINT fk_scan_job_root
        FOREIGN KEY (root_id) REFERENCES dataset_scan_root(id) ON DELETE RESTRICT""")

    op.execute("""ALTER TABLE dataset_staging_file ADD CONSTRAINT fk_staging_scan_root
        FOREIGN KEY (scan_root_id) REFERENCES dataset_scan_root(id) ON DELETE SET NULL""")
    op.execute("""ALTER TABLE dataset_staging_file ADD CONSTRAINT fk_staging_scan_job
        FOREIGN KEY (scan_job_id) REFERENCES dataset_scan_job(id) ON DELETE SET NULL""")
    op.execute("""ALTER TABLE dataset_staging_file ADD CONSTRAINT fk_staging_linked_dataset
        FOREIGN KEY (linked_dataset_id) REFERENCES dataset_registry(id) ON DELETE SET NULL""")

    op.execute("""ALTER TABLE dataset_version_publish_record ADD CONSTRAINT fk_version_pub_version
        FOREIGN KEY (dataset_version_id) REFERENCES dataset_version(id) ON DELETE RESTRICT""")

    op.execute("""ALTER TABLE dataset_registry ADD CONSTRAINT fk_registry_default_version
        FOREIGN KEY (default_public_version_id) REFERENCES dataset_version(id) ON DELETE SET NULL""")

    op.execute("""ALTER TABLE asset_file ADD CONSTRAINT fk_asset_file_index_of
        FOREIGN KEY (index_of_file_id) REFERENCES asset_file(id) ON DELETE SET NULL""")

    # P0-1b: Functional annotation triplets
    for table in ('functional_gene', 'functional_term', 'functional_term_assignment'):
        op.execute(f"""ALTER TABLE {table} ADD CONSTRAINT fk_{table}_dataset
            FOREIGN KEY (dataset_id) REFERENCES dataset_registry(id) ON DELETE RESTRICT""")
        op.execute(f"""ALTER TABLE {table} ADD CONSTRAINT fk_{table}_version
            FOREIGN KEY (version_id) REFERENCES dataset_version(id) ON DELETE RESTRICT""")
        op.execute(f"""ALTER TABLE {table} ADD CONSTRAINT fk_{table}_asset
            FOREIGN KEY (asset_id) REFERENCES dataset_asset(id) ON DELETE RESTRICT""")

    # Phenome tables
    for table in ('phn_import_run', 'phn_subject', 'phn_trait', 'phn_source_column',
                  'phn_observation', 'phn_trial', 'phn_plot'):
        op.execute(f"""ALTER TABLE {table} ADD CONSTRAINT fk_{table}_dataset
            FOREIGN KEY (dataset_id) REFERENCES dataset_registry(id) ON DELETE RESTRICT""")
        op.execute(f"""ALTER TABLE {table} ADD CONSTRAINT fk_{table}_version
            FOREIGN KEY (version_id) REFERENCES dataset_version(id) ON DELETE RESTRICT""")
        op.execute(f"""ALTER TABLE {table} ADD CONSTRAINT fk_{table}_asset
            FOREIGN KEY (asset_id) REFERENCES dataset_asset(id) ON DELETE RESTRICT""")

    op.execute("""ALTER TABLE phn_subject ADD CONSTRAINT fk_phn_subject_import_run
        FOREIGN KEY (import_run_id) REFERENCES phn_import_run(id) ON DELETE RESTRICT""")
    op.execute("""ALTER TABLE phn_trait ADD CONSTRAINT fk_phn_trait_import_run
        FOREIGN KEY (import_run_id) REFERENCES phn_import_run(id) ON DELETE RESTRICT""")
    op.execute("""ALTER TABLE phn_source_column ADD CONSTRAINT fk_phn_source_column_trait
        FOREIGN KEY (trait_id) REFERENCES phn_trait(id) ON DELETE RESTRICT""")
    op.execute("""ALTER TABLE phn_observation ADD CONSTRAINT fk_phn_observation_trait
        FOREIGN KEY (trait_id) REFERENCES phn_trait(id) ON DELETE RESTRICT""")

    # P0-2: Add dataset_id to workflow_task and publish_record
    op.execute("""ALTER TABLE dataset_workflow_task ADD COLUMN dataset_id INTEGER""")
    op.execute("""ALTER TABLE dataset_workflow_task ADD CONSTRAINT fk_workflow_task_dataset
        FOREIGN KEY (dataset_id) REFERENCES dataset_registry(id) ON DELETE RESTRICT""")
    op.create_index('ix_dataset_workflow_task_dataset_id', 'dataset_workflow_task', ['dataset_id'])

    op.execute("""ALTER TABLE dataset_publish_record ADD COLUMN dataset_id INTEGER""")
    op.execute("""ALTER TABLE dataset_publish_record ADD CONSTRAINT fk_publish_record_dataset
        FOREIGN KEY (dataset_id) REFERENCES dataset_registry(id) ON DELETE RESTRICT""")
    op.create_index('ix_dataset_publish_record_dataset_id', 'dataset_publish_record', ['dataset_id'])


def downgrade() -> None:
    # P0-2
    op.drop_index('ix_dataset_publish_record_dataset_id', 'dataset_publish_record')
    op.execute("ALTER TABLE dataset_publish_record DROP CONSTRAINT fk_publish_record_dataset")
    op.drop_column('dataset_publish_record', 'dataset_id')

    op.drop_index('ix_dataset_workflow_task_dataset_id', 'dataset_workflow_task')
    op.execute("ALTER TABLE dataset_workflow_task DROP CONSTRAINT fk_workflow_task_dataset")
    op.drop_column('dataset_workflow_task', 'dataset_id')

    # P0-1b Phenome
    for table in ('phn_plot', 'phn_trial', 'phn_observation', 'phn_source_column',
                  'phn_trait', 'phn_subject', 'phn_import_run'):
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT fk_{table}_asset")
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT fk_{table}_version")
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT fk_{table}_dataset")

    op.execute("ALTER TABLE phn_observation DROP CONSTRAINT fk_phn_observation_trait")
    op.execute("ALTER TABLE phn_source_column DROP CONSTRAINT fk_phn_source_column_trait")
    op.execute("ALTER TABLE phn_trait DROP CONSTRAINT fk_phn_trait_import_run")
    op.execute("ALTER TABLE phn_subject DROP CONSTRAINT fk_phn_subject_import_run")

    # Functional
    for table in ('functional_term_assignment', 'functional_term', 'functional_gene'):
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT fk_{table}_asset")
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT fk_{table}_version")
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT fk_{table}_dataset")

    # P0-1a
    op.execute("ALTER TABLE asset_file DROP CONSTRAINT fk_asset_file_index_of")
    op.execute("ALTER TABLE dataset_registry DROP CONSTRAINT fk_registry_default_version")
    op.execute("ALTER TABLE dataset_version_publish_record DROP CONSTRAINT fk_version_pub_version")
    op.execute("ALTER TABLE dataset_staging_file DROP CONSTRAINT fk_staging_linked_dataset")
    op.execute("ALTER TABLE dataset_staging_file DROP CONSTRAINT fk_staging_scan_job")
    op.execute("ALTER TABLE dataset_staging_file DROP CONSTRAINT fk_staging_scan_root")
    op.execute("ALTER TABLE dataset_scan_job DROP CONSTRAINT fk_scan_job_root")
    op.execute("ALTER TABLE dataset_lineage_edge DROP CONSTRAINT fk_lineage_dst_asset")
    op.execute("ALTER TABLE dataset_lineage_edge DROP CONSTRAINT fk_lineage_src_asset")
    op.execute("ALTER TABLE dataset_lineage_edge DROP CONSTRAINT fk_lineage_dst_version")
    op.execute("ALTER TABLE dataset_lineage_edge DROP CONSTRAINT fk_lineage_src_version")
    op.execute("ALTER TABLE asset_file DROP CONSTRAINT fk_asset_file_dataset_asset")
