"""merge_two_heads

Revision ID: 96c22c5beea4
Revises: 5769fa7b2725, a7b8c9d0e1f2
Create Date: 2026-05-16 01:32:36.586162

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '96c22c5beea4'
down_revision = ('5769fa7b2725', 'a7b8c9d0e1f2')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
