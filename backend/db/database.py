"""Backward-compat shim — re-exports from shared.database."""
from shared.database import get_db, get_db3, MyDBManager, mydb, engine, Base  # noqa: F401
