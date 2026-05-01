from fastapi import APIRouter

# 创建 APIRouter 实例
router = APIRouter(
    prefix="/app",
    tags=["Application API"]
)

# 表型特征 API
@router.get("/aimodel", summary="AI")
async def get_ai():
    return {"message": "Here are AI Model"}