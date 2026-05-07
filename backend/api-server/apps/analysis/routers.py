from fastapi import APIRouter
from .api.core import analysis_router

app_analysis_router = APIRouter()
app_analysis_router.include_router(analysis_router, prefix="/analysis")


def on_startup():
    """Register built-in tools and start the worker. Called from main.py startup."""
    from apps.analysis.tools.go_enrich import GoEnrichTool
    from apps.analysis.tools.kegg_enrich import KeggEnrichTool
    from apps.analysis.worker import register_tool, start_worker
    from db.database import mydb

    # Register built-in tools
    register_tool(GoEnrichTool())
    register_tool(KeggEnrichTool())

    # Start worker
    start_worker(lambda: mydb.session_local())
