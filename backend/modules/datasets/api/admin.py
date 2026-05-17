"""Admin-only dataset endpoints (force-delete, state-rollback)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from modules.common.depends import get_db, require_superadmin
from shared.responses import response_200

router = APIRouter()


@router.post("/{dataset_id}/force-delete", dependencies=[Depends(require_superadmin)])
def admin_force_delete_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
):
    """Superadmin only: permanently remove a dataset and all related records."""
    from modules.datasets.dataset_model import Dataset
    from modules.datasets.models import DatasetVersion, DatasetAsset, AssetFile

    ds = db.query(Dataset).filter_by(id=dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Delete cascade: asset_files → assets → versions → dataset
    versions = db.query(DatasetVersion).filter_by(dataset_id=dataset_id).all()
    for v in versions:
        assets = db.query(DatasetAsset).filter_by(version_id=v.id).all()
        for a in assets:
            db.query(AssetFile).filter_by(asset_id=a.id).delete()
        db.query(DatasetAsset).filter_by(version_id=v.id).delete()
    db.query(DatasetVersion).filter_by(dataset_id=dataset_id).delete()

    # Delete breeding link table records
    from modules.breeding.models import (
        BreedingVariantSampleMap, BreedingPhenotypeSubjectMap,
        BreedingDatasetSubjectLink, BreedingDatasetAssayLink,
    )
    for model in [BreedingVariantSampleMap, BreedingPhenotypeSubjectMap,
                   BreedingDatasetSubjectLink, BreedingDatasetAssayLink]:
        db.query(model).filter_by(dataset_id=dataset_id).delete()

    db.delete(ds)
    db.commit()
    return response_200(data={"deleted_dataset_id": dataset_id})


@router.post("/{dataset_id}/rollback-lifecycle", dependencies=[Depends(require_superadmin)])
def admin_rollback_lifecycle_state(
    dataset_id: int,
    target_state: str = "draft",
    db: Session = Depends(get_db),
):
    """Superadmin only: rollback a dataset's lifecycle_state."""
    from modules.datasets.dataset_model import Dataset

    valid_states = {"draft", "active", "archived", "deprecated"}
    if target_state not in valid_states:
        raise HTTPException(status_code=400, detail=f"Invalid target state. Must be one of: {sorted(valid_states)}")

    ds = db.query(Dataset).filter_by(id=dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")

    old_state = ds.lifecycle_state
    ds.lifecycle_state = target_state
    db.commit()

    return response_200(data={
        "dataset_id": dataset_id,
        "previous_state": old_state,
        "current_state": target_state,
    })
