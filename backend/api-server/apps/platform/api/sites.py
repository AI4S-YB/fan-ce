from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from apps.common.depends import get_active_user
from db.database import get_db
from libs.responses.response import response_200

from ..models import PlatformSiteDatasetLink, PlatformSiteSetting
from ..multi_site import bind_dataset_to_site, get_site_dataset_ids
from ..schemas import PlatformSiteCreateRequest, PlatformSiteDatasetBindRequest, PlatformSiteUpdateRequest

sites_router = APIRouter(tags=["app:platform:站点管理"])


def _require_admin(user):
    if getattr(user, "is_superman", False) or int(getattr(user, "user_type", 0) or 0) == 1:
        return
    raise HTTPException(status_code=403, detail="Admin access required")


@sites_router.post("/sites", summary="创建站点")
async def create_site(
    request_data: PlatformSiteCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(get_active_user),
):
    _require_admin(user)
    existing = db.query(PlatformSiteSetting).filter(
        PlatformSiteSetting.site_code == request_data.site_code
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Site code already exists")

    site = PlatformSiteSetting(
        site_code=request_data.site_code,
        site_name=request_data.site_name or "",
        site_title=request_data.site_title or "",
        domain=request_data.domain or "",
        test_port=request_data.test_port or "",
        logo_text=request_data.logo_text or "",
        contact_email=request_data.contact_email or "",
        footer_copyright=request_data.footer_copyright or "",
        extra_json=request_data.extra_json or "{}",
    )
    db.add(site)
    db.commit()
    db.refresh(site)
    return response_200(data=site.to_dict())


@sites_router.get("/sites", summary="站点列表")
async def list_sites(
    db: Session = Depends(get_db),
    user=Depends(get_active_user),
):
    _require_admin(user)
    sites = db.query(PlatformSiteSetting).order_by(PlatformSiteSetting.id.asc()).all()

    # Single aggregation query instead of N+1
    count_rows = (
        db.query(
            PlatformSiteDatasetLink.site_code,
            func.count(PlatformSiteDatasetLink.id).label("cnt"),
        )
        .group_by(PlatformSiteDatasetLink.site_code)
        .all()
    )
    counts = {row.site_code: row.cnt for row in count_rows}

    items = []
    for site in sites:
        d = site.to_dict()
        d["dataset_count"] = counts.get(site.site_code, 0)
        items.append(d)
    return response_200(data={"items": items})


@sites_router.put("/sites/{site_code}", summary="更新站点")
async def update_site(
    site_code: str,
    request_data: PlatformSiteUpdateRequest,
    db: Session = Depends(get_db),
    user=Depends(get_active_user),
):
    _require_admin(user)
    site = db.query(PlatformSiteSetting).filter(
        PlatformSiteSetting.site_code == site_code
    ).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    update_fields = request_data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(site, field, value)
    db.add(site)
    db.commit()
    db.refresh(site)
    return response_200(data=site.to_dict())


@sites_router.delete("/sites/{site_code}", summary="删除站点")
async def delete_site(
    site_code: str,
    db: Session = Depends(get_db),
    user=Depends(get_active_user),
):
    _require_admin(user)
    if site_code == "default":
        raise HTTPException(status_code=400, detail="Cannot delete default site")
    site = db.query(PlatformSiteSetting).filter(
        PlatformSiteSetting.site_code == site_code
    ).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    db.delete(site)
    db.commit()
    return response_200(data={"deleted": site_code})


# ── Dataset binding ──

@sites_router.post("/sites/{site_code}/datasets", summary="绑定数据集到站点")
async def bind_dataset(
    site_code: str,
    request_data: PlatformSiteDatasetBindRequest,
    db: Session = Depends(get_db),
    user=Depends(get_active_user),
):
    _require_admin(user)
    site = db.query(PlatformSiteSetting).filter(
        PlatformSiteSetting.site_code == site_code
    ).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")
    try:
        bind_dataset_to_site(db, site_code, request_data.dataset_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return response_200(data={"bound": True})


@sites_router.delete("/sites/{site_code}/datasets/{dataset_id}", summary="解绑数据集")
async def unbind_dataset(
    site_code: str,
    dataset_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_active_user),
):
    _require_admin(user)
    link = db.query(PlatformSiteDatasetLink).filter(
        PlatformSiteDatasetLink.site_code == site_code,
        PlatformSiteDatasetLink.dataset_id == dataset_id,
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="Binding not found")
    db.delete(link)
    db.commit()
    return response_200(data={"unbound": True})


@sites_router.get("/sites/{site_code}/datasets", summary="站点已绑定数据集列表")
async def list_site_datasets(
    site_code: str,
    db: Session = Depends(get_db),
    user=Depends(get_active_user),
):
    _require_admin(user)
    site = db.query(PlatformSiteSetting).filter(
        PlatformSiteSetting.site_code == site_code
    ).first()
    if not site:
        raise HTTPException(status_code=404, detail="Site not found")

    from apps.datasets.models import DatasetRegistry

    bound_ids = get_site_dataset_ids(db, site_code)
    if not bound_ids:
        return response_200(data={"items": []})
    datasets = db.query(DatasetRegistry).filter(
        DatasetRegistry.id.in_(list(bound_ids))
    ).all()
    return response_200(data={"items": [ds.to_dict() for ds in datasets]})


@sites_router.get("/datasets/{dataset_id}/sites", summary="数据集已绑定的站点列表")
async def list_dataset_sites(
    dataset_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_active_user),
):
    _require_admin(user)
    links = db.query(PlatformSiteDatasetLink).filter(
        PlatformSiteDatasetLink.dataset_id == dataset_id
    ).all()
    site_codes = [link.site_code for link in links]
    if not site_codes:
        return response_200(data={"items": []})
    sites = db.query(PlatformSiteSetting).filter(
        PlatformSiteSetting.site_code.in_(site_codes)
    ).all()
    return response_200(data={"items": [s.to_dict() for s in sites]})
