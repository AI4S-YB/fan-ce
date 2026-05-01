#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ABD SDK 基因管理API模块
提供基因相关的API操作
"""

from typing import Optional, Dict, Any, List
from .base import BaseAPI


class GeneAPI(BaseAPI):
    """基因管理API模块"""
    
    def __init__(self, http_client, api_prefix: str = "/api/v1"):
        super().__init__(http_client, api_prefix)
        self.base_endpoint = "/genes"
    
    def list_genes(
        self, 
        page: int = 1, 
        size: int = 20, 
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """获取基因列表"""
        return self.list_resources(
            self.base_endpoint,
            page=page,
            size=size,
            filters=filters,
            **kwargs
        )
    
    def get_gene(self, gene_id: str) -> Dict[str, Any]:
        """获取基因信息"""
        return self.get_resource(self.base_endpoint, gene_id)
    
    def create_gene(self, gene_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建基因记录"""
        return self.create_resource(self.base_endpoint, gene_data)
    
    def update_gene(self, gene_id: str, gene_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新基因信息"""
        return self.update_resource(self.base_endpoint, gene_id, gene_data)
    
    def delete_gene(self, gene_id: str) -> Dict[str, Any]:
        """删除基因记录"""
        return self.delete_resource(self.base_endpoint, gene_id)
    
    def get_gene_sequence(self, gene_id: str) -> Dict[str, Any]:
        """获取基因序列"""
        return self.get(f"{self.base_endpoint}/{gene_id}/sequence")
    
    def update_gene_sequence(self, gene_id: str, sequence_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新基因序列"""
        return self.put(f"{self.base_endpoint}/{gene_id}/sequence", data=sequence_data)
    
    def get_gene_annotations(self, gene_id: str) -> Dict[str, Any]:
        """获取基因注释"""
        return self.get(f"{self.base_endpoint}/{gene_id}/annotations")
    
    def add_gene_annotation(self, gene_id: str, annotation_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加基因注释"""
        return self.post(f"{self.base_endpoint}/{gene_id}/annotations", data=annotation_data)
    
    def update_gene_annotation(self, gene_id: str, annotation_id: str, annotation_data: Dict[str, Any]) -> Dict[str, Any]:
        """更新基因注释"""
        return self.put(f"{self.base_endpoint}/{gene_id}/annotations/{annotation_id}", data=annotation_data)
    
    def delete_gene_annotation(self, gene_id: str, annotation_id: str) -> Dict[str, Any]:
        """删除基因注释"""
        return self.delete(f"{self.base_endpoint}/{gene_id}/annotations/{annotation_id}")
    
    def get_gene_expression(
        self, 
        gene_id: str,
        page: int = 1,
        size: int = 20,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """获取基因表达数据"""
        params = {"page": page, "size": size}
        if filters:
            params.update(filters)
        
        return self.get(f"{self.base_endpoint}/{gene_id}/expression", params=params)
    
    def add_gene_expression(self, gene_id: str, expression_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加基因表达数据"""
        return self.post(f"{self.base_endpoint}/{gene_id}/expression", data=expression_data)
    
    def get_gene_variants(
        self, 
        gene_id: str,
        page: int = 1,
        size: int = 20,
        filters: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """获取基因变异信息"""
        params = {"page": page, "size": size}
        if filters:
            params.update(filters)
        
        return self.get(f"{self.base_endpoint}/{gene_id}/variants", params=params)
    
    def add_gene_variant(self, gene_id: str, variant_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加基因变异信息"""
        return self.post(f"{self.base_endpoint}/{gene_id}/variants", data=variant_data)
    
    def get_gene_orthologs(self, gene_id: str) -> Dict[str, Any]:
        """获取基因同源基因"""
        return self.get(f"{self.base_endpoint}/{gene_id}/orthologs")
    
    def add_gene_ortholog(self, gene_id: str, ortholog_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加基因同源基因"""
        return self.post(f"{self.base_endpoint}/{gene_id}/orthologs", data=ortholog_data)
    
    def get_gene_pathways(self, gene_id: str) -> Dict[str, Any]:
        """获取基因参与的代谢通路"""
        return self.get(f"{self.base_endpoint}/{gene_id}/pathways")
    
    def add_gene_pathway(self, gene_id: str, pathway_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加基因参与的代谢通路"""
        return self.post(f"{self.base_endpoint}/{gene_id}/pathways", data=pathway_data)
    
    def get_gene_publications(
        self, 
        gene_id: str,
        page: int = 1,
        size: int = 20,
        **kwargs
    ) -> Dict[str, Any]:
        """获取基因相关文献"""
        params = {"page": page, "size": size}
        return self.get(f"{self.base_endpoint}/{gene_id}/publications", params=params)
    
    def add_gene_publication(self, gene_id: str, publication_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加基因相关文献"""
        return self.post(f"{self.base_endpoint}/{gene_id}/publications", data=publication_data)
    
    def search_genes(
        self, 
        query: str, 
        page: int = 1, 
        size: int = 20,
        **kwargs
    ) -> Dict[str, Any]:
        """搜索基因"""
        return self.search_resources(
            self.base_endpoint,
            query=query,
            page=page,
            size=size,
            **kwargs
        )
    
    def search_genes_by_sequence(self, sequence: str, search_type: str = "blast") -> Dict[str, Any]:
        """通过序列搜索基因"""
        data = {
            "sequence": sequence,
            "search_type": search_type
        }
        return self.post(f"{self.base_endpoint}/search-by-sequence", data=data)
    
    def get_gene_families(self) -> Dict[str, Any]:
        """获取基因家族列表"""
        return self.get(f"{self.base_endpoint}/families")
    
    def get_genes_by_family(self, family_id: str, page: int = 1, size: int = 20) -> Dict[str, Any]:
        """获取指定家族的基因"""
        params = {"page": page, "size": size}
        return self.get(f"{self.base_endpoint}/families/{family_id}/genes", params=params)
    
    def get_gene_ontology_terms(self, gene_id: str) -> Dict[str, Any]:
        """获取基因GO注释"""
        return self.get(f"{self.base_endpoint}/{gene_id}/go-terms")
    
    def add_gene_ontology_term(self, gene_id: str, go_term_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加基因GO注释"""
        return self.post(f"{self.base_endpoint}/{gene_id}/go-terms", data=go_term_data)
    
    def get_gene_protein_domains(self, gene_id: str) -> Dict[str, Any]:
        """获取基因蛋白结构域"""
        return self.get(f"{self.base_endpoint}/{gene_id}/protein-domains")
    
    def add_gene_protein_domain(self, gene_id: str, domain_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加基因蛋白结构域"""
        return self.post(f"{self.base_endpoint}/{gene_id}/protein-domains", data=domain_data)
    
    def get_gene_interactions(
        self, 
        gene_id: str,
        interaction_type: Optional[str] = None,
        page: int = 1,
        size: int = 20,
        **kwargs
    ) -> Dict[str, Any]:
        """获取基因相互作用"""
        params = {"page": page, "size": size}
        if interaction_type:
            params["interaction_type"] = interaction_type
        
        return self.get(f"{self.base_endpoint}/{gene_id}/interactions", params=params)
    
    def add_gene_interaction(self, gene_id: str, interaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """添加基因相互作用"""
        return self.post(f"{self.base_endpoint}/{gene_id}/interactions", data=interaction_data)
    
    def get_gene_evolution(self, gene_id: str) -> Dict[str, Any]:
        """获取基因进化信息"""
        return self.get(f"{self.base_endpoint}/{gene_id}/evolution")
    
    def get_gene_phylogeny(self, gene_id: str) -> Dict[str, Any]:
        """获取基因系统发育树"""
        return self.get(f"{self.base_endpoint}/{gene_id}/phylogeny")
    
    def export_gene_data(self, gene_id: str, format: str = "fasta", save_path: str = None) -> str:
        """导出基因数据"""
        if save_path is None:
            save_path = f"gene_{gene_id}.{format}"
        
        return self.download_file(f"{self.base_endpoint}/{gene_id}/export?format={format}", save_path)
    
    def import_gene_data(self, import_file_path: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """导入基因数据"""
        data = metadata or {}
        return self.upload_file(f"{self.base_endpoint}/import", import_file_path, metadata=data)
    
    def get_gene_statistics(self) -> Dict[str, Any]:
        """获取基因统计信息"""
        return self.get(f"{self.base_endpoint}/statistics")
    
    def get_gene_comparison(self, gene_ids: List[str]) -> Dict[str, Any]:
        """比较多个基因"""
        data = {"gene_ids": gene_ids}
        return self.post(f"{self.base_endpoint}/compare", data=data)
