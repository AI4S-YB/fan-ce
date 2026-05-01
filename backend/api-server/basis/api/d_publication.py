from fastapi import APIRouter

# 创建 APIRouter 实例
router = APIRouter(
    prefix="/data",
    tags=["Publication API"]
)

# 表型特征 API
@router.get("/publication", summary="文章")
async def get_pub():
    return {"message": "Here are some publication"}