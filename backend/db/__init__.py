"""Backward-compat shim for plugins that import from db.* — use shared.* instead."""
import warnings
warnings.warn("Importing from db.* is deprecated. Use shared.* instead.", DeprecationWarning)
