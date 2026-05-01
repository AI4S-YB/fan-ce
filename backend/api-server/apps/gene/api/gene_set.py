# -*- coding: utf-8 -*-
"""
@Author  : llq
@Time    : 2024/9/23 10:20
@Function:
@version :  1.0
@Desc    :  None
"""
import time
from fastapi import APIRouter, Depends

from apps.common.depends import get_active_user
from db.database import get_db
from libs.responses.response import response_200,response_2000
from ..crud import gene_set_db, gene_set_link_db
from ..schemas import PageList, DataInfo, DataDelete, GeneSetCrate, GeneSetUpdate, GeneSetCreate, GeneSetListByGenome, GeneSetDetail, GeneSetOptionsQuery
from ..models import GeneSet, GeneSetLink

gene_set_router = APIRouter(tags=['app:geneset:基因集'])


@gene_set_router.post("/list", summary="基因集列表==app:gene:list")
async def databases_list(request_data: PageList, db=Depends(get_db), _user=Depends(get_active_user)):
    db_obj = gene_set_db.get_list(db=db, page=request_data.page, size=request_data.size)
    return response_200(data=db_obj)


@gene_set_router.post("/info", summary="基因集列表==app:gene:list")
async def databases_list(request_data: DataInfo, db=Depends(get_db), _user=Depends(get_active_user)):
    db_obj = gene_set_db.get_one(db=db, id=request_data.id)
    return response_200(data=db_obj)


@gene_set_router.post("/options", summary="基因集下拉列表（支持file_path过滤）==app:gene:options")
async def get_geneset_options(request_data: GeneSetOptionsQuery, db=Depends(get_db), _user=Depends(get_active_user)):
    """
    获取基因集选项列表，支持按file_path过滤
    - 如果传入file_path：只返回该基因组文件下的基因集
    - 如果不传file_path：返回所有基因集（保持向后兼容）
    - 支持权限控制（team_id/project_id）
    """
    try:
        # 如果请求中没有权限信息，尝试从全局参数获取（由request拦截器添加）
        team_id = request_data.team_id
        project_id = request_data.project_id
        
        # 使用新的CRUD方法获取基因集选项
        result = gene_set_link_db.get_geneset_options_by_file_path(
            db=db,
            file_path=request_data.file_path,
            team_id=team_id,
            project_id=project_id
        )
        
        return response_2000(data=result)
        
    except Exception as e:
        # 如果新方法失败，回退到原有逻辑（向后兼容）
        print(f"New method failed, falling back to original: {str(e)}")
        new_data = []
        list_data = []
        seen_names = set()  # 用于去重的集合
        db_obj = gene_set_db.get_list(db=db, page=0)
        for i in db_obj['dataList']:
            # 如果name还没有出现过，则添加到结果中
            if i.name not in seen_names:
                seen_names.add(i.name)
                new_data.append({'id': i.name, 'name': i.name})
            # 所有数据都添加到list中，用于获取关联的样本ID
            list_data.append({'gene_id': i.gene_id, 'name': i.name})
        return response_2000(data={'list': list_data, 'options': new_data})


@gene_set_router.post("/genome/list", summary="按基因组文件路径获取基因集列表（一级表格）==app:gene:genome_list")
async def get_geneset_by_genome(request_data: GeneSetListByGenome, db=Depends(get_db), _user=Depends(get_active_user)):
    """
    获取指定基因组文件路径下的基因集列表，用于前端一级表格展示
    返回基因集基本信息和该基因集在当前基因组下的基因数量
    支持团队和项目权限控制
    """
    try:
        result = gene_set_link_db.get_geneset_summary_by_file_path(
            db=db, 
            file_path=request_data.file_path,
            team_id=request_data.team_id,
            project_id=request_data.project_id,
            page=request_data.page,
            size=request_data.size
        )
        
        return response_200(data={
            "dataList": result["items"],
            "total": result["total"],
            "page": result["page"],
            "size": result["size"]
        })
    except Exception as e:
        return response_200(code=500, msg=f"获取基因集列表失败: {str(e)}", data=[])


@gene_set_router.post("/detail", summary="基因集详情展开（二级表格）==app:gene:detail")
async def get_geneset_detail(request_data: GeneSetDetail, db=Depends(get_db), _user=Depends(get_active_user)):
    """
    获取基因集在指定基因组文件路径下的基因列表详情，用于前端二级表格展示
    返回该基因集在指定基因组下的所有基因信息，支持权限控制
    """
    try:
        result = gene_set_link_db.get_geneset_genes(
            db=db,
            file_path=request_data.file_path,
            geneset_id=request_data.geneset_id,
            team_id=request_data.team_id,
            project_id=request_data.project_id,
            page=request_data.page,
            size=request_data.size
        )
        
        # 格式化返回数据
        gene_list = []
        for item in result["items"]:
            gene_list.append({
                "id": item.id,
                "gene_id": item.gene_id,
                "file_path": item.file_path,
                "geneset_id": item.geneset_id,
                "create_time": item.create_time
            })
        
        return response_200(data={
            "dataList": gene_list,
            "total": result["total"],
            "page": result["page"],
            "size": result["size"]
        })
    except Exception as e:
        return response_200(code=500, msg=f"获取基因集详情失败: {str(e)}", data=[])


@gene_set_router.post("/genomes/options", summary="获取有基因集数据的基因组选项==app:gene:genome_options")
async def get_genome_options(db=Depends(get_db), _user=Depends(get_active_user)):
    """
    获取所有有基因集数据的基因组选项，用于前端下拉选择器
    """
    try:
        # 查询所有不同的文件路径
        distinct_file_paths = db.query(GeneSetLink.file_path).filter(
            GeneSetLink.is_delete == 0
        ).distinct().all()
        
        genome_options = []
        for file_path_tuple in distinct_file_paths:
            file_path = file_path_tuple[0]
            # 从文件路径中提取基因组名称作为显示标签
            file_name = file_path.split('/')[-1] if file_path else file_path
            genome_options.append({
                "value": file_path,
                "label": f"基因组 ({file_name})"
            })
        
        return response_200(data=genome_options)
    except Exception as e:
        return response_200(code=500, msg=f"获取基因组选项失败: {str(e)}", data=[])



@gene_set_router.post("/add", summary="基因集添加==app:gene:add")
async def add_geneset(request_data: GeneSetCreate, db=Depends(get_db), _user=Depends(get_active_user)):
    """
    新的基因集添加逻辑：实现三层关联 genome_id ↔ geneset_id ↔ gene_id
    """
    try:
        current_time = int(time.time())
        
        # 1. 检查基因集是否已存在（在同一团队和项目下）
        existing_geneset = db.query(GeneSet).filter(
            GeneSet.name == request_data.name,
            GeneSet.team_id == request_data.team_id,
            GeneSet.project_id == request_data.project_id,
            GeneSet.is_delete == 0
        ).first()
        
        # 2. 不存在则创建新基因集
        if not existing_geneset:
            geneset = GeneSet(
                name=request_data.name,
                description=request_data.description,
                user_id=_user.id if hasattr(_user, 'id') else None,
                team_id=request_data.team_id,
                project_id=request_data.project_id,
                create_time=current_time
            )
            db.add(geneset)
            db.flush()  # 获取geneset.id
            geneset_id = geneset.id
        else:
            geneset_id = existing_geneset.id
        
        # 3. 创建基因关联关系
        added_count = 0
        skipped_count = 0
        
        for gene_id in request_data.gene_list:
            # 检查关联是否已存在
            if not gene_set_link_db.check_link_exists(db, request_data.file_path, geneset_id, gene_id):
                link = GeneSetLink(
                    file_path=request_data.file_path,
                    geneset_id=geneset_id,
                    gene_id=gene_id,
                    create_time=current_time,
                    added_at=current_time
                )
                db.add(link)
                added_count += 1
            else:
                skipped_count += 1
        
        db.commit()
        
        return response_200(data={
            "geneset_id": geneset_id,
            "geneset_name": request_data.name,
            "added_genes": added_count,
            "skipped_genes": skipped_count,
            "total_requested": len(request_data.gene_list)
        })
    except Exception as e:
        db.rollback()
        return response_200(code=500, msg=f"基因集添加失败: {str(e)}", data=None)

@gene_set_router.post("/batch/add", summary="基因集批量添加（兼容接口）==app:gene:batch_add")
async def batch_add_geneset(request_data: GeneSetCrate, db=Depends(get_db), _user=Depends(get_active_user)):
    """
    保留的批量添加接口，用于向后兼容
    注意：此接口使用旧的数据模型，建议使用新的 /add 接口
    """
    request_data.is_deleted = False
    db_obj = gene_set_db.create_batch(db=db, add_data=request_data)
    return response_200(data=db_obj)

@gene_set_router.post("/update", summary="基因集修改==app:gene:update")
async def databases_list(request_data: GeneSetUpdate, db=Depends(get_db), _user=Depends(get_active_user)):
    one_obj = gene_set_db.get(db=db, id=request_data.id)
    db_obj = gene_set_db.update_one(db=db, db_obj=one_obj, obj_in=request_data)
    return response_200(data=db_obj)


@gene_set_router.post("/delete", summary="基因集删除==app:gene:delete")
async def databases_list(request_data: DataDelete, db=Depends(get_db), _user=Depends(get_active_user)):
    if request_data.ids:
        for i in request_data.ids:
            gene_set_db.remove(db=db, id=int(i))
    else:
        gene_set_db.remove(db=db, id=request_data.id)
    return response_200(data={})
