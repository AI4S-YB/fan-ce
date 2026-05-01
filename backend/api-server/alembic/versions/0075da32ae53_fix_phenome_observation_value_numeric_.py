"""fix_phenome_observation_value_numeric_type

Revision ID: 0075da32ae53
Revises: 8579d73151c6
Create Date: 2026-04-29 17:51:44.623916

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0075da32ae53'
down_revision = '8579d73151c6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE phn_observation ALTER COLUMN value_numeric
        TYPE double precision USING value_numeric::double precision
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE phn_observation ALTER COLUMN value_numeric
        TYPE varchar(255) USING value_numeric::varchar
    """)
