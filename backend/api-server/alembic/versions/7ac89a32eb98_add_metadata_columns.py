"""add_metadata_columns

Revision ID: 7ac89a32eb98
Revises: 8a2ffc31402f
Create Date: 2026-05-03 19:04:32.883158

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7ac89a32eb98'
down_revision = '8a2ffc31402f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add description_md to dataset_registry
    op.add_column('dataset_registry', sa.Column('description_md', sa.Text(), nullable=True, comment='Markdown 格式的数据描述文档'))

    # 2. Create trigram GIN index on description_md for full-text search
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_index(
        "ix_dataset_registry_description_md_trgm",
        "dataset_registry",
        ["description_md"],
        postgresql_using="gin",
        postgresql_ops={"description_md": "gin_trgm_ops"},
    )

    # 3. Add organism to brd_biosample
    op.add_column('brd_biosample', sa.Column('organism', sa.String(length=128), nullable=True, comment='物种'))

    # 4. Add 6 SRA columns to brd_assay
    op.add_column('brd_assay', sa.Column('library_strategy', sa.String(length=64), nullable=True, comment='文库策略: WGS, RNA-Seq, ChIP-Seq 等'))
    op.add_column('brd_assay', sa.Column('library_source', sa.String(length=64), nullable=True, comment='文库来源: GENOMIC, TRANSCRIPTOMIC 等'))
    op.add_column('brd_assay', sa.Column('library_selection', sa.String(length=64), nullable=True, comment='文库选择: PolyA, RANDOM, ChIP 等'))
    op.add_column('brd_assay', sa.Column('library_layout', sa.String(length=32), nullable=True, comment='文库布局: SINGLE, PAIRED'))
    op.add_column('brd_assay', sa.Column('instrument_model', sa.String(length=128), nullable=True, comment='仪器型号: HiSeq 4000, NovaSeq 6000 等'))
    op.add_column('brd_assay', sa.Column('read_length', sa.Integer(), nullable=True, comment='读长 bp'))


def downgrade() -> None:
    # 1. Drop trigram index on dataset_registry
    op.drop_index("ix_dataset_registry_description_md_trgm", table_name="dataset_registry", postgresql_using="gin")
    op.drop_column('dataset_registry', 'description_md')

    # 2. Drop organism from brd_biosample
    op.drop_column('brd_biosample', 'organism')

    # 3. Drop 6 SRA columns from brd_assay
    op.drop_column('brd_assay', 'read_length')
    op.drop_column('brd_assay', 'instrument_model')
    op.drop_column('brd_assay', 'library_layout')
    op.drop_column('brd_assay', 'library_selection')
    op.drop_column('brd_assay', 'library_source')
    op.drop_column('brd_assay', 'library_strategy')
