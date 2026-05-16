from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from apps.datasets.models import DatasetRegistry
from db.database import get_db

from ..multi_site import get_current_site, get_site_dataset_ids

public_router = APIRouter(tags=["public:公开门户"])


@public_router.get("/site/info", summary="当前站点信息")
async def public_site_info(
    request: Request,
    db: Session = Depends(get_db),
):
    site = get_current_site(request, db)
    return {
        "site_code": site.site_code,
        "site_name": site.site_name,
        "site_title": site.site_title,
        "logo_text": site.logo_text,
        "contact_email": site.contact_email,
        "footer_copyright": site.footer_copyright,
    }


@public_router.get("/datasets", summary="当前站点可见数据集")
async def public_datasets(
    request: Request,
    db: Session = Depends(get_db),
):
    site = get_current_site(request, db)
    bound_ids = get_site_dataset_ids(db, site.site_code)
    if not bound_ids:
        return {"items": []}

    datasets = db.query(DatasetRegistry).filter(
        DatasetRegistry.id.in_(list(bound_ids)),
        DatasetRegistry.is_public == True,
    ).all()
    return {"items": [ds.to_dict() for ds in datasets]}


@public_router.get("/datasets/{dataset_id}", summary="公开数据集详情")
async def public_dataset_detail(
    dataset_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    site = get_current_site(request, db)
    bound_ids = get_site_dataset_ids(db, site.site_code)
    if dataset_id not in bound_ids:
        raise HTTPException(status_code=404, detail="Dataset not found on this site")

    ds = db.query(DatasetRegistry).filter(
        DatasetRegistry.id == dataset_id,
        DatasetRegistry.is_public == True,
    ).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return ds.to_dict()
