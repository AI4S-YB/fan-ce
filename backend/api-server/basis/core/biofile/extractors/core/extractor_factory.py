# app/extractors/extractor_factory.py
from typing import Dict, Any, Optional, Type
from .base_extractor import BaseExtractor
import importlib
import json
from pathlib import Path

class ExtractorFactory:
    """
    提取器工厂类
    
    负责管理和创建各种文件类型的提取器实例
    """
    
    def __init__(self):
        self._extractors: Dict[str, BaseExtractor] = {}
        self._templates: Dict[str, Dict[str, Any]] = {}
        self._load_templates()
    
    def _load_templates(self):
        """加载所有JSON模板"""
        template_dir = Path(__file__).parent.parent / "templates"
        if template_dir.exists():
            for template_file in template_dir.glob("*.json"):
                file_type = template_file.stem.upper()
                with open(template_file, 'r', encoding='utf-8') as f:
                    self._templates[file_type] = json.load(f)
    
    def register_extractor(self, file_type: str, extractor_class: Type[BaseExtractor]):
        """注册提取器类"""
        file_type = file_type.upper()
        self._extractors[file_type] = extractor_class()
    
    def get_extractor(self, file_type: str) -> Optional[BaseExtractor]:
        """获取提取器实例"""
        file_type = file_type.upper()
        return self._extractors.get(file_type)
    
    def get_template(self, file_type: str) -> Optional[Dict[str, Any]]:
        """获取文件类型的模板"""
        file_type = file_type.upper()
        return self._templates.get(file_type)
    
    def extract(self, file_type: str, path: str, sniff: Dict[str, Any]) -> Dict[str, Any]:
        """统一的提取接口"""
        extractor = self.get_extractor(file_type)
        if extractor:
            return extractor.extract(path, sniff)
        else:
            # 如果没有找到对应的提取器，返回基础结构
            template = self.get_template(file_type)
            if template:
                out = template.copy()
                out["type"] = file_type.upper()
                out["sidecars"] = sniff.get("sidecars", []) if sniff else []
                return out
            else:
                # 返回最基础的结构
                return {
                    "type": file_type.upper(),
                    "sidecars": sniff.get("sidecars", []) if sniff else []
                }
    
    def list_supported_types(self) -> list:
        """列出支持的文件类型"""
        return list(self._extractors.keys())
    
    def list_available_templates(self) -> list:
        """列出可用的模板"""
        return list(self._templates.keys())
    
    def validate_template(self, file_type: str) -> bool:
        """验证模板是否有效"""
        template = self.get_template(file_type)
        if not template:
            return False
        
        required_fields = ["type", "sidecars"]
        return all(field in template for field in required_fields)
    
    def get_extraction_fields(self, file_type: str) -> list:
        """获取需要提取的字段列表"""
        template = self.get_template(file_type)
        if not template:
            return []
        
        # 返回模板中除了基础字段外的所有字段
        basic_fields = {"type", "sidecars"}
        all_fields = [key for key in template.keys() if key not in basic_fields]
        return all_fields

# 全局工厂实例
factory = ExtractorFactory()

# 便捷函数
def register_extractor_class(file_type: str):
    """装饰器：注册提取器类"""
    def decorator(extractor_class: Type[BaseExtractor]):
        factory.register_extractor(file_type, extractor_class)
        return extractor_class
    return decorator

def extract_file(file_type: str, path: str, sniff: Dict[str, Any]) -> Dict[str, Any]:
    """便捷的文件提取函数"""
    return factory.extract(file_type, path, sniff)

def get_supported_types() -> list:
    """获取支持的文件类型列表"""
    return factory.list_supported_types()

def get_template_info(file_type: str) -> Optional[Dict[str, Any]]:
    """获取模板信息"""
    return factory.get_template(file_type)

def register_extractor(file_type: str, extractor_instance: BaseExtractor):
    """注册提取器实例"""
    file_type = file_type.upper()
    factory._extractors[file_type] = extractor_instance