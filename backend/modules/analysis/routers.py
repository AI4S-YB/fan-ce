from fastapi import APIRouter
from .api.core import analysis_router

app_analysis_router = APIRouter()
app_analysis_router.include_router(analysis_router, prefix="/analysis")

# Include plugin API routers
from omics.analysis.registry import discover_plugin_routers
for name, plugin_router in discover_plugin_routers():
    app_analysis_router.include_router(plugin_router, prefix="/analysis")
    import logging
    logging.getLogger(__name__).info(f"Loaded plugin router: {name}")


def on_startup():
    """Register built-in tools and start the worker. Called from main.py startup."""
    import os
    from modules.analysis.worker import register_tool, start_worker, scan_plugin_dir
    from omics.analysis.registry import discover_plugins
    from shared.database import mydb

    # Discover tools from installed entry_points
    for tool in discover_plugins():
        t = register_tool(tool)
        if getattr(t, 'tool_status', None) is None:
            t.tool_status = "active"

    # Scan plugin/ directory for .whl files
    base = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )))
    plugin_dir = os.path.join(base, "plugin")
    if os.path.isdir(plugin_dir):
        try:
            scan_plugin_dir(plugin_dir)
        except Exception:
            pass

    # Start worker
    start_worker(lambda: mydb.session_local())
