# Extractors package - now using ExtractorFactory from core module
from .core.extractor_factory import factory

# Auto-discover and import all extractor modules to trigger registration
def _autodiscover():
    import pkgutil
    import importlib
    pkg_name = __name__
    for m in pkgutil.iter_modules(__path__):  # type: ignore[name-defined]
        # Skip packages and files starting with underscore
        if m.ispkg or m.name.startswith("_"):
            continue
        importlib.import_module(f"{pkg_name}.{m.name}")

_autodiscover()

# Export the factory for easy access
__all__ = ['factory']