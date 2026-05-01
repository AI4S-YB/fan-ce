"""
@Author  : llq
@Time    : 2024/10/8 17:34
@Function:
@version :  1.0
@Desc    :  None
"""
from typing import TypeVar, List
from sqlalchemy.orm import Session
from sqlalchemy import func

from db.base import CRUDBase
from db.database import Base
from .models import GeneSet, GeneSetLink
from .schemas import CreateModel

ModelType = TypeVar("ModelType", bound=Base)


class CRUDGeneSet(CRUDBase[GeneSet, CreateModel, CreateModel]):
    pass


class CRUDGeneSetLink(CRUDBase[GeneSetLink, CreateModel, CreateModel]):
    def get_by_file_path(self, db: Session, file_path: str) -> List[GeneSetLink]:
        """获取指定基因组文件路径下的所有基因集关联"""
        return db.query(GeneSetLink).filter(
            GeneSetLink.file_path == file_path,
            GeneSetLink.is_delete == 0
        ).all()
    
    def get_geneset_genes(self, db: Session, file_path: str, geneset_id: int, project_id: int, page: int = 1, size: int = 10) -> dict:
        """获取基因集下的基因列表，支持分页和权限控制"""
        query = db.query(GeneSetLink).join(
            GeneSet, GeneSetLink.geneset_id == GeneSet.id
        ).filter(
            GeneSetLink.file_path == file_path,
            GeneSetLink.geneset_id == geneset_id,
            GeneSetLink.is_delete == 0,
            GeneSet.project_id == project_id,
            GeneSet.is_delete == 0
        )
        
        # 获取总数
        total = query.count()
        
        # 分页查询
        if page > 0 and size > 0:
            offset = (page - 1) * size
            items = query.offset(offset).limit(size).all()
        else:
            items = query.all()
        
        return {
            "total": total,
            "items": items,
            "page": page,
            "size": size
        }
    
    def get_geneset_summary_by_file_path(self, db: Session, file_path: str, project_id: int, page: int = 1, size: int = 10) -> dict:
        """获取基因组文件路径下的基因集汇总信息（一级表格数据）- 按基因集名称去重，取最小ID，支持权限控制"""
        # 子查询：获取每个基因集名称的最小ID（去重逻辑），加上权限过滤
        subquery = db.query(
            func.min(GeneSet.id).label('min_id'),
            GeneSet.name,
            func.ifnull(GeneSet.description, '').label('description_normalized')
        ).filter(
            GeneSet.is_delete == 0,
            GeneSet.project_id == project_id
        ).group_by(
            GeneSet.name, 
            func.ifnull(GeneSet.description, '')  # 按名称和描述组合去重
        ).subquery()
        
        # 主查询：基于去重后的基因集获取汇总信息
        query = db.query(
            GeneSet.id.label('geneset_id'),
            GeneSet.name.label('geneset_name'),
            GeneSet.description,
            GeneSet.create_time,
            func.count(GeneSetLink.gene_id).label('gene_count')
        ).join(
            subquery, GeneSet.id == subquery.c.min_id
        ).join(
            GeneSetLink, GeneSet.id == GeneSetLink.geneset_id
        ).filter(
            GeneSetLink.file_path == file_path,
            GeneSetLink.is_delete == 0,
            GeneSet.is_delete == 0,
            GeneSet.project_id == project_id
        ).group_by(
            GeneSet.id, GeneSet.name, GeneSet.description, GeneSet.create_time
        )
        
        # 获取总数
        total = query.count()
        
        # 分页查询
        if page > 0 and size > 0:
            offset = (page - 1) * size
            items = query.offset(offset).limit(size).all()
        else:
            items = query.all()
        
        return {
            "total": total,
            "items": [dict(item._asdict()) for item in items],
            "page": page,
            "size": size
        }
    
    def check_link_exists(self, db: Session, file_path: str, geneset_id: int, gene_id: str) -> bool:
        """检查基因集关联是否已存在"""
        return db.query(GeneSetLink).filter(
            GeneSetLink.file_path == file_path,
            GeneSetLink.geneset_id == geneset_id,
            GeneSetLink.gene_id == gene_id,
            GeneSetLink.is_delete == 0
        ).first() is not None

    def get_geneset_options_by_file_path(self, db: Session, file_path: str = None, project_id: int = None):
        """
        获取基因集选项，支持按file_path过滤
        用于在其他业务模块中提供基因集下拉选项
        """
        # 基础查询：获取基因集基本信息
        query = db.query(
            GeneSet.id,
            GeneSet.name,
            GeneSet.description
        ).filter(
            GeneSet.is_delete == 0
        )
        
        # If specified, add project-level filtering
        if project_id is not None:
            query = query.filter(GeneSet.project_id == project_id)
        
        # 如果指定了file_path，只返回该基因组下有数据的基因集
        if file_path:
            query = query.join(GeneSetLink, GeneSet.id == GeneSetLink.geneset_id).filter(
                GeneSetLink.file_path == file_path,
                GeneSetLink.is_delete == 0
            ).distinct()
        
        # 执行查询
        gene_sets = query.all()
        
        # 格式化返回数据
        options = []
        list_data = []
        
        for geneset in gene_sets:
            options.append({
                'id': geneset.name,  # 保持与原接口兼容
                'name': geneset.name
            })
            
            # 如果需要获取基因列表（保持与原接口兼容）
            if file_path:
                genes = db.query(GeneSetLink.gene_id).filter(
                    GeneSetLink.geneset_id == geneset.id,
                    GeneSetLink.file_path == file_path,
                    GeneSetLink.is_delete == 0
                ).all()
                
                for gene in genes:
                    list_data.append({
                        'gene_id': gene.gene_id,
                        'name': geneset.name
                    })
        
        return {
            'options': options,
            'list': list_data
        }


gene_set_db = CRUDGeneSet(GeneSet)
gene_set_link_db = CRUDGeneSetLink(GeneSetLink)