"""refactor site_setting: replace domain/ip/port with logo/copyright/contact

Revision ID: a7b8c9d0e1f2
Revises: d1e2f3a4b5c6
Create Date: 2026-05-06 11:00:00

"""
from alembic import op
import sqlalchemy as sa


revision = 'a7b8c9d0e1f2'
down_revision = 'd1e2f3a4b5c6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column('pf_site_setting', 'domain')
    op.drop_column('pf_site_setting', 'ip_address')
    op.drop_column('pf_site_setting', 'port')
    op.add_column('pf_site_setting', sa.Column('logo_text', sa.String(255), nullable=True, server_default='', comment='Logo 文字'))
    op.add_column('pf_site_setting', sa.Column('contact_email', sa.String(255), nullable=True, server_default='', comment='联系邮箱'))
    op.add_column('pf_site_setting', sa.Column('footer_copyright', sa.String(255), nullable=True, server_default='', comment='Footer 版权信息'))


def downgrade() -> None:
    op.drop_column('pf_site_setting', 'footer_copyright')
    op.drop_column('pf_site_setting', 'contact_email')
    op.drop_column('pf_site_setting', 'logo_text')
    op.add_column('pf_site_setting', sa.Column('port', sa.Integer(), nullable=True, server_default='0', comment='通信端口'))
    op.add_column('pf_site_setting', sa.Column('ip_address', sa.String(255), nullable=True, server_default='', comment='服务IP地址'))
    op.add_column('pf_site_setting', sa.Column('domain', sa.String(255), nullable=True, server_default='', comment='网站域名'))
