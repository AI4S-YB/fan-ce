import json
from types import SimpleNamespace
from pathlib import Path
import sys

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.datasets.models import (
    AssetFile,
    AssetFileTypeRegistry,
    AssetTypeRegistry,
    DatasetAsset,
    DatasetKindRegistry,
    DatasetLineageEdge,
    DatasetPublishRecord,
    DatasetRegistry,
    DatasetStagingFile,
    DatasetVersion,
    DatasetVersionPublishRecord,
    DatasetWorkflowTask,
)
from modules.datasets.schemas import (
    AssetTypeRegistryCreateRequest,
    DatasetKindRegistryCreateRequest,
    DatasetVersionReleaseRequest,
)
from modules.datasets.services import dataset_domain_service
from modules.system.user.models import Role, User
from shared.database import Base


DATASET_TEST_TABLES = [
    User.__table__,
    Role.__table__,
    DatasetKindRegistry.__table__,
    AssetTypeRegistry.__table__,
    AssetFileTypeRegistry.__table__,
    DatasetStagingFile.__table__,
    DatasetRegistry.__table__,
    DatasetWorkflowTask.__table__,
    DatasetPublishRecord.__table__,
    DatasetVersion.__table__,
    DatasetAsset.__table__,
    AssetFile.__table__,
    DatasetLineageEdge.__table__,
    DatasetVersionPublishRecord.__table__,
]


def make_user(user_id, *, is_superman=False, user_type=0):
    return SimpleNamespace(id=user_id, is_superman=is_superman, user_type=user_type)


def create_dataset(db, *, name, team_id=0, dataset_type="generic"):
    row = DatasetRegistry(
        title=name,
        dataset_type=dataset_type,
        lifecycle_state="ready",
        is_public=False,
        create_time=1,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    # Set database_id to self-reference so legacy_bridge.get_database can find it
    row.dataset_id = row.id
    db.commit()
    db.refresh(row)
    return row


def create_version(
    db,
    *,
    dataset_id,
    version,
    dataset_type="generic",
    is_current=False,
    lifecycle_state="draft",
    file_path=None,
    file_format=None,
):
    row = DatasetVersion(
        database_id=dataset_id,
        version=version,
        title=version,
        dataset_type=dataset_type,
        lifecycle_state=lifecycle_state,
        visibility="private",
        release_state="unreleased",
        file_path=file_path,
        file_format=file_format,
        query_engine="file",
        validation_summary=None,
        index_summary=None,
        meta_json=None,
        is_current=is_current,
        is_default_public=False,
        create_time=1,
        update_time=1,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def create_asset(db, *, dataset_id, version_id, asset_code="asset_1", file_format="txt"):
    row = DatasetAsset(
        database_id=dataset_id,
        dataset_version_id=version_id,
        asset_code=asset_code,
        asset_name=asset_code,
        asset_type="metadata_table",
        file_format=file_format,
        query_engine="file",
        storage_backend="local",
        workflow_state="draft",
        status="active",
        is_required=True,
        is_query_entry=True,
        display_order=0,
        meta_json=None,
        create_time=1,
        update_time=1,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def create_asset_file(db, *, dataset_id, asset_id, local_path="/tmp/test.txt", file_format="txt"):
    row = AssetFile(
        database_id=dataset_id,
        dataset_asset_id=asset_id,
        file_role="primary",
        file_name=Path(local_path).name,
        storage_uri=f"file://{local_path}",
        local_path=local_path,
        file_format=file_format,
        mime_type=None,
        checksum_type=None,
        checksum_value=None,
        file_size=1,
        compress_type=None,
        index_of_file_id=None,
        status="active",
        meta_json=None,
        create_time=1,
        update_time=1,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def create_dataset_kind_registry(db, *, code="generic", base_code="generic", name="Generic"):
    row = DatasetKindRegistry(
        code=code,
        base_code=base_code,
        name=name,
        description=None,
        is_system=False,
        is_active=True,
        sort_order=0,
        meta_json=None,
        create_time=1,
        update_time=1,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine, tables=DATASET_TEST_TABLES)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_owner_can_get_dataset_and_unrelated_user_is_denied(db_session):
    dataset = create_dataset(db_session, name="owned-dataset", team_id=0)

    owner_payload = dataset_domain_service.get_dataset(db=db_session, dataset_id=dataset.id, user=make_user(101))
    assert owner_payload["id"] == dataset.id

    with pytest.raises(HTTPException) as exc_info:
        dataset_domain_service.get_dataset(db=db_session, dataset_id=dataset.id, user=make_user(202))
    assert exc_info.value.status_code == 403



def test_list_datasets_filters_inaccessible_rows(db_session):
    owned_dataset = create_dataset(db_session, name="visible", team_id=0)
    create_dataset(db_session, name="hidden", team_id=0)

    request_data = SimpleNamespace(
        page=1,
        size=20,
        team_id=0,
        project_id=None,
        dataset_id=None,
        name=None,
        dataset_type=None,
        lifecycle_state=None,
        visibility=None,
    )

    result = dataset_domain_service.list_datasets(db=db_session, request_data=request_data, user=make_user(401))
    assert result["total"] == 1
    assert [item["id"] for item in result["dataList"]] == [owned_dataset.id]


def test_get_options_filters_inaccessible_rows(db_session):
    visible_dataset = create_dataset(db_session, name="visible-option", team_id=0)
    create_dataset(db_session, name="hidden-option", team_id=0)

    request_data = SimpleNamespace(
        page=1,
        size=20,
        team_id=0,
        project_id=None,
        dataset_id=None,
        name=None,
        dataset_type=None,
        lifecycle_state=None,
        visibility=None,
    )

    result = dataset_domain_service.get_options(db=db_session, request_data=request_data, user=make_user(451))
    assert [item["id"] for item in result] == [visible_dataset.id]


def test_get_options_exposes_resolved_file_path_from_current_version_asset(db_session, tmp_path):
    """get_options resolves file_path from the current version's primary asset file."""
    # Seed dataset kind registry so "variant" type is recognized
    kind = DatasetKindRegistry(
        code="variant",
        base_code="variant",
        name="Variant",
        is_system=False,
        is_active=True,
        sort_order=1,
        create_time=1,
        update_time=1,
    )
    db_session.add(kind)
    db_session.commit()

    dataset = create_dataset(db_session, name="visible-option", team_id=0, dataset_type="variant")
    version = create_version(
        db_session,
        dataset_id=dataset.id,
        version="v1",
        dataset_type="variant",
        lifecycle_state="ready",
        file_path=None,
        file_format="vcf.gz",
        is_current=True,
    )
    asset = create_asset(
        db_session,
        dataset_id=dataset.id,
        version_id=version.id,
        asset_code="variant_asset",
        file_format="vcf.gz",
    )
    file_path = tmp_path / "dataset.vcf.gz"
    file_path.write_text("##fileformat=VCFv4.2\n", encoding="utf-8")
    create_asset_file(
        db_session,
        dataset_id=dataset.id,
        asset_id=asset.id,
        local_path=str(file_path),
        file_format="vcf.gz",
    )

    request_data = SimpleNamespace(
        page=1,
        size=20,
        team_id=0,
        project_id=None,
        dataset_id=None,
        name=None,
        dataset_type="variant",
        lifecycle_state=None,
        visibility=None,
    )

    result = dataset_domain_service.get_options(db=db_session, request_data=request_data, user=make_user(452))

    assert len(result) == 1
    assert result[0]["id"] == dataset.id
    assert result[0]["file_path"] == str(file_path)
    assert result[0]["file_format"] == "vcf.gz"
    assert result[0]["version"] == "v1"


def test_version_asset_file_and_lineage_inherit_dataset_scope(db_session):
    dataset = create_dataset(db_session, name="versioned", team_id=0)
    version_a = create_version(db_session, dataset_id=dataset.id, version="v1", is_current=True)
    version_b = create_version(db_session, dataset_id=dataset.id, version="v2")
    asset = create_asset(db_session, dataset_id=dataset.id, version_id=version_a.id)
    asset_file = create_asset_file(db_session, dataset_id=dataset.id, asset_id=asset.id)
    lineage = DatasetLineageEdge(
        database_id=dataset.id,
        src_dataset_version_id=version_a.id,
        src_asset_id=asset.id,
        dst_dataset_version_id=version_b.id,
        dst_asset_id=None,
        relation_type="derived_from",
        direction="forward",
        detail_json=None,
        create_user_id=501,
        create_time=1,
    )
    db_session.add(lineage)
    db_session.commit()
    db_session.refresh(lineage)

    owner = make_user(501)
    outsider = make_user(502)

    assert dataset_domain_service.get_dataset_version(db=db_session, version_id=version_a.id, user=owner)["id"] == version_a.id
    assert dataset_domain_service.get_dataset_asset(db=db_session, asset_id=asset.id, user=owner)["id"] == asset.id
    assert dataset_domain_service.get_asset_file(db=db_session, asset_file_id=asset_file.id, user=owner)["id"] == asset_file.id
    lineage_payload = dataset_domain_service.list_dataset_lineage(db=db_session, version_id=version_a.id, limit=10, user=owner)
    assert [item["id"] for item in lineage_payload["items"]] == [lineage.id]

    with pytest.raises(HTTPException) as version_exc:
        dataset_domain_service.get_dataset_version(db=db_session, version_id=version_a.id, user=outsider)
    assert version_exc.value.status_code == 403

    with pytest.raises(HTTPException) as asset_exc:
        dataset_domain_service.get_dataset_asset(db=db_session, asset_id=asset.id, user=outsider)
    assert asset_exc.value.status_code == 403

    with pytest.raises(HTTPException) as file_exc:
        dataset_domain_service.get_asset_file(db=db_session, asset_file_id=asset_file.id, user=outsider)
    assert file_exc.value.status_code == 403

    with pytest.raises(HTTPException) as lineage_exc:
        dataset_domain_service.list_dataset_lineage(db=db_session, version_id=version_a.id, limit=10, user=outsider)
    assert lineage_exc.value.status_code == 403


def test_workflow_task_access_uses_dataset_scope_or_operator_scope(db_session):
    dataset = create_dataset(db_session, name="task-dataset", team_id=0)
    dataset_task = DatasetWorkflowTask(
        database_id=dataset.id,
        task_type="validate",
        status="success",
        from_lifecycle_state="uploaded",
        to_lifecycle_state="validated",
        operator_id=999,
        detail="ok",
        create_time=1,
        finish_time=1,
    )
    global_task = DatasetWorkflowTask(
        database_id=None,
        task_type="validate",
        status="pending",
        from_lifecycle_state=None,
        to_lifecycle_state=None,
        operator_id=602,
        detail="queued",
        create_time=1,
        finish_time=None,
    )
    db_session.add_all([dataset_task, global_task])
    db_session.commit()
    db_session.refresh(dataset_task)
    db_session.refresh(global_task)

    assert dataset_domain_service.get_task_info(db=db_session, task_id=dataset_task.id, user=make_user(601))["id"] == dataset_task.id
    assert dataset_domain_service.get_task_info(db=db_session, task_id=global_task.id, user=make_user(602))["id"] == global_task.id

    with pytest.raises(HTTPException) as dataset_task_exc:
        dataset_domain_service.get_task_info(db=db_session, task_id=dataset_task.id, user=make_user(603))
    assert dataset_task_exc.value.status_code == 403

    with pytest.raises(HTTPException) as global_task_exc:
        dataset_domain_service.get_task_info(db=db_session, task_id=global_task.id, user=make_user(603))
    assert global_task_exc.value.status_code == 403


def test_registry_management_requires_platform_admin(db_session):
    create_dataset_kind_registry(db_session, code="generic", base_code="generic", name="Generic")
    normal_user = make_user(801)
    platform_admin = make_user(802, is_superman=True)

    with pytest.raises(HTTPException) as kind_exc:
        dataset_domain_service.create_dataset_kind_registry(
            db=db_session,
            request_data=DatasetKindRegistryCreateRequest(
                code="genome_resource",
                base_code="genome_resource",
                name="Genome Resource",
            ),
            user=normal_user,
        )
    assert kind_exc.value.status_code == 403

    created_kind = dataset_domain_service.create_dataset_kind_registry(
        db=db_session,
        request_data=DatasetKindRegistryCreateRequest(
            code="genome_resource",
            base_code="genome_resource",
            name="Genome Resource",
        ),
        user=platform_admin,
    )
    assert created_kind["code"] == "genome_resource"

    with pytest.raises(HTTPException) as asset_type_exc:
        dataset_domain_service.create_asset_type_registry(
            db=db_session,
            request_data=AssetTypeRegistryCreateRequest(
                code="reference_fasta",
                base_code="reference_fasta",
                name="Reference FASTA",
                allowed_dataset_types=["generic"],
            ),
            user=normal_user,
        )
    assert asset_type_exc.value.status_code == 403

    created_asset_type = dataset_domain_service.create_asset_type_registry(
        db=db_session,
        request_data=AssetTypeRegistryCreateRequest(
            code="reference_fasta",
            base_code="reference_fasta",
            name="Reference FASTA",
            allowed_dataset_types=["generic"],
        ),
        user=platform_admin,
    )
    assert created_asset_type["code"] == "reference_fasta"


def test_user_type_admin_has_global_dataset_access_and_registry_access(db_session):
    dataset = create_dataset(db_session, name="admin-visible", team_id=0)
    platform_admin = make_user(902, user_type=1)

    dataset_payload = dataset_domain_service.get_dataset(
        db=db_session,
        dataset_id=dataset.id,
        user=platform_admin,
    )
    assert dataset_payload["id"] == dataset.id

    created_kind = dataset_domain_service.create_dataset_kind_registry(
        db=db_session,
        request_data=DatasetKindRegistryCreateRequest(
            code="expression_matrix",
            base_code="expression_matrix",
            name="Expression Matrix",
        ),
        user=platform_admin,
    )
    assert created_kind["code"] == "expression_matrix"


def test_global_version_publish_record_list_is_filtered_by_access_scope(db_session, tmp_path):
    """Release publishes a version and creates publish records accessible to owners and admins."""
    owner_a = make_user(1001)
    owner_b = make_user(1002)
    admin = make_user(1003, user_type=1)

    dataset_a = create_dataset(db_session, name="publish-visible"owner_a.id, team_id=0)
    dataset_b = create_dataset(db_session, name="publish-hidden"owner_b.id, team_id=0)

    file_a = tmp_path / "visible.txt"
    file_b = tmp_path / "hidden.txt"
    file_a.write_text("visible\n", encoding="utf-8")
    file_b.write_text("hidden\n", encoding="utf-8")

    version_a = create_version(
        db_session,
        dataset_id=dataset_a.id,
        version="v1",
        lifecycle_state="ready",
        file_path=str(file_a),
        file_format="txt",
    )
    version_b = create_version(
        db_session,
        dataset_id=dataset_b.id,
        version="v1",
        lifecycle_state="ready",
        file_path=str(file_b),
        file_format="txt",
    )

    dataset_domain_service.release_dataset_version(
        db=db_session,
        version_id=version_a.id,
        request_data=DatasetVersionReleaseRequest(id=version_a.id, note="release visible"),
        user=owner_a,
    )
    dataset_domain_service.release_dataset_version(
        db=db_session,
        version_id=version_b.id,
        request_data=DatasetVersionReleaseRequest(id=version_b.id, note="release hidden"),
        user=owner_b,
    )

    # After release, datasets are public so any authenticated user can see records
    # Admin sees publish records for all datasets
    admin_records = dataset_domain_service.get_version_publish_record_list(
        db=db_session, user=admin, limit=20
    )
    assert len(admin_records["items"]) >= 2

    # Owner can also see their own publish records via dataset_id filter
    owner_records = dataset_domain_service.get_version_publish_record_list(
        db=db_session, dataset_id=dataset_a.id, user=owner_a, limit=20
    )
    assert owner_records["dataset_id"] == dataset_a.id
    assert len(owner_records["items"]) >= 1



# Community Edition: system_project removed. test_project_filter uses Project which is deleted.
# Rewrite with brd_program when breeding program linkage is available.
# def test_project_filter_still_respects_row_access_while_admin_sees_all(db_session):
#     project = Project(name="shared-project", code="shared-project", user_id=1300, type="1", sort=1, status=1, is_public=0, is_active=True, is_delete=0, create_time=1, remark="")
#     db_session.add(project)
#     db_session.commit()
#     db_session.refresh(project)
#
#     owned_dataset = create_dataset(db_session, name="owned-filtered", team_id=0)
#     hidden_dataset = create_dataset(db_session, name="hidden-filtered", team_id=0)
#     db_session.add_all(
#         [
#             ProjectDatabasesLink(database_id=owned_dataset.id, project_id=project.id),
#             ProjectDatabasesLink(database_id=hidden_dataset.id, project_id=project.id),
#         ]
#     )
#     db_session.commit()
#
#     request_data = SimpleNamespace(
#         page=1,
#         size=20,
#         team_id=0,
#         project_id=project.id,
#         dataset_id=None,
#         name=None,
#         dataset_type=None,
#         lifecycle_state=None,
#         visibility=None,
#     )
#
#     owner_result = dataset_domain_service.list_datasets(db=db_session, request_data=request_data, user=make_user(1301))
#     admin_result = dataset_domain_service.list_datasets(db=db_session, request_data=request_data, user=make_user(1309, user_type=1))
#
#     assert [item["id"] for item in owner_result["dataList"]] == [owned_dataset.id]
#     assert {item["id"] for item in admin_result["dataList"]} == {owned_dataset.id, hidden_dataset.id}


def test_retry_ingest_task_respects_dataset_scope_and_global_operator_scope(db_session):
    dataset = create_dataset(db_session, name="retry-dataset", team_id=0)
    dataset_task = DatasetWorkflowTask(
        database_id=dataset.id,
        task_type="validate",
        status="failed",
        from_lifecycle_state="uploaded",
        to_lifecycle_state="uploaded",
        operator_id=1402,
        detail=json.dumps({"async_task": True, "action": "validate", "request": {"id": dataset.id}, "attempt": 1}, ensure_ascii=False),
        create_time=1,
        finish_time=1,
    )
    global_task = DatasetWorkflowTask(
        database_id=None,
        task_type="index",
        status="failed",
        from_lifecycle_state=None,
        to_lifecycle_state=None,
        operator_id=1403,
        detail=json.dumps({"async_task": True, "action": "index", "request": {"file_path": "/tmp/demo.txt"}, "attempt": 1}, ensure_ascii=False),
        create_time=1,
        finish_time=1,
    )
    db_session.add_all([dataset_task, global_task])
    db_session.commit()
    db_session.refresh(dataset_task)
    db_session.refresh(global_task)

    retried_dataset_task = dataset_domain_service.retry_ingest_task(db=db_session, task_id=dataset_task.id, user=make_user(1401))
    retried_global_task = dataset_domain_service.retry_ingest_task(db=db_session, task_id=global_task.id, user=make_user(1403))

    assert retried_dataset_task["operator_id"] == 1401
    assert retried_dataset_task["dataset_id"] == dataset.id
    assert retried_dataset_task["status"] == "pending"
    assert retried_global_task["operator_id"] == 1403
    assert retried_global_task["dataset_id"] is None
    assert retried_global_task["status"] == "pending"

    with pytest.raises(HTTPException) as dataset_retry_exc:
        dataset_domain_service.retry_ingest_task(db=db_session, task_id=dataset_task.id, user=make_user(1402))
    assert dataset_retry_exc.value.status_code == 403

    with pytest.raises(HTTPException) as global_retry_exc:
        dataset_domain_service.retry_ingest_task(db=db_session, task_id=global_task.id, user=make_user(1404))
    assert global_retry_exc.value.status_code == 403
