"""fix remaining Integer boolean columns

Revision ID: b2c3d4e5f6a8
Revises: a0b1c2d3e4f5
Create Date: 2026-05-17
"""
from alembic import op

revision = 'b2c3d4e5f6a8'
down_revision = 'a0b1c2d3e4f5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE brd_germplasm ALTER COLUMN is_public TYPE BOOLEAN USING (is_public::int != 0)")
    op.execute("ALTER TABLE brd_germplasm ALTER COLUMN is_public SET DEFAULT FALSE")
    op.execute("ALTER TABLE brd_germplasm_import_batch ALTER COLUMN is_public TYPE BOOLEAN USING (is_public::int != 0)")
    op.execute("ALTER TABLE brd_germplasm_import_batch ALTER COLUMN is_public SET DEFAULT FALSE")
    op.execute("ALTER TABLE system_role ALTER COLUMN is_active TYPE BOOLEAN USING (is_active::int != 0)")
    op.execute("ALTER TABLE system_role ALTER COLUMN is_active SET DEFAULT FALSE")
    op.execute("ALTER TABLE system_users ALTER COLUMN is_active TYPE BOOLEAN USING (is_active::int != 0)")
    op.execute("ALTER TABLE system_users ALTER COLUMN is_active SET DEFAULT FALSE")


def downgrade() -> None:
    for table, col in [('brd_germplasm', 'is_public'), ('brd_germplasm_import_batch', 'is_public'),
                        ('system_role', 'is_active'), ('system_users', 'is_active')]:
        op.execute(f"ALTER TABLE {table} ALTER COLUMN {col} TYPE INTEGER USING (CASE WHEN {col} THEN 1 ELSE 0 END)")
        op.execute(f"ALTER TABLE {table} ALTER COLUMN {col} SET DEFAULT 0")
