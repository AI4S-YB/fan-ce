"""remove file_path,file_format,query_engine,validation_summary,index_summary from dataset_version

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-05-18
"""
from alembic import op
import sqlalchemy as sa

revision = 'f7a8b9c0d1e2'
down_revision = 'e6f7a8b9c0d1'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.drop_column('dataset_version', 'index_summary')
    op.drop_column('dataset_version', 'validation_summary')
    op.drop_column('dataset_version', 'query_engine')
    op.drop_column('dataset_version', 'file_format')
    op.drop_column('dataset_version', 'file_path')

def downgrade() -> None:
    op.add_column('dataset_version', sa.Column('file_path', sa.Text()))
    op.add_column('dataset_version', sa.Column('file_format', sa.String(128)))
    op.add_column('dataset_version', sa.Column('query_engine', sa.String(128)))
    op.add_column('dataset_version', sa.Column('validation_summary', sa.Text()))
    op.add_column('dataset_version', sa.Column('index_summary', sa.Text()))
