from pathlib import Path
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.breeding.models import BreedingTaxonomySourceSnapshot
from apps.breeding.models import BreedingTaxonomyCache, BreedingTaxonomyName, BreedingTaxonomyNode
from apps.platform.setup_jobs import get_taxonomy_import_job, run_taxonomy_import_job, submit_taxonomy_import_job
from apps.platform.setup_state import (
    is_taxonomy_ready,
    list_taxonomy_packages,
    query_taxonomy_setup_state,
    register_taxonomy_package,
)
from apps.system.base.models import SystemInstallJob, SystemInstallLock, SystemInstallPackage
from db.database import Base


TEST_TABLES = [
    BreedingTaxonomySourceSnapshot.__table__,
    BreedingTaxonomyNode.__table__,
    BreedingTaxonomyName.__table__,
    BreedingTaxonomyCache.__table__,
    SystemInstallPackage.__table__,
    SystemInstallJob.__table__,
    SystemInstallLock.__table__,
]

@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine, tables=TEST_TABLES)
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    session = testing_session()
    try:
        yield session, engine, testing_session
    finally:
        session.close()
        engine.dispose()


def _patch_system_init(monkeypatch, testing_session, engine):
    class TestingDBManager:
        def __enter__(self):
            self.db = testing_session()
            return self.db

        def __exit__(self, exc_type, exc_value, traceback):
            self.db.close()

    monkeypatch.setattr("apps.system.init.engine", engine)
    monkeypatch.setattr("apps.system.init.MyDBManager", TestingDBManager)


def _patch_setup_jobs(monkeypatch, testing_session):
    class TestingDBManager:
        def __enter__(self):
            self.db = testing_session()
            return self.db

        def __exit__(self, exc_type, exc_value, traceback):
            self.db.close()

    monkeypatch.setattr("apps.platform.setup_jobs.MyDBManager", TestingDBManager)


def _build_small_taxdump_dir(base_dir: Path):
    taxdump_dir = base_dir / "taxdump"
    taxdump_dir.mkdir()
    (taxdump_dir / "nodes.dmp").write_text(
        "1\t|\t1\t|\tno rank\t|\n"
        "3702\t|\t1\t|\tspecies\t|\n",
        encoding="utf-8",
    )
    (taxdump_dir / "names.dmp").write_text(
        "1\t|\troot\t|\t\t|\tscientific name\t|\n"
        "3702\t|\tArabidopsis thaliana\t|\t\t|\tscientific name\t|\n"
        "3702\t|\tthale cress\t|\t\t|\tcommon name\t|\n",
        encoding="utf-8",
    )
    return taxdump_dir


def test_init_system_tables_creates_locked_taxonomy_guard_without_snapshot(db_session, monkeypatch):
    _session, engine, testing_session = db_session
    _patch_system_init(monkeypatch, testing_session, engine)

    from apps.system.init import init_system_tables

    init_system_tables()

    verify_session = testing_session()
    try:
        lock_obj = verify_session.query(SystemInstallLock).filter(SystemInstallLock.lock_code == "taxonomy_required").first()
        assert lock_obj is not None
        assert lock_obj.is_locked == 1
        assert lock_obj.reason == "taxonomy 未安装"
        assert lock_obj.required_action == "install_taxonomy"
        assert is_taxonomy_ready(verify_session) is False
    finally:
        verify_session.close()


def test_init_system_tables_unlocks_when_taxonomy_snapshot_exists(db_session, monkeypatch):
    session, engine, testing_session = db_session
    session.add(
        BreedingTaxonomySourceSnapshot(
            source_name="ncbi_new_taxdump",
            source_version="2026-04-05",
            node_count=10,
            name_count=20,
        )
    )
    session.commit()

    _patch_system_init(monkeypatch, testing_session, engine)

    from apps.system.init import init_system_tables

    init_system_tables()

    verify_session = testing_session()
    try:
        lock_obj = verify_session.query(SystemInstallLock).filter(SystemInstallLock.lock_code == "taxonomy_required").first()
        assert lock_obj is not None
        assert lock_obj.is_locked == 0
        assert lock_obj.reason == "taxonomy 已安装"
        assert is_taxonomy_ready(verify_session) is True
    finally:
        verify_session.close()


def test_platform_setup_state_payload(db_session):
    session, _engine, _testing_session = db_session
    session.add(
        BreedingTaxonomySourceSnapshot(
            source_name="ncbi_new_taxdump",
            source_version="2026-04-05",
            node_count=2735827,
            name_count=3212928,
        )
    )
    session.add(
        SystemInstallLock(
            lock_code="taxonomy_required",
            is_locked=0,
            reason="taxonomy 已安装",
            required_action="install_taxonomy",
        )
    )
    session.add(
        SystemInstallPackage(
            package_code="builtin-taxonomy-2026-04-05",
            package_type="taxonomy_bundle",
            package_name="FAN taxonomy bundle 2026-04-05",
            source="builtin",
            source_version="2026-04-05",
            storage_path="/opt/fan/packages/taxonomy/fan-taxonomy-bundle-2026-04-05.tar.gz",
            status="ready",
        )
    )
    session.commit()
    package_obj = session.query(SystemInstallPackage).order_by(SystemInstallPackage.id.desc()).first()
    session.add(
        SystemInstallJob(
            job_type="taxonomy_import",
            package_id=package_obj.id,
            status="success",
            stage="completed",
            progress_percent=100,
        )
    )
    session.commit()

    state = query_taxonomy_setup_state(session)

    assert state["ready"] is True
    assert state["status"] == "ready"
    assert state["lock"]["is_locked"] == 0
    assert state["package"]["package_code"] == "builtin-taxonomy-2026-04-05"
    assert state["snapshot"]["source_version"] == "2026-04-05"
    assert state["job"]["status"] == "success"


def test_register_and_list_taxonomy_packages(db_session, tmp_path):
    session, _engine, _testing_session = db_session
    bundle_path = tmp_path / "fan-taxonomy-bundle-2026-04-05.tar.gz"
    bundle_path.write_bytes(b"taxonomy-bundle")

    package = register_taxonomy_package(
        session,
        payload={
            "package_code": "builtin-taxonomy-2026-04-05",
            "package_name": "FAN taxonomy bundle 2026-04-05",
            "package_type": "taxonomy_bundle",
            "storage_path": str(bundle_path),
            "source": "builtin",
            "source_version": "2026-04-05",
            "manifest_json": '{"package_type":"taxonomy_bundle"}',
        },
        created_by=1,
    )
    package_list = list_taxonomy_packages(session)

    assert package["package_code"] == "builtin-taxonomy-2026-04-05"
    assert package["file_size"] == len(b"taxonomy-bundle")
    assert package_list["recommended_package"]["package_code"] == "builtin-taxonomy-2026-04-05"
    assert len(package_list["items"]) == 1


def test_submit_and_run_taxonomy_import_job(db_session, tmp_path, monkeypatch):
    session, _engine, testing_session = db_session
    dump_dir = _build_small_taxdump_dir(tmp_path)
    _patch_setup_jobs(monkeypatch, testing_session)

    package = register_taxonomy_package(
        session,
        payload={
            "package_code": "local-taxdump-test",
            "package_name": "Local taxonomy test dump",
            "package_type": "taxonomy_raw_dump",
            "storage_path": str(dump_dir),
            "source": "builtin",
            "source_version": "2026-04-05",
        },
        created_by=1,
    )
    job = submit_taxonomy_import_job(session, package_id=package["id"], force_reinstall=False, operator_id=1)
    run_taxonomy_import_job(job["id"])

    verify_session = testing_session()
    try:
        job_payload = get_taxonomy_import_job(verify_session, job_id=job["id"])
        lock_obj = verify_session.query(SystemInstallLock).filter(SystemInstallLock.lock_code == "taxonomy_required").first()
        snapshot = verify_session.query(BreedingTaxonomySourceSnapshot).order_by(BreedingTaxonomySourceSnapshot.id.desc()).first()
        node_count = verify_session.query(BreedingTaxonomyNode).count()
        name_count = verify_session.query(BreedingTaxonomyName).count()
        cache_count = verify_session.query(BreedingTaxonomyCache).count()

        assert job_payload["status"] == "success"
        assert job_payload["stage"] == "completed"
        assert job_payload["setup_state"]["ready"] is True
        assert lock_obj.is_locked == 0
        assert snapshot.source_version == "2026-04-05"
        assert node_count == 2
        assert name_count == 3
        assert cache_count == 2
    finally:
        verify_session.close()
