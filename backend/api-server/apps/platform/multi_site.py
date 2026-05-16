"""Multi-site support: site identification and dataset access control."""
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from .models import PlatformSiteDatasetLink, PlatformSiteSetting


def get_current_site(request: Request, db: Session) -> PlatformSiteSetting:
    """Resolve the current site from the request Host header."""
    host = request.headers.get("host", "")  # "rice.org" or "127.0.0.1:5677"

    # Try exact domain match first
    site = db.query(PlatformSiteSetting).filter(
        PlatformSiteSetting.domain == host
    ).first()
    if site:
        return site

    # Try port match (for testing with IP:port)
    if ":" in host:
        port = host.split(":")[-1]
        site = db.query(PlatformSiteSetting).filter(
            PlatformSiteSetting.test_port == port
        ).first()
        if site:
            return site

    # Fallback: return default site if exists
    site = db.query(PlatformSiteSetting).filter(
        PlatformSiteSetting.site_code == "default"
    ).first()
    if site:
        return site

    raise HTTPException(status_code=404, detail="Site not found")


def get_site_dataset_ids(db: Session, site_code: str) -> set[int]:
    """Return the set of dataset IDs visible to a given site."""
    links = db.query(PlatformSiteDatasetLink.dataset_id).filter(
        PlatformSiteDatasetLink.site_code == site_code
    ).all()
    return {row.dataset_id for row in links}


def bind_dataset_to_site(db: Session, site_code: str, dataset_id: int):
    """Bind a dataset to a site. Dataset must be public."""
    from apps.datasets.models import DatasetRegistry

    ds = db.query(DatasetRegistry).filter(DatasetRegistry.id == dataset_id).first()
    if not ds:
        raise ValueError("Dataset not found")
    if not ds.is_public:
        raise ValueError("Dataset must be public before binding to a site")

    existing = db.query(PlatformSiteDatasetLink).filter(
        PlatformSiteDatasetLink.site_code == site_code,
        PlatformSiteDatasetLink.dataset_id == dataset_id,
    ).first()
    if existing:
        return existing

    link = PlatformSiteDatasetLink(site_code=site_code, dataset_id=dataset_id)
    db.add(link)
    db.commit()
    return link


def unbind_dataset_from_site(db: Session, site_code: str, dataset_id: int):
    """Remove a dataset from a site."""
    db.query(PlatformSiteDatasetLink).filter(
        PlatformSiteDatasetLink.site_code == site_code,
        PlatformSiteDatasetLink.dataset_id == dataset_id,
    ).delete()
    db.commit()
