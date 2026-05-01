# app/extractors/base_extractor.py
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import os
import json
from pathlib import Path

class BaseExtractor(ABC):
    """
    生信文件提取器基类
    
    自动加载JSON模板字段作为属性，子类只需实现extract方法给属性赋值
    """
    
    def __init__(self, template_path: str):
        self._template_fields = {}
        self._template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates', template_path)
        
        # 直接使用指定的模板文件
        self._load_template_from_path(self._template_path)
            
        self._init_fields()
    

    
    def _load_template_from_path(self, template_path: str):
        """从指定路径加载JSON模板"""
        template_file = Path(template_path)
        
        if not template_file.exists():
            raise ValueError(f"模板文件 {template_path} 不存在")
            
        if not template_file.suffix == '.json':
            raise ValueError(f"模板文件 {template_path} 必须是JSON格式")
            
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                self._template_fields = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"模板文件 {template_path} 格式错误: {e}")
    

    
    def _init_fields(self):
        """将模板字段初始化为实例属性"""
        for key, field_config in self._template_fields.items():
            if key not in ['type']:  # 保留固定字段
                # 从模板格式中提取value值进行初始化
                value = field_config['value']
                # 根据value的类型进行初始化
                if isinstance(value, list):
                    setattr(self, key, [])
                elif isinstance(value, dict):
                    # 深拷贝字典结构，保持原有的值
                    import copy
                    setattr(self, key, copy.deepcopy(value))
                else:
                    setattr(self, key, value)  # 使用模板中的默认值
    
    def _set_fields(self, data: Dict[str, Any]):
        """根据数据字典自动设置对应的属性值"""
        for key, value in data.items():
            if hasattr(self, key):  # 只设置模板中定义的字段
                setattr(self, key, value)
    
    def _build_result(self) -> Dict[str, Any]:
        """根据已设置的属性构建返回结果"""
        # 处理type字段
        type_config = self._template_fields.get("type")
        result = {
            "type": {
                "value": type_config['value'],
                "desc": type_config.get('desc', '')
            }
        }
        
        # 只包含已设置且不为None的字段
        for key, field_config in self._template_fields.items():
            if key not in ['type']:
                attr_value = getattr(self, key, None)
                if attr_value is not None:
                    result[key] = {
                        "value": attr_value,
                        "desc": field_config['desc']
                    }
        
        return result
    
    @abstractmethod
    def extract(self, path: str, sniff: Dict[str, Any]) -> Dict[str, Any]:
        """
        提取文件信息并给对应属性赋值，最后调用_build_result()返回结果
        
        Args:
            path: 文件路径
            sniff: 文件检测信息
            
        Returns:
            包含该文件类型所有已提取字段的字典
        """
        pass
    
    # 通用工具方法
    def _open_maybe_gz(self, path: str):
        """智能打开文件（支持gzip压缩）"""
        import gzip
        return gzip.open(path, "rt") if path.endswith(".gz") else open(path, "rt", encoding="utf-8", errors="replace")
    
    def _is_compressed(self, path: str) -> bool:
        """检查文件是否压缩"""
        return path.endswith(".gz")
    
    def _get_file_size(self, path: str) -> int:
        """获取文件大小"""
        return os.path.getsize(path)
    
    def _update_field(self, out: Dict[str, Any], field_path: str, value: Any) -> None:
        """根据字段路径更新输出字典"""
        keys = field_path.split('.')
        current = out
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value