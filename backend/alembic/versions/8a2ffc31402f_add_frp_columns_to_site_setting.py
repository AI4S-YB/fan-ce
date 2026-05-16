"""add_frp_columns_to_site_setting

Revision ID: 8a2ffc31402f
Revises: f5347d1ec742
Create Date: 2026-05-02 13:19:59.275765

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8a2ffc31402f'
down_revision = 'f5347d1ec742'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('pf_site_setting', sa.Column('frp_enabled', sa.Boolean(), nullable=True, comment='是否启用隧道共享'))
    op.add_column('pf_site_setting', sa.Column('frp_server_addr', sa.String(length=255), nullable=True, comment='云服务器IP地址'))
    op.add_column('pf_site_setting', sa.Column('frp_server_port', sa.Integer(), nullable=True, comment='frps绑定端口'))
    op.add_column('pf_site_setting', sa.Column('frp_token', sa.String(length=255), nullable=True, comment='frps与frpc认证密钥'))
    op.add_column('pf_site_setting', sa.Column('frp_public_port', sa.Integer(), nullable=True, comment='对外HTTP端口'))
    op.add_column('pf_site_setting', sa.Column('frp_status', sa.String(length=32), nullable=True, comment='stopped/running/error'))
    op.add_column('pf_site_setting', sa.Column('frp_config_json', sa.Text(), nullable=True, comment='高级自定义frpc配置'))


def downgrade() -> None:
    op.drop_column('pf_site_setting', 'frp_config_json')
    op.drop_column('pf_site_setting', 'frp_status')
    op.drop_column('pf_site_setting', 'frp_public_port')
    op.drop_column('pf_site_setting', 'frp_token')
    op.drop_column('pf_site_setting', 'frp_server_port')
    op.drop_column('pf_site_setting', 'frp_server_addr')
    op.drop_column('pf_site_setting', 'frp_enabled')
