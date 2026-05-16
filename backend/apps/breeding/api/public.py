"""Public germplasm API — read-only access to breeding germplasm records."""

from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from typing import Optional

from db.database import get_db
from libs.responses.response import response_200

from ..services import breeding_domain_service

public_germplasm_router = APIRouter(tags=["public:germplasm:公开种质资源"])


class PublicGermplasmListRequest(BaseModel):
    keyword: Optional[str] = Field(default=None, description="搜索关键词（名称/编号/英文名）")
    taxonomy_tax_id: Optional[int] = Field(default=None, description="物种分类 ID")
    batch_id: Optional[int] = Field(default=None, description="批次 ID")
    status: Optional[str] = Field(default=None, description="状态筛选")
    page: int = Field(default=1, ge=1)
    size: int = Field(default=20, ge=1, le=100)


class PublicGermplasmInfoRequest(BaseModel):
    accession_id: str = Field(..., description="种质编号")
    taxonomy_tax_id: int = Field(..., description="物种分类 ID")


@public_germplasm_router.post("/list", summary="公开种质资源列表")
def public_germplasm_list(request_data: PublicGermplasmListRequest, db=Depends(get_db)):
    data = breeding_domain_service.list_germplasms(db=db, request_data=request_data, public_only=True)
    return response_200(data=jsonable_encoder(data))


@public_germplasm_router.post("/info", summary="公开种质资源详情")
def public_germplasm_info(request_data: PublicGermplasmInfoRequest, db=Depends(get_db)):
    data = breeding_domain_service.get_germplasm(
        db=db,
        accession_id=request_data.accession_id,
        taxonomy_tax_id=request_data.taxonomy_tax_id,
        public_only=True,
    )
    return response_200(data=jsonable_encoder(data))
