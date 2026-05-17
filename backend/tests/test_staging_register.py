import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from modules.datasets.services import DatasetDomainService
from modules.datasets.models import DatasetStagingFile, DatasetRegistry
from shared.database import Base

TEST_TABLES = [
    DatasetStagingFile.__table__,
    DatasetRegistry.__table__,
]

@pytest.fixture()
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine, tables=TEST_TABLES)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


class TestRegisterStagingFiles:
    def test_register_staging_files_exists(self):
        """New method exists on the service."""
        svc = DatasetDomainService()
        assert hasattr(svc, 'register_staging_files')

    def test_all_old_candidate_methods_removed(self):
        """All candidate-specific methods have been deleted."""
        svc = DatasetDomainService()
        removed = [
            'list_registration_candidates',
            'get_registration_candidate',
            'create_registration_candidate',
            'update_registration_candidate',
            'delete_registration_candidate',
            'register_candidate',
            'list_registration_candidate_files',
            'update_registration_candidate_file',
            '_build_candidate_payload',
            '_build_candidate_file_payload',
            '_parse_candidate_meta',
            '_encode_candidate_meta',
            '_infer_candidate_source_kind',
        ]
        for name in removed:
            assert not hasattr(svc, name), f"'{name}' should have been removed from DatasetDomainService"

    def test_renamed_helpers_exist(self):
        """All renamed helpers exist with new names."""
        svc = DatasetDomainService()
        renamed = [
            '_staging_file_format',
            '_staging_name_hint',
            '_is_index_format',
            '_is_metadata_format',
            '_infer_file_role',
            '_resolve_file_role',
            '_infer_asset_mapping',
            '_asset_query_engine',
            '_asset_name_from_type',
            '_get_primary_staging',
            '_ensure_asset',
            '_validate_staging_available',
            'validate_staging_files',
        ]
        for name in renamed:
            assert hasattr(svc, name), f"'{name}' should exist on DatasetDomainService"

    def test_no_candidate_prefix_in_method_names(self):
        """No method on the service should contain 'candidate' in its name."""
        svc = DatasetDomainService()
        candidate_methods = [
            name for name in dir(svc)
            if 'candidate' in name.lower() and callable(getattr(svc, name, None))
        ]
        assert len(candidate_methods) == 0, (
            f"Found candidate-prefixed methods: {candidate_methods}"
        )

    def test_supported_registration_modes_removed(self):
        """SUPPORTED_REGISTRATION_MODES class attribute is gone."""
        svc = DatasetDomainService()
        assert not hasattr(svc, 'SUPPORTED_REGISTRATION_MODES')
        assert not hasattr(DatasetDomainService, 'SUPPORTED_REGISTRATION_MODES')

    def test_register_staging_files_validates_staging_file_status(self, db_session):
        """Staging files with invalid status are rejected."""
        sf = DatasetStagingFile(
            staging_code="stg-deleted", local_path="/tmp/x.fa",
            file_format="fasta", dataset_type="genome",
            status="deleted", create_time=1, update_time=1,
        )
        db_session.add(sf)
        db_session.commit()

        svc = DatasetDomainService()
        from types import SimpleNamespace
        with pytest.raises(Exception):
            svc.register_staging_files(
                db=db_session,
                request_data=SimpleNamespace(
                    staging_file_ids=[sf.id],
                    name="Test",
                    dataset_type="genome",
                    organism="Oryza sativa",
                    is_public=False,
                    team_id=0,
                    project_id=0,
                ),
                user=SimpleNamespace(id=1),
            )
