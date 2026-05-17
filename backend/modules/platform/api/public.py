from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from modules.datasets.models import DatasetRegistry
from shared.database import get_db
from shared.responses import response_200

from ..multi_site import get_current_site, get_site_dataset_ids

public_router = APIRouter(tags=["public:公开门户"])


def _public_dataset_dict(ds) -> dict:
    """Return only public-safe fields from a dataset, excluding internal/sensitive data."""
    return {
        "id": ds.id,
        "dataset_code": ds.dataset_code,
        "title": ds.title,
        "dataset_type": ds.dataset_type,
        "version": ds.version,
        "description_md": ds.description_md,
        "organism": ds.organism,
        "file_format": ds.file_format,
        "is_public": ds.is_public,
        "lifecycle_state": ds.lifecycle_state,
        "create_time": ds.create_time,
        "update_time": ds.update_time,
    }


@public_router.get("/site/info", summary="当前站点信息")
async def public_site_info(
    request: Request,
    db: Session = Depends(get_db),
):
    site = get_current_site(request, db)
    return response_200(data={
        "site_code": site.site_code,
        "site_name": site.site_name,
        "site_title": site.site_title,
        "logo_text": site.logo_text,
        "contact_email": site.contact_email,
        "footer_copyright": site.footer_copyright,
    })


@public_router.get("/datasets", summary="当前站点可见数据集")
async def public_datasets(
    request: Request,
    db: Session = Depends(get_db),
):
    site = get_current_site(request, db)
    bound_ids = get_site_dataset_ids(db, site.site_code)
    if not bound_ids:
        return response_200(data={"items": []})

    datasets = db.query(DatasetRegistry).filter(
        DatasetRegistry.id.in_(list(bound_ids)),
        DatasetRegistry.is_public == True,
    ).all()
    return response_200(data={"items": [_public_dataset_dict(ds) for ds in datasets]})


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
    return response_200(data=_public_dataset_dict(ds))
