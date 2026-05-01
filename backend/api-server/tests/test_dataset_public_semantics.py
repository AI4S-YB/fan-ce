from pathlib import Path
import json
import sqlite3
import sys
from types import SimpleNamespace

import h5py
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import apps.datasets.adapters.expression as expression_adapter_module
import apps.datasets.adapters.sequence as sequence_adapter_module
import apps.datasets.adapters.signal as signal_adapter_module
import apps.datasets.adapters.variant as variant_adapter_module
import apps.datasets.bundle_provisioning as bundle_provisioning
import apps.datasets.init as dataset_init_module
import apps.datasets.services as dataset_services
from apps.datasets.crud import dataset_registry_db
from apps.databases.models import Databases, DatabasesFile, DatabasesMeta, ProjectDatabasesLink
from apps.datasets.constants import (
    DEFAULT_ASSET_FILE_TYPE_REGISTRY_ITEMS,
    DEFAULT_ASSET_TYPE_REGISTRY_ITEMS,
    DEFAULT_DATASET_KIND_REGISTRY_ITEMS,
)
from apps.datasets.models import (
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
    FunctionalGene,
    FunctionalTerm,
    FunctionalTermAssignment,
    PhenomeImportRun,
    PhenomeObservation,
    PhenomeSourceColumn,
    PhenomeSubject,
    PhenomeTrait,
)
from apps.datasets.schemas import (
    DatasetVersionReleaseRequest,
    DatasetVersionSetDefaultPublicRequest,
    DatasetVersionWithdrawRequest,
)
from apps.datasets.services import dataset_domain_service
from apps.system.user.models import Role, User
from db.database import Base


DATASET_TEST_TABLES = [
    Databases.__table__,
    DatabasesFile.__table__,
    DatabasesMeta.__table__,
    ProjectDatabasesLink.__table__,
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
    FunctionalGene.__table__,
    FunctionalTerm.__table__,
    FunctionalTermAssignment.__table__,
    PhenomeImportRun.__table__,
    PhenomeSubject.__table__,
    PhenomeTrait.__table__,
    PhenomeSourceColumn.__table__,
    PhenomeObservation.__table__,
]


def make_user(user_id, *, is_superman=False, user_type=0):
    return type("UserStub", (), {"id": user_id, "is_superman": is_superman, "user_type": user_type})()


def create_dataset(db, *, name, owner_id, team_id=0, dataset_type="generic"):
    row = Databases(
        name=name,
        user_id=owner_id,
        type=dataset_type,
        status=1,
        is_public=False,
        is_active=True,
        is_delete=False,
        create_time=1,
        remark="",
        team_id=team_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def create_version(
    db,
    *,
    dataset_id,
    version,
    file_path,
    title=None,
    dataset_type="generic",
    file_format="txt",
    query_engine="file",
    lifecycle_state="draft",
    release_state="unreleased",
    visibility="private",
    is_current=0,
    is_default_public=0,
):
    row = DatasetVersion(
        database_id=dataset_id,
        version=version,
        title=title or version,
        dataset_type=dataset_type,
        lifecycle_state=lifecycle_state,
        visibility=visibility,
        release_state=release_state,
        file_path=file_path,
        file_format=file_format,
        query_engine=query_engine,
        validation_summary=None,
        index_summary=None,
        extra_json=None,
        is_current=is_current,
        is_default_public=is_default_public,
        create_time=1,
        update_time=1,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def create_asset(
    db,
    *,
    dataset_id,
    version_id,
    asset_code="asset_1",
    asset_type="metadata_table",
    file_format="txt",
    query_engine="file",
    is_query_entry=1,
):
    row = DatasetAsset(
        database_id=dataset_id,
        dataset_version_id=version_id,
        asset_code=asset_code,
        asset_name=asset_code,
        asset_type=asset_type,
        file_format=file_format,
        query_engine=query_engine,
        storage_backend="local",
        workflow_state="ready",
        status="active",
        is_required=1,
        is_query_entry=is_query_entry,
        display_order=0,
        meta_json=None,
        create_time=1,
        update_time=1,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def create_asset_file(db, *, dataset_id, asset_id, local_path, file_role="primary", file_format="txt"):
    row = AssetFile(
        database_id=dataset_id,
        dataset_asset_id=asset_id,
        file_role=file_role,
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


def create_functional_annotation_sqlite(path: Path):
    conn = sqlite3.connect(path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE hse_genes (
                gene_id TEXT PRIMARY KEY,
                chrom TEXT NOT NULL,
                start INTEGER NOT NULL,
                stop INTEGER NOT NULL,
                strand TEXT NOT NULL,
                description TEXT NOT NULL,
                canonical_transcript TEXT NOT NULL,
                family TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE hse_transcripts (
                transcript_id TEXT PRIMARY KEY,
                gene_id TEXT NOT NULL,
                chrom TEXT NOT NULL,
                start INTEGER NOT NULL,
                stop INTEGER NOT NULL,
                strand TEXT NOT NULL,
                description TEXT NOT NULL,
                blast_TAIR JSON,
                blast_nr JSON,
                blast_Swiss_Prot JSON,
                blast_TrEMBL JSON,
                InterPro JSON,
                GO JSON,
                KEGG JSON,
                family JSON
            )
            """
        )
        cursor.execute(
            """
            INSERT INTO hse_genes (gene_id, chrom, start, stop, strand, description, canonical_transcript, family)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "AT1G01010",
                "chr1",
                10,
                90,
                "+",
                "NAC domain containing protein 1",
                "AT1G01010.1",
                "NAC",
            ),
        )
        cursor.execute(
            """
            INSERT INTO hse_transcripts (
                transcript_id, gene_id, chrom, start, stop, strand, description,
                blast_TAIR, blast_nr, blast_Swiss_Prot, blast_TrEMBL,
                InterPro, GO, KEGG, family
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "AT1G01010.1",
                "AT1G01010",
                "chr1",
                10,
                90,
                "+",
                "Canonical transcript",
                json.dumps([{"hit": "TAIR:AT1G01010", "score": 100.0}], ensure_ascii=False),
                None,
                None,
                None,
                json.dumps(
                    {
                        "matches_format": [
                            {
                                "source_term": "PF02365",
                                "source_database": "Pfam",
                                "description": "NAM",
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                json.dumps(
                    [
                        {"term": "GO:0003677", "name": "DNA binding", "namespace": "molecular_function"},
                        {"term": "GO:0006355", "name": "regulation of transcription", "namespace": "biological_process"},
                    ],
                    ensure_ascii=False,
                ),
                json.dumps(
                    [
                        {
                            "pathway": "map04075",
                            "description": "Plant hormone signal transduction",
                            "orthology": ["ko:K14496"],
                        }
                    ],
                    ensure_ascii=False,
                ),
                json.dumps([{"name": "NAC", "type": "TF", "database": "iTAK"}], ensure_ascii=False),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def seed_registry_defaults(db):
    for index, item in enumerate(DEFAULT_DATASET_KIND_REGISTRY_ITEMS, start=1):
        db.add(
            DatasetKindRegistry(
                id=index,
                code=item["code"],
                base_code=item["base_code"],
                name=item["name"],
                description=item["description"],
                is_system=item["is_system"],
                is_active=item["is_active"],
                sort_order=item["sort_order"],
                meta_json=None,
                create_time=1,
                update_time=1,
            )
        )
    for index, item in enumerate(DEFAULT_ASSET_TYPE_REGISTRY_ITEMS, start=1):
        db.add(
            AssetTypeRegistry(
                id=index,
                code=item["code"],
                base_code=item["base_code"],
                name=item["name"],
                description=item["description"],
                allowed_dataset_types=json.dumps(item["allowed_dataset_types"], ensure_ascii=False),
                is_system=item["is_system"],
                is_active=item["is_active"],
                sort_order=item["sort_order"],
                meta_json=None,
                create_time=1,
                update_time=1,
            )
        )
    for index, item in enumerate(DEFAULT_ASSET_FILE_TYPE_REGISTRY_ITEMS, start=1):
        db.add(
            AssetFileTypeRegistry(
                id=index,
                code=item["code"],
                base_code=item["base_code"],
                name=item["name"],
                description=item["description"],
                supported_file_formats=json.dumps(item["supported_file_formats"], ensure_ascii=False),
                file_role=item["file_role"],
                allowed_asset_types=json.dumps(item["allowed_asset_types"], ensure_ascii=False),
                is_system=item["is_system"],
                is_active=item["is_active"],
                sort_order=item["sort_order"],
                meta_json=None,
                create_time=1,
                update_time=1,
            )
        )
    db.commit()


def test_seed_dataset_registry_defaults_updates_existing_registry_rows(db_session, monkeypatch):
    variome_default = next(item for item in DEFAULT_DATASET_KIND_REGISTRY_ITEMS if item["code"] == "variome")
    variant_asset_default = next(item for item in DEFAULT_ASSET_TYPE_REGISTRY_ITEMS if item["code"] == "variant_vcf")

    db_session.add(
        DatasetKindRegistry(
            id=1,
            code="variome",
            base_code="legacy",
            name="旧变异组",
            description="outdated",
            is_system=1,
            is_active=1,
            sort_order=1,
            meta_json=None,
            create_time=1,
            update_time=1,
        )
    )
    db_session.add(
        AssetTypeRegistry(
            id=1,
            code="variant_vcf",
            base_code="legacy",
            name="旧 Variant VCF",
            description="outdated",
            allowed_dataset_types=json.dumps(["variant"], ensure_ascii=False),
            is_system=1,
            is_active=1,
            sort_order=1,
            meta_json=None,
            create_time=1,
            update_time=1,
        )
    )
    db_session.commit()

    class DBManagerStub:
        def __enter__(self):
            return db_session

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    monkeypatch.setattr(dataset_init_module, "MyDBManager", DBManagerStub)
    dataset_init_module.seed_dataset_registry_defaults()
    db_session.expire_all()

    variome_row = db_session.query(DatasetKindRegistry).filter(DatasetKindRegistry.code == "variome").first()
    variant_asset_row = db_session.query(AssetTypeRegistry).filter(AssetTypeRegistry.code == "variant_vcf").first()

    assert variome_row.base_code == variome_default["base_code"]
    assert variome_row.name == variome_default["name"]
    assert variome_row.description == variome_default["description"]
    assert json.loads(variant_asset_row.allowed_dataset_types) == variant_asset_default["allowed_dataset_types"]


def test_asset_file_type_registry_defaults_cover_genome_chain(db_session):
    seed_registry_defaults(db_session)

    reference_file_types = (
        db_session.query(AssetFileTypeRegistry)
        .filter(AssetFileTypeRegistry.is_active == 1)
        .filter(AssetFileTypeRegistry.allowed_asset_types.like('%reference_fasta%'))
        .order_by(AssetFileTypeRegistry.sort_order.asc(), AssetFileTypeRegistry.id.asc())
        .all()
    )
    annotation_file_types = (
        db_session.query(AssetFileTypeRegistry)
        .filter(AssetFileTypeRegistry.is_active == 1)
        .filter(AssetFileTypeRegistry.allowed_asset_types.like('%gene_annotation%'))
        .order_by(AssetFileTypeRegistry.sort_order.asc(), AssetFileTypeRegistry.id.asc())
        .all()
    )
    functional_file_types = (
        db_session.query(AssetFileTypeRegistry)
        .filter(AssetFileTypeRegistry.is_active == 1)
        .filter(AssetFileTypeRegistry.allowed_asset_types.like('%functional_annotation%'))
        .order_by(AssetFileTypeRegistry.sort_order.asc(), AssetFileTypeRegistry.id.asc())
        .all()
    )

    assert {item.code for item in reference_file_types} >= {"genome_sequence", "genome_sequence_index"}
    assert {item.code for item in annotation_file_types} >= {
        "gene_models",
        "gene_models_index",
        "transcript_sequence",
        "protein_sequence",
    }
    assert {item.code for item in functional_file_types} >= {"functional_annotation_db", "functional_annotation_table"}
    assert any(
        item.code == "genome_sequence"
        and set(json.loads(item.supported_file_formats)) >= {"fa", "fasta", "fna", "fa.gz", "fasta.gz", "fna.gz"}
        for item in reference_file_types
    )
    assert any(
        item.code == "genome_sequence_index"
        and item.file_role == "index"
        and set(json.loads(item.supported_file_formats)) >= {"fai", "gzi"}
        for item in reference_file_types
    )
    assert any(
        item.code == "gene_models"
        and set(json.loads(item.supported_file_formats)) >= {"gff", "gff.gz", "gff3", "gff3.gz", "gtf", "gtf.gz", "db", "sqlite"}
        for item in annotation_file_types
    )
    assert any(
        item.code == "gene_models_index"
        and item.file_role == "index"
        and "tbi" in set(json.loads(item.supported_file_formats))
        for item in annotation_file_types
    )


def test_asset_file_type_registry_defaults_cover_variome_transcriptome_and_phenome(db_session):
    seed_registry_defaults(db_session)

    variant_file_types = (
        db_session.query(AssetFileTypeRegistry)
        .filter(AssetFileTypeRegistry.is_active == 1)
        .filter(AssetFileTypeRegistry.allowed_asset_types.like('%variant_vcf%'))
        .order_by(AssetFileTypeRegistry.sort_order.asc(), AssetFileTypeRegistry.id.asc())
        .all()
    )
    expression_file_types = (
        db_session.query(AssetFileTypeRegistry)
        .filter(AssetFileTypeRegistry.is_active == 1)
        .filter(AssetFileTypeRegistry.allowed_asset_types.like('%expression_matrix%'))
        .order_by(AssetFileTypeRegistry.sort_order.asc(), AssetFileTypeRegistry.id.asc())
        .all()
    )
    phenotype_table_file_types = (
        db_session.query(AssetFileTypeRegistry)
        .filter(AssetFileTypeRegistry.is_active == 1)
        .filter(AssetFileTypeRegistry.allowed_asset_types.like('%phenotype_table%'))
        .order_by(AssetFileTypeRegistry.sort_order.asc(), AssetFileTypeRegistry.id.asc())
        .all()
    )
    phenotype_index_file_types = (
        db_session.query(AssetFileTypeRegistry)
        .filter(AssetFileTypeRegistry.is_active == 1)
        .filter(AssetFileTypeRegistry.allowed_asset_types.like('%phenotype_index%'))
        .order_by(AssetFileTypeRegistry.sort_order.asc(), AssetFileTypeRegistry.id.asc())
        .all()
    )

    assert {item.code for item in variant_file_types} >= {"variant_calls", "variant_calls_index"}
    assert any(
        item.code == "variant_calls"
        and set(json.loads(item.supported_file_formats)) >= {"vcf", "vcf.gz", "bcf"}
        for item in variant_file_types
    )
    assert any(
        item.code == "variant_calls_index"
        and set(json.loads(item.supported_file_formats)) >= {"tbi", "csi"}
        for item in variant_file_types
    )

    assert {item.code for item in expression_file_types} >= {"expression_matrix_store", "expression_quant_table"}
    assert any(
        item.code == "expression_matrix_store"
        and set(json.loads(item.supported_file_formats)) >= {"h5", "hdf5"}
        for item in expression_file_types
    )
    assert any(
        item.code == "expression_quant_table"
        and set(json.loads(item.supported_file_formats)) >= {"csv", "tsv", "xlsx", "xls"}
        for item in expression_file_types
    )

    assert {item.code for item in phenotype_table_file_types} >= {"phenotype_observation_table"}
    assert any(
        item.code == "phenotype_observation_table"
        and set(json.loads(item.supported_file_formats)) >= {"xlsx", "xls", "csv", "tsv"}
        for item in phenotype_table_file_types
    )
    assert {item.code for item in phenotype_index_file_types} >= {"phenotype_query_index_db"}
    assert any(
        item.code == "phenotype_query_index_db"
        and set(json.loads(item.supported_file_formats)) >= {"db", "sqlite"}
        for item in phenotype_index_file_types
    )


def test_genome_asset_registration_enforces_registry_file_types(db_session, tmp_path):
    seed_registry_defaults(db_session)
    owner = make_user(80315)
    dataset = create_dataset(db_session, name="genome-registry-binding", owner_id=owner.id, dataset_type="genome")
    version = create_version(
        db_session,
        dataset_id=dataset.id,
        version="v1",
        file_path=None,
        dataset_type="genome",
        file_format="fa.gz",
        query_engine="samtools/faidx",
        lifecycle_state="ready",
        is_current=1,
    )
    fasta_path = tmp_path / "genome.fa.gz"
    fasta_path.write_text(">chr1\nACGT\n", encoding="utf-8")
    index_path = tmp_path / "genome.fa.gz.fai"
    index_path.write_text("chr1\t4\t6\t4\t5\n", encoding="utf-8")
    invalid_index_path = tmp_path / "genome.fa.gz.txt"
    invalid_index_path.write_text("bad-index\n", encoding="utf-8")

    asset = dataset_domain_service.create_dataset_asset(
        db=db_session,
        request_data=SimpleNamespace(
            version_id=version.id,
            asset_code="reference_fasta",
            asset_name="Reference FASTA",
            asset_type="reference_fasta",
            file_format="fa.gz",
            query_engine="samtools/faidx",
            storage_backend="local",
            workflow_state="ready",
            status="active",
            is_required=True,
            is_query_entry=True,
            display_order=0,
            meta_json=None,
            local_path=str(fasta_path),
        ),
        user=owner,
    )

    index_file = dataset_domain_service.register_asset_file(
        db=db_session,
        request_data=SimpleNamespace(
            asset_id=asset["id"],
            file_role="index",
            local_path=str(index_path),
            file_format="fai",
            index_of_file_id=asset["files"][0]["id"],
            status="active",
        ),
        user=owner,
    )

    assert asset["asset_type"] == "reference_fasta"
    assert asset["file_format"] == "fa.gz"
    assert asset["files"][0]["file_format"] == "fa.gz"
    assert index_file["file_role"] == "index"
    assert index_file["file_format"] == "fai"

    with pytest.raises(HTTPException) as error:
        dataset_domain_service.register_asset_file(
            db=db_session,
            request_data=SimpleNamespace(
                asset_id=asset["id"],
                file_role="index",
                local_path=str(invalid_index_path),
                file_format="txt",
                index_of_file_id=asset["files"][0]["id"],
                status="active",
            ),
            user=owner,
        )
    assert error.value.status_code == 400
    assert "asset file is not allowed for asset_type reference_fasta" in error.value.detail


def test_genome_asset_registration_rejects_invalid_primary_format(db_session, tmp_path):
    seed_registry_defaults(db_session)
    owner = make_user(80316)
    dataset = create_dataset(db_session, name="genome-invalid-primary", owner_id=owner.id, dataset_type="genome")
    version = create_version(
        db_session,
        dataset_id=dataset.id,
        version="v1",
        file_path=None,
        dataset_type="genome",
        file_format="gff3",
        query_engine="file",
        lifecycle_state="ready",
        is_current=1,
    )
    invalid_primary = tmp_path / "genome.gff3"
    invalid_primary.write_text("chr1\tsrc\tgene\t1\t4\t.\t+\t.\tID=g1\n", encoding="utf-8")

    with pytest.raises(HTTPException) as error:
        dataset_domain_service.create_dataset_asset(
            db=db_session,
            request_data=SimpleNamespace(
                version_id=version.id,
                asset_code="reference_fasta",
                asset_name="Reference FASTA",
                asset_type="reference_fasta",
                file_format="gff3",
                query_engine="file",
                storage_backend="local",
                workflow_state="ready",
                status="active",
                is_required=True,
                is_query_entry=True,
                display_order=0,
                meta_json=None,
                local_path=str(invalid_primary),
            ),
            user=owner,
        )
    assert error.value.status_code == 400
    assert "asset file is not allowed for asset_type reference_fasta" in error.value.detail


def test_update_dataset_asset_rejects_incompatible_asset_type_for_existing_files(db_session, tmp_path):
    seed_registry_defaults(db_session)
    owner = make_user(80317)
    dataset = create_dataset(db_session, name="genome-asset-type-switch", owner_id=owner.id, dataset_type="genome")
    version = create_version(
        db_session,
        dataset_id=dataset.id,
        version="v1",
        file_path=None,
        dataset_type="genome",
        file_format="fa",
        query_engine="samtools/faidx",
        lifecycle_state="ready",
        is_current=1,
    )
    fasta_path = tmp_path / "genome.fa"
    fasta_path.write_text(">chr1\nACGT\n", encoding="utf-8")

    asset = dataset_domain_service.create_dataset_asset(
        db=db_session,
        request_data=SimpleNamespace(
            version_id=version.id,
            asset_code="reference_fasta",
            asset_name="Reference FASTA",
            asset_type="reference_fasta",
            file_format="fa",
            query_engine="samtools/faidx",
            storage_backend="local",
            workflow_state="ready",
            status="active",
            is_required=True,
            is_query_entry=True,
            display_order=0,
            meta_json=None,
            local_path=str(fasta_path),
        ),
        user=owner,
    )

    with pytest.raises(HTTPException) as error:
        dataset_domain_service.update_dataset_asset(
            db=db_session,
            asset_id=asset["id"],
            request_data=SimpleNamespace(
                id=asset["id"],
                asset_name=None,
                asset_type="functional_annotation",
                file_format=None,
                query_engine=None,
                storage_backend=None,
                workflow_state=None,
                status=None,
                is_required=None,
                is_query_entry=None,
                display_order=None,
                meta_json=None,
            ),
            user=owner,
        )
    assert error.value.status_code == 400
    assert "asset file is not allowed for asset_type functional_annotation" in error.value.detail


def test_new_dataset_type_filters_match_legacy_dataset_rows(db_session, tmp_path):
    seed_registry_defaults(db_session)
    owner = make_user(80311)
    file_path = tmp_path / "legacy.fa"
    file_path.write_text(">chr1\nACGT\n", encoding="utf-8")

    dataset = create_dataset(db_session, name="legacy-sequence-filter", owner_id=owner.id, dataset_type="sequence")
    create_version(
        db_session,
        dataset_id=dataset.id,
        version="v1",
        file_path=str(file_path),
        dataset_type="sequence",
        file_format="fa",
        query_engine="samtools/faidx",
        lifecycle_state="ready",
        is_current=1,
    )

    options = dataset_domain_service.get_options(
        db=db_session,
        request_data=SimpleNamespace(
            team_id=0,
            project_id=0,
            dataset_id=0,
            name=None,
            dataset_type="genome",
            lifecycle_state=None,
            visibility=None,
            page=1,
            size=20,
        ),
        user=owner,
    )
    asset_options = dataset_domain_service.get_asset_type_options(
        db=db_session,
        request_data=SimpleNamespace(dataset_type="genome", active_only=True),
    )

    assert [item["id"] for item in options] == [dataset.id]
    assert any(item["code"] == "reference_fasta" for item in asset_options)


def create_phenome_sqlite(db_path: Path):
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE phenotype (
                ID TEXT,
                花瓣长 REAL,
                花瓣宽 REAL,
                连续开花性 INTEGER
            )
            """
        )
        conn.executemany(
            "INSERT INTO phenotype (ID, 花瓣长, 花瓣宽, 连续开花性) VALUES (?, ?, ?, ?)",
            [
                ("RH00004", 2.87, 2.6, 2),
                ("RH00010", None, None, 2),
                ("RH00012", 3.47, 3.1, 2),
            ],
        )
        conn.commit()
    finally:
        conn.close()


def create_phenome_sqlite_with_timepoints(db_path: Path):
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE phenotype (
                ID TEXT,
                "2021年花瓣数量" REAL,
                "2022年花瓣数量" REAL,
                "2023年花瓣数量" REAL,
                花直径 REAL
            )
            """
        )
        conn.executemany(
            """
            INSERT INTO phenotype (ID, "2021年花瓣数量", "2022年花瓣数量", "2023年花瓣数量", 花直径)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                ("RH00004", 20, 24, 26, 5.6),
                ("RH00010", 18, None, 19, 5.1),
                ("RH00012", 25, 27, 30, 6.0),
            ],
        )
        conn.commit()
    finally:
        conn.close()


def test_phenome_sqlite_adapter_supports_summary_and_detail_queries(db_session, tmp_path):
    seed_registry_defaults(db_session)
    owner = make_user(80312)
    dataset = create_dataset(db_session, name="rose-phenome", owner_id=owner.id, dataset_type="phenome")
    sqlite_path = tmp_path / "rose_phenome.db"
    create_phenome_sqlite(sqlite_path)

    version = create_version(
        db_session,
        dataset_id=dataset.id,
        version="v1",
        file_path=str(sqlite_path),
        dataset_type="phenome",
        file_format="db",
        query_engine="phenome",
        lifecycle_state="ready",
        is_current=1,
    )
    asset = create_asset(
        db_session,
        dataset_id=dataset.id,
        version_id=version.id,
        asset_code="phenotype_index",
        asset_type="phenotype_index",
        file_format="db",
        query_engine="phenome",
        is_query_entry=1,
    )
    create_asset_file(
        db_session,
        dataset_id=dataset.id,
        asset_id=asset.id,
        local_path=str(sqlite_path),
        file_role="primary",
        file_format="db",
    )

    caps = dataset_domain_service.get_dataset_version_query_capabilities(
        db=db_session,
        version_id=version.id,
        user=owner,
    )
    summary = dataset_domain_service.execute_dataset_version_query(
        db=db_session,
        version_id=version.id,
        operation="dataset_summary",
        user=owner,
    )
    traits = dataset_domain_service.execute_dataset_version_query(
        db=db_session,
        version_id=version.id,
        operation="trait_list",
        user=owner,
    )
    subjects = dataset_domain_service.execute_dataset_version_query(
        db=db_session,
        version_id=version.id,
        operation="subject_list",
        user=owner,
    )
    detail = dataset_domain_service.execute_dataset_version_query(
        db=db_session,
        version_id=version.id,
        operation="subject_detail",
        params={"subject_id": "RH00004"},
        user=owner,
    )
    trait_values = dataset_domain_service.execute_dataset_version_query(
        db=db_session,
        version_id=version.id,
        operation="trait_values",
        params={"trait": "花瓣长"},
        user=owner,
    )

    assert caps["query_adapter"]["adapter"] == "phenome"
    assert summary["data"]["subject_count"] == 3
    assert summary["data"]["trait_count"] == 3
    assert traits["data"]["items"][0]["name"] == "花瓣长"
    assert subjects["data"]["items"] == ["RH00004", "RH00010", "RH00012"]
    assert detail["data"]["subject_id"] == "RH00004"
    assert detail["data"]["traits"]["花瓣宽"] == 2.6
    assert trait_values["data"]["trait"] == "花瓣长"
    assert trait_values["data"]["items"][0]["subject_id"] == "RH00004"
    assert trait_values["data"]["non_missing_count"] == 2


def test_phenome_index_is_rebuilt_when_phenotype_index_asset_file_is_registered(db_session, tmp_path):
    seed_registry_defaults(db_session)
    owner = make_user(80313, is_superman=True)
    dataset = create_dataset(db_session, name="rose-phenome-indexing", owner_id=owner.id, dataset_type="phenome")
    sqlite_path = tmp_path / "rose_phenome_index.db"
    create_phenome_sqlite(sqlite_path)

    version = create_version(
        db_session,
        dataset_id=dataset.id,
        version="v1",
        file_path=str(sqlite_path),
        dataset_type="phenome",
        file_format="db",
        query_engine="file",
        lifecycle_state="ready",
        is_current=1,
    )

    asset = dataset_domain_service.create_dataset_asset(
        db=db_session,
        request_data=SimpleNamespace(
            version_id=version.id,
            asset_code="phenotype_index",
            asset_name="Phenotype Index",
            asset_type="phenotype_index",
            file_format="db",
            query_engine="phenome",
            storage_backend="local",
            workflow_state="ready",
            status="active",
            is_required=True,
            is_query_entry=True,
            display_order=0,
            meta_json=None,
            local_path=None,
        ),
        user=owner,
    )

    dataset_domain_service.register_asset_file(
        db=db_session,
        request_data=SimpleNamespace(
            asset_id=asset["id"],
            file_role="primary",
            local_path=str(sqlite_path),
            file_format="db",
            index_of_file_id=None,
            status="active",
        ),
        user=owner,
    )

    import_runs = db_session.query(PhenomeImportRun).filter(PhenomeImportRun.asset_id == asset["id"]).count()
    subject_count = db_session.query(PhenomeSubject).filter(PhenomeSubject.asset_id == asset["id"]).count()
    trait_count = db_session.query(PhenomeTrait).filter(PhenomeTrait.asset_id == asset["id"]).count()
    source_column_count = db_session.query(PhenomeSourceColumn).filter(PhenomeSourceColumn.asset_id == asset["id"]).count()
    observation_count = db_session.query(PhenomeObservation).filter(PhenomeObservation.asset_id == asset["id"]).count()

    assert import_runs == 1
    assert subject_count == 3
    assert trait_count == 3
    assert source_column_count == 3
    assert observation_count == 9


def test_phenome_pg_index_queries_grouped_traits_and_timepoints(db_session, tmp_path):
    seed_registry_defaults(db_session)
    owner = make_user(80314, is_superman=True)
    dataset = create_dataset(db_session, name="rose-phenome-pg-query", owner_id=owner.id, dataset_type="phenome")
    sqlite_path = tmp_path / "rose_phenome_timepoints.db"
    create_phenome_sqlite_with_timepoints(sqlite_path)

    version = create_version(
        db_session,
        dataset_id=dataset.id,
        version="v1",
        file_path=str(sqlite_path),
        dataset_type="phenome",
        file_format="db",
        query_engine="file",
        lifecycle_state="ready",
        is_current=1,
    )

    asset = dataset_domain_service.create_dataset_asset(
        db=db_session,
        request_data=SimpleNamespace(
            version_id=version.id,
            asset_code="phenotype_index",
            asset_name="Phenotype Index",
            asset_type="phenotype_index",
            file_format="db",
            query_engine="phenome",
            storage_backend="local",
            workflow_state="ready",
            status="active",
            is_required=True,
            is_query_entry=True,
            display_order=0,
            meta_json=None,
            local_path=None,
        ),
        user=owner,
    )

    dataset_domain_service.register_asset_file(
        db=db_session,
        request_data=SimpleNamespace(
            asset_id=asset["id"],
            file_role="primary",
            local_path=str(sqlite_path),
            file_format="db",
            index_of_file_id=None,
            status="active",
        ),
        user=owner,
    )

    summary = dataset_domain_service.execute_dataset_version_query(
        db=db_session,
        version_id=version.id,
        operation="dataset_summary",
        user=owner,
    )
    traits = dataset_domain_service.execute_dataset_version_query(
        db=db_session,
        version_id=version.id,
        operation="trait_list",
        user=owner,
    )
    search = dataset_domain_service.execute_dataset_version_query(
        db=db_session,
        version_id=version.id,
        operation="trait_search",
        params={"keyword": "花瓣"},
        user=owner,
    )
    values = dataset_domain_service.execute_dataset_version_query(
        db=db_session,
        version_id=version.id,
        operation="trait_values",
        params={"trait": "花瓣数量", "timepoint": "2022"},
        user=owner,
    )

    assert summary["data"]["source"] == "postgresql"
    assert summary["data"]["trait_count"] == 2
    assert summary["data"]["observation_count"] == 12
    assert traits["data"]["source"] == "postgresql"
    assert [item["name"] for item in traits["data"]["items"]] == ["花瓣数量", "花直径"]
    assert search["data"]["source"] == "postgresql"
    assert search["data"]["count"] == 1
    assert search["data"]["items"][0]["trait_code"] == "花瓣数量"
    assert values["data"]["source"] == "postgresql"
    assert values["data"]["trait"] == "花瓣数量"
    assert values["data"]["timepoint"] == "2022"
    assert [item["subject_id"] for item in values["data"]["items"]] == ["RH00004", "RH00010", "RH00012"]
    assert values["data"]["items"][0]["value"] == 24.0
    assert values["data"]["items"][1]["value"] is None
    assert values["data"]["non_missing_count"] == 2


def create_sequence_bundle_dir(bundle_dir: Path):
    bundle_dir.mkdir(parents=True, exist_ok=True)
    (bundle_dir / "genome.fa.gz").write_text(">chr1\nACGTACGTACGT\n", encoding="utf-8")
    (bundle_dir / "genome.fa.gz.fai").write_text("chr1\t12\t6\t12\t13\n", encoding="utf-8")
    (bundle_dir / "genome.fa.gz.gzi").write_text("0\t0\n", encoding="utf-8")
    (bundle_dir / "gene_model_sorted.gff3.gz").write_text(
        "##gff-version 3\nchr1\tdemo\tgene\t1\t12\t.\t+\t.\tID=AT1G01010;gene_id=AT1G01010\n",
        encoding="utf-8",
    )
    (bundle_dir / "gene_model_sorted.gff3.gz.tbi").write_text("index\n", encoding="utf-8")
    (bundle_dir / "mRNA.fa.gz").write_text(">AT1G01010.1\nAUGCUA\n", encoding="utf-8")
    (bundle_dir / "protein.fa.gz").write_text(">AT1G01010.1\nMSTNPK\n", encoding="utf-8")
    (bundle_dir / "func_anno").mkdir(exist_ok=True)
    create_functional_annotation_sqlite(bundle_dir / "genome.db")
    return bundle_dir


def create_expression_bundle_dir(bundle_dir: Path):
    bundle_dir.mkdir(parents=True, exist_ok=True)
    matrix_path = bundle_dir / "01.phytohormones_RNAseq.h5"
    metadata_path = bundle_dir / "01.phytohormones_RNAseq.h5.json"

    with h5py.File(matrix_path, "w") as handle:
        count_group = handle.create_group("count")
        count_group.create_dataset("matrix", data=[[10, 20], [30, 40]], dtype="i4")
        count_group.create_dataset("samples", data=[b"SampleA", b"SampleB"])

        fpkm_group = handle.create_group("fpkm")
        fpkm_group.create_dataset("matrix", data=[[1.5, 2.5], [3.5, 4.5]], dtype="f4")
        fpkm_group.create_dataset("samples", data=[b"SampleA", b"SampleB"])

        meta_group = handle.create_group("meta")
        meta_group.create_dataset("genes", data=[b"Gene1", b"Gene2"])
        meta_group.create_dataset("count_file_path", data=b"01.phytohormones_RNAseq_count.txt")
        meta_group.create_dataset("fpkm_file_path", data=b"01.phytohormones_RNAseq_fpkm.txt")

    metadata_path.write_text(
        json.dumps(
            {
                "dataset_info": {
                    "dataset_id": "phytohormones_transcriptome_2024",
                    "title": "Plant Hormone Treatment Transcriptome Expression Profile Dataset",
                    "version": "2024",
                    "data_type": "transcriptome",
                    "organism": "rose",
                    "technology": "RNA-seq",
                    "total_samples": 2,
                },
                "samples": [
                    {"sample_id": "SampleA", "treatment": "mock", "replicate": 1},
                    {"sample_id": "SampleB", "treatment": "auxin", "replicate": 1},
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (bundle_dir / "01.phytohormones_RNAseq_count.txt").write_text(
        "gene\tSampleA\tSampleB\nGene1\t10\t20\nGene2\t30\t40\n",
        encoding="utf-8",
    )
    (bundle_dir / "01.phytohormones_RNAseq_fpkm.txt").write_text(
        "gene\tSampleA\tSampleB\nGene1\t1.5\t2.5\nGene2\t3.5\t4.5\n",
        encoding="utf-8",
    )
    return bundle_dir


def create_variome_bundle_dir(bundle_dir: Path):
    bundle_dir.mkdir(parents=True, exist_ok=True)
    (bundle_dir / "test.vcf").write_text("##fileformat=VCFv4.2\n", encoding="utf-8")
    (bundle_dir / "gwas358_AB.snp.mafgeno.test.vcf.gz").write_text("##fileformat=VCFv4.2\n", encoding="utf-8")
    (bundle_dir / "gwas358_AB.snp.mafgeno.test.vcf.gz.csi").write_text("index\n", encoding="utf-8")
    return bundle_dir


def create_cool_group(group, *, chrom_length, bin_size, pixels, weights=None, storage_mode="symmetric-upper"):
    chroms_group = group.create_group("chroms")
    chroms_group.create_dataset("name", data=[b"chr1"])
    chroms_group.create_dataset("length", data=[chrom_length])

    nbins = chrom_length // bin_size
    starts = [index * bin_size for index in range(nbins)]
    ends = [(index + 1) * bin_size for index in range(nbins)]

    bins_group = group.create_group("bins")
    bins_group.create_dataset("chrom", data=[0] * nbins, dtype="i8")
    bins_group.create_dataset("start", data=starts, dtype="i8")
    bins_group.create_dataset("end", data=ends, dtype="i8")
    if weights is not None:
        bins_group.create_dataset("weight", data=weights, dtype="f8")

    sorted_pixels = sorted(pixels, key=lambda item: (item[0], item[1]))
    pixels_group = group.create_group("pixels")
    pixels_group.create_dataset("bin1_id", data=[item[0] for item in sorted_pixels], dtype="i8")
    pixels_group.create_dataset("bin2_id", data=[item[1] for item in sorted_pixels], dtype="i8")
    pixels_group.create_dataset("count", data=[item[2] for item in sorted_pixels], dtype="i8")

    row_offsets = []
    cursor = 0
    for bin_id in range(nbins):
        row_offsets.append(cursor)
        while cursor < len(sorted_pixels) and sorted_pixels[cursor][0] == bin_id:
            cursor += 1
    row_offsets.append(len(sorted_pixels))

    indexes_group = group.create_group("indexes")
    indexes_group.create_dataset("chrom_offset", data=[0, nbins], dtype="i8")
    indexes_group.create_dataset("bin1_offset", data=row_offsets, dtype="i8")

    group.attrs["bin-size"] = bin_size
    group.attrs["nbins"] = nbins
    group.attrs["nchroms"] = 1
    group.attrs["storage-mode"] = storage_mode


def create_cool_file(path, *, chrom_length, bin_size, pixels, weights=None):
    with h5py.File(path, "w") as handle:
        create_cool_group(
            handle,
            chrom_length=chrom_length,
            bin_size=bin_size,
            pixels=pixels,
            weights=weights,
        )


def create_mcool_file(path, *, resolutions):
    with h5py.File(path, "w") as handle:
        resolutions_group = handle.create_group("resolutions")
        for resolution, config in resolutions.items():
            create_cool_group(
                resolutions_group.create_group(str(resolution)),
                chrom_length=config["chrom_length"],
                bin_size=resolution,
                pixels=config["pixels"],
                weights=config.get("weights"),
            )


@pytest.fixture()
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine, tables=DATASET_TEST_TABLES)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture()
def db_session(db_engine):
    testing_session = sessionmaker(bind=db_engine, autocommit=False, autoflush=False, expire_on_commit=False)
    session = testing_session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def patch_public_db(monkeypatch, db_engine):
    testing_session = sessionmaker(bind=db_engine, autocommit=False, autoflush=False, expire_on_commit=False)
    monkeypatch.setattr(dataset_services.mydb, "get_dbs", lambda: testing_session())


def test_public_dataset_prefers_default_public_version(db_session, patch_public_db, tmp_path):
    owner = make_user(801)
    dataset = create_dataset(db_session, name="public-default-version", owner_id=owner.id)
    file_v1 = tmp_path / "v1.txt"
    file_v2 = tmp_path / "v2.txt"
    file_v1.write_text("version-1\n", encoding="utf-8")
    file_v2.write_text("version-2\n", encoding="utf-8")

    version_v1 = create_version(
        db_session,
        dataset_id=dataset.id,
        version="v1",
        file_path=str(file_v1),
        lifecycle_state="ready",
        is_current=1,
    )
    version_v2 = create_version(
        db_session,
        dataset_id=dataset.id,
        version="v2",
        file_path=str(file_v2),
        lifecycle_state="ready",
    )

    dataset_domain_service.release_dataset_version(
        db=db_session,
        version_id=version_v1.id,
        request_data=DatasetVersionReleaseRequest(id=version_v1.id, note="release v1"),
        user=owner,
    )
    dataset_domain_service.release_dataset_version(
        db=db_session,
        version_id=version_v2.id,
        request_data=DatasetVersionReleaseRequest(id=version_v2.id, note="release v2"),
        user=owner,
    )
    dataset_domain_service.set_default_public_dataset_version(
        db=db_session,
        version_id=version_v2.id,
        request_data=DatasetVersionSetDefaultPublicRequest(id=version_v2.id, note="switch default to v2"),
        user=owner,
    )

    payload = dataset_domain_service.get_public_dataset(dataset.id)
    version_list = dataset_domain_service.list_public_dataset_versions(dataset.id)
    capabilities = dataset_domain_service.get_public_query_capabilities(dataset.id)

    assert payload["default_public_version"]["id"] == version_v2.id
    assert payload["published_version"]["id"] == version_v2.id
    assert payload["selected_version"]["id"] == version_v2.id
    assert payload["file"]["path"] == str(file_v2)
    assert capabilities["published_version"]["id"] == version_v2.id
    assert capabilities["file_path"] == str(file_v2)
    assert capabilities["file_access"]["exists_on_server"] is True
    assert version_list["default_public_version"]["id"] == version_v2.id
    assert {item["id"] for item in version_list["items"]} == {version_v1.id, version_v2.id}


def test_released_non_default_version_can_be_accessed_explicitly(db_session, patch_public_db, tmp_path):
    owner = make_user(802)
    dataset = create_dataset(db_session, name="public-explicit-version", owner_id=owner.id)
    file_v1 = tmp_path / "default.txt"
    file_v2 = tmp_path / "alt.txt"
    file_v1.write_text("default\n", encoding="utf-8")
    file_v2.write_text("alt\n", encoding="utf-8")

    version_v1 = create_version(
        db_session,
        dataset_id=dataset.id,
        version="v1",
        file_path=str(file_v1),
        lifecycle_state="ready",
        is_current=1,
    )
    version_v2 = create_version(
        db_session,
        dataset_id=dataset.id,
        version="v2",
        file_path=str(file_v2),
        lifecycle_state="ready",
    )

    dataset_domain_service.release_dataset_version(
        db=db_session,
        version_id=version_v1.id,
        request_data=DatasetVersionReleaseRequest(id=version_v1.id, note="release v1"),
        user=owner,
    )
    dataset_domain_service.release_dataset_version(
        db=db_session,
        version_id=version_v2.id,
        request_data=DatasetVersionReleaseRequest(id=version_v2.id, note="release v2"),
        user=owner,
    )

    default_payload = dataset_domain_service.get_public_dataset(dataset.id)
    explicit_payload = dataset_domain_service.get_public_dataset_version(dataset.id, version_v2.id)
    explicit_caps = dataset_domain_service.get_public_dataset_version_query_capabilities(dataset.id, version_v2.id)

    assert default_payload["default_public_version"]["id"] == version_v1.id
    assert default_payload["published_version"]["id"] == version_v1.id
    assert explicit_payload["default_public_version"]["id"] == version_v1.id
    assert explicit_payload["published_version"]["id"] == version_v2.id
    assert explicit_payload["selected_version"]["id"] == version_v2.id
    assert explicit_payload["file"]["path"] == str(file_v2)
    assert explicit_caps["default_public_version"]["id"] == version_v1.id
    assert explicit_caps["published_version"]["id"] == version_v2.id
    assert explicit_caps["file_path"] == str(file_v2)


def test_public_dataset_version_list_supports_filters(db_session, patch_public_db, tmp_path):
    owner = make_user(8022)
    dataset = create_dataset(db_session, name="public-version-filtering", owner_id=owner.id)
    file_v1 = tmp_path / "v1.txt"
    file_v2 = tmp_path / "v2.txt"
    file_v3 = tmp_path / "draft.txt"
    file_v1.write_text("v1\n", encoding="utf-8")
    file_v2.write_text("v2\n", encoding="utf-8")
    file_v3.write_text("draft\n", encoding="utf-8")

    version_v1 = create_version(
        db_session,
        dataset_id=dataset.id,
        version="v1",
        title="Genome Release 1",
        file_path=str(file_v1),
        lifecycle_state="ready",
        is_current=1,
    )
    version_v2 = create_version(
        db_session,
        dataset_id=dataset.id,
        version="v2",
        title="Genome Release 2",
        file_path=str(file_v2),
        lifecycle_state="ready",
    )
    create_version(
        db_session,
        dataset_id=dataset.id,
        version="draft-v3",
        title="Genome Draft 3",
        file_path=str(file_v3),
        lifecycle_state="draft",
    )

    dataset_domain_service.release_dataset_version(
        db=db_session,
        version_id=version_v1.id,
        request_data=DatasetVersionReleaseRequest(id=version_v1.id, note="release v1"),
        user=owner,
    )
    dataset_domain_service.release_dataset_version(
        db=db_session,
        version_id=version_v2.id,
        request_data=DatasetVersionReleaseRequest(id=version_v2.id, note="release v2"),
        user=owner,
    )
    dataset_domain_service.set_default_public_dataset_version(
        db=db_session,
        version_id=version_v2.id,
        request_data=DatasetVersionSetDefaultPublicRequest(id=version_v2.id, note="set v2 default public"),
        user=owner,
    )

    all_versions = dataset_domain_service.list_public_dataset_versions(dataset.id)
    default_only = dataset_domain_service.list_public_dataset_versions(dataset.id, is_default_public=True)
    current_only = dataset_domain_service.list_public_dataset_versions(dataset.id, is_current=True)
    keyword_v2 = dataset_domain_service.list_public_dataset_versions(dataset.id, keyword="release 2")
    released_only = dataset_domain_service.list_public_dataset_versions(dataset.id, release_state="released")
    unreleased = dataset_domain_service.list_public_dataset_versions(dataset.id, release_state="unreleased")

    assert all_versions["total"] == 2
    assert [item["version"] for item in all_versions["items"]] == ["v2", "v1"]

    assert default_only["total"] == 1
    assert [item["version"] for item in default_only["items"]] == ["v2"]

    assert current_only["total"] == 1
    assert [item["version"] for item in current_only["items"]] == ["v1"]

    assert keyword_v2["total"] == 1
    assert [item["version"] for item in keyword_v2["items"]] == ["v2"]

    assert released_only["total"] == 2
    assert unreleased["total"] == 0


def test_withdraw_default_public_version_leaves_no_default_public_dataset(db_session, patch_public_db, tmp_path):
    owner = make_user(8021)
    dataset = create_dataset(db_session, name="withdraw-default-no-public", owner_id=owner.id)
    file_v1 = tmp_path / "v1.txt"
    file_v2 = tmp_path / "v2.txt"
    file_v1.write_text("v1\n", encoding="utf-8")
    file_v2.write_text("v2\n", encoding="utf-8")

    version_v1 = create_version(
        db_session,
        dataset_id=dataset.id,
        version="v1",
        file_path=str(file_v1),
        lifecycle_state="ready",
        is_current=1,
    )
    version_v2 = create_version(
        db_session,
        dataset_id=dataset.id,
        version="v2",
        file_path=str(file_v2),
        lifecycle_state="ready",
    )

    dataset_domain_service.release_dataset_version(
        db=db_session,
        version_id=version_v1.id,
        request_data=DatasetVersionReleaseRequest(id=version_v1.id, note="release v1"),
        user=owner,
    )
    dataset_domain_service.release_dataset_version(
        db=db_session,
        version_id=version_v2.id,
        request_data=DatasetVersionReleaseRequest(id=version_v2.id, note="release v2"),
        user=owner,
    )
    dataset_domain_service.set_default_public_dataset_version(
        db=db_session,
        version_id=version_v2.id,
        request_data=DatasetVersionSetDefaultPublicRequest(id=version_v2.id, note="switch default to v2"),
        user=owner,
    )
    dataset_domain_service.withdraw_dataset_version(
        db=db_session,
        version_id=version_v2.id,
        request_data=DatasetVersionWithdrawRequest(id=version_v2.id, note="withdraw v2"),
        user=owner,
    )

    dataset_payload = dataset_domain_service.get_dataset(db=db_session, dataset_id=dataset.id, user=owner)

    assert dataset_payload["default_public_version"] is None
    with pytest.raises(HTTPException) as exc_info:
        dataset_domain_service.get_public_dataset(dataset.id)
    assert exc_info.value.status_code == 404


def test_unpublish_dataset_clears_stale_default_public_registry_state(db_session, patch_public_db, tmp_path):
    owner = make_user(80211)
    dataset = create_dataset(db_session, name="stale-public-registry", owner_id=owner.id)
    file_v1 = tmp_path / "v1.txt"
    file_v1.write_text("v1\n", encoding="utf-8")

    version_v1 = create_version(
        db_session,
        dataset_id=dataset.id,
        version="v1",
        file_path=str(file_v1),
        lifecycle_state="ready",
        visibility="private",
        release_state="unreleased",
        is_current=1,
    )

    dataset_payload = dataset_domain_service.get_dataset(db=db_session, dataset_id=dataset.id, user=owner)
    registry_obj = dataset_registry_db.get_filter(db=db_session, filters={"database_id": dataset.id})
    dataset_registry_db.update_one(
        db=db_session,
        db_obj=registry_obj,
        obj_in={
            "visibility": "public",
            "lifecycle_state": "public",
            "default_public_version_id": version_v1.id,
            "update_time": 2,
        },
    )
    db_session.refresh(version_v1)
    version_v1.visibility = "public"
    version_v1.lifecycle_state = "public"
    version_v1.is_default_public = 1
    version_v1.update_time = 2
    db_session.add(version_v1)
    db_session.commit()
    db_session.refresh(version_v1)

    result = dataset_domain_service.unpublish_dataset(
        db=db_session,
        dataset_id=dataset.id,
        request_data=type("Req", (), {"id": dataset.id, "note": "clear stale public registry"})(),
        user=owner,
    )

    assert dataset_payload["id"] == dataset.id
    assert result["visibility"] == "private"
    assert result["lifecycle_state"] == "ready"
    assert result["default_public_version_id"] is None
    assert result["default_public_version"] is None
    assert result["current_version"]["visibility"] == "private"
    assert result["current_version"]["lifecycle_state"] == "ready"


def test_unreleased_version_is_not_accessible_through_public_version_api(db_session, patch_public_db, tmp_path):
    owner = make_user(803)
    dataset = create_dataset(db_session, name="public-unreleased-blocked", owner_id=owner.id)
    file_v1 = tmp_path / "released.txt"
    file_v2 = tmp_path / "draft.txt"
    file_v1.write_text("released\n", encoding="utf-8")
    file_v2.write_text("draft\n", encoding="utf-8")

    version_v1 = create_version(
        db_session,
        dataset_id=dataset.id,
        version="v1",
        file_path=str(file_v1),
        lifecycle_state="ready",
        is_current=1,
    )
    version_v2 = create_version(
        db_session,
        dataset_id=dataset.id,
        version="v2",
        file_path=str(file_v2),
        lifecycle_state="ready",
    )

    dataset_domain_service.release_dataset_version(
        db=db_session,
        version_id=version_v1.id,
        request_data=DatasetVersionReleaseRequest(id=version_v1.id, note="release v1"),
        user=owner,
    )

    public_payload = dataset_domain_service.get_public_dataset(dataset.id)
    assert public_payload["published_version"]["id"] == version_v1.id

    with pytest.raises(HTTPException) as exc_info:
        dataset_domain_service.get_public_dataset_version(dataset.id, version_v2.id)
    assert exc_info.value.status_code == 404


def test_public_dataset_version_info_includes_public_lineage(db_session, patch_public_db, tmp_path):
    owner = make_user(8031)
    genome_dataset = create_dataset(db_session, name="rose-genome", owner_id=owner.id, dataset_type="sequence")
    expr_dataset = create_dataset(db_session, name="rose-expression", owner_id=owner.id, dataset_type="expression")
    genome_file = tmp_path / "genome.fa"
    expr_file = tmp_path / "expr.h5"
    genome_file.write_text(">chr1\nACGT\n", encoding="utf-8")
    expr_file.write_text("placeholder\n", encoding="utf-8")

    genome_version = create_version(
        db_session,
        dataset_id=genome_dataset.id,
        version="SMT2024",
        file_path=str(genome_file),
        dataset_type="sequence",
        file_format="fa",
        query_engine="samtools/faidx",
        lifecycle_state="ready",
        is_current=1,
    )
    expr_version = create_version(
        db_session,
        dataset_id=expr_dataset.id,
        version="2024",
        file_path=str(expr_file),
        dataset_type="expression",
        file_format="h5",
        query_engine="hdf5",
        lifecycle_state="ready",
        is_current=1,
    )

    genome_asset = create_asset(
        db_session,
        dataset_id=genome_dataset.id,
        version_id=genome_version.id,
        asset_code="reference_fasta",
        asset_type="reference_fasta",
        file_format="fa",
        query_engine="samtools/faidx",
        is_query_entry=1,
    )
    expr_asset = create_asset(
        db_session,
        dataset_id=expr_dataset.id,
        version_id=expr_version.id,
        asset_code="expression_matrix",
        asset_type="expression_matrix",
        file_format="h5",
        query_engine="hdf5",
        is_query_entry=1,
    )
    create_asset_file(db_session, dataset_id=genome_dataset.id, asset_id=genome_asset.id, local_path=str(genome_file), file_format="fa")
    create_asset_file(db_session, dataset_id=expr_dataset.id, asset_id=expr_asset.id, local_path=str(expr_file), file_format="h5")

    dataset_domain_service.release_dataset_version(
        db=db_session,
        version_id=genome_version.id,
        request_data=DatasetVersionReleaseRequest(id=genome_version.id, note="release genome"),
        user=owner,
    )
    dataset_domain_service.release_dataset_version(
        db=db_session,
        version_id=expr_version.id,
        request_data=DatasetVersionReleaseRequest(id=expr_version.id, note="release expression"),
        user=owner,
    )
    dataset_domain_service.create_dataset_lineage(
        db=db_session,
        request_data=type(
            "Req",
            (),
            {
                "src_version_id": expr_version.id,
                "dst_version_id": genome_version.id,
                "relation_type": "quantified_against",
                "src_asset_id": expr_asset.id,
                "dst_asset_id": genome_asset.id,
                "direction": "forward",
                "detail_json": '{"note":"expr quantified against genome"}',
            },
        )(),
        user=owner,
    )

    payload = dataset_domain_service.get_public_dataset_version(expr_dataset.id, expr_version.id)

    assert payload["selected_version"]["id"] == expr_version.id
    assert len(payload["lineage"]) == 1
    assert payload["lineage"][0]["relation_type"] == "quantified_against"
    assert payload["lineage"][0]["src_dataset_id"] == expr_dataset.id
    assert payload["lineage"][0]["src_dataset_title"] == "rose-expression"
    assert payload["lineage"][0]["dst_dataset_id"] == genome_dataset.id
    assert payload["lineage"][0]["dst_dataset_title"] == "rose-genome"
    assert payload["lineage"][0]["dst_asset_code"] == "reference_fasta"


def test_query_capabilities_can_resolve_primary_file_from_asset_when_version_file_path_is_empty(
    db_session,
    patch_public_db,
    tmp_path,
):
    owner = make_user(804)
    dataset = create_dataset(db_session, name="asset-first-query", owner_id=owner.id)
    file_path = tmp_path / "asset-primary.txt"
    file_path.write_text("asset-first\n", encoding="utf-8")

    version = create_version(
        db_session,
        dataset_id=dataset.id,
        version="v1",
        file_path=None,
        lifecycle_state="ready",
        is_current=1,
    )
    asset = create_asset(
        db_session,
        dataset_id=dataset.id,
        version_id=version.id,
        asset_code="query_asset",
        is_query_entry=1,
    )
    create_asset_file(
        db_session,
        dataset_id=dataset.id,
        asset_id=asset.id,
        local_path=str(file_path),
    )

    private_caps = dataset_domain_service.get_dataset_version_query_capabilities(
        db=db_session,
        version_id=version.id,
        user=owner,
    )
    private_version = dataset_domain_service.get_dataset_version(
        db=db_session,
        version_id=version.id,
        user=owner,
    )

    dataset_domain_service.release_dataset_version(
        db=db_session,
        version_id=version.id,
        request_data=DatasetVersionReleaseRequest(id=version.id, note="release asset-first version"),
        user=owner,
    )
    public_caps = dataset_domain_service.get_public_query_capabilities(dataset.id)

    assert private_caps["file_path"] == str(file_path)
    assert private_caps["file_access"]["exists_on_server"] is True
    assert private_caps["query_entry_asset"]["id"] == asset.id
    assert private_version["file_path"] == str(file_path)
    assert private_version["assets"][0]["files"][0]["local_path"] == str(file_path)
    assert public_caps["file_path"] == str(file_path)
    assert public_caps["published_version"]["id"] == version.id


def test_version_payloads_prefer_asset_primary_file_over_stale_version_file_path(db_session, patch_public_db, tmp_path):
    owner = make_user(8041)
    dataset = create_dataset(db_session, name="asset-first-version-payload", owner_id=owner.id)
    stale_file = tmp_path / "stale.txt"
    asset_file = tmp_path / "asset-primary.txt"
    stale_file.write_text("stale\n", encoding="utf-8")
    asset_file.write_text("current\n", encoding="utf-8")

    version = create_version(
        db_session,
        dataset_id=dataset.id,
        version="v1",
        file_path=str(stale_file),
        lifecycle_state="ready",
        is_current=1,
    )
    asset = create_asset(
        db_session,
        dataset_id=dataset.id,
        version_id=version.id,
        asset_code="query_asset",
        is_query_entry=1,
    )
    create_asset_file(
        db_session,
        dataset_id=dataset.id,
        asset_id=asset.id,
        local_path=str(asset_file),
    )

    private_version = dataset_domain_service.get_dataset_version(
        db=db_session,
        version_id=version.id,
        user=owner,
    )
    private_versions = dataset_domain_service.list_dataset_versions(
        db=db_session,
        dataset_id=dataset.id,
        user=owner,
    )

    dataset_domain_service.release_dataset_version(
        db=db_session,
        version_id=version.id,
        request_data=DatasetVersionReleaseRequest(id=version.id, note="release asset-first version payload"),
        user=owner,
    )
    public_dataset = dataset_domain_service.get_public_dataset(dataset.id)
    public_versions = dataset_domain_service.list_public_dataset_versions(dataset.id)

    assert private_version["file_path"] == str(asset_file)
    assert private_version["assets"][0]["id"] == asset.id
    assert private_versions["items"][0]["file_path"] == str(asset_file)
    assert public_dataset["published_version"]["file_path"] == str(asset_file)
    assert public_versions["items"][0]["file_path"] == str(asset_file)


def test_sequence_query_works_with_asset_first_when_version_file_path_is_empty(db_session, patch_public_db, tmp_path, monkeypatch):
    owner = make_user(910)
    dataset = create_dataset(db_session, name="sequence-asset-first", owner_id=owner.id, dataset_type="sequence")
    fasta_path = tmp_path / "genome.fa"
    fai_path = tmp_path / "genome.fa.fai"
    fasta_path.write_text(">chr1\nACGTACGT\n", encoding="utf-8")
    fai_path.write_text("chr1\t8\t6\t8\t9\n", encoding="utf-8")

    version = create_version(
        db_session,
        dataset_id=dataset.id,
        version="v1",
        file_path=None,
        dataset_type="sequence",
        file_format="fasta",
        query_engine="samtools",
        lifecycle_state="ready",
        is_current=1,
    )
    asset = create_asset(
        db_session,
        dataset_id=dataset.id,
        version_id=version.id,
        asset_code="reference",
        asset_type="reference_sequence",
        file_format="fasta",
        query_engine="samtools",
        is_query_entry=1,
    )
    primary_file = create_asset_file(
        db_session,
        dataset_id=dataset.id,
        asset_id=asset.id,
        local_path=str(fasta_path),
        file_format="fasta",
    )
    create_asset_file(
        db_session,
        dataset_id=dataset.id,
        asset_id=asset.id,
        local_path=str(fai_path),
        file_role="index",
        file_format="fai",
    )

    monkeypatch.setattr(sequence_adapter_module, "extract_sequence", lambda *args, **kwargs: ">chr1\nACGT\n")
    monkeypatch.setattr(
        sequence_adapter_module,
        "extract_batch_sequences",
        lambda *args, **kwargs: str(tmp_path / "batch.fa"),
    )

    private_caps = dataset_domain_service.get_dataset_version_query_capabilities(
        db=db_session,
        version_id=version.id,
        user=owner,
    )
    private_result = dataset_domain_service.execute_dataset_version_query(
        db=db_session,
        version_id=version.id,
        operation="fetch",
        params={"seq_id": "chr1", "start": 1, "end": 4},
        user=owner,
    )

    dataset_domain_service.release_dataset_version(
        db=db_session,
        version_id=version.id,
        request_data=DatasetVersionReleaseRequest(id=version.id, note="release sequence asset-first"),
        user=owner,
    )
    public_result = dataset_domain_service.execute_public_query(
        dataset.id,
        operation="fetch",
        params={"seq_id": "chr1", "start": 1, "end": 4},
    )

    assert private_caps["file_path"] == str(fasta_path)
    assert private_caps["query_entry_asset"]["id"] == asset.id
    assert private_caps["assets"][0]["files"][0]["id"] == primary_file.id
    assert private_result["query_adapter"]["adapter"] == "sequence"
    assert private_result["data"]["sequence"] == "ACGT"
    assert public_result["query_adapter"]["adapter"] == "sequence"
    assert public_result["data"]["sequence"] == "ACGT"


def test_version_query_can_select_asset_code_for_capabilities_and_execute(db_session, patch_public_db, tmp_path, monkeypatch):
    owner = make_user(9101)
    dataset = create_dataset(db_session, name="sequence-multi-asset", owner_id=owner.id, dataset_type="sequence")
    ref_path = tmp_path / "ref.fa"
    ref_fai_path = tmp_path / "ref.fa.fai"
    alt_path = tmp_path / "alt.fa"
    alt_fai_path = tmp_path / "alt.fa.fai"
    ref_path.write_text(">chr1\nAAAA\n", encoding="utf-8")
    ref_fai_path.write_text("chr1\t4\t6\t4\t5\n", encoding="utf-8")
    alt_path.write_text(">chr1\nCCCC\n", encoding="utf-8")
    alt_fai_path.write_text("chr1\t4\t6\t4\t5\n", encoding="utf-8")

    version = create_version(
        db_session,
        dataset_id=dataset.id,
        version="v1",
        file_path=None,
        dataset_type="sequence",
        file_format="fasta",
        query_engine="samtools",
        lifecycle_state="ready",
        is_current=1,
    )
    ref_asset = create_asset(
        db_session,
        dataset_id=dataset.id,
        version_id=version.id,
        asset_code="reference",
        asset_type="reference_sequence",
        file_format="fasta",
        query_engine="samtools",
        is_query_entry=1,
    )
    create_asset_file(
        db_session,
        dataset_id=dataset.id,
        asset_id=ref_asset.id,
        local_path=str(ref_path),
        file_format="fasta",
    )
    create_asset_file(
        db_session,
        dataset_id=dataset.id,
        asset_id=ref_asset.id,
        local_path=str(ref_fai_path),
        file_role="index",
        file_format="fai",
    )
    alt_asset = create_asset(
        db_session,
        dataset_id=dataset.id,
        version_id=version.id,
        asset_code="alt_reference",
        asset_type="reference_sequence",
        file_format="fasta",
        query_engine="samtools",
        is_query_entry=0,
    )
    create_asset_file(
        db_session,
        dataset_id=dataset.id,
        asset_id=alt_asset.id,
        local_path=str(alt_path),
        file_format="fasta",
    )
    create_asset_file(
        db_session,
        dataset_id=dataset.id,
        asset_id=alt_asset.id,
        local_path=str(alt_fai_path),
        file_role="index",
        file_format="fai",
    )

    monkeypatch.setattr(
        sequence_adapter_module,
        "extract_sequence",
        lambda fasta_path, *_args, **_kwargs: f">{Path(fasta_path).stem}\n{Path(fasta_path).stem.upper()}\n",
    )

    default_caps = dataset_domain_service.get_dataset_version_query_capabilities(
        db=db_session,
        version_id=version.id,
        user=owner,
    )
    selected_caps = dataset_domain_service.get_dataset_version_query_capabilities(
        db=db_session,
        version_id=version.id,
        asset_code="alt_reference",
        user=owner,
    )
    selected_result = dataset_domain_service.execute_dataset_version_query(
        db=db_session,
        version_id=version.id,
        asset_code="alt_reference",
        operation="fetch",
        params={"seq_id": "chr1", "start": 1, "end": 4},
        user=owner,
    )

    dataset_domain_service.release_dataset_version(
        db=db_session,
        version_id=version.id,
        request_data=DatasetVersionReleaseRequest(id=version.id, note="release multi-asset sequence"),
        user=owner,
    )
    public_caps = dataset_domain_service.get_public_dataset_version_query_capabilities(
        dataset_id=dataset.id,
        version_id=version.id,
        asset_code="alt_reference",
    )
    public_result = dataset_domain_service.execute_public_dataset_version_query(
        dataset_id=dataset.id,
        version_id=version.id,
        asset_code="alt_reference",
        operation="fetch",
        params={"seq_id": "chr1", "start": 1, "end": 4},
    )

    assert default_caps["query_entry_asset"]["asset_code"] == "reference"
    assert default_caps["file_path"] == str(ref_path)
    assert selected_caps["query_entry_asset"]["asset_code"] == "alt_reference"
    assert selected_caps["file_path"] == str(alt_path)
    assert selected_caps["query_adapter"]["adapter"] == "sequence"
    assert selected_result["data"]["sequence"] == "ALT"
    assert public_caps["query_entry_asset"]["asset_code"] == "alt_reference"
    assert public_caps["file_path"] == str(alt_path)
    assert public_result["data"]["sequence"] == "ALT"

    with pytest.raises(HTTPException) as error:
        dataset_domain_service.get_dataset_version_query_capabilities(
            db=db_session,
            version_id=version.id,
            asset_code="missing_asset",
            user=owner,
        )
    assert error.value.status_code == 404


def test_variant_query_works_with_asset_first_when_version_file_path_is_empty(db_session, patch_public_db, tmp_path, monkeypatch):
    owner = make_user(911)
    dataset = create_dataset(db_session, name="variant-asset-first", owner_id=owner.id, dataset_type="variant")
    vcf_path = tmp_path / "variants.vcf.gz"
    tbi_path = tmp_path / "variants.vcf.gz.tbi"
    vcf_path.write_text("##fileformat=VCFv4.2\n", encoding="utf-8")
    tbi_path.write_text("index\n", encoding="utf-8")

    version = create_version(
        db_session,
        dataset_id=dataset.id,
        version="v1",
        file_path=None,
        dataset_type="variant",
        file_format="vcf.gz",
        query_engine="bcftools",
        lifecycle_state="ready",
        is_current=1,
    )
    asset = create_asset(
        db_session,
        dataset_id=dataset.id,
        version_id=version.id,
        asset_code="variants",
        asset_type="variant_calls",
        file_format="vcf.gz",
        query_engine="bcftools",
        is_query_entry=1,
    )
    create_asset_file(
        db_session,
        dataset_id=dataset.id,
        asset_id=asset.id,
        local_path=str(vcf_path),
        file_format="vcf.gz",
    )
    create_asset_file(
        db_session,
        dataset_id=dataset.id,
        asset_id=asset.id,
        local_path=str(tbi_path),
        file_role="index",
        file_format="tbi",
    )

    monkeypatch.setattr(variant_adapter_module, "check_vcf_file", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        variant_adapter_module,
        "extract_variants",
        lambda **_kwargs: {"vcf_path": str(vcf_path), "preview": "chr1\t10\t.\tA\tT\n", "size": 18},
    )
    monkeypatch.setattr(variant_adapter_module.VariantAdapter, "require_binary", lambda self, name: f"/usr/bin/{name}")

    private_caps = dataset_domain_service.get_dataset_version_query_capabilities(
        db=db_session,
        version_id=version.id,
        user=owner,
    )
    private_result = dataset_domain_service.execute_dataset_version_query(
        db=db_session,
        version_id=version.id,
        operation="query",
        params={"regions": ["chr1:1-100"]},
        user=owner,
    )

    dataset_domain_service.release_dataset_version(
        db=db_session,
        version_id=version.id,
        request_data=DatasetVersionReleaseRequest(id=version.id, note="release variant asset-first"),
        user=owner,
    )
    public_result = dataset_domain_service.execute_public_query(
        dataset.id,
        operation="query",
        params={"regions": ["chr1:1-100"]},
    )

    assert private_caps["file_path"] == str(vcf_path)
    assert private_caps["query_adapter"]["adapter"] == "variant"
    assert private_result["query_adapter"]["adapter"] == "variant"
    assert private_result["data"]["count"] == 1
    assert public_result["query_adapter"]["adapter"] == "variant"
    assert public_result["data"]["count"] == 1


def test_expression_query_works_with_asset_first_when_version_file_path_is_empty(db_session, patch_public_db, tmp_path, monkeypatch):
    owner = make_user(912)
    dataset = create_dataset(db_session, name="expression-asset-first", owner_id=owner.id, dataset_type="expression")
    h5_path = tmp_path / "expr.h5"
    h5_path.write_text("placeholder\n", encoding="utf-8")

    version = create_version(
        db_session,
        dataset_id=dataset.id,
        version="v1",
        file_path=None,
        dataset_type="expression",
        file_format="h5",
        query_engine="hdf5",
        lifecycle_state="ready",
        is_current=1,
    )
    asset = create_asset(
        db_session,
        dataset_id=dataset.id,
        version_id=version.id,
        asset_code="matrix",
        asset_type="expression_matrix",
        file_format="h5",
        query_engine="hdf5",
        is_query_entry=1,
    )
    create_asset_file(
        db_session,
        dataset_id=dataset.id,
        asset_id=asset.id,
        local_path=str(h5_path),
        file_format="h5",
    )

    monkeypatch.setattr(
        expression_adapter_module,
        "load_gene_sample_names",
        lambda *_args, **_kwargs: (["Gene1", "Gene2"], ["SampleA", "SampleB"]),
    )
    monkeypatch.setattr(
        expression_adapter_module,
        "extract_expression_matrix",
        lambda **_kwargs: ([[1.0]], ["Gene1"], ["SampleA"], str(tmp_path / "slice.tsv")),
    )

    private_caps = dataset_domain_service.get_dataset_version_query_capabilities(
        db=db_session,
        version_id=version.id,
        user=owner,
    )
    private_result = dataset_domain_service.execute_dataset_version_query(
        db=db_session,
        version_id=version.id,
        operation="genes_list",
        params={"max_records": 10},
        user=owner,
    )

    dataset_domain_service.release_dataset_version(
        db=db_session,
        version_id=version.id,
        request_data=DatasetVersionReleaseRequest(id=version.id, note="release expression asset-first"),
        user=owner,
    )
    public_result = dataset_domain_service.execute_public_query(
        dataset.id,
        operation="genes_list",
        params={"max_records": 10},
    )

    assert private_caps["file_path"] == str(h5_path)
    assert private_caps["query_adapter"]["adapter"] == "expression"
    assert private_result["query_adapter"]["adapter"] == "expression"
    assert private_result["data"]["genes"] == ["Gene1", "Gene2"]
    assert public_result["query_adapter"]["adapter"] == "expression"
    assert public_result["data"]["genes"] == ["Gene1", "Gene2"]


@pytest.mark.parametrize(
    ("dataset_type", "asset_type", "file_name", "file_format", "query_engine", "content", "operation", "params", "expected_count"),
    [
        (
            "annotation",
            "gene_annotation",
            "genes.gff3",
            "gff3",
            "tabix",
            "chr1\tsrc\tgene\t10\t30\t.\t+\t.\tID=Gene001;Name=Gene001\n",
            "region_features",
            {"seq_id": "chr1", "start": 1, "end": 100, "feature_type": "gene"},
            1,
        ),
        (
            "signal",
            "signal_track",
            "signal.bed",
            "bed",
            "tabix",
            "chr1\t10\t30\tpeak1\t5\n",
            "region_features",
            {"seq_id": "chr1", "start": 1, "end": 100},
            1,
        ),
        (
            "interaction",
            "interaction_matrix",
            "loops.bedpe",
            "bedpe",
            "tabix",
            "chr1\t10\t30\tchr1\t40\t60\tloop1\t8\n",
            "region_contacts",
            {"seq_id": "chr1", "start": 1, "end": 100, "target_chrom": "chr1"},
            1,
        ),
    ],
)
def test_asset_first_query_works_for_specialized_dataset_types(
    db_session,
    patch_public_db,
    tmp_path,
    dataset_type,
    asset_type,
    file_name,
    file_format,
    query_engine,
    content,
    operation,
    params,
    expected_count,
):
    owner = make_user(900)
    dataset = create_dataset(db_session, name=f"{dataset_type}-asset-first", owner_id=owner.id, dataset_type=dataset_type)
    file_path = tmp_path / file_name
    file_path.write_text(content, encoding="utf-8")

    version = create_version(
        db_session,
        dataset_id=dataset.id,
        version="v1",
        file_path=None,
        dataset_type=dataset_type,
        file_format=file_format,
        query_engine=query_engine,
        lifecycle_state="ready",
        is_current=1,
    )
    asset = create_asset(
        db_session,
        dataset_id=dataset.id,
        version_id=version.id,
        asset_code=f"{dataset_type}_entry",
        asset_type=asset_type,
        file_format=file_format,
        query_engine=query_engine,
        is_query_entry=1,
    )
    create_asset_file(
        db_session,
        dataset_id=dataset.id,
        asset_id=asset.id,
        local_path=str(file_path),
        file_format=file_format,
    )

    private_caps = dataset_domain_service.get_dataset_version_query_capabilities(
        db=db_session,
        version_id=version.id,
        user=owner,
    )
    private_result = dataset_domain_service.execute_dataset_version_query(
        db=db_session,
        version_id=version.id,
        operation=operation,
        params=params,
        user=owner,
    )

    dataset_domain_service.release_dataset_version(
        db=db_session,
        version_id=version.id,
        request_data=DatasetVersionReleaseRequest(id=version.id, note=f"release {dataset_type} asset-first"),
        user=owner,
    )
    public_caps = dataset_domain_service.get_public_query_capabilities(dataset.id)
    public_result = dataset_domain_service.execute_public_query(
        dataset.id,
        operation=operation,
        params=params,
    )

    assert private_caps["file_path"] == str(file_path)
    assert private_caps["query_entry_asset"]["id"] == asset.id
    assert private_caps["query_adapter"]["adapter"] == dataset_type
    assert operation in private_caps["query_adapter"]["supported_operations"]
    assert private_result["query_adapter"]["adapter"] == dataset_type
    assert private_result["data"]["count"] == expected_count

    assert public_caps["file_path"] == str(file_path)
    assert public_caps["query_entry_asset"]["id"] == asset.id
    assert public_caps["query_adapter"]["adapter"] == dataset_type
    assert public_result["query_adapter"]["adapter"] == dataset_type
    assert public_result["data"]["count"] == expected_count


def test_annotation_gtf_queries_work_for_private_and_public_versions(db_session, patch_public_db, tmp_path):
    owner = make_user(9001)
    dataset = create_dataset(db_session, name="annotation-gtf-asset-first", owner_id=owner.id, dataset_type="annotation")
    file_path = tmp_path / "genes.gtf"
    file_path.write_text(
        'chr1\tsrc\tgene\t10\t90\t.\t+\t.\tgene_id "Gene001"; gene_name "Gene001";\n'
        'chr1\tsrc\ttranscript\t10\t90\t.\t+\t.\tgene_id "Gene001"; transcript_id "Tx001"; gene_name "Gene001";\n',
        encoding="utf-8",
    )

    version = create_version(
        db_session,
        dataset_id=dataset.id,
        version="v1",
        file_path=None,
        dataset_type="annotation",
        file_format="gtf",
        query_engine="tabix",
        lifecycle_state="ready",
        is_current=1,
    )
    asset = create_asset(
        db_session,
        dataset_id=dataset.id,
        version_id=version.id,
        asset_code="annotation_gtf_entry",
        asset_type="gene_annotation",
        file_format="gtf",
        query_engine="tabix",
        is_query_entry=1,
    )
    create_asset_file(
        db_session,
        dataset_id=dataset.id,
        asset_id=asset.id,
        local_path=str(file_path),
        file_format="gtf",
    )

    private_caps = dataset_domain_service.get_dataset_version_query_capabilities(
        db=db_session,
        version_id=version.id,
        user=owner,
    )
    private_region_result = dataset_domain_service.execute_dataset_version_query(
        db=db_session,
        version_id=version.id,
        operation="region_features",
        params={"seq_id": "chr1", "start": 1, "end": 100, "feature_type": "gene"},
        user=owner,
    )
    private_gene_result = dataset_domain_service.execute_dataset_version_query(
        db=db_session,
        version_id=version.id,
        operation="gene_lookup",
        params={"gene_id": "Gene001"},
        user=owner,
    )

    dataset_domain_service.release_dataset_version(
        db=db_session,
        version_id=version.id,
        request_data=DatasetVersionReleaseRequest(id=version.id, note="release annotation gtf asset-first"),
        user=owner,
    )
    public_caps = dataset_domain_service.get_public_query_capabilities(dataset.id)
    public_gene_result = dataset_domain_service.execute_public_query(
        dataset.id,
        operation="gene_lookup",
        params={"gene_id": "Gene001"},
    )

    assert private_caps["file_path"] == str(file_path)
    assert private_caps["query_entry_asset"]["id"] == asset.id
    assert private_caps["query_adapter"]["adapter"] == "annotation"
    assert set(private_caps["query_adapter"]["supported_operations"]) == {"gene_lookup", "region_features"}

    assert private_region_result["query_adapter"]["adapter"] == "annotation"
    assert private_region_result["data"]["count"] == 1
    assert private_region_result["data"]["items"][0]["id"] == "Gene001"

    assert private_gene_result["query_adapter"]["adapter"] == "annotation"
    assert private_gene_result["data"]["gene"]["id"] == "Gene001"
    assert private_gene_result["data"]["transcript_count"] == 1
    assert private_gene_result["data"]["transcripts"][0]["id"] == "Tx001"

    assert public_caps["file_path"] == str(file_path)
    assert public_caps["query_adapter"]["adapter"] == "annotation"
    assert public_gene_result["query_adapter"]["adapter"] == "annotation"
    assert public_gene_result["data"]["gene"]["id"] == "Gene001"
    assert public_gene_result["data"]["transcript_count"] == 1


def test_sequence_functional_annotation_asset_queries_work_for_private_and_public_versions(db_session, patch_public_db, tmp_path):
    owner = make_user(90015)
    dataset = create_dataset(db_session, name="sequence-functional-annotation", owner_id=owner.id, dataset_type="sequence")
    fasta_path = tmp_path / "genome.fa"
    fasta_path.write_text(">chr1\nACTGACTGACTG\n", encoding="utf-8")
    functional_db_path = tmp_path / "genome.db"
    create_functional_annotation_sqlite(functional_db_path)

    version = create_version(
        db_session,
        dataset_id=dataset.id,
        version="tair10",
        file_path=None,
        dataset_type="sequence",
        file_format="fa",
        query_engine="samtools/faidx",
        lifecycle_state="ready",
        is_current=1,
    )
    reference_asset = create_asset(
        db_session,
        dataset_id=dataset.id,
        version_id=version.id,
        asset_code="reference_entry",
        asset_type="reference_fasta",
        file_format="fa",
        query_engine="samtools/faidx",
        is_query_entry=1,
    )
    create_asset_file(
        db_session,
        dataset_id=dataset.id,
        asset_id=reference_asset.id,
        local_path=str(fasta_path),
        file_format="fa",
    )
    functional_asset = create_asset(
        db_session,
        dataset_id=dataset.id,
        version_id=version.id,
        asset_code="functional_annotation_v1",
        asset_type="functional_annotation",
        file_format="db",
        query_engine="functional_annotation",
        is_query_entry=0,
    )
    create_asset_file(
        db_session,
        dataset_id=dataset.id,
        asset_id=functional_asset.id,
        local_path=str(functional_db_path),
        file_format="db",
    )

    default_caps = dataset_domain_service.get_dataset_version_query_capabilities(
        db=db_session,
        version_id=version.id,
        user=owner,
    )
    functional_caps = dataset_domain_service.get_dataset_version_query_capabilities(
        db=db_session,
        version_id=version.id,
        asset_code="functional_annotation_v1",
        user=owner,
    )
    private_gene_detail = dataset_domain_service.execute_dataset_version_query(
        db=db_session,
        version_id=version.id,
        asset_code="functional_annotation_v1",
        operation="gene_detail",
        params={"gene_id": "AT1G01010"},
        user=owner,
    )
    private_transcript_detail = dataset_domain_service.execute_dataset_version_query(
        db=db_session,
        version_id=version.id,
        asset_code="functional_annotation_v1",
        operation="transcript_detail",
        params={"transcript_id": "AT1G01010.1"},
        user=owner,
    )
    private_term_lookup = dataset_domain_service.execute_dataset_version_query(
        db=db_session,
        version_id=version.id,
        asset_code="functional_annotation_v1",
        operation="term_lookup",
        params={"term_source": "go", "keyword": "DNA binding"},
        user=owner,
    )
    private_term_genes = dataset_domain_service.execute_dataset_version_query(
        db=db_session,
        version_id=version.id,
        asset_code="functional_annotation_v1",
        operation="term_gene_list",
        params={"term_source": "go", "term_id": "GO:0003677"},
        user=owner,
    )

    dataset_domain_service.release_dataset_version(
        db=db_session,
        version_id=version.id,
        request_data=DatasetVersionReleaseRequest(id=version.id, note="release functional annotation asset"),
        user=owner,
    )
    public_caps = dataset_domain_service.get_public_dataset_version_query_capabilities(
        dataset.id,
        version.id,
        asset_code="functional_annotation_v1",
    )
    public_gene_summary = dataset_domain_service.execute_public_dataset_version_query(
        dataset.id,
        version.id,
        asset_code="functional_annotation_v1",
        operation="gene_function_summary",
        params={"gene_id": "AT1G01010"},
    )
    public_term_aggregation = dataset_domain_service.execute_public_dataset_version_query(
        dataset.id,
        version.id,
        asset_code="functional_annotation_v1",
        operation="term_aggregation",
        params={"limit": 10},
    )

    assert default_caps["query_adapter"]["adapter"] == "sequence"
    assert functional_caps["query_entry_asset"]["id"] == functional_asset.id
    assert functional_caps["query_adapter"]["adapter"] == "functional_annotation"
    assert set(functional_caps["query_adapter"]["supported_operations"]) == {
        "gene_detail",
        "transcript_detail",
        "gene_function_summary",
        "term_lookup",
        "term_gene_list",
        "term_aggregation",
    }

    assert private_gene_detail["query_adapter"]["adapter"] == "functional_annotation"
    assert private_gene_detail["data"]["gene"]["gene_id"] == "AT1G01010"
    assert private_gene_detail["data"]["canonical_transcript"]["transcript_id"] == "AT1G01010.1"
    assert private_gene_detail["data"]["canonical_transcript"]["annotation_counts"]["go"] == 2
    assert private_gene_detail["data"]["canonical_transcript"]["annotation_counts"]["kegg"] == 1

    assert private_transcript_detail["data"]["transcript"]["transcript_id"] == "AT1G01010.1"
    assert private_transcript_detail["data"]["transcript"]["annotations"]["family"][0]["name"] == "NAC"
    assert private_transcript_detail["data"]["gene"]["canonical_transcript"] == "AT1G01010.1"
    assert private_term_lookup["data"]["source"] == "postgresql_index"
    assert private_term_lookup["data"]["items"][0]["term_id"] == "GO:0003677"
    assert private_term_lookup["data"]["items"][0]["gene_count"] == 1
    assert private_term_genes["data"]["items"][0]["gene"]["gene_id"] == "AT1G01010"
    assert private_term_genes["data"]["items"][0]["assignment_hits"] == 1

    assert public_caps["query_adapter"]["adapter"] == "functional_annotation"
    assert public_gene_summary["query_adapter"]["adapter"] == "functional_annotation"
    assert public_gene_summary["data"]["annotation_counts"]["go"] == 2
    assert public_gene_summary["data"]["annotation_counts"]["interpro"] == 1
    assert {item["term_source"] for item in public_term_aggregation["data"]["by_source"]} >= {"family", "go", "interpro", "itak", "kegg"}
    assert public_term_aggregation["data"]["top_terms"][0]["gene_count"] >= 1


def test_sequence_bundle_provisioning_registers_reference_gene_and_functional_assets(db_session, tmp_path):
    seed_registry_defaults(db_session)
    admin = make_user(99001, is_superman=True)
    bundle_dir = create_sequence_bundle_dir(tmp_path / "dataset01")

    result = bundle_provisioning.provision_sequence_bundle(
        db=db_session,
        bundle_dir=bundle_dir,
        user=admin,
        dataset_title="arabidopsis_dataset01",
        version="TAIR10",
        organism="Arabidopsis thaliana",
        assembly="TAIR10",
    )

    dataset_payload = result["dataset"]
    version_payload = result["version"]
    asset_rows = dataset_domain_service.list_dataset_assets(db=db_session, version_id=version_payload["id"], user=admin)["items"]
    asset_by_code = {item["asset_code"]: item for item in asset_rows}

    assert dataset_payload["title"] == "arabidopsis_dataset01"
    assert dataset_payload["dataset_type"] == "genome"
    assert dataset_payload["lifecycle_state"] == "ready"
    assert dataset_payload["organism"] == "Arabidopsis thaliana"
    assert dataset_payload["assembly"] == "TAIR10"
    assert dataset_payload["default_public_version_id"] is None
    assert version_payload["version"] == "TAIR10"
    assert version_payload["is_current"] is True
    assert version_payload["release_state"] == "unreleased"

    assert set(asset_by_code) >= {"reference_fasta", "gene_annotation", "functional_annotation"}
    assert asset_by_code["reference_fasta"]["is_query_entry"] is True
    assert asset_by_code["gene_annotation"]["file_format"] == "gff3.gz"
    assert asset_by_code["gene_annotation"]["query_engine"] == "tabix/gff"
    assert asset_by_code["functional_annotation"]["query_engine"] == "functional_annotation"
    functional_meta = json.loads(asset_by_code["functional_annotation"]["meta_json"])

    reference_files = {item["local_path"] for item in asset_by_code["reference_fasta"]["files"]}
    reference_file_types = {item["asset_file_type_code"] for item in asset_by_code["reference_fasta"]["files"]}
    annotation_files = {item["local_path"] for item in asset_by_code["gene_annotation"]["files"]}
    annotation_file_types = {item["asset_file_type_code"] for item in asset_by_code["gene_annotation"]["files"]}
    functional_file_types = {item["asset_file_type_code"] for item in asset_by_code["functional_annotation"]["files"]}

    assert str(bundle_dir / "genome.fa.gz") in reference_files
    assert str(bundle_dir / "genome.fa.gz.fai") in reference_files
    assert str(bundle_dir / "genome.fa.gz.gzi") in reference_files
    assert reference_file_types == {"genome_sequence", "genome_sequence_index"}
    assert str(bundle_dir / "gene_model_sorted.gff3.gz") in annotation_files
    assert str(bundle_dir / "gene_model_sorted.gff3.gz.tbi") in annotation_files
    assert str(bundle_dir / "mRNA.fa.gz") in annotation_files
    assert str(bundle_dir / "protein.fa.gz") in annotation_files
    assert annotation_file_types == {"gene_models", "gene_models_index", "transcript_sequence", "protein_sequence"}
    assert functional_file_types == {"functional_annotation_db"}
    assert functional_meta["source_dir"] == str(bundle_dir / "func_anno")

    query_result = dataset_domain_service.execute_dataset_version_query(
        db=db_session,
        version_id=version_payload["id"],
        asset_code="functional_annotation",
        operation="gene_detail",
        params={"gene_id": "AT1G01010"},
        user=admin,
    )
    indexed_term_count = (
        db_session.query(FunctionalTerm)
        .filter(
            FunctionalTerm.dataset_id == dataset_payload["id"],
            FunctionalTerm.version_id == version_payload["id"],
            FunctionalTerm.asset_id == asset_by_code["functional_annotation"]["id"],
        )
        .count()
    )
    indexed_gene_count = (
        db_session.query(FunctionalGene)
        .filter(
            FunctionalGene.dataset_id == dataset_payload["id"],
            FunctionalGene.version_id == version_payload["id"],
            FunctionalGene.asset_id == asset_by_code["functional_annotation"]["id"],
        )
        .count()
    )

    assert version_payload["lifecycle_state"] == "ready"
    assert query_result["query_adapter"]["adapter"] == "functional_annotation"
    assert query_result["data"]["gene"]["gene_id"] == "AT1G01010"
    assert indexed_term_count >= 5
    assert indexed_gene_count == 1


def test_expression_bundle_provisioning_registers_expression_assets_and_reference_lineage(db_session, tmp_path):
    seed_registry_defaults(db_session)
    admin = make_user(99002, is_superman=True)
    reference_bundle_dir = create_sequence_bundle_dir(tmp_path / "genome" / "dataset01")
    expression_bundle_dir = create_expression_bundle_dir(tmp_path / "transcriptome")

    reference_result = bundle_provisioning.provision_sequence_bundle(
        db=db_session,
        bundle_dir=reference_bundle_dir,
        user=admin,
        dataset_title="arabidopsis_dataset01",
        version="TAIR10",
        organism="Arabidopsis thaliana",
        assembly="TAIR10",
    )

    result = bundle_provisioning.provision_expression_bundle(
        db=db_session,
        bundle_dir=expression_bundle_dir,
        user=admin,
        version="2024",
        reference_version_id=reference_result["version"]["id"],
    )

    dataset_payload = result["dataset"]
    version_payload = result["version"]
    asset_rows = dataset_domain_service.list_dataset_assets(db=db_session, version_id=version_payload["id"], user=admin)["items"]
    asset_by_code = {item["asset_code"]: item for item in asset_rows}
    lineage_rows = dataset_domain_service.list_dataset_lineage(db=db_session, version_id=version_payload["id"], limit=20, user=admin)["items"]

    assert dataset_payload["title"] == "Plant Hormone Treatment Transcriptome Expression Profile Dataset"
    assert dataset_payload["dataset_type"] == "transcriptome"
    assert dataset_payload["organism"] == "rose"
    assert dataset_payload["lifecycle_state"] == "ready"
    assert dataset_payload["default_public_version_id"] is None
    assert version_payload["version"] == "2024"
    assert version_payload["dataset_type"] == "transcriptome"
    assert version_payload["release_state"] == "unreleased"

    assert set(asset_by_code) >= {"expression_matrix", "sample_metadata", "count_matrix_raw", "fpkm_matrix_raw"}
    assert asset_by_code["expression_matrix"]["is_query_entry"] is True
    assert asset_by_code["expression_matrix"]["query_engine"] == "hdf5"
    assert asset_by_code["sample_metadata"]["file_format"] == "json"

    genes_result = dataset_domain_service.execute_dataset_version_query(
        db=db_session,
        version_id=version_payload["id"],
        operation="genes_list",
        params={"max_records": 10},
        user=admin,
    )
    matrix_result = dataset_domain_service.execute_dataset_version_query(
        db=db_session,
        version_id=version_payload["id"],
        operation="matrix_slice",
        params={"data_type": "fpkm", "genes": ["Gene1"], "samples": ["SampleB"]},
        user=admin,
    )

    assert genes_result["query_adapter"]["adapter"] == "expression"
    assert genes_result["data"]["genes"] == ["Gene1", "Gene2"]
    assert matrix_result["data"]["genes"] == ["Gene1"]
    assert matrix_result["data"]["samples"] == ["SampleB"]
    assert matrix_result["data"]["matrix"] == [[2.5]]

    assert len(lineage_rows) == 1
    assert lineage_rows[0]["relation_type"] == "quantified_against"
    assert lineage_rows[0]["src_version_id"] == version_payload["id"]
    assert lineage_rows[0]["dst_version_id"] == reference_result["version"]["id"]
    assert lineage_rows[0]["src_asset_code"] == "expression_matrix"
    assert lineage_rows[0]["dst_asset_code"] == "reference_fasta"


def test_variome_bundle_provisioning_registers_indexed_variant_asset_and_reference_lineage(db_session, tmp_path):
    seed_registry_defaults(db_session)
    admin = make_user(99003, is_superman=True)
    reference_bundle_dir = create_sequence_bundle_dir(tmp_path / "genome" / "SMT2024")
    variome_bundle_dir = create_variome_bundle_dir(tmp_path / "variome")

    reference_result = bundle_provisioning.provision_sequence_bundle(
        db=db_session,
        bundle_dir=reference_bundle_dir,
        user=admin,
        dataset_title="rose_genome_SMT2024",
        version="SMT2024",
        organism="Rosa chinensis",
        assembly="SMT2024",
    )

    result = bundle_provisioning.provision_variome_bundle(
        db=db_session,
        bundle_dir=variome_bundle_dir,
        user=admin,
        dataset_title="rose_variome_test",
        version="v1",
        organism="Rosa chinensis",
        assembly="SMT2024",
        reference_version_id=reference_result["version"]["id"],
    )

    dataset_payload = result["dataset"]
    version_payload = result["version"]
    asset_rows = dataset_domain_service.list_dataset_assets(db=db_session, version_id=version_payload["id"], user=admin)["items"]
    asset_by_code = {item["asset_code"]: item for item in asset_rows}
    lineage_rows = dataset_domain_service.list_dataset_lineage(db=db_session, version_id=version_payload["id"], limit=20, user=admin)["items"]

    assert dataset_payload["title"] == "rose_variome_test"
    assert dataset_payload["dataset_type"] == "variome"
    assert dataset_payload["organism"] == "Rosa chinensis"
    assert dataset_payload["assembly"] == "SMT2024"
    assert dataset_payload["lifecycle_state"] == "ready"
    assert version_payload["version"] == "v1"
    assert version_payload["dataset_type"] == "variome"
    assert version_payload["release_state"] == "unreleased"

    assert set(asset_by_code) == {"variant_calls"}
    assert asset_by_code["variant_calls"]["asset_type"] == "variant_vcf"
    assert asset_by_code["variant_calls"]["is_query_entry"] is True
    assert asset_by_code["variant_calls"]["query_engine"] == "tabix/bcftools"

    variant_files = {item["local_path"] for item in asset_by_code["variant_calls"]["files"]}
    assert str(variome_bundle_dir / "gwas358_AB.snp.mafgeno.test.vcf.gz") in variant_files
    assert str(variome_bundle_dir / "gwas358_AB.snp.mafgeno.test.vcf.gz.csi") in variant_files
    assert str(variome_bundle_dir / "test.vcf") not in variant_files
    assert result["plan"]["primary_file_path"] == str((variome_bundle_dir / "gwas358_AB.snp.mafgeno.test.vcf.gz").resolve())

    assert len(lineage_rows) == 1
    assert lineage_rows[0]["relation_type"] == "called_against"
    assert lineage_rows[0]["src_version_id"] == version_payload["id"]
    assert lineage_rows[0]["dst_version_id"] == reference_result["version"]["id"]
    assert lineage_rows[0]["src_asset_code"] == "variant_calls"
    assert lineage_rows[0]["dst_asset_code"] == "reference_fasta"


def test_signal_bigwig_region_signal_works_for_private_and_public_versions(db_session, patch_public_db, tmp_path, monkeypatch):
    owner = make_user(9002)
    dataset = create_dataset(db_session, name="signal-bigwig-asset-first", owner_id=owner.id, dataset_type="signal")
    file_path = tmp_path / "signal.bw"
    file_path.write_bytes(b"bigwig")

    version = create_version(
        db_session,
        dataset_id=dataset.id,
        version="v1",
        file_path=None,
        dataset_type="signal",
        file_format="bw",
        query_engine="bigwig",
        lifecycle_state="ready",
        is_current=1,
    )
    asset = create_asset(
        db_session,
        dataset_id=dataset.id,
        version_id=version.id,
        asset_code="signal_bigwig_entry",
        asset_type="signal_track",
        file_format="bw",
        query_engine="bigwig",
        is_query_entry=1,
    )
    create_asset_file(
        db_session,
        dataset_id=dataset.id,
        asset_id=asset.id,
        local_path=str(file_path),
        file_format="bw",
    )

    class FakeBigWigFile:
        def __init__(self, path):
            self.path = path

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def chroms(self):
            return {"chr1": 1000}

        def header(self):
            return {"maxVal": 9.0, "minVal": 1.0, "nBasesCovered": 800}

        def stats(self, chrom, start, end, nBins=1, type="mean", exact=True):
            assert chrom == "chr1"
            assert start == 1
            assert end == 101
            assert type == "mean"
            if nBins == 1:
                return [3.5]
            return [1.0, 2.0, None, 4.5]

    fake_pybigwig = type("FakePyBigWig", (), {"open": staticmethod(lambda path: FakeBigWigFile(path))})
    monkeypatch.setattr(signal_adapter_module, "pyBigWig", fake_pybigwig)

    private_caps = dataset_domain_service.get_dataset_version_query_capabilities(
        db=db_session,
        version_id=version.id,
        user=owner,
    )
    private_describe = dataset_domain_service.execute_dataset_version_query(
        db=db_session,
        version_id=version.id,
        operation="describe_signal",
        params={},
        user=owner,
    )
    private_region = dataset_domain_service.execute_dataset_version_query(
        db=db_session,
        version_id=version.id,
        operation="region_signal",
        params={"seq_id": "chr1", "start": 1, "end": 101, "bins": 4, "summary_type": "mean"},
        user=owner,
    )

    dataset_domain_service.release_dataset_version(
        db=db_session,
        version_id=version.id,
        request_data=DatasetVersionReleaseRequest(id=version.id, note="release signal bigwig asset-first"),
        user=owner,
    )
    public_region = dataset_domain_service.execute_public_query(
        dataset.id,
        operation="region_signal",
        params={"seq_id": "chr1", "start": 1, "end": 101, "bins": 4, "summary_type": "mean"},
    )

    assert private_caps["query_adapter"]["adapter"] == "signal"
    assert set(private_caps["query_adapter"]["supported_operations"]) == {"describe_signal", "region_signal"}
    assert private_describe["data"]["source"] == "bigwig"
    assert private_describe["data"]["chromosome_count"] == 1
    assert private_region["data"]["source"] == "bigwig"
    assert private_region["data"]["summary"]["value"] == 3.5
    assert private_region["data"]["count"] == 4
    assert private_region["data"]["non_null_count"] == 3
    assert private_region["data"]["items"][2]["value"] is None
    assert public_region["data"]["source"] == "bigwig"
    assert public_region["data"]["summary"]["max"] == 4.5


def test_interaction_cool_matrix_queries_work_for_private_and_public_versions(db_session, patch_public_db, tmp_path):
    owner = make_user(9003)
    dataset = create_dataset(db_session, name="interaction-cool-asset-first", owner_id=owner.id, dataset_type="interaction")
    file_path = tmp_path / "matrix.cool"
    create_cool_file(
        file_path,
        chrom_length=30000,
        bin_size=10000,
        pixels=[(0, 0, 5), (0, 1, 7), (1, 1, 11), (1, 2, 13), (2, 2, 17)],
        weights=[1.0, 0.5, 2.0],
    )

    version = create_version(
        db_session,
        dataset_id=dataset.id,
        version="v1",
        file_path=None,
        dataset_type="interaction",
        file_format="cool",
        query_engine="cooler",
        lifecycle_state="ready",
        is_current=1,
    )
    asset = create_asset(
        db_session,
        dataset_id=dataset.id,
        version_id=version.id,
        asset_code="interaction_cool_entry",
        asset_type="interaction_matrix",
        file_format="cool",
        query_engine="cooler",
        is_query_entry=1,
    )
    create_asset_file(
        db_session,
        dataset_id=dataset.id,
        asset_id=asset.id,
        local_path=str(file_path),
        file_format="cool",
    )

    private_caps = dataset_domain_service.get_dataset_version_query_capabilities(
        db=db_session,
        version_id=version.id,
        user=owner,
    )
    private_meta = dataset_domain_service.execute_dataset_version_query(
        db=db_session,
        version_id=version.id,
        operation="matrix_meta",
        params={},
        user=owner,
    )
    private_slice = dataset_domain_service.execute_dataset_version_query(
        db=db_session,
        version_id=version.id,
        operation="matrix_slice",
        params={"chrom": "chr1", "start": 0, "end": 20000, "limit_bins": 5},
        user=owner,
    )

    dataset_domain_service.release_dataset_version(
        db=db_session,
        version_id=version.id,
        request_data=DatasetVersionReleaseRequest(id=version.id, note="release interaction cool asset-first"),
        user=owner,
    )
    public_slice = dataset_domain_service.execute_public_query(
        dataset.id,
        operation="matrix_slice",
        params={"chrom": "chr1", "start": 0, "end": 20000, "limit_bins": 5},
    )

    assert private_caps["query_adapter"]["adapter"] == "interaction"
    assert set(private_caps["query_adapter"]["supported_operations"]) == {"matrix_meta", "matrix_slice"}
    assert private_meta["data"]["source"] == "cool"
    assert private_meta["data"]["format"] == "cool"
    assert private_meta["data"]["bin_size"] == 10000
    assert private_meta["data"]["balanced_supported"] is True
    assert private_slice["data"]["shape"] == [2, 2]
    assert private_slice["data"]["matrix"] == [[5, 7], [7, 11]]
    assert private_slice["data"]["x_labels"] == ["chr1:0-10000", "chr1:10000-20000"]
    assert public_slice["data"]["source"] == "cool"
    assert public_slice["data"]["matrix"] == [[5, 7], [7, 11]]


def test_interaction_mcool_can_switch_query_asset_by_asset_code(db_session, patch_public_db, tmp_path):
    owner = make_user(9004)
    dataset = create_dataset(db_session, name="interaction-mcool-multi-asset", owner_id=owner.id, dataset_type="interaction")
    default_file_path = tmp_path / "default.mcool"
    alt_file_path = tmp_path / "alt.mcool"
    create_mcool_file(
        default_file_path,
        resolutions={
            10000: {
                "chrom_length": 20000,
                "pixels": [(0, 0, 1), (0, 1, 2), (1, 1, 3)],
                "weights": [1.0, 1.0],
            },
            50000: {
                "chrom_length": 50000,
                "pixels": [(0, 0, 9)],
                "weights": [1.0],
            },
        },
    )
    create_mcool_file(
        alt_file_path,
        resolutions={
            10000: {
                "chrom_length": 20000,
                "pixels": [(0, 0, 10), (0, 1, 20), (1, 1, 30)],
                "weights": [1.0, 1.0],
            },
            50000: {
                "chrom_length": 50000,
                "pixels": [(0, 0, 99)],
                "weights": [1.0],
            },
        },
    )

    version = create_version(
        db_session,
        dataset_id=dataset.id,
        version="v1",
        file_path=None,
        dataset_type="interaction",
        file_format="mcool",
        query_engine="cooler",
        lifecycle_state="ready",
        is_current=1,
    )
    default_asset = create_asset(
        db_session,
        dataset_id=dataset.id,
        version_id=version.id,
        asset_code="default_interaction_mcool",
        asset_type="interaction_matrix",
        file_format="mcool",
        query_engine="cooler",
        is_query_entry=1,
    )
    create_asset_file(
        db_session,
        dataset_id=dataset.id,
        asset_id=default_asset.id,
        local_path=str(default_file_path),
        file_format="mcool",
    )
    alt_asset = create_asset(
        db_session,
        dataset_id=dataset.id,
        version_id=version.id,
        asset_code="alt_interaction_mcool",
        asset_type="interaction_matrix",
        file_format="mcool",
        query_engine="cooler",
        is_query_entry=0,
    )
    create_asset_file(
        db_session,
        dataset_id=dataset.id,
        asset_id=alt_asset.id,
        local_path=str(alt_file_path),
        file_format="mcool",
    )

    default_private_result = dataset_domain_service.execute_dataset_version_query(
        db=db_session,
        version_id=version.id,
        operation="matrix_slice",
        params={"chrom": "chr1", "start": 0, "end": 20000, "resolution": 10000, "limit_bins": 5},
        user=owner,
    )
    alt_private_caps = dataset_domain_service.get_dataset_version_query_capabilities(
        db=db_session,
        version_id=version.id,
        asset_code="alt_interaction_mcool",
        user=owner,
    )
    alt_private_resolutions = dataset_domain_service.execute_dataset_version_query(
        db=db_session,
        version_id=version.id,
        asset_code="alt_interaction_mcool",
        operation="resolutions_list",
        params={},
        user=owner,
    )
    alt_private_result = dataset_domain_service.execute_dataset_version_query(
        db=db_session,
        version_id=version.id,
        asset_code="alt_interaction_mcool",
        operation="matrix_slice",
        params={"chrom": "chr1", "start": 0, "end": 20000, "resolution": 10000, "limit_bins": 5},
        user=owner,
    )

    dataset_domain_service.release_dataset_version(
        db=db_session,
        version_id=version.id,
        request_data=DatasetVersionReleaseRequest(id=version.id, note="release interaction mcool multi-asset"),
        user=owner,
    )
    alt_public_caps = dataset_domain_service.get_public_query_capabilities(dataset.id, asset_code="alt_interaction_mcool")
    alt_public_result = dataset_domain_service.execute_public_query(
        dataset.id,
        asset_code="alt_interaction_mcool",
        operation="matrix_slice",
        params={"chrom": "chr1", "start": 0, "end": 20000, "resolution": 10000, "limit_bins": 5},
    )

    assert default_private_result["data"]["matrix"] == [[1, 2], [2, 3]]
    assert alt_private_caps["query_entry_asset"]["id"] == alt_asset.id
    assert set(alt_private_caps["query_adapter"]["supported_operations"]) == {"matrix_meta", "matrix_slice", "resolutions_list"}
    assert alt_private_resolutions["data"]["resolutions"] == [10000, 50000]
    assert alt_private_resolutions["data"]["default_resolution"] == 10000
    assert alt_private_result["data"]["format"] == "mcool"
    assert alt_private_result["data"]["resolution"] == 10000
    assert alt_private_result["data"]["matrix"] == [[10, 20], [20, 30]]
    assert alt_public_caps["query_entry_asset"]["id"] == alt_asset.id
    assert alt_public_result["data"]["matrix"] == [[10, 20], [20, 30]]


@pytest.mark.parametrize(
    (
        "dataset_type",
        "asset_type",
        "default_file_name",
        "alt_file_name",
        "file_format",
        "query_engine",
        "default_content",
        "alt_content",
        "operation",
        "params",
        "default_count",
        "alt_count",
    ),
    [
        (
            "annotation",
            "gene_annotation",
            "default.gff3",
            "alt.gff3",
            "gff3",
            "tabix",
            "chr1\tsrc\tgene\t10\t30\t.\t+\t.\tID=Gene001;Name=Gene001\n",
            "chr1\tsrc\tgene\t10\t30\t.\t+\t.\tID=Gene101;Name=Gene101\n"
            "chr1\tsrc\tgene\t40\t60\t.\t+\t.\tID=Gene102;Name=Gene102\n",
            "region_features",
            {"seq_id": "chr1", "start": 1, "end": 100, "feature_type": "gene"},
            1,
            2,
        ),
        (
            "signal",
            "signal_track",
            "default.bed",
            "alt.bed",
            "bed",
            "tabix",
            "chr1\t10\t30\tpeak1\t5\n",
            "chr1\t10\t30\tpeakA\t5\nchr1\t50\t70\tpeakB\t8\n",
            "region_features",
            {"seq_id": "chr1", "start": 1, "end": 100},
            1,
            2,
        ),
        (
            "interaction",
            "interaction_matrix",
            "default.bedpe",
            "alt.bedpe",
            "bedpe",
            "tabix",
            "chr1\t10\t30\tchr1\t40\t60\tloop1\t8\n",
            "chr1\t10\t30\tchr1\t40\t60\tloopA\t8\nchr1\t20\t40\tchr1\t70\t90\tloopB\t9\n",
            "region_contacts",
            {"seq_id": "chr1", "start": 1, "end": 100, "target_chrom": "chr1"},
            1,
            2,
        ),
    ],
)
def test_specialized_dataset_types_can_switch_query_asset_by_asset_code(
    db_session,
    patch_public_db,
    tmp_path,
    dataset_type,
    asset_type,
    default_file_name,
    alt_file_name,
    file_format,
    query_engine,
    default_content,
    alt_content,
    operation,
    params,
    default_count,
    alt_count,
):
    owner = make_user(901)
    dataset = create_dataset(db_session, name=f"{dataset_type}-multi-asset", owner_id=owner.id, dataset_type=dataset_type)
    default_file_path = tmp_path / default_file_name
    alt_file_path = tmp_path / alt_file_name
    default_file_path.write_text(default_content, encoding="utf-8")
    alt_file_path.write_text(alt_content, encoding="utf-8")

    version = create_version(
        db_session,
        dataset_id=dataset.id,
        version="v1",
        file_path=None,
        dataset_type=dataset_type,
        file_format=file_format,
        query_engine=query_engine,
        lifecycle_state="ready",
        is_current=1,
    )
    default_asset = create_asset(
        db_session,
        dataset_id=dataset.id,
        version_id=version.id,
        asset_code=f"{dataset_type}_default",
        asset_type=asset_type,
        file_format=file_format,
        query_engine=query_engine,
        is_query_entry=1,
    )
    create_asset_file(
        db_session,
        dataset_id=dataset.id,
        asset_id=default_asset.id,
        local_path=str(default_file_path),
        file_format=file_format,
    )
    alt_asset = create_asset(
        db_session,
        dataset_id=dataset.id,
        version_id=version.id,
        asset_code=f"{dataset_type}_alt",
        asset_type=asset_type,
        file_format=file_format,
        query_engine=query_engine,
        is_query_entry=0,
    )
    create_asset_file(
        db_session,
        dataset_id=dataset.id,
        asset_id=alt_asset.id,
        local_path=str(alt_file_path),
        file_format=file_format,
    )

    default_caps = dataset_domain_service.get_dataset_version_query_capabilities(
        db=db_session,
        version_id=version.id,
        user=owner,
    )
    default_result = dataset_domain_service.execute_dataset_version_query(
        db=db_session,
        version_id=version.id,
        operation=operation,
        params=params,
        user=owner,
    )
    alt_caps = dataset_domain_service.get_dataset_version_query_capabilities(
        db=db_session,
        version_id=version.id,
        asset_code=f"{dataset_type}_alt",
        user=owner,
    )
    alt_result = dataset_domain_service.execute_dataset_version_query(
        db=db_session,
        version_id=version.id,
        asset_code=f"{dataset_type}_alt",
        operation=operation,
        params=params,
        user=owner,
    )

    dataset_domain_service.release_dataset_version(
        db=db_session,
        version_id=version.id,
        request_data=DatasetVersionReleaseRequest(id=version.id, note=f"release {dataset_type} multi-asset"),
        user=owner,
    )
    public_alt_caps = dataset_domain_service.get_public_dataset_version_query_capabilities(
        dataset_id=dataset.id,
        version_id=version.id,
        asset_code=f"{dataset_type}_alt",
    )
    public_alt_result = dataset_domain_service.execute_public_dataset_version_query(
        dataset_id=dataset.id,
        version_id=version.id,
        asset_code=f"{dataset_type}_alt",
        operation=operation,
        params=params,
    )

    assert default_caps["query_entry_asset"]["asset_code"] == f"{dataset_type}_default"
    assert default_caps["file_path"] == str(default_file_path)
    assert default_result["data"]["count"] == default_count

    assert alt_caps["query_entry_asset"]["asset_code"] == f"{dataset_type}_alt"
    assert alt_caps["file_path"] == str(alt_file_path)
    assert alt_caps["query_adapter"]["adapter"] == dataset_type
    assert alt_result["query_adapter"]["adapter"] == dataset_type
    assert alt_result["data"]["count"] == alt_count

    assert public_alt_caps["query_entry_asset"]["asset_code"] == f"{dataset_type}_alt"
    assert public_alt_caps["file_path"] == str(alt_file_path)
    assert public_alt_caps["query_adapter"]["adapter"] == dataset_type
    assert public_alt_result["query_adapter"]["adapter"] == dataset_type
    assert public_alt_result["data"]["count"] == alt_count


def test_annotation_gtf_can_switch_query_asset_by_asset_code(db_session, patch_public_db, tmp_path):
    owner = make_user(9011)
    dataset = create_dataset(db_session, name="annotation-gtf-multi-asset", owner_id=owner.id, dataset_type="annotation")
    default_file_path = tmp_path / "default.gtf"
    alt_file_path = tmp_path / "alt.gtf"
    default_file_path.write_text(
        'chr1\tsrc\tgene\t10\t90\t.\t+\t.\tgene_id "Gene001"; gene_name "Gene001";\n'
        'chr1\tsrc\ttranscript\t10\t90\t.\t+\t.\tgene_id "Gene001"; transcript_id "Tx001"; gene_name "Gene001";\n',
        encoding="utf-8",
    )
    alt_file_path.write_text(
        'chr1\tsrc\tgene\t20\t120\t.\t+\t.\tgene_id "Gene101"; gene_name "Gene101";\n'
        'chr1\tsrc\ttranscript\t20\t120\t.\t+\t.\tgene_id "Gene101"; transcript_id "Tx101"; gene_name "Gene101";\n'
        'chr1\tsrc\ttranscript\t30\t140\t.\t+\t.\tgene_id "Gene101"; transcript_id "Tx102"; gene_name "Gene101";\n',
        encoding="utf-8",
    )

    version = create_version(
        db_session,
        dataset_id=dataset.id,
        version="v1",
        file_path=None,
        dataset_type="annotation",
        file_format="gtf",
        query_engine="tabix",
        lifecycle_state="ready",
        is_current=1,
    )
    default_asset = create_asset(
        db_session,
        dataset_id=dataset.id,
        version_id=version.id,
        asset_code="default_annotation_gtf",
        asset_type="gene_annotation",
        file_format="gtf",
        query_engine="tabix",
        is_query_entry=1,
    )
    create_asset_file(
        db_session,
        dataset_id=dataset.id,
        asset_id=default_asset.id,
        local_path=str(default_file_path),
        file_format="gtf",
    )
    alt_asset = create_asset(
        db_session,
        dataset_id=dataset.id,
        version_id=version.id,
        asset_code="alt_annotation_gtf",
        asset_type="gene_annotation",
        file_format="gtf",
        query_engine="tabix",
        is_query_entry=0,
    )
    create_asset_file(
        db_session,
        dataset_id=dataset.id,
        asset_id=alt_asset.id,
        local_path=str(alt_file_path),
        file_format="gtf",
    )

    default_private_result = dataset_domain_service.execute_dataset_version_query(
        db=db_session,
        version_id=version.id,
        operation="gene_lookup",
        params={"gene_id": "Gene001"},
        user=owner,
    )
    alt_private_caps = dataset_domain_service.get_dataset_version_query_capabilities(
        db=db_session,
        version_id=version.id,
        asset_code="alt_annotation_gtf",
        user=owner,
    )
    alt_private_result = dataset_domain_service.execute_dataset_version_query(
        db=db_session,
        version_id=version.id,
        asset_code="alt_annotation_gtf",
        operation="gene_lookup",
        params={"gene_id": "Gene101"},
        user=owner,
    )

    dataset_domain_service.release_dataset_version(
        db=db_session,
        version_id=version.id,
        request_data=DatasetVersionReleaseRequest(id=version.id, note="release annotation gtf multi-asset"),
        user=owner,
    )
    alt_public_caps = dataset_domain_service.get_public_query_capabilities(
        dataset.id,
        asset_code="alt_annotation_gtf",
    )
    alt_public_result = dataset_domain_service.execute_public_query(
        dataset.id,
        asset_code="alt_annotation_gtf",
        operation="gene_lookup",
        params={"gene_id": "Gene101"},
    )

    assert default_private_result["data"]["gene"]["id"] == "Gene001"
    assert default_private_result["data"]["transcript_count"] == 1

    assert alt_private_caps["query_entry_asset"]["id"] == alt_asset.id
    assert alt_private_caps["file_path"] == str(alt_file_path)
    assert alt_private_result["query_adapter"]["adapter"] == "annotation"
    assert alt_private_result["data"]["gene"]["id"] == "Gene101"
    assert alt_private_result["data"]["transcript_count"] == 2

    assert alt_public_caps["query_entry_asset"]["id"] == alt_asset.id
    assert alt_public_caps["file_path"] == str(alt_file_path)
    assert alt_public_result["query_adapter"]["adapter"] == "annotation"
    assert alt_public_result["data"]["gene"]["id"] == "Gene101"
    assert alt_public_result["data"]["transcript_count"] == 2


def test_signal_bigwig_can_switch_query_asset_by_asset_code(db_session, patch_public_db, tmp_path, monkeypatch):
    owner = make_user(9012)
    dataset = create_dataset(db_session, name="signal-bigwig-multi-asset", owner_id=owner.id, dataset_type="signal")
    default_file_path = tmp_path / "default.bw"
    alt_file_path = tmp_path / "alt.bw"
    default_file_path.write_bytes(b"default-bigwig")
    alt_file_path.write_bytes(b"alt-bigwig")

    version = create_version(
        db_session,
        dataset_id=dataset.id,
        version="v1",
        file_path=None,
        dataset_type="signal",
        file_format="bw",
        query_engine="bigwig",
        lifecycle_state="ready",
        is_current=1,
    )
    default_asset = create_asset(
        db_session,
        dataset_id=dataset.id,
        version_id=version.id,
        asset_code="default_signal_bw",
        asset_type="signal_track",
        file_format="bw",
        query_engine="bigwig",
        is_query_entry=1,
    )
    create_asset_file(
        db_session,
        dataset_id=dataset.id,
        asset_id=default_asset.id,
        local_path=str(default_file_path),
        file_format="bw",
    )
    alt_asset = create_asset(
        db_session,
        dataset_id=dataset.id,
        version_id=version.id,
        asset_code="alt_signal_bw",
        asset_type="signal_track",
        file_format="bw",
        query_engine="bigwig",
        is_query_entry=0,
    )
    create_asset_file(
        db_session,
        dataset_id=dataset.id,
        asset_id=alt_asset.id,
        local_path=str(alt_file_path),
        file_format="bw",
    )

    class FakeBigWigFile:
        def __init__(self, path):
            self.path = path

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def chroms(self):
            return {"chr1": 1000}

        def header(self):
            return {"maxVal": 10.0, "minVal": 0.5, "nBasesCovered": 900}

        def stats(self, chrom, start, end, nBins=1, type="mean", exact=True):
            assert chrom == "chr1"
            values_map = {
                str(default_file_path): [1.0, 1.5],
                str(alt_file_path): [7.0, 8.5],
            }
            values = values_map[self.path]
            if nBins == 1:
                return [sum(values) / len(values)]
            return values

    fake_pybigwig = type("FakePyBigWig", (), {"open": staticmethod(lambda path: FakeBigWigFile(path))})
    monkeypatch.setattr(signal_adapter_module, "pyBigWig", fake_pybigwig)

    default_private_result = dataset_domain_service.execute_dataset_version_query(
        db=db_session,
        version_id=version.id,
        operation="region_signal",
        params={"seq_id": "chr1", "start": 1, "end": 101, "bins": 2},
        user=owner,
    )
    alt_private_caps = dataset_domain_service.get_dataset_version_query_capabilities(
        db=db_session,
        version_id=version.id,
        asset_code="alt_signal_bw",
        user=owner,
    )
    alt_private_result = dataset_domain_service.execute_dataset_version_query(
        db=db_session,
        version_id=version.id,
        asset_code="alt_signal_bw",
        operation="region_signal",
        params={"seq_id": "chr1", "start": 1, "end": 101, "bins": 2},
        user=owner,
    )

    dataset_domain_service.release_dataset_version(
        db=db_session,
        version_id=version.id,
        request_data=DatasetVersionReleaseRequest(id=version.id, note="release signal bigwig multi-asset"),
        user=owner,
    )
    alt_public_caps = dataset_domain_service.get_public_query_capabilities(dataset.id, asset_code="alt_signal_bw")
    alt_public_result = dataset_domain_service.execute_public_query(
        dataset.id,
        asset_code="alt_signal_bw",
        operation="region_signal",
        params={"seq_id": "chr1", "start": 1, "end": 101, "bins": 2},
    )

    assert default_private_result["data"]["summary"]["value"] == 1.25
    assert alt_private_caps["query_entry_asset"]["id"] == alt_asset.id
    assert alt_private_caps["file_path"] == str(alt_file_path)
    assert alt_private_result["data"]["summary"]["value"] == 7.75
    assert [item["value"] for item in alt_private_result["data"]["items"]] == [7.0, 8.5]
    assert alt_public_caps["query_entry_asset"]["id"] == alt_asset.id
    assert alt_public_result["data"]["summary"]["value"] == 7.75
