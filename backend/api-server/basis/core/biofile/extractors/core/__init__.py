# core package for extractor infrastructure
from .base_extractor import BaseExtractor
from .extractor_factory import (
    factory, 
    register_extractor, 
    register_extractor_class, 
    extract_file, 
    get_supported_types, 
    get_template_info
)