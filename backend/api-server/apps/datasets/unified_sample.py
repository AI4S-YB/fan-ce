"""Unified BiologicalSample and SequencingExperiment VIEW definitions.

These PostgreSQL views UNION ALL old SRA models (abd_sample/abd_experiment)
with new Breeding models (brd_biosample/brd_assay) for cross-domain queries.
"""

BIOLOGICAL_SAMPLE_VIEW_DDL = """
CREATE OR REPLACE VIEW biological_sample_view AS
SELECT
    id AS source_id,
    sample_code,
    sample_name,
    type AS sample_type,
    NULL::bigint AS material_id,
    project_id::bigint AS project_id,
    NULL::bigint AS program_id,
    'abd_sample' AS source_table,
    to_timestamp(create_time) AS created_at,
    to_timestamp(update_time) AS updated_at
FROM abd_sample
WHERE is_delete = false

UNION ALL

SELECT
    id AS source_id,
    sample_code,
    NULL::varchar AS sample_name,
    sample_type,
    material_id,
    NULL::bigint AS project_id,
    (SELECT program_id FROM brd_material WHERE id = brd_biosample.material_id) AS program_id,
    'brd_biosample' AS source_table,
    created_at,
    updated_at
FROM brd_biosample
WHERE status = 'active'
"""

SEQUENCING_EXPERIMENT_VIEW_DDL = """
CREATE OR REPLACE VIEW sequencing_experiment_view AS
SELECT
    e.id AS source_id,
    e.accession AS experiment_code,
    e.title AS experiment_name,
    e.experiment_type,
    e.library_strategy,
    e.platform,
    e.instrument_model,
    e.read_length,
    e.sample_id AS old_sample_id,
    NULL::bigint AS biosample_id,
    NULL::bigint AS assay_id,
    'abd_experiment' AS source_table,
    to_timestamp(e.create_time) AS created_at
FROM abd_experiment e
WHERE e.is_delete = false

UNION ALL

SELECT
    a.id AS source_id,
    a.assay_code AS experiment_code,
    NULL::varchar AS experiment_name,
    a.assay_type AS experiment_type,
    NULL::varchar AS library_strategy,
    a.platform,
    NULL::varchar AS instrument_model,
    NULL::integer AS read_length,
    NULL::integer AS old_sample_id,
    a.biosample_id,
    a.id AS assay_id,
    'brd_assay' AS source_table,
    a.created_at
FROM brd_assay a
JOIN brd_biosample bs ON bs.id = a.biosample_id
WHERE a.status = 'active'
"""


def create_unified_views(connection):
    """Execute CREATE OR REPLACE VIEW DDL on the given connection."""
    from sqlalchemy import text
    connection.execute(text(BIOLOGICAL_SAMPLE_VIEW_DDL))
    connection.execute(text(SEQUENCING_EXPERIMENT_VIEW_DDL))


def drop_unified_views(connection):
    """Drop the unified views."""
    from sqlalchemy import text
    connection.execute(text("DROP VIEW IF EXISTS biological_sample_view"))
    connection.execute(text("DROP VIEW IF EXISTS sequencing_experiment_view"))
