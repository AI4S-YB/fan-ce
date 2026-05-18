"""migrate dataset_registry.organism from text to tax_id FK

Revision ID: c4d5e6f7a8b9
Revises: b2c3d4e5f6a8
Create Date: 2026-05-18
"""
from alembic import op

revision = 'c4d5e6f7a8b9'
down_revision = 'b2c3d4e5f6a8'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Add temp column
    op.execute("ALTER TABLE dataset_registry ADD COLUMN organism_tax_id BIGINT")
    # Map existing text values
    op.execute("UPDATE dataset_registry SET organism_tax_id = 3702 WHERE organism ILIKE '%arabidopsis%'")
    op.execute("UPDATE dataset_registry SET organism_tax_id = 3764 WHERE organism_tax_id IS NULL AND organism IS NOT NULL")
    # Drop old column
    op.execute("ALTER TABLE dataset_registry DROP COLUMN organism")
    # Rename new column
    op.execute("ALTER TABLE dataset_registry RENAME COLUMN organism_tax_id TO organism")
    # Add FK
    op.execute("ALTER TABLE dataset_registry ADD CONSTRAINT fk_dataset_registry_organism FOREIGN KEY (organism) REFERENCES brd_taxonomy_node(tax_id) ON DELETE RESTRICT")

def downgrade() -> None:
    op.execute("ALTER TABLE dataset_registry DROP CONSTRAINT fk_dataset_registry_organism")
    op.execute("ALTER TABLE dataset_registry ALTER COLUMN organism TYPE VARCHAR(128) USING organism::text")
