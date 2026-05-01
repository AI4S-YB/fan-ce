#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ABD SDK 基础生物信息学API模块
提供基础生物信息学分析相关的API操作
"""

from typing import Optional, Dict, Any, List
from .base import BaseAPI


class BasisAPI(BaseAPI):
    """基础生物信息学API模块"""
    
    def __init__(self, http_client, api_prefix: str = "/api/v1"):
        super().__init__(http_client, api_prefix)
        self.base_endpoint = "/basis"
    
    # 基因组相关
    def list_genomes(
        self, 
        page: int = 1, 
        size: int = 20, 
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """获取基因组列表"""
        return self.list_resources(
            f"{self.base_endpoint}/genomes",
            page=page,
            size=size,
            filters=filters,
            **kwargs
        )
    
    def get_genome(self, genome_id: str) -> Dict[str, Any]:
        """获取基因组信息"""
        return self.get_resource(f"{self.base_endpoint}/genomes", genome_id)
    
    def get_genome_meta(self, genome_id: str) -> Dict[str, Any]:
        """获取基因组元数据"""
        return self.get(f"{self.base_endpoint}/genomes/{genome_id}/meta")
    
    def get_genome_files(self, genome_id: str, page: int = 1, size: int = 20) -> Dict[str, Any]:
        """获取基因组文件列表"""
        params = {"page": page, "size": size}
        return self.get(f"{self.base_endpoint}/genomes/{genome_id}/files", params=params)
    
    def download_genome_file(self, genome_id: str, file_id: str, save_path: str) -> str:
        """下载基因组文件"""
        return self.download_file(f"{self.base_endpoint}/genomes/{genome_id}/files/{file_id}", save_path)
    
    # 序列分析
    def sequence_blast(
        self, 
        query_sequence: str, 
        database: str = "nr",
        e_value: float = 1e-5,
        max_target_seqs: int = 10,
        **kwargs
    ) -> Dict[str, Any]:
        """执行BLAST序列搜索"""
        data = {
            "query_sequence": query_sequence,
            "database": database,
            "e_value": e_value,
            "max_target_seqs": max_target_seqs
        }
        data.update(kwargs)
        
        return self.post(f"{self.base_endpoint}/blast", data=data)
    
    def sequence_alignment(
        self, 
        sequences: List[str], 
        algorithm: str = "clustalw",
        **kwargs
    ) -> Dict[str, Any]:
        """执行多序列比对"""
        data = {
            "sequences": sequences,
            "algorithm": algorithm
        }
        data.update(kwargs)
        
        return self.post(f"{self.base_endpoint}/alignment", data=data)
    
    def sequence_phylogeny(
        self, 
        sequences: List[str], 
        method: str = "neighbor_joining",
        **kwargs
    ) -> Dict[str, Any]:
        """构建系统发育树"""
        data = {
            "sequences": sequences,
            "method": method
        }
        data.update(kwargs)
        
        return self.post(f"{self.base_endpoint}/phylogeny", data=data)
    
    # 基因表达分析
    def expression_analysis(
        self, 
        expression_data: Dict[str, Any],
        analysis_type: str = "differential",
        **kwargs
    ) -> Dict[str, Any]:
        """执行基因表达分析"""
        data = {
            "expression_data": expression_data,
            "analysis_type": analysis_type
        }
        data.update(kwargs)
        
        return self.post(f"{self.base_endpoint}/expression/analysis", data=data)
    
    def get_expression_datasets(
        self, 
        page: int = 1, 
        size: int = 20, 
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """获取表达数据集列表"""
        params = {"page": page, "size": size}
        if filters:
            params.update(filters)
        
        return self.get(f"{self.base_endpoint}/expression/datasets", params=params)
    
    def get_expression_dataset(self, dataset_id: str) -> Dict[str, Any]:
        """获取表达数据集信息"""
        return self.get(f"{self.base_endpoint}/expression/datasets/{dataset_id}")
    
    # 变异分析
    def variant_calling(
        self, 
        bam_file_path: str,
        reference_genome: str,
        **kwargs
    ) -> Dict[str, Any]:
        """执行变异检测"""
        data = {
            "reference_genome": reference_genome
        }
        data.update(kwargs)
        
        return self.upload_file(f"{self.base_endpoint}/variant/calling", bam_file_path, metadata=data)
    
    def variant_annotation(
        self, 
        vcf_file_path: str,
        annotation_databases: List[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """执行变异注释"""
        data = {
            "annotation_databases": annotation_databases or ["dbsnp", "1000g"]
        }
        data.update(kwargs)
        
        return self.upload_file(f"{self.base_endpoint}/variant/annotation", vcf_file_path, metadata=data)
    
    def get_variant_databases(self) -> Dict[str, Any]:
        """获取变异数据库列表"""
        return self.get(f"{self.base_endpoint}/variant/databases")
    
    # 功能注释
    def functional_annotation(
        self, 
        sequences: List[str],
        annotation_type: str = "all",
        **kwargs
    ) -> Dict[str, Any]:
        """执行功能注释"""
        data = {
            "sequences": sequences,
            "annotation_type": annotation_type
        }
        data.update(kwargs)
        
        return self.post(f"{self.base_endpoint}/annotation/functional", data=data)
    
    def go_enrichment(
        self, 
        gene_list: List[str],
        background_genes: List[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """执行GO富集分析"""
        data = {
            "gene_list": gene_list
        }
        if background_genes:
            data["background_genes"] = background_genes
        data.update(kwargs)
        
        return self.post(f"{self.base_endpoint}/annotation/go-enrichment", data=data)
    
    def pathway_enrichment(
        self, 
        gene_list: List[str],
        pathway_database: str = "kegg",
        **kwargs
    ) -> Dict[str, Any]:
        """执行通路富集分析"""
        data = {
            "gene_list": gene_list,
            "pathway_database": pathway_database
        }
        data.update(kwargs)
        
        return self.post(f"{self.base_endpoint}/annotation/pathway-enrichment", data=data)
    
    # 文件处理
    def convert_file_format(
        self, 
        input_file_path: str,
        output_format: str,
        **kwargs
    ) -> str:
        """转换文件格式"""
        data = {"output_format": output_format}
        data.update(kwargs)
        
        response = self.upload_file(f"{self.base_endpoint}/convert-format", input_file_path, metadata=data)
        
        if "download_url" in response:
            # 下载转换后的文件
            output_filename = f"converted.{output_format}"
            return self.download_file(response["download_url"], output_filename)
        
        raise Exception("File conversion failed")
    
    def validate_file_format(
        self, 
        file_path: str,
        expected_format: str
    ) -> Dict[str, Any]:
        """验证文件格式"""
        data = {"expected_format": expected_format}
        return self.upload_file(f"{self.base_endpoint}/validate-format", file_path, metadata=data)
    
    # 统计分析
    def statistical_analysis(
        self, 
        data: List[float],
        analysis_type: str = "descriptive",
        **kwargs
    ) -> Dict[str, Any]:
        """执行统计分析"""
        request_data = {
            "data": data,
            "analysis_type": analysis_type
        }
        request_data.update(kwargs)
        
        return self.post(f"{self.base_endpoint}/statistics/analysis", data=request_data)
    
    def correlation_analysis(
        self, 
        data_matrix: List[List[float]],
        method: str = "pearson",
        **kwargs
    ) -> Dict[str, Any]:
        """执行相关性分析"""
        data = {
            "data_matrix": data_matrix,
            "method": method
        }
        data.update(kwargs)
        
        return self.post(f"{self.base_endpoint}/statistics/correlation", data=data)
    
    # 可视化
    def create_plot(
        self, 
        plot_data: Dict[str, Any],
        plot_type: str = "scatter",
        **kwargs
    ) -> str:
        """创建图表"""
        data = {
            "plot_data": plot_data,
            "plot_type": plot_type
        }
        data.update(kwargs)
        
        response = self.post(f"{self.base_endpoint}/visualization/plot", data=data)
        
        if "plot_url" in response:
            # 下载生成的图表
            plot_filename = f"plot_{plot_type}.png"
            return self.download_file(response["plot_url"], plot_filename)
        
        raise Exception("Plot creation failed")
    
    def create_heatmap(
        self, 
        data_matrix: List[List[float]],
        row_labels: List[str] = None,
        col_labels: List[str] = None,
        **kwargs
    ) -> str:
        """创建热图"""
        data = {
            "data_matrix": data_matrix
        }
        if row_labels:
            data["row_labels"] = row_labels
        if col_labels:
            data["col_labels"] = col_labels
        data.update(kwargs)
        
        response = self.post(f"{self.base_endpoint}/visualization/heatmap", data=data)
        
        if "plot_url" in response:
            heatmap_filename = "heatmap.png"
            return self.download_file(response["plot_url"], heatmap_filename)
        
        raise Exception("Heatmap creation failed")
    
    # 工具集成
    def run_tool(
        self, 
        tool_name: str,
        parameters: Dict[str, Any],
        input_files: List[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """运行生物信息学工具"""
        data = {
            "tool_name": tool_name,
            "parameters": parameters
        }
        if input_files:
            data["input_files"] = input_files
        data.update(kwargs)
        
        return self.post(f"{self.base_endpoint}/tools/run", data=data)
    
    def get_available_tools(self) -> Dict[str, Any]:
        """获取可用工具列表"""
        return self.get(f"{self.base_endpoint}/tools/available")
    
    def get_tool_help(self, tool_name: str) -> Dict[str, Any]:
        """获取工具帮助信息"""
        return self.get(f"{self.base_endpoint}/tools/{tool_name}/help")
    
    # 工作流管理
    def create_workflow(
        self, 
        workflow_definition: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """创建工作流"""
        data = {"workflow_definition": workflow_definition}
        data.update(kwargs)
        
        return self.post(f"{self.base_endpoint}/workflows", data=data)
    
    def execute_workflow(
        self, 
        workflow_id: str,
        input_parameters: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """执行工作流"""
        data = {"input_parameters": input_parameters}
        data.update(kwargs)
        
        return self.post(f"{self.base_endpoint}/workflows/{workflow_id}/execute", data=data)
    
    def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """获取工作流状态"""
        return self.get(f"{self.base_endpoint}/workflows/{workflow_id}/status")
    
    def get_workflow_results(self, workflow_id: str) -> Dict[str, Any]:
        """获取工作流结果"""
        return self.get(f"{self.base_endpoint}/workflows/{workflow_id}/results")
    
    # 数据导入导出
    def import_data(
        self, 
        import_file_path: str,
        data_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """导入数据"""
        data = {"data_type": data_type}
        if metadata:
            data.update(metadata)
        data.update(kwargs)
        
        return self.upload_file(f"{self.base_endpoint}/import", import_file_path, metadata=data)
    
    def export_data(
        self, 
        data_id: str,
        export_format: str = "json",
        save_path: str = None,
        **kwargs
    ) -> str:
        """导出数据"""
        if save_path is None:
            save_path = f"exported_data_{data_id}.{export_format}"
        
        params = {"format": export_format}
        params.update(kwargs)
        
        return self.download_file(f"{self.base_endpoint}/export/{data_id}", save_path, params=params)
    
    # 系统信息
    def get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        return self.get(f"{self.base_endpoint}/system/info")
    
    def get_available_databases(self) -> Dict[str, Any]:
        """获取可用数据库列表"""
        return self.get(f"{self.base_endpoint}/databases/available")
    
    def get_database_status(self, database_name: str) -> Dict[str, Any]:
        """获取数据库状态"""
        return self.get(f"{self.base_endpoint}/databases/{database_name}/status")
