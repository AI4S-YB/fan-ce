import os
from typing import Dict, Any
from .detector import detect_path
from .extractors import factory


def analyze_file(path: str) -> Dict[str, Any]:
    """
    分析生物文件，返回文件类型检测结果和元数据
    
    Args:
        path: 文件路径
        
    Returns:
        包含检测结果和元数据的字典:
        {
            "detect": {...},     # 文件类型检测结果
            "metadata": {...}    # 文件元数据
        }
    """
    # 1. 获取文件基本信息
    file_size = _get_file_size(path)
    
    # 2. 文件类型检测
    detection_result = detect_path(path)
    detection_result = _normalize_detection_result(detection_result)
    file_type = _extract_file_type(detection_result)
    
    # 3. 元数据提取
    metadata = _extract_metadata(file_type, path, detection_result, file_size)
    
    return {
        "detect": detection_result,
        "metadata": metadata
    }


def _get_file_size(path: str) -> int:
    """获取文件大小，异常时返回0"""
    try:
        return os.path.getsize(path)
    except (OSError, IOError):
        return 0


def _normalize_detection_result(detection_result: Dict[str, Any]) -> Dict[str, Any]:
    """标准化检测结果，修正字段名以匹配响应模型"""
    if 'tmp_path' in detection_result:
        detection_result['path'] = detection_result.pop('tmp_path')
    return detection_result


def _extract_file_type(detection_result: Dict[str, Any]) -> str:
    """从检测结果中提取文件类型"""
    candidates = detection_result.get("candidates") or [{}]
    top_candidate = candidates[0] if candidates else {}
    return top_candidate.get("type") or "unknown"


def _extract_metadata(file_type: str, path: str, detection_result: Dict[str, Any], file_size: int) -> Dict[str, Any]:
    """提取文件元数据"""
    # 检查是否有对应的提取器
    if file_type.upper() not in factory.list_supported_types():
        return _create_unsupported_metadata(file_type, file_size)
    
    try:
        # 使用提取器提取元数据
        metadata = factory.extract(file_type, path, detection_result)
        
        # 添加文件大小信息
        if isinstance(metadata, dict):
            metadata["file_size"] = {
                "value": file_size,
                "desc": "文件大小（字节）"
            }
        
        return metadata
    except Exception as e:
        # 如果提取过程中出现异常，返回带有错误信息的基础元数据
        error_metadata = _create_unsupported_metadata(file_type, file_size)
        error_metadata["note"] = {
            "value": f"extraction failed: {str(e)}",
            "desc": "处理说明"
        }
        return error_metadata


def _create_unsupported_metadata(file_type: str, file_size: int) -> Dict[str, Any]:
    """为不支持的文件类型创建基础元数据"""
    return {
        "type": {
            "value": file_type,
            "desc": "文件类型标识"
        },
        "summary": {
            "value": {},
            "desc": "文件摘要信息"
        },
        "note": {
            "value": "no extractor registered",
            "desc": "处理说明"
        },
        "file_size": {
            "value": file_size,
            "desc": "文件大小（字节）"
        }
    }