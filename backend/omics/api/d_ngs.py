from fastapi import APIRouter, HTTPException
from omics.schemas.ngs import NGSFileFilterRequest, NGSFileListResponse
from omics.core.file_utils import list_ngs_files
from shared.responses import response_200


# 创建 APIRouter 实例
ngs_router = APIRouter(
    prefix="/omics/ngs",
    tags=["omics:NGS"]
)

# the NGS files do not need to be processed

@ngs_router.post("/file/list", 
    summary="List NGS files based on filter conditions")
async def filter_ngs_files(req: NGSFileFilterRequest):
    try:
        all_files = list_ngs_files(
            directory=req.directory,
            keyword=req.keyword,
            modified_after=req.modified_after,
            modified_before=req.modified_before,
            min_size=req.min_size_bytes,
            max_size=req.max_size_bytes,
            recursive=req.recursive
        )

        # 排序
        if req.sort_by in {"size", "modified"}:
            reverse = req.sort_order == "desc"
            if req.sort_by == "size":
                all_files.sort(key=lambda x: x.size_bytes, reverse=reverse)
            else:
                all_files.sort(key=lambda x: x.modified_time, reverse=reverse)

        # 分页
        total = len(all_files)
        start = (req.page - 1) * req.page_size
        end = start + req.page_size
        page_files = all_files[start:end]

        result = NGSFileListResponse(
            total=total,
            page=req.page,
            page_size=req.page_size,
            files=[file.dict() for file in page_files]  # Convert each file object to dictionary
        )
        
        return response_200(
            code=2000,
            msg="NGS files listed successfully",
            data=result.dict()  # Convert NGSFileListResponse to dictionary
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

