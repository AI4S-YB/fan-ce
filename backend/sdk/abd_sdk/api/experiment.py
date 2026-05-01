#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ABD SDK 实验管理API模块
提供实验相关的API操作
"""

from typing import Optional, Dict, Any, List
from .base import BaseAPI


class ExperimentAPI(BaseAPI):
    """实验管理API模块"""
    
    def __init__(self, http_client, api_prefix: str = "/api/v1"):
        super().__init__(http_client, api_prefix)
        self.base_endpoint = "/experiments"
    
    def list_experiments(
        self, 
        page: int = 1, 
        size: int = 20, 
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """获取实验列表"""
        return self.list_resources(
            self.base_endpoint,
            page=page,
            size=size,
            filters=filters,
            **kwargs
        )
    
    def get_experiment(self, experiment_id: str) -> Dict[str, Any]:
        """获取实验信息"""
        data = {"id": experiment_id}
        return self.post(f"{self.base_endpoint}/profile", data=data)
    
    def create_experiment(self, experiment_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建实验"""
        return self.create_resource(self.base_endpoint, experiment_data)
    
    def update_experiment(self, experiment_id: str, experiment_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新实验"""
        experiment_data["id"] = experiment_id
        return self.post(f"{self.base_endpoint}/update", data=experiment_data)
    
    def delete_experiment(self, experiment_id: str) -> Dict[str, Any]:
        """删除实验"""
        data = {"id": experiment_id}
        return self.post(f"{self.base_endpoint}/delete", data=data)
    
    def get_experiment_meta(self, experiment_id: str) -> Dict[str, Any]:
        """获取实验元数据"""
        data = {"id": experiment_id}
        return self.post(f"{self.base_endpoint}/meta", data=data)
    
    def update_experiment_meta(self, experiment_id: str, meta_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新实验元数据"""
        meta_data["id"] = experiment_id
        return self.post(f"{self.base_endpoint}/update-meta", data=meta_data)
    
    def get_experiment_samples(
        self, 
        experiment_id: str,
        page: int = 1,
        size: int = 20,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """获取实验样本列表"""
        data = {"id": experiment_id, "page": page, "size": size}
        if filters:
            data.update(filters)
        
        return self.post(f"{self.base_endpoint}/samples", data=data)
    
    def add_sample_to_experiment(self, experiment_id: str, sample_id: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """添加样本到实验"""
        data = {"experiment_id": experiment_id, "sample_id": sample_id}
        if metadata:
            data.update(metadata)
        
        return self.post(f"{self.base_endpoint}/add-sample", data=data)
    
    def remove_sample_from_experiment(self, experiment_id: str, sample_id: str) -> Dict[str, Any]:
        """从实验中移除样本"""
        data = {"experiment_id": experiment_id, "sample_id": sample_id}
        return self.post(f"{self.base_endpoint}/remove-sample", data=data)
    
    def get_experiment_files(
        self, 
        experiment_id: str,
        page: int = 1,
        size: int = 20,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """获取实验文件列表"""
        data = {"id": experiment_id, "page": page, "size": size}
        if filters:
            data.update(filters)
        
        return self.post(f"{self.base_endpoint}/files", data=data)
    
    def upload_experiment_file(self, experiment_id: str, file_path: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """上传实验文件"""
        data = metadata or {}
        data["experiment_id"] = experiment_id
        return self.upload_file(f"{self.base_endpoint}/upload-file", file_path, metadata=data)
    
    def download_experiment_file(self, experiment_id: str, file_id: str, save_path: str) -> str:
        """下载实验文件"""
        return self.download_file(f"{self.base_endpoint}/download-file", save_path)
    
    def delete_experiment_file(self, experiment_id: str, file_id: str) -> Dict[str, Any]:
        """删除实验文件"""
        data = {"experiment_id": experiment_id, "file_id": file_id}
        return self.post(f"{self.base_endpoint}/delete-file", data=data)
    
    def get_experiment_status(self, experiment_id: str) -> Dict[str, Any]:
        """获取实验状态"""
        data = {"id": experiment_id}
        return self.post(f"{self.base_endpoint}/status", data=data)
    
    def update_experiment_status(self, experiment_id: str, status: str, notes: Optional[str] = None) -> Dict[str, Any]:
        """更新实验状态"""
        data = {"id": experiment_id, "status": status}
        if notes:
            data["notes"] = notes
        
        return self.post(f"{self.base_endpoint}/update-status", data=data)
    
    def get_experiment_results(
        self, 
        experiment_id: str,
        page: int = 1,
        size: int = 20,
        **kwargs
    ) -> Dict[str, Any]:
        """获取实验结果"""
        data = {"id": experiment_id, "page": page, "size": size}
        return self.post(f"{self.base_endpoint}/results", data=data)
    
    def add_experiment_result(self, experiment_id: str, result_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加实验结果"""
        result_data["experiment_id"] = experiment_id
        return self.post(f"{self.base_endpoint}/add-result", data=result_data)
    
    def get_experiment_analyses(
        self, 
        experiment_id: str,
        page: int = 1,
        size: int = 20,
        **kwargs
    ) -> Dict[str, Any]:
        """获取实验分析列表"""
        data = {"id": experiment_id, "page": page, "size": size}
        return self.post(f"{self.base_endpoint}/analyses", data=data)
    
    def create_experiment_analysis(self, experiment_id: str, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建实验分析"""
        analysis_data["experiment_id"] = experiment_id
        return self.post(f"{self.base_endpoint}/create-analysis", data=analysis_data)
    
    def get_experiment_analysis(self, experiment_id: str, analysis_id: str) -> Dict[str, Any]:
        """获取实验分析详情"""
        data = {"experiment_id": experiment_id, "analysis_id": analysis_id}
        return self.post(f"{self.base_endpoint}/analysis-profile", data=data)
    
    def update_experiment_analysis(self, experiment_id: str, analysis_id: str, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新实验分析"""
        analysis_data["experiment_id"] = experiment_id
        analysis_data["analysis_id"] = analysis_id
        return self.post(f"{self.base_endpoint}/update-analysis", data=analysis_data)
    
    def delete_experiment_analysis(self, experiment_id: str, analysis_id: str) -> Dict[str, Any]:
        """删除实验分析"""
        data = {"experiment_id": experiment_id, "analysis_id": analysis_id}
        return self.post(f"{self.base_endpoint}/delete-analysis", data=data)
    
    def get_experiment_workflow(self, experiment_id: str) -> Dict[str, Any]:
        """获取实验工作流"""
        data = {"id": experiment_id}
        return self.post(f"{self.base_endpoint}/workflow", data=data)
    
    def update_experiment_workflow(self, experiment_id: str, workflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新实验工作流"""
        workflow_data["id"] = experiment_id
        return self.post(f"{self.base_endpoint}/update-workflow", data=workflow_data)
    
    def execute_experiment_step(self, experiment_id: str, step_id: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """执行实验步骤"""
        data = {"experiment_id": experiment_id, "step_id": step_id}
        if params:
            data.update(params)
        
        return self.post(f"{self.base_endpoint}/execute-step", data=data)
    
    def get_experiment_logs(
        self, 
        experiment_id: str,
        level: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        page: int = 1,
        size: int = 100,
        **kwargs
    ) -> Dict[str, Any]:
        """获取实验日志"""
        data = {
            "id": experiment_id,
            "page": page,
            "size": size
        }
        if level:
            data["level"] = level
        if start_time:
            data["start_time"] = start_time
        if end_time:
            data["end_time"] = end_time
        
        return self.post(f"{self.base_endpoint}/logs", data=data)
    
    def search_experiments(
        self, 
        query: str, 
        page: int = 1, 
        size: int = 20,
        **kwargs
    ) -> Dict[str, Any]:
        """搜索实验"""
        return self.search_resources(
            self.base_endpoint,
            query=query,
            page=page,
            size=size,
            **kwargs
        )
    
    def get_experiment_types(self) -> Dict[str, Any]:
        """获取实验类型列表"""
        return self.post(f"{self.base_endpoint}/types")
    
    def get_experiment_templates(self) -> Dict[str, Any]:
        """获取实验模板列表"""
        return self.post(f"{self.base_endpoint}/templates")
    
    def create_experiment_from_template(self, template_id: str, experiment_data: Dict[str, Any]) -> Dict[str, Any]:
        """从模板创建实验"""
        data = {"template_id": template_id}
        data.update(experiment_data)
        
        return self.post(f"{self.base_endpoint}/from-template", data=data)
    
    def clone_experiment(self, experiment_id: str, new_name: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """克隆实验"""
        data = {"experiment_id": experiment_id, "new_name": new_name}
        if metadata:
            data.update(metadata)
        
        return self.post(f"{self.base_endpoint}/clone", data=data)
    
    def export_experiment(self, experiment_id: str, format: str = "json", save_path: str = None) -> str:
        """导出实验数据"""
        if save_path is None:
            save_path = f"experiment_{experiment_id}.{format}"
        
        return self.download_file(f"{self.base_endpoint}/export", save_path)
    
    def import_experiment(self, import_file_path: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """导入实验数据"""
        data = metadata or {}
        return self.upload_file(f"{self.base_endpoint}/import", import_file_path, metadata=data)
