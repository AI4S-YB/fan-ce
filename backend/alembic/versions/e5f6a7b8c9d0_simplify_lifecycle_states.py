"""remap lifecycle states: 10→3 (draft, ready, archived)

Revision ID: e5f6a7b8c9d0
Revises: c3d4e5f6a7b8
Create Date: 2026-05-04 02:30:00.000000

"""
from alembic import op


revision = 'e5f6a7b8c9d0'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None

REMAP = {
    "draft": "draft",
    "uploaded": "draft",
    "validating": "ready",
    "validated": "ready",
    "indexing": "ready",
    "ready": "ready",
    "publishing": "ready",
    "public": "ready",
    "failed": "draft",
    "archived": "archived",
}


def upgrade() -> None:
    for old, new in REMAP.items():
        # dataset_registry
        op.execute(
            f"UPDATE dataset_registry SET lifecycle_state = '{new}' WHERE lifecycle_state = '{old}'"
        )
        # dataset_version
        op.execute(
            f"UPDATE dataset_version SET lifecycle_state = '{new}' WHERE lifecycle_state = '{old}'"
        )


def downgrade() -> None:
    # Cannot reliably reverse — remap is lossy
    pass
