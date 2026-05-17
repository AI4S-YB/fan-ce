import pytest


class TestLineageConstraints:
    def test_duplicate_lineage_edge_is_rejected(self, db_session):
        """Duplicate same src+dst+relation_type should raise IntegrityError"""
        from modules.datasets.models import DatasetLineageEdge

        edge1 = DatasetLineageEdge(
            src_dataset_version_id=1, dst_dataset_version_id=2,
            relation_type="derived_from", direction="forward",
        )
        db_session.add(edge1)
        db_session.commit()

        edge2 = DatasetLineageEdge(
            src_dataset_version_id=1, dst_dataset_version_id=2,
            relation_type="derived_from", direction="forward",
        )
        db_session.add(edge2)
        with pytest.raises(Exception):
            db_session.commit()

    def test_invalid_relation_type_is_rejected(self):
        """Invalid relation_type should raise HTTPException"""
        from fastapi import HTTPException
        from modules.datasets.services import DatasetDomainService, validate_lineage_relation_type

        svc = DatasetDomainService()
        valid_types = svc.VALID_RELATION_TYPES
        assert "invalid_type_xyz" not in valid_types

        with pytest.raises(HTTPException) as exc:
            validate_lineage_relation_type("invalid_type_xyz")
        assert exc.value.status_code == 400

    def test_valid_relation_types_are_accepted(self):
        """All valid relation_types pass validation"""
        from modules.datasets.services import validate_lineage_relation_type

        for rt in ["derived_from", "derived_from_legacy", "cites", "supersedes", "complements", "references"]:
            result = validate_lineage_relation_type(rt)
            assert result is True
