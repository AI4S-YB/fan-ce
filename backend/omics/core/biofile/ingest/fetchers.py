# fetchers.py - 文件获取器模块

import os
import tempfile
from typing import Dict, Any
from pathlib import Path
import logging

# 配置logger
logger = logging.getLogger(__name__)

class FetchError(Exception):
    """文件获取异常"""
    pass

def parse_obs_event(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    解析 OBS 事件数据，提取文件信息
    
    Args:
        event_data: OBS 事件数据
    
    Returns:
        Dict: 包含文件规格信息的字典
    """
    try:
        # 解析实际的 OBS 事件结构
        records = event_data.get("Records", [])
        if not records:
            raise FetchError("No records found in OBS event")
        
        record = records[0]  # 取第一条记录
        
        # 获取 OBS 事件信息
        obs_info = record.get("obs", {})
        bucket_info = obs_info.get("bucket", {})
        object_info = obs_info.get("object", {})
        
        bucket_name = bucket_info.get("name")
        object_key = object_info.get("key")
        
        return {
            "metadata": {
                "bucket": bucket_name,
                "key": object_key,
                "size": object_info.get("size"),
                "event_name": record.get("eventName"),
                "event_time": record.get("eventTime"),
                "event_version": record.get("eventVersion"),
                "event_source": record.get("eventSource")
            },
            "source_type": "obs",
            "url": f"obs://{bucket_name}/{object_key}",
            # 添加本地文件路径信息（用于回退机制）
            "local_path": f"/data/{bucket_name}{object_key}" if bucket_name and object_key else None
        }
    except Exception as e:
        raise FetchError(f"Failed to parse OBS event: {str(e)}")

def fetch_to_local(file_spec: Dict[str, Any]) -> str:
    """
    根据文件规格下载文件到本地临时目录
    
    Args:
        file_spec: 文件规格信息
    
    Returns:
        str: 本地临时文件路径
    """
    import shutil
    
    try:
        metadata = file_spec.get("metadata", {})
        bucket = metadata.get("bucket")
        key = metadata.get("key")
        local_path = file_spec.get("local_path")
        
        if not bucket or not key:
            raise FetchError("Missing bucket or key in file specification")
        
        # 过滤掉 aria2 临时文件和其他临时文件
        if key and (key.endswith('.aria2') or key.endswith('.tmp') or key.endswith('.part')):
            raise FetchError(f"跳过临时文件处理: {key}")
        
        # 创建临时文件
        suffix = Path(key).suffix if key else ""
        fd, tmp_path = tempfile.mkstemp(suffix=suffix, prefix="obs_fetch_")
        os.close(fd)
        
        # 尝试方法1：使用 OBS SDK 下载（当前未实现）
        obs_download_success = False
        try:
            # TODO: 实现实际的 OBS 下载逻辑
            # 这里需要根据实际的 OBS SDK 来实现文件下载
            # 示例代码（需要替换为实际的下载逻辑）:
            # obs_client = ObsClient(...)
            # obs_client.getObject(bucket, key, downloadPath=tmp_path)
            # obs_download_success = True
            logger.warning(f"⚠️ OBS SDK 下载功能暂未实现，尝试本地路径回退机制")
        except Exception as obs_error:
            logger.warning(f"⚠️ OBS SDK 下载失败: {obs_error}")
        
        # 方法2：本地文件路径回退机制
        if not obs_download_success and local_path:
            logger.info(f"🔄 尝试从本地路径获取文件: {local_path}")
            
            if os.path.exists(local_path) and os.path.isfile(local_path):
                # 直接复制本地文件到临时目录
                shutil.copy2(local_path, tmp_path)
                logger.info(f"✅ 文件已从本地路径复制到临时目录: {local_path} -> {tmp_path}")
                return tmp_path
            else:
                # 尝试不同的本地路径映射策略
                alternative_paths = [
                    f"/data/{bucket}/{key}",  # 标准路径
                    f"/data/{key}",           # 简化路径
                    f"/tmp/{key}",            # 临时目录路径
                    key,                      # 直接使用key作为绝对路径
                    f"/data{key}",            # data目录 + key路径
                    key.lstrip('/'),          # 去掉开头的斜杠，作为相对路径
                ]
                
                for alt_path in alternative_paths:
                    if os.path.exists(alt_path) and os.path.isfile(alt_path):
                        shutil.copy2(alt_path, tmp_path)
                        logger.info(f"✅ 文件已从替代路径复制: {alt_path} -> {tmp_path}")
                        return tmp_path
                
                raise FetchError(f"本地文件不存在，已尝试路径: {local_path}, {', '.join(alternative_paths)}")
        
        # 方法3：如果以上都失败，创建占位符文件（用于测试）
        if not obs_download_success and not local_path:
            logger.warning(f"⚠️ 无可用的文件获取方式，创建占位符文件")
            with open(tmp_path, 'w') as f:
                f.write(f"# Placeholder for {bucket}/{key}\n")
            logger.info(f"📝 占位符文件已创建: {tmp_path}")
        
        return tmp_path
        
    except Exception as e:
        # 清理可能创建的临时文件
        if 'tmp_path' in locals() and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except:
                pass
        raise FetchError(f"Failed to fetch file: {str(e)}")