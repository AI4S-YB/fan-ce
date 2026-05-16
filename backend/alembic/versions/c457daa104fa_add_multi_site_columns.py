"""add_multi_site_columns

Revision ID: c457daa104fa
Revises: 96c22c5beea4
Create Date: 2026-05-16 20:14:14.639441

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c457daa104fa'
down_revision = '96c22c5beea4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add site_code as nullable first (needed for backfill)
    op.add_column('pf_site_setting',
                  sa.Column('site_code', sa.String(length=64), nullable=True, comment='站点编码'))

    # 2. Add domain and test_port (nullable, no default constraint on DB side)
    op.add_column('pf_site_setting',
                  sa.Column('domain', sa.String(length=255), nullable=True, comment='正式域名'))
    op.add_column('pf_site_setting',
                  sa.Column('test_port', sa.String(length=8), nullable=True, comment='测试端口'))

    # 3. Backfill existing row(s) with a default site_code
    op.execute("UPDATE pf_site_setting SET site_code = 'default' WHERE site_code IS NULL")

    # 4. Make site_code non-nullable and add unique constraint
    op.alter_column('pf_site_setting', 'site_code', nullable=False)
    op.create_unique_constraint('uq_pf_site_setting_site_code', 'pf_site_setting', ['site_code'])

    # 5. Create pf_site_dataset_link table
    op.create_table('pf_site_dataset_link',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('site_code', sa.String(length=64), nullable=False, comment='站点编码'),
                    sa.Column('dataset_id', sa.Integer(), nullable=False, comment='数据集ID'),
                    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'),
                              nullable=True, comment='创建时间'),
                    sa.ForeignKeyConstraint(['dataset_id'], ['dataset_registry.id'], ondelete='CASCADE'),
                    sa.ForeignKeyConstraint(['site_code'], ['pf_site_setting.site_code'], ondelete='CASCADE'),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('site_code', 'dataset_id', name='uq_site_dataset_link')
                    )
    op.create_index(op.f('ix_pf_site_dataset_link_id'), 'pf_site_dataset_link', ['id'], unique=False)


def downgrade() -> None:
    # 1. Drop pf_site_dataset_link table
    op.drop_index(op.f('ix_pf_site_dataset_link_id'), table_name='pf_site_dataset_link')
    op.drop_table('pf_site_dataset_link')

    # 2. Remove unique constraint and site_code column from pf_site_setting
    op.drop_constraint('uq_pf_site_setting_site_code', 'pf_site_setting', type_='unique')
    op.drop_column('pf_site_setting', 'site_code')

    # 3. Drop domain and test_port columns
    op.drop_column('pf_site_setting', 'test_port')
    op.drop_column('pf_site_setting', 'domain')
