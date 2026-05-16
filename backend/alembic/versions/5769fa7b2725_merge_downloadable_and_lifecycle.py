"""merge_downloadable_and_lifecycle

Revision ID: 5769fa7b2725
Revises: d1e2f3a4b5c6, e5f6a7b8c9d0
Create Date: 2026-05-06 09:38:11.273116

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5769fa7b2725'
down_revision = ('d1e2f3a4b5c6', 'e5f6a7b8c9d0')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
