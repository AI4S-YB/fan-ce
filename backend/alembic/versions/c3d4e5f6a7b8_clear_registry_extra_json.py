"""clear dataset_registry.extra_json — pipeline data now on dataset_version

Revision ID: c3d4e5f6a7b8
Revises: b7e8f9a0c1d2
Create Date: 2026-05-04 01:35:00.000000

"""
from alembic import op


revision = 'c3d4e5f6a7b8'
down_revision = 'b7e8f9a0c1d2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Pipeline provisioning data has been moved to dataset_version.extra_json.
    # Clear dataset_registry.extra_json to repurpose for user structured attributes.
    op.execute("UPDATE dataset_registry SET extra_json = NULL")


def downgrade() -> None:
    pass
