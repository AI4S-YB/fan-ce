"""Plugin discovery: scans entry_points and returns tool instances."""
from importlib.metadata import entry_points
from .base import BaseAnalysisTool
from fastapi import APIRouter


def discover_plugins(group: str = "fance.analysis_tools") -> list[BaseAnalysisTool]:
    """Scan installed packages for analysis tool plugins."""
    tools = []
    try:
        for ep in entry_points(group=group):
            try:
                tool_cls = ep.load()
                tool = tool_cls()
                tools.append(tool)
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Failed to load plugin {ep.name}: {e}")
    except Exception:
        pass  # no entry_points available
    return tools


def discover_plugin_routers() -> list[APIRouter]:
    """Scan installed packages for plugin API routers."""
    routers = []
    try:
        for ep in entry_points(group="fance.analysis_api"):
            try:
                router = ep.load()
                routers.append((ep.name, router))
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Failed to load plugin router {ep.name}: {e}")
    except Exception:
        pass
    return routers
