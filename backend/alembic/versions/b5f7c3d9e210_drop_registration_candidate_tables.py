"""drop registration candidate tables

Revision ID: b5f7c3d9e210
Revises: ae08f2974c0f
Create Date: 2026-05-17
"""
from alembic import op
import sqlalchemy as sa

revision = 'b5f7c3d9e210'
down_revision = 'ae08f2974c0f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table('dataset_registration_candidate_file')
    op.drop_table('dataset_registration_candidate')


def downgrade() -> None:
    op.create_table('dataset_registration_candidate',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('candidate_code', sa.String(128)),
        sa.Column('scan_root_id', sa.Integer()),
        sa.Column('dataset_type', sa.String(128)),
        sa.Column('recipe_code', sa.String(128)),
        sa.Column('registration_mode', sa.String(64)),
        sa.Column('candidate_name', sa.String(320)),
        sa.Column('version_name', sa.String(128)),
        sa.Column('organism', sa.String(255)),
        sa.Column('reference_dataset_id', sa.Integer()),
        sa.Column('reference_version_id', sa.Integer()),
        sa.Column('status', sa.String(64)),
        sa.Column('validation_status', sa.String(64)),
        sa.Column('build_status', sa.String(64)),
        sa.Column('registration_status', sa.String(64)),
        sa.Column('source_kind', sa.String(64)),
        sa.Column('meta_json', sa.Text()),
        sa.Column('create_user_id', sa.Integer()),
        sa.Column('create_time', sa.Integer()),
        sa.Column('update_time', sa.Integer()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('candidate_code', name='uq_dataset_registration_candidate_code'),
    )
    op.create_table('dataset_registration_candidate_file',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('candidate_id', sa.Integer()),
        sa.Column('staging_file_id', sa.Integer()),
        sa.Column('source_role', sa.String(128)),
        sa.Column('asset_type', sa.String(128)),
        sa.Column('asset_file_type_code', sa.String(128)),
        sa.Column('file_role', sa.String(64)),
        sa.Column('is_primary', sa.Boolean()),
        sa.Column('is_required', sa.Boolean()),
        sa.Column('validation_status', sa.String(64)),
        sa.Column('confidence', sa.Float()),
        sa.Column('origin_type', sa.String(64)),
        sa.Column('sort_order', sa.Integer()),
        sa.Column('meta_json', sa.Text()),
        sa.Column('create_time', sa.Integer()),
        sa.Column('update_time', sa.Integer()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('candidate_id', 'staging_file_id', name='uq_dataset_registration_candidate_file_candidate_staging'),
    )
