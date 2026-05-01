from fastapi import APIRouter

# 创建 APIRouter 实例
router = APIRouter(
    prefix="/phenomics",
    tags=["Phenomics API"]
)

# 表型特征 API
@router.get("/traits", summary="获取表型特征")
async def get_traits():
    return {"message": "Here are some phenotypic traits"}