import pytest


class TestPublicLineage:
    def test_public_lineage_endpoint_returns_empty_when_no_lineage(self, db_session):
        """Public lineage returns empty list when no edges exist"""
        from apps.datasets.dataset_model import Dataset
        from apps.datasets.models import DatasetVersion
        from apps.datasets.services import DatasetDomainService

        ds = Dataset(dataset_code="DS_NO_LINEAGE", dataset_type="genome",
                     visibility="public", assembly="IRGSP-1.0")
        db_session.add(ds)
        db_session.commit()

        v1 = DatasetVersion(
            dataset_id=ds.id, database_id=ds.id,
            version="v1", release_state="released",
        )
        db_session.add(v1)
        db_session.commit()

        svc = DatasetDomainService()
        result = svc._list_public_lineage(db=db_session, dataset_id=ds.id)
        assert isinstance(result, list)
        assert len(result) == 0

    def test_public_lineage_excludes_draft_versions(self, db_session):
        """Edges with draft dst version are excluded from public lineage"""
        from apps.datasets.dataset_model import Dataset
        from apps.datasets.models import DatasetVersion, DatasetLineageEdge
        from apps.datasets.services import DatasetDomainService

        ds1 = Dataset(dataset_code="DS_LIN_SRC", dataset_type="genome",
                      visibility="public", assembly="IRGSP-1.0")
        ds2 = Dataset(dataset_code="DS_LIN_DST", dataset_type="annotation",
                      visibility="public", assembly="IRGSP-1.0")
        db_session.add_all([ds1, ds2])
        db_session.commit()

        v1 = DatasetVersion(
            dataset_id=ds1.id, database_id=ds1.id,
            version="v1", release_state="released",
        )
        v2 = DatasetVersion(
            dataset_id=ds2.id, database_id=ds2.id,
            version="v1", release_state="draft",
        )
        db_session.add_all([v1, v2])
        db_session.commit()

        edge = DatasetLineageEdge(
            src_dataset_version_id=v1.id, dst_dataset_version_id=v2.id,
            relation_type="derived_from", direction="forward",
        )
        db_session.add(edge)
        db_session.commit()

        svc = DatasetDomainService()
        result = svc._list_public_lineage(db=db_session, dataset_id=ds1.id)
        # dst version is draft, edge should be excluded
        assert len(result) == 0

    def test_public_lineage_includes_released_edges(self, db_session):
        """Edges where both src and dst are released are included"""
        from apps.databases.models import Databases
        from apps.datasets.dataset_model import Dataset
        from apps.datasets.models import DatasetVersion, DatasetLineageEdge
        from apps.datasets.services import DatasetDomainService

        ds1 = Dataset(dataset_code="DS_LIN_BOTH_SRC", dataset_type="genome",
                      visibility="public", assembly="IRGSP-1.0")
        ds2 = Dataset(dataset_code="DS_LIN_BOTH_DST", dataset_type="annotation",
                      visibility="public", assembly="IRGSP-1.0")
        db_session.add_all([ds1, ds2])
        db_session.commit()

        # Legacy databases records needed by _build_lineage_payload
        db1 = Databases(id=ds1.id, name="DS_LIN_BOTH_SRC")
        db2 = Databases(id=ds2.id, name="DS_LIN_BOTH_DST")
        db_session.add_all([db1, db2])
        db_session.commit()

        v1 = DatasetVersion(
            dataset_id=ds1.id, database_id=ds1.id,
            version="v1", release_state="released",
        )
        v2 = DatasetVersion(
            dataset_id=ds2.id, database_id=ds2.id,
            version="v1", release_state="released",
        )
        db_session.add_all([v1, v2])
        db_session.commit()

        edge = DatasetLineageEdge(
            src_dataset_version_id=v1.id, dst_dataset_version_id=v2.id,
            relation_type="derived_from", direction="forward",
        )
        db_session.add(edge)
        db_session.commit()

        svc = DatasetDomainService()
        result = svc._list_public_lineage(db=db_session, dataset_id=ds1.id)
        assert len(result) == 1
        assert result[0]["relation_type"] == "derived_from"
        assert result[0]["src_version_id"] == v1.id
        assert result[0]["dst_version_id"] == v2.id
