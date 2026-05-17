"""Consolidate table creation from init_*_tables() into alembic.

This migration replaces the table.create(checkfirst=True) calls in:
- modules/breeding/init.py
- modules/datasets/init.py
- modules/platform/init.py
- modules/system/init.py

All ORM-registered tables are created here. checkfirst=True ensures
existing tables are not recreated.
"""
from alembic import op

# revision identifiers
revision = 'consolidate_init_tables'
down_revision = 'c457daa104fa'
branch_labels = None
depends_on = None


def upgrade():
    from shared.database import Base
    # Import all model modules to register tables with Base.metadata
    import modules.breeding.models as _bm       # noqa: F401
    import modules.datasets.models as _dm       # noqa: F401
    import modules.datasets.dataset_model as _ddm  # noqa: F401
    import modules.platform.models as _pm       # noqa: F401
    import modules.system.base.models as _sm    # noqa: F401
    import modules.analysis.models as _am       # noqa: F401

    Base.metadata.create_all(bind=op.get_bind(), checkfirst=True)


def downgrade():
    # Baseline tables should not be dropped automatically
    pass
