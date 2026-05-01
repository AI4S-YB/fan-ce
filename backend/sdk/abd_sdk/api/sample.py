#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ABD SDK 样本管理API模块
提供样本相关的API操作
"""

from typing import Optional, Dict, Any, List
from .base import BaseAPI


class SampleAPI(BaseAPI):
    """样本管理API模块"""
    
    def __init__(self, http_client, api_prefix: str = "/api/v1"):
        super().__init__(http_client, api_prefix)
        self.base_endpoint = "/sample"
    
    def list_samples(
        self, 
        page: int = 1, 
        size: int = 20, 
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """获取样本列表"""
        return self.list_resources(
            self.base_endpoint + "/list",
            page=page,
            size=size,
            filters=filters,
            **kwargs
        )
    
    def get_sample(self, sample_id: str) -> Dict[str, Any]:
        """获取样本信息"""
        return self.get_resource(self.base_endpoint, sample_id)
    
    def create_sample(self, sample_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建样本记录"""
        return self.create_resource(self.base_endpoint, sample_data)
    
    def update_sample(self, sample_id: str, sample_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新样本信息"""
        return self.update_resource(self.base_endpoint, sample_id, sample_data)
    
    def delete_sample(self, sample_id: str) -> Dict[str, Any]:
        """删除样本记录"""
        return self.delete_resource(self.base_endpoint, sample_id)
    
    def get_sample_meta(self, sample_id: str) -> Dict[str, Any]:
        """获取样本元数据"""
        return self.get(f"{self.base_endpoint}/{sample_id}/meta")
    
    def update_sample_meta(self, sample_id: str, meta_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新样本元数据"""
        return self.put(f"{self.base_endpoint}/{sample_id}/meta", data=meta_data)
    
    def get_sample_files(
        self, 
        sample_id: str,
        page: int = 1,
        size: int = 20,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """获取样本文件列表"""
        params = {"page": page, "size": size}
        if filters:
            params.update(filters)
        
        return self.get(f"{self.base_endpoint}/{sample_id}/files", params=params)
    
    def upload_sample_file(self, sample_id: str, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """上传样本文件"""
        data = metadata or {}
        return self.upload_file(f"{self.base_endpoint}/{sample_id}/files", file_path, metadata=data)
    
    def download_sample_file(self, sample_id: str, file_id: str, save_path: str) -> str:
        """下载样本文件"""
        return self.download_file(f"{self.base_endpoint}/{sample_id}/files/{file_id}", save_path)
    
    def delete_sample_file(self, sample_id: str, file_id: str) -> Dict[str, Any]:
        """删除样本文件"""
        return self.delete(f"{self.base_endpoint}/{sample_id}/files/{file_id}")
    
    def get_sample_status(self, sample_id: str) -> Dict[str, Any]:
        """获取样本状态"""
        return self.get(f"{self.base_endpoint}/{sample_id}/status")
    
    def update_sample_status(self, sample_id: str, status: str, notes: Optional[str] = None) -> Dict[str, Any]:
        """更新样本状态"""
        data = {"status": status}
        if notes:
            data["notes"] = notes
        
        return self.put(f"{self.base_endpoint}/{sample_id}/status", data=data)
    
    def get_sample_quality(self, sample_id: str) -> Dict[str, Any]:
        """获取样本质量信息"""
        return self.get(f"{self.base_endpoint}/{sample_id}/quality")
    
    def update_sample_quality(self, sample_id: str, quality_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新样本质量信息"""
        return self.put(f"{self.base_endpoint}/{sample_id}/quality", data=quality_data)
    
    def get_sample_annotations(
        self, 
        sample_id: str,
        page: int = 1,
        size: int = 20,
        **kwargs
    ) -> Dict[str, Any]:
        """获取样本注释"""
        params = {"page": page, "size": size}
        return self.get(f"{self.base_endpoint}/{sample_id}/annotations", params=params)
    
    def add_sample_annotation(self, sample_id: str, annotation_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加样本注释"""
        return self.post(f"{self.base_endpoint}/{sample_id}/annotations", data=annotation_data)
    
    def update_sample_annotation(self, sample_id: str, annotation_id: str, annotation_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新样本注释"""
        return self.put(f"{self.base_endpoint}/{sample_id}/annotations/{annotation_id}", data=annotation_data)
    
    def delete_sample_annotation(self, sample_id: str, annotation_id: str) -> Dict[str, Any]:
        """删除样本注释"""
        return self.delete(f"{self.base_endpoint}/{sample_id}/annotations/{annotation_id}")
    
    def get_sample_experiments(
        self, 
        sample_id: str,
        page: int = 1,
        size: int = 20,
        **kwargs
    ) -> Dict[str, Any]:
        """获取样本参与的实验"""
        params = {"page": page, "size": size}
        return self.get(f"{self.base_endpoint}/{sample_id}/experiments", params=params)
    
    def get_sample_analyses(
        self, 
        sample_id: str,
        page: int = 1,
        size: int = 20,
        **kwargs
    ) -> Dict[str, Any]:
        """获取样本分析结果"""
        params = {"page": page, "size": size}
        return self.get(f"{self.base_endpoint}/{sample_id}/analyses", params=params)
    
    def create_sample_analysis(self, sample_id: str, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建样本分析"""
        return self.post(f"{self.base_endpoint}/{sample_id}/analyses", data=analysis_data)
    
    def get_sample_analysis(self, sample_id: str, analysis_id: str) -> Dict[str, Any]:
        """获取样本分析详情"""
        return self.get(f"{self.base_endpoint}/{sample_id}/analyses/{analysis_id}")
    
    def update_sample_analysis(self, sample_id: str, analysis_id: str, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新样本分析"""
        return self.put(f"{self.base_endpoint}/{sample_id}/analyses/{analysis_id}", data=analysis_data)
    
    def delete_sample_analysis(self, sample_id: str, analysis_id: str) -> Dict[str, Any]:
        """删除样本分析"""
        return self.delete(f"{self.base_endpoint}/{sample_id}/analyses/{analysis_id}")
    
    def get_sample_collections(
        self, 
        sample_id: str,
        page: int = 1,
        size: int = 20,
        **kwargs
    ) -> Dict[str, Any]:
        """获取样本所属的集合"""
        params = {"page": page, "size": size}
        return self.get(f"{self.base_endpoint}/{sample_id}/collections", params=params)
    
    def add_sample_to_collection(self, sample_id: str, collection_id: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """将样本添加到集合"""
        data = {"collection_id": collection_id}
        if metadata:
            data.update(metadata)
        
        return self.post(f"{self.base_endpoint}/{sample_id}/collections", data=data)
    
    def remove_sample_from_collection(self, sample_id: str, collection_id: str) -> Dict[str, Any]:
        """从集合中移除样本"""
        return self.delete(f"{self.base_endpoint}/{sample_id}/collections/{collection_id}")
    
    def get_sample_lineage(self, sample_id: str) -> Dict[str, Any]:
        """获取样本谱系信息"""
        return self.get(f"{self.base_endpoint}/{sample_id}/lineage")
    
    def update_sample_lineage(self, sample_id: str, lineage_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新样本谱系信息"""
        return self.put(f"{self.base_endpoint}/{sample_id}/lineage", data=lineage_data)
    
    def get_sample_relationships(
        self, 
        sample_id: str,
        relationship_type: Optional[str] = None,
        page: int = 1,
        size: int = 20,
        **kwargs
    ) -> Dict[str, Any]:
        """获取样本关系"""
        params = {"page": page, "size": size}
        if relationship_type:
            params["relationship_type"] = relationship_type
        
        return self.get(f"{self.base_endpoint}/{sample_id}/relationships", params=params)
    
    def add_sample_relationship(self, sample_id: str, relationship_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加样本关系"""
        return self.post(f"{self.base_endpoint}/{sample_id}/relationships", data=relationship_data)
    
    def get_sample_traits(
        self, 
        sample_id: str,
        page: int = 1,
        size: int = 20,
        **kwargs
    ) -> Dict[str, Any]:
        """获取样本性状"""
        params = {"page": page, "size": size}
        return self.get(f"{self.base_endpoint}/{sample_id}/traits", params=params)
    
    def add_sample_trait(self, sample_id: str, trait_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加样本性状"""
        return self.post(f"{self.base_endpoint}/{sample_id}/traits", data=trait_data)
    
    def search_samples(
        self, 
        query: str, 
        page: int = 1, 
        size: int = 20,
        **kwargs
    ) -> Dict[str, Any]:
        """搜索样本"""
        return self.search_resources(
            self.base_endpoint,
            query=query,
            page=page,
            size=size,
            **kwargs
        )
    
    def search_samples_by_metadata(self, metadata_filters: Dict[str, Any], page: int = 1, size: int = 20) -> Dict[str, Any]:
        """通过元数据搜索样本"""
        params = {"page": page, "size": size}
        params.update(metadata_filters)
        
        return self.get(f"{self.base_endpoint}/search-by-metadata", params=params)
    
    def get_sample_types(self) -> Dict[str, Any]:
        """获取样本类型列表"""
        return self.get(f"{self.base_endpoint}/types")
    
    def get_sample_sources(self) -> Dict[str, Any]:
        """获取样本来源列表"""
        return self.get(f"{self.base_endpoint}/sources")
    
    def get_sample_collections_list(
        self, 
        page: int = 1, 
        size: int = 20, 
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """获取样本集合列表"""
        return self.list_resources(
            f"{self.base_endpoint}/collections",
            page=page,
            size=size,
            filters=filters,
            **kwargs
        )
    
    def get_sample_collection(self, collection_id: str) -> Dict[str, Any]:
        """获取样本集合信息"""
        return self.get_resource(f"{self.base_endpoint}/collections", collection_id)
    
    def create_sample_collection(self, collection_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建样本集合"""
        return self.create_resource(f"{self.base_endpoint}/collections", collection_data)
    
    def update_sample_collection(self, collection_id: str, collection_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新样本集合"""
        return self.update_resource(f"{self.base_endpoint}/collections", collection_id, collection_data)
    
    def delete_sample_collection(self, collection_id: str) -> Dict[str, Any]:
        """删除样本集合"""
        return self.delete_resource(f"{self.base_endpoint}/collections", collection_id)
    
    def get_collection_samples(
        self, 
        collection_id: str,
        page: int = 1,
        size: int = 20,
        **kwargs
    ) -> Dict[str, Any]:
        """获取集合中的样本"""
        params = {"page": page, "size": size}
        return self.get(f"{self.base_endpoint}/collections/{collection_id}/samples", params=params)
    
    def export_sample_data(self, sample_id: str, format: str = "json", save_path: str = None) -> str:
        """导出样本数据"""
        if save_path is None:
            save_path = f"sample_{sample_id}.{format}"
        
        return self.download_file(f"{self.base_endpoint}/{sample_id}/export?format={format}", save_path)
    
    def import_sample_data(self, import_file_path: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """导入样本数据"""
        data = metadata or {}
        return self.upload_file(f"{self.base_endpoint}/import", import_file_path, metadata=data)
    
    def get_sample_statistics(self) -> Dict[str, Any]:
        """获取样本统计信息"""
        return self.get(f"{self.base_endpoint}/statistics")
    
    def get_sample_comparison(self, sample_ids: List[str]) -> Dict[str, Any]:
        """比较多个样本"""
        data = {"sample_ids": sample_ids}
        return self.post(f"{self.base_endpoint}/compare", data=data)
