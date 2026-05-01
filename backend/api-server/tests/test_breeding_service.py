import os
from pathlib import Path
import sys

import pytest
from openpyxl import Workbook
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from apps.breeding.models import (
    BreedingAssay,
    BreedingBioSample,
    BreedingDataFile,
    BreedingDatasetAssayLink,
    BreedingDatasetSubjectLink,
    BreedingGermplasm,
    BreedingGermplasmImportBatch,
    BreedingGermplasmLineage,
    BreedingMaterial,
    BreedingObservation,
    BreedingPhenotypeSubjectMap,
    BreedingPlot,
    BreedingProgram,
    BreedingTaxonomyCache,
    BreedingTaxonomyName,
    BreedingTaxonomyNode,
    BreedingTaxonomySourceSnapshot,
    BreedingTrial,
    BreedingVariantSampleMap,
)
from apps.breeding.taxonomy_loader import load_taxonomy_dump
from apps.breeding.services import breeding_domain_service
from apps.datasets.models import AssetFile, DatasetAsset, DatasetRegistry, DatasetVersion
from apps.datasets.dataset_model import Dataset
from db.database import Base


BREEDING_CORE_TABLES = [
    Dataset.__table__,
    BreedingProgram.__table__,
    BreedingMaterial.__table__,
    BreedingTaxonomySourceSnapshot.__table__,
    BreedingTaxonomyNode.__table__,
    BreedingTaxonomyName.__table__,
    BreedingTrial.__table__,
    BreedingPlot.__table__,
    BreedingObservation.__table__,
    BreedingBioSample.__table__,
    BreedingAssay.__table__,
    BreedingDataFile.__table__,
    BreedingDatasetSubjectLink.__table__,
    BreedingDatasetAssayLink.__table__,
    BreedingTaxonomyCache.__table__,
    BreedingGermplasmImportBatch.__table__,
    BreedingGermplasm.__table__,
    BreedingGermplasmLineage.__table__,
    BreedingVariantSampleMap.__table__,
    BreedingPhenotypeSubjectMap.__table__,
    DatasetRegistry.__table__,
    DatasetVersion.__table__,
    DatasetAsset.__table__,
    AssetFile.__table__,
]


def make_user(user_id):
    return type("UserStub", (), {"id": user_id})()


def build_rose_germplasm_xlsx(
    path: Path,
    *,
    with_template_comments: bool = False,
    custom_headers: list[str] | None = None,
    data_rows: list[list[str]] | None = None,
):
    workbook = Workbook()
    sheet = workbook.active
    if with_template_comments:
        sheet.append(["#title", "Crop Germplasm Import Template v1"])
        sheet.append(["#description", "Use this worksheet to prepare FAN-CE germplasm import data."])
        sheet.append(["#required", "Columns ID and chinese_name are required."])
        sheet.append(["#custom_fields", "All columns after M_name are treated as batch-level dynamic fields."])
        sheet.append(["#notes", "Rows beginning with # are treated as instructions and ignored by validation."])
    custom_headers = custom_headers or ["育种历史", "花朵性状", "植株特征", "用途"]
    sheet.append(
        [
            "ID",
            "chinese_name",
            "english_name",
            "P",
            "M",
            "P_name",
            "M_name",
            *custom_headers,
        ]
    )
    if data_rows is None:
        data_rows = [
            [
                "RH00004",
                "蓝色奥塔",
                "Outta The Blue",
                "RH00010",
                "RH00011",
                "绿色行星",
                "丽娜",
                "历史1",
                "花朵1",
                "植株1",
                "切花",
            ],
            [
                "RH00010",
                "绿色行星",
                "Green Planet",
                "RH00011",
                "RH00012",
                "丽娜",
                "粉色达芬奇",
                "历史2",
                "花朵2",
                "植株2",
                "展览",
            ],
        ]
    for row in data_rows:
        sheet.append(row)
    workbook.save(path)


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine, tables=BREEDING_CORE_TABLES)
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    session = testing_session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_breeding_service_program_material_trial_plot_flow(db_session):
    user = make_user(1001)

    program = breeding_domain_service.create_program(
        db=db_session,
        request_data=type(
            "ProgramReq",
            (),
            {"model_dump": lambda self, exclude_none=True: {"code": "P1", "name": "Program 1", "status": "active"}},
        )(),
        user=user,
    )
    assert program["code"] == "P1"

    material = breeding_domain_service.create_material(
        db=db_session,
        request_data=type(
            "MaterialReq",
            (),
            {
                "model_dump": lambda self, exclude_none=True: {
                    "program_id": program["id"],
                    "material_code": "M1",
                    "material_name": "Material 1",
                    "material_type": "line",
                    "germplasm_accession": "RH00004",
                    "germplasm_name": "蓝色奥塔",
                    "germplasm_source_file": os.environ.get("TEST_GERMPLASM_FILE", "test_data/germplasm/rose_germplasm_test.xlsx"),
                    "status": "active",
                    "is_check": 0,
                }
            },
        )(),
        user=user,
    )
    assert material["material_code"] == "M1"
    assert material["germplasm_accession"] == "RH00004"

    trial = breeding_domain_service.create_trial(
        db=db_session,
        request_data=type(
            "TrialReq",
            (),
            {
                "model_dump": lambda self, exclude_none=True: {
                    "program_id": program["id"],
                    "trial_code": "T1",
                    "trial_name": "Trial 1",
                    "trial_type": "field",
                    "status": "active",
                }
            },
        )(),
        user=user,
    )
    assert trial["trial_code"] == "T1"

    plot = breeding_domain_service.create_plot(
        db=db_session,
        request_data=type(
            "PlotReq",
            (),
            {
                "model_dump": lambda self, exclude_none=True: {
                    "trial_id": trial["id"],
                    "material_id": material["id"],
                    "plot_code": "PLOT-1",
                    "status": "active",
                }
            },
        )(),
        user=user,
    )
    assert plot["plot_code"] == "PLOT-1"

    program_list = breeding_domain_service.list_programs(
        db=db_session,
        request_data=type("ProgramListReq", (), {"page": 1, "size": 10, "status": "active", "species_name": None, "keyword": "Program"})(),
    )
    assert program_list["total"] == 1
    assert program_list["items"][0]["summary_counts"]["materials"] == 1
    assert program_list["items"][0]["summary_counts"]["trials"] == 1
    assert program_list["items"][0]["summary_counts"]["plots"] == 1
    assert program_list["items"][0]["preview_summary"]["materials"][0]["material_code"] == "M1"

    plot_info = breeding_domain_service.get_plot(db=db_session, plot_id=plot["id"])
    assert plot_info["material_id"] == material["id"]

    germplasm_filtered = breeding_domain_service.list_materials(
        db=db_session,
        request_data=type(
            "MaterialListReq",
            (),
            {"page": 1, "size": 10, "program_id": program["id"], "material_type": None, "status": "active", "keyword": "RH00004"},
        )(),
    )
    assert germplasm_filtered["total"] == 1


def test_breeding_service_update_and_filter(db_session):
    user = make_user(1002)
    program = breeding_domain_service.create_program(
        db=db_session,
        request_data=type(
            "ProgramReq",
            (),
            {"model_dump": lambda self, exclude_none=True: {"code": "P2", "name": "Rose Program", "status": "active"}},
        )(),
        user=user,
    )

    updated = breeding_domain_service.update_program(
        db=db_session,
        program_id=program["id"],
        request_data=type(
            "ProgramUpdateReq",
            (),
            {
                "id": program["id"],
                "model_dump": lambda self, exclude_none=True, exclude=None: {
                    "code": "P2",
                    "name": "Rose Program Updated",
                    "status": "archived",
                },
            },
        )(),
        user=user,
    )
    assert updated["name"] == "Rose Program Updated"

    filtered = breeding_domain_service.list_programs(
        db=db_session,
        request_data=type("ProgramListReq", (), {"page": 1, "size": 10, "status": "archived", "species_name": None, "keyword": "Updated"})(),
    )
    assert filtered["total"] == 1


def test_breeding_service_biosample_assay_data_file_flow(db_session):
    user = make_user(1003)

    program = breeding_domain_service.create_program(
        db=db_session,
        request_data=type("ProgramReq", (), {"model_dump": lambda self, exclude_none=True: {"code": "P3", "name": "Program 3", "status": "active"}})(),
        user=user,
    )
    material = breeding_domain_service.create_material(
        db=db_session,
        request_data=type(
            "MaterialReq",
            (),
            {"model_dump": lambda self, exclude_none=True: {"program_id": program["id"], "material_code": "M3", "material_name": "Material 3", "material_type": "line", "status": "active", "is_check": 0}},
        )(),
        user=user,
    )
    trial = breeding_domain_service.create_trial(
        db=db_session,
        request_data=type(
            "TrialReq",
            (),
            {"model_dump": lambda self, exclude_none=True: {"program_id": program["id"], "trial_code": "T3", "trial_name": "Trial 3", "trial_type": "field", "status": "active"}},
        )(),
        user=user,
    )
    plot = breeding_domain_service.create_plot(
        db=db_session,
        request_data=type(
            "PlotReq",
            (),
            {"model_dump": lambda self, exclude_none=True: {"trial_id": trial["id"], "material_id": material["id"], "plot_code": "PLOT-3", "status": "active"}},
        )(),
        user=user,
    )

    biosample = breeding_domain_service.create_biosample(
        db=db_session,
        request_data=type(
            "BioSampleReq",
            (),
            {"model_dump": lambda self, exclude_none=True: {"sample_code": "BS-001", "material_id": material["id"], "plot_id": plot["id"], "sample_type": "RNA", "status": "active"}},
        )(),
        user=user,
    )
    assert biosample["sample_code"] == "BS-001"

    assay = breeding_domain_service.create_assay(
        db=db_session,
        request_data=type(
            "AssayReq",
            (),
            {"model_dump": lambda self, exclude_none=True: {"assay_code": "AS-001", "biosample_id": biosample["id"], "assay_type": "RNAseq", "platform": "illumina", "status": "active"}},
        )(),
        user=user,
    )
    assert assay["assay_code"] == "AS-001"

    dataset = DatasetRegistry(
        database_id=11,
        dataset_code="expr-1",
        dataset_type="expression",
        version="v1",
        title="expression 1",
        lifecycle_state="draft",
        visibility="private",
        create_time=1,
        update_time=1,
    )
    db_session.add(dataset)
    db_session.commit()
    db_session.refresh(dataset)

    version = DatasetVersion(
        database_id=dataset.database_id,
        version="v1",
        title="v1",
        dataset_type="expression",
        lifecycle_state="draft",
        visibility="private",
        release_state="unreleased",
        create_time=1,
        update_time=1,
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(version)

    asset = DatasetAsset(
        database_id=dataset.database_id,
        dataset_version_id=version.id,
        asset_code="expr_matrix",
        asset_name="expr_matrix",
        asset_type="expression_matrix",
        workflow_state="ready",
        status="active",
        is_required=1,
        is_query_entry=1,
        display_order=0,
        create_time=1,
        update_time=1,
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)

    asset_file = AssetFile(
        database_id=dataset.database_id,
        dataset_asset_id=asset.id,
        file_role="primary",
        file_name="expr.h5",
        storage_uri="file:///tmp/expr.h5",
        local_path="/tmp/expr.h5",
        file_format="h5",
        status="active",
        create_time=1,
        update_time=1,
    )
    db_session.add(asset_file)
    db_session.commit()
    db_session.refresh(asset_file)

    data_file = breeding_domain_service.create_data_file(
        db=db_session,
        request_data=type(
            "DataFileReq",
            (),
            {
                "model_dump": lambda self, exclude_none=True: {
                    "assay_id": assay["id"],
                    "source_mode": "dataset_file",
                    "dataset_id": dataset.id,
                    "version_id": version.id,
                    "asset_id": asset.id,
                    "asset_file_id": asset_file.id,
                    "file_role": "quantification",
                    "file_name": "expr.h5",
                    "status": "active",
                }
            },
        )(),
        user=user,
    )
    assert data_file["file_role"] == "quantification"

    biosample_list = breeding_domain_service.list_biosamples(
        db=db_session,
        request_data=type("BioSampleListReq", (), {"page": 1, "size": 10, "material_id": material["id"], "plot_id": None, "sample_type": "RNA", "status": "active", "keyword": "BS"})(),
    )
    assert biosample_list["total"] == 1

    assay_list = breeding_domain_service.list_assays(
        db=db_session,
        request_data=type("AssayListReq", (), {"page": 1, "size": 10, "biosample_id": biosample["id"], "assay_type": "RNAseq", "platform": "illumina", "status": "active", "keyword": "AS"})(),
    )
    assert assay_list["total"] == 1

    data_file_list = breeding_domain_service.list_data_files(
        db=db_session,
        request_data=type(
            "DataFileListReq",
            (),
            {
                "page": 1,
                "size": 10,
                "assay_id": assay["id"],
                "dataset_id": dataset.id,
                "version_id": version.id,
                "asset_id": asset.id,
                "source_mode": "dataset_file",
                "file_role": "quantification",
                "status": "active",
                "keyword": "expr",
            },
        )(),
    )
    assert data_file_list["total"] == 1

    program_list = breeding_domain_service.list_programs(
        db=db_session,
        request_data=type("ProgramListReq", (), {"page": 1, "size": 10, "status": "active", "species_name": None, "keyword": "Program"})(),
    )
    summary_counts = program_list["items"][0]["summary_counts"]
    assert summary_counts["materials"] == 1
    assert summary_counts["trials"] == 1
    assert summary_counts["plots"] == 1
    assert summary_counts["biosamples"] == 1
    assert summary_counts["assays"] == 1
    assert summary_counts["data_files"] == 1
    preview_summary = program_list["items"][0]["preview_summary"]
    assert preview_summary["materials"][0]["material_code"] == "M3"
    assert preview_summary["assay_types"][0]["assay_type"] == "RNAseq"


def test_breeding_service_link_tables_flow(db_session):
    user = make_user(1004)

    program = breeding_domain_service.create_program(
        db=db_session,
        request_data=type("ProgramReq", (), {"model_dump": lambda self, exclude_none=True: {"code": "P4", "name": "Program 4", "status": "active"}})(),
        user=user,
    )
    material = breeding_domain_service.create_material(
        db=db_session,
        request_data=type(
            "MaterialReq",
            (),
            {"model_dump": lambda self, exclude_none=True: {"program_id": program["id"], "material_code": "M4", "material_name": "Material 4", "material_type": "line", "status": "active", "is_check": 0}},
        )(),
        user=user,
    )
    trial = breeding_domain_service.create_trial(
        db=db_session,
        request_data=type(
            "TrialReq",
            (),
            {"model_dump": lambda self, exclude_none=True: {"program_id": program["id"], "trial_code": "T4", "trial_name": "Trial 4", "trial_type": "field", "status": "active"}},
        )(),
        user=user,
    )
    plot = breeding_domain_service.create_plot(
        db=db_session,
        request_data=type(
            "PlotReq",
            (),
            {"model_dump": lambda self, exclude_none=True: {"trial_id": trial["id"], "material_id": material["id"], "plot_code": "PLOT-4", "status": "active"}},
        )(),
        user=user,
    )
    biosample = breeding_domain_service.create_biosample(
        db=db_session,
        request_data=type(
            "BioSampleReq",
            (),
            {"model_dump": lambda self, exclude_none=True: {"sample_code": "BS-004", "material_id": material["id"], "plot_id": plot["id"], "sample_type": "DNA", "status": "active"}},
        )(),
        user=user,
    )
    assay = breeding_domain_service.create_assay(
        db=db_session,
        request_data=type(
            "AssayReq",
            (),
            {"model_dump": lambda self, exclude_none=True: {"assay_code": "AS-004", "biosample_id": biosample["id"], "assay_type": "genotyping", "status": "active"}},
        )(),
        user=user,
    )

    dataset = DatasetRegistry(
        database_id=12,
        dataset_code="variant-4",
        dataset_type="variant",
        version="v1",
        title="variant 4",
        lifecycle_state="draft",
        visibility="private",
        create_time=1,
        update_time=1,
    )
    db_session.add(dataset)
    db_session.commit()
    db_session.refresh(dataset)

    version = DatasetVersion(
        database_id=dataset.database_id,
        version="v1",
        title="v1",
        dataset_type="variant",
        lifecycle_state="draft",
        visibility="private",
        release_state="unreleased",
        create_time=1,
        update_time=1,
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(version)

    asset = DatasetAsset(
        database_id=dataset.database_id,
        dataset_version_id=version.id,
        asset_code="variant_calls",
        asset_name="variant_calls",
        asset_type="variant_calls",
        workflow_state="ready",
        status="active",
        is_required=1,
        is_query_entry=1,
        display_order=0,
        create_time=1,
        update_time=1,
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)

    subject_link = breeding_domain_service.create_dataset_subject_link(
        db=db_session,
        request_data=type(
            "DatasetSubjectReq",
            (),
            {
                "model_dump": lambda self, exclude_none=True: {
                    "dataset_id": dataset.id,
                    "version_id": version.id,
                    "asset_id": asset.id,
                    "material_id": material["id"],
                    "role": "about",
                    "mapping_status": "reviewed",
                    "mapping_method": "manual",
                    "is_primary": 1,
                }
            },
        )(),
        user=user,
    )
    assert subject_link["material_id"] == material["id"]

    assay_link = breeding_domain_service.create_dataset_assay_link(
        db=db_session,
        request_data=type(
            "DatasetAssayReq",
            (),
            {
                "model_dump": lambda self, exclude_none=True: {
                    "dataset_id": dataset.id,
                    "version_id": version.id,
                    "asset_id": asset.id,
                    "assay_id": assay["id"],
                    "role": "variant_calls",
                    "mapping_status": "reviewed",
                    "mapping_method": "manual",
                    "is_primary": 1,
                }
            },
        )(),
        user=user,
    )
    assert assay_link["assay_id"] == assay["id"]

    variant_map = breeding_domain_service.create_variant_sample_map(
        db=db_session,
        request_data=type(
            "VariantMapReq",
            (),
            {
                "model_dump": lambda self, exclude_none=True: {
                    "dataset_id": dataset.id,
                    "version_id": version.id,
                    "asset_id": asset.id,
                    "vcf_sample_name": "M4",
                    "material_id": material["id"],
                    "mapping_status": "reviewed",
                    "mapping_method": "manual",
                    "is_primary": 1,
                }
            },
        )(),
        user=user,
    )
    assert variant_map["vcf_sample_name"] == "M4"

    phenotype_map = breeding_domain_service.create_phenotype_subject_map(
        db=db_session,
        request_data=type(
            "PhenotypeMapReq",
            (),
            {
                "model_dump": lambda self, exclude_none=True: {
                    "dataset_id": dataset.id,
                    "version_id": version.id,
                    "asset_id": asset.id,
                    "row_key": "sheet1_row1",
                    "trial_id": trial["id"],
                    "plot_id": plot["id"],
                    "material_id": material["id"],
                    "trait_code": "YLD",
                    "mapping_status": "reviewed",
                    "mapping_method": "manual",
                    "is_primary": 1,
                }
            },
        )(),
        user=user,
    )
    assert phenotype_map["row_key"] == "sheet1_row1"

    subject_list = breeding_domain_service.list_dataset_subject_links(
        db=db_session,
        request_data=type(
            "DatasetSubjectListReq",
            (),
            {
                "page": 1,
                "size": 10,
                "dataset_id": dataset.id,
                "version_id": version.id,
                "asset_id": asset.id,
                "material_id": material["id"],
                "plot_id": None,
                "biosample_id": None,
                "role": "about",
                "mapping_status": "reviewed",
                "keyword": None,
            },
        )(),
    )
    assert subject_list["total"] == 1

    assay_list = breeding_domain_service.list_dataset_assay_links(
        db=db_session,
        request_data=type(
            "DatasetAssayListReq",
            (),
            {
                "page": 1,
                "size": 10,
                "dataset_id": dataset.id,
                "version_id": version.id,
                "asset_id": asset.id,
                "assay_id": assay["id"],
                "role": "variant_calls",
                "mapping_status": "reviewed",
                "keyword": None,
            },
        )(),
    )
    assert assay_list["total"] == 1

    variant_list = breeding_domain_service.list_variant_sample_maps(
        db=db_session,
        request_data=type(
            "VariantMapListReq",
            (),
            {
                "page": 1,
                "size": 10,
                "dataset_id": dataset.id,
                "version_id": version.id,
                "asset_id": asset.id,
                "material_id": material["id"],
                "biosample_id": None,
                "plot_id": None,
                "mapping_status": "reviewed",
                "keyword": "M4",
            },
        )(),
    )
    assert variant_list["total"] == 1

    phenotype_list = breeding_domain_service.list_phenotype_subject_maps(
        db=db_session,
        request_data=type(
            "PhenotypeMapListReq",
            (),
            {
                "page": 1,
                "size": 10,
                "dataset_id": dataset.id,
                "version_id": version.id,
                "asset_id": asset.id,
                "trial_id": trial["id"],
                "plot_id": plot["id"],
                "material_id": material["id"],
                "trait_code": "YLD",
                "mapping_status": "reviewed",
                "keyword": "sheet1",
            },
        )(),
    )
    assert phenotype_list["total"] == 1


def test_breeding_service_germplasm_validate_and_commit_flow(db_session, tmp_path):
    user = make_user(1006)
    db_session.add(
        BreedingTaxonomyCache(
            tax_id=74636,
            scientific_name="Rosa chinensis",
            common_name="rose",
            rank="species",
            lineage="Eukaryota; Plantae; Rosaceae; Rosa",
            source="manual",
            is_active=1,
        )
    )
    db_session.commit()

    source_path = tmp_path / "rose_germplasm_test.xlsx"
    build_rose_germplasm_xlsx(source_path)

    validation = breeding_domain_service.validate_germplasm_import(
        db=db_session,
        template_profile="crop_germplasm_v1",
        taxonomy_tax_id=74636,
        source_path=str(source_path),
        source_filename=source_path.name,
        user=user,
    )
    assert validation["summary"]["passed"] is True
    assert validation["summary"]["valid_rows"] == 2
    assert validation["validation_token"]
    assert validation["taxonomy"]["tax_id"] == 74636
    assert [item["source_header"] for item in validation["builtin_fields"]] == [
        "ID",
        "chinese_name",
        "english_name",
        "P",
        "M",
        "P_name",
        "M_name",
    ]
    assert [item["source_header"] for item in validation["dynamic_fields"]] == [
        "育种历史",
        "花朵性状",
        "植株特征",
        "用途",
    ]
    assert validation["dynamic_fields"][0]["field_key"] == "attr_001"

    commit = breeding_domain_service.commit_germplasm_import(
        db=db_session,
        validation_token=validation["validation_token"],
        user=user,
    )
    assert commit["status"] == "imported"
    assert commit["imported_count"] == 2
    assert commit["lineage_edge_count"] == 4

    assert db_session.query(BreedingGermplasmImportBatch).count() == 1
    assert db_session.query(BreedingGermplasm).count() == 2
    assert db_session.query(BreedingGermplasmLineage).count() == 4

    taxonomy_options = breeding_domain_service.list_germplasm_taxonomy_options(
        db=db_session,
        request_data=type(
            "TaxonomyReq",
            (),
            {"keyword": "Rosa", "limit": 20, "active_only": 1},
        )(),
    )
    assert taxonomy_options["total"] == 1
    assert taxonomy_options["items"][0]["germplasm_count"] == 2

    existing_taxonomy_options = breeding_domain_service.list_germplasm_taxonomy_options(
        db=db_session,
        request_data=type(
            "TaxonomyExistingReq",
            (),
            {
                "keyword": None,
                "limit": 20,
                "active_only": 1,
                "tax_id": None,
                "with_germplasm_only": 1,
            },
        )(),
    )
    assert existing_taxonomy_options["source_mode"] == "germplasm"
    assert existing_taxonomy_options["total"] == 1
    assert existing_taxonomy_options["items"][0]["tax_id"] == 74636
    assert existing_taxonomy_options["items"][0]["germplasm_count"] == 2
    germplasm_list = breeding_domain_service.list_germplasms(
        db=db_session,
        request_data=type(
            "GermplasmListReq",
            (),
            {
                "page": 1,
                "size": 10,
                "taxonomy_tax_id": 74636,
                "batch_id": None,
                "status": "active",
                "keyword": "蓝色奥塔",
            },
        )(),
    )
    assert germplasm_list["total"] == 1
    assert germplasm_list["items"][0]["accession_id"] == "RH00004"
    assert germplasm_list["items"][0]["taxonomy"]["tax_id"] == 74636
    assert germplasm_list["items"][0]["attributes"]["育种历史"] == "历史1"
    assert germplasm_list["items"][0]["attributes"]["花朵性状"] == "花朵1"

    germplasm_info = breeding_domain_service.get_germplasm(
        db=db_session,
        accession_id="RH00004",
        taxonomy_tax_id=74636,
    )
    assert germplasm_info["display_name"] == "蓝色奥塔"
    assert germplasm_info["lineage_summary"]["parent_count"] == 2
    assert germplasm_info["taxonomy"]["scientific_name"] == "Rosa chinensis"
    assert germplasm_info["attributes"]["植株特征"] == "植株1"

    batch_list = breeding_domain_service.list_germplasm_import_batches(
        db=db_session,
        request_data=type(
            "BatchListReq",
            (),
            {
                "page": 1,
                "size": 10,
                "taxonomy_tax_id": 74636,
                "status": "imported",
                "keyword": "rose_germplasm_test",
            },
        )(),
    )
    assert batch_list["total"] == 1
    assert batch_list["items"][0]["taxonomy"]["tax_id"] == 74636

    batch_info = breeding_domain_service.get_germplasm_import_batch(
        db=db_session,
        batch_id=batch_list["items"][0]["id"],
    )
    assert batch_info["batch_code"]
    assert batch_info["validation_report"]["summary"]["valid_rows"] == 2
    assert [item["source_header"] for item in batch_info["field_schema"]] == [
        "ID",
        "chinese_name",
        "english_name",
        "P",
        "M",
        "P_name",
        "M_name",
        "育种历史",
        "花朵性状",
        "植株特征",
        "用途",
    ]

    statistics = breeding_domain_service.get_germplasm_statistics(
        db=db_session,
        request_data=type(
            "GermplasmStatsReq",
            (),
            {
                "taxonomy_tax_id": 74636,
                "batch_id": batch_list["items"][0]["id"],
                "status": "active",
            },
        )(),
    )
    assert statistics["node_count"] == 4
    assert statistics["edge_count"] == 4
    assert statistics["connected_components"] == 1

    relationship = breeding_domain_service.get_germplasm_relationship(
        db=db_session,
        request_data=type(
            "GermplasmRelationshipReq",
            (),
            {
                "taxonomy_tax_id": 74636,
                "batch_id": batch_list["items"][0]["id"],
                "accession_id_1": "RH00004",
                "accession_id_2": "RH00010",
            },
        )(),
    )
    assert relationship["exists"] is True
    assert relationship["relationship_type"] == "parent-child"
    assert relationship["direct_edges"][0]["parent_accession"] == "RH00010"

    batch_graph = breeding_domain_service.get_germplasm_batch_relationships(
        db=db_session,
        request_data=type(
            "GermplasmBatchRelationshipReq",
            (),
            {
                "taxonomy_tax_id": 74636,
                "batch_id": batch_list["items"][0]["id"],
                "selected_nodes": ["RH00004"],
                "include_internal": True,
                "include_external": True,
                "max_connections_per_node": 10,
            },
        )(),
    )
    assert batch_graph["summary"]["selected_node_count"] == 1
    assert {node["id"] for node in batch_graph["nodes"]} >= {"RH00004", "RH00010", "RH00011"}
    assert len(batch_graph["edges"]) == 2

    scope = breeding_domain_service.resolve_germplasm_import_scope(
        db=db_session,
        file_path=str(source_path),
    )
    assert scope is not None
    assert scope["batch_id"] == batch_list["items"][0]["id"]
    assert scope["taxonomy_tax_id"] == 74636


def test_breeding_service_taxonomy_sync_and_local_only_search(db_session, monkeypatch):
    remote_record = {
        "tax_id": 74649,
        "scientific_name": "Rosa chinensis",
        "common_name": "China rose",
        "rank": "species",
        "parent_tax_id": 3764,
        "lineage": "cellular organisms; Eukaryota; Viridiplantae; Rosaceae; Rosa",
        "lineage_names": ["Eukaryota", "Viridiplantae", "Rosaceae", "Rosa"],
        "source": "ncbi_sync",
        "is_active": 1,
    }

    import apps.breeding.services as breeding_services_module

    monkeypatch.setattr(
        breeding_services_module.ncbi_taxonomy_client,
        "fetch_taxon",
        lambda tax_id: remote_record if int(tax_id) == 74649 else None,
    )
    monkeypatch.setattr(
        breeding_services_module.ncbi_taxonomy_client,
        "search_taxa",
        lambda keyword, limit=20: [remote_record] if "rosa" in keyword.lower() else [],
    )

    sync_result = breeding_domain_service.sync_germplasm_taxonomy_cache(
        db=db_session,
        request_data=type(
            "TaxonomySyncReq",
            (),
            {"tax_id": 74649, "keyword": None, "limit": 20, "active_only": 1, "force_refresh": 1},
        )(),
    )
    assert sync_result["total"] == 1
    assert sync_result["items"][0]["tax_id"] == 74649

    cached = db_session.query(BreedingTaxonomyCache).filter(BreedingTaxonomyCache.tax_id == 74649).first()
    assert cached is not None
    assert cached.scientific_name == "Rosa chinensis"
    assert cached.source == "ncbi_sync"

    db_session.query(BreedingTaxonomyCache).filter(BreedingTaxonomyCache.tax_id == 74649).delete()
    db_session.commit()

    search_result = breeding_domain_service.list_germplasm_taxonomy_options(
        db=db_session,
        request_data=type(
            "TaxonomySearchReq",
            (),
            {"keyword": "Rosa chinensis", "limit": 20, "active_only": 1},
        )(),
    )
    assert search_result["total"] == 0
    assert search_result["source_mode"] == "cache"


def test_breeding_service_germplasm_template_supports_comment_rows_and_legacy_alias(db_session, tmp_path):
    user = make_user(1007)
    db_session.add(
        BreedingTaxonomyCache(
            tax_id=74649,
            scientific_name="Rosa chinensis",
            common_name="China rose",
            rank="species",
            lineage="Eukaryota; Plantae; Rosaceae; Rosa",
            source="manual",
            is_active=1,
        )
    )
    db_session.commit()

    source_path = tmp_path / "crop_germplasm_template.xlsx"
    build_rose_germplasm_xlsx(source_path, with_template_comments=True)

    validation = breeding_domain_service.validate_germplasm_import(
        db=db_session,
        template_profile="rose_germplasm_v1",
        taxonomy_tax_id=74649,
        source_path=str(source_path),
        source_filename=source_path.name,
        user=user,
    )

    assert validation["summary"]["passed"] is True
    assert validation["summary"]["template_profile"] == "crop_germplasm_v1"
    assert validation["template_profile"] == "crop_germplasm_v1"
    assert validation["summary"]["valid_rows"] == 2
    assert validation["dynamic_fields"][0]["source_header"] == "育种历史"


def test_breeding_service_germplasm_template_accepts_arbitrary_dynamic_headers(db_session, tmp_path):
    user = make_user(1008)
    db_session.add(
        BreedingTaxonomyCache(
            tax_id=3702,
            scientific_name="Arabidopsis thaliana",
            common_name="thale cress",
            rank="species",
            lineage="Eukaryota; Plantae; Brassicaceae; Arabidopsis",
            source="manual",
            is_active=1,
        )
    )
    db_session.commit()

    source_path = tmp_path / "crop_germplasm_dynamic_headers.xlsx"
    build_rose_germplasm_xlsx(
        source_path,
        custom_headers=["flower_color", "collector_note", "trait_score"],
        data_rows=[
            [
                "AT-G-001",
                "哥伦比亚",
                "Col-0",
                "AT-G-010",
                "AT-G-011",
                "Parent A",
                "Parent B",
                "white",
                "field observation",
                "8.5",
            ]
        ],
    )

    validation = breeding_domain_service.validate_germplasm_import(
        db=db_session,
        template_profile="crop_germplasm_v1",
        taxonomy_tax_id=3702,
        source_path=str(source_path),
        source_filename=source_path.name,
        user=user,
    )

    assert validation["summary"]["passed"] is True
    assert validation["summary"]["warning_rows"] == 0
    assert [item["source_header"] for item in validation["dynamic_fields"]] == [
        "flower_color",
        "collector_note",
        "trait_score",
    ]
    assert validation["preview_rows"][0]["accession_id"] == "AT-G-001"


def test_breeding_service_germplasm_template_rejects_blank_header_columns_with_data(db_session, tmp_path):
    user = make_user(1009)
    db_session.add(
        BreedingTaxonomyCache(
            tax_id=3885,
            scientific_name="Pisum sativum",
            common_name="pea",
            rank="species",
            lineage="Eukaryota; Plantae; Fabaceae; Pisum",
            source="manual",
            is_active=1,
        )
    )
    db_session.commit()

    source_path = tmp_path / "crop_germplasm_blank_header.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["#title", "Crop Germplasm Import Template v1"])
    sheet.append(["ID", "chinese_name", "english_name", "P", "M", "P_name", "M_name", "", "remark"])
    sheet.append(["PEA-001", "豌豆材料1", "Pea line 1", "", "", "", "", "should_fail", "ok"])
    workbook.save(source_path)

    validation = breeding_domain_service.validate_germplasm_import(
        db=db_session,
        template_profile="crop_germplasm_v1",
        taxonomy_tax_id=3885,
        source_path=str(source_path),
        source_filename=source_path.name,
        user=user,
    )

    assert validation["summary"]["passed"] is False
    assert any(issue["error_code"] == "blank_header_with_data" for issue in validation["errors"])


def test_breeding_service_delete_germplasm_import_batch_removes_related_records(db_session, tmp_path):
    user = make_user(1010)
    db_session.add(
        BreedingTaxonomyCache(
            tax_id=4530,
            scientific_name="Oryza sativa",
            common_name="rice",
            rank="species",
            lineage="Eukaryota; Plantae; Poaceae; Oryza",
            source="manual",
            is_active=1,
        )
    )
    db_session.commit()

    source_path = tmp_path / "rice_germplasm_test.xlsx"
    build_rose_germplasm_xlsx(
        source_path,
        custom_headers=["trait_source", "grain_type"],
        data_rows=[
            ["RICE0001", "籼稻材料1", "Rice Line 1", "RICE0101", "RICE0102", "Parent 1", "Parent 2", "field", "indica"],
            ["RICE0002", "籼稻材料2", "Rice Line 2", "RICE0103", "RICE0104", "Parent 3", "Parent 4", "lab", "japonica"],
        ],
    )

    validation = breeding_domain_service.validate_germplasm_import(
        db=db_session,
        template_profile="crop_germplasm_v1",
        taxonomy_tax_id=4530,
        source_path=str(source_path),
        source_filename=source_path.name,
        user=user,
    )
    commit = breeding_domain_service.commit_germplasm_import(
        db=db_session,
        validation_token=validation["validation_token"],
        user=user,
    )

    batch_id = commit["batch_id"]
    assert db_session.query(BreedingGermplasm).filter(BreedingGermplasm.batch_id == batch_id).count() == 2
    assert db_session.query(BreedingGermplasmLineage).filter(BreedingGermplasmLineage.batch_id == batch_id).count() == 4

    delete_result = breeding_domain_service.delete_germplasm_import_batch(
        db=db_session,
        batch_id=batch_id,
        user=user,
    )

    assert delete_result["status"] == "deleted"
    assert delete_result["deleted_germplasm_count"] == 2
    assert delete_result["deleted_lineage_count"] == 4
    assert db_session.query(BreedingGermplasm).filter(BreedingGermplasm.batch_id == batch_id).count() == 0
    assert db_session.query(BreedingGermplasmLineage).filter(BreedingGermplasmLineage.batch_id == batch_id).count() == 0
    batch = db_session.query(BreedingGermplasmImportBatch).filter(BreedingGermplasmImportBatch.id == batch_id).first()
    assert batch is not None
    assert batch.status == "deleted"


def test_breeding_service_taxonomy_audit(db_session, monkeypatch):
    cache_rows = [
        BreedingTaxonomyCache(
            tax_id=74636,
            scientific_name="Rosa chinensis",
            common_name="China rose",
            rank="species",
            parent_tax_id=3764,
            lineage="cellular organisms; Eukaryota; Viridiplantae; Rosaceae; Rosa",
            source="manual",
            is_active=1,
        ),
        BreedingTaxonomyCache(
            tax_id=74649,
            scientific_name="Rosa chinensis",
            common_name="China rose",
            rank="species",
            parent_tax_id=3764,
            lineage="cellular organisms; Eukaryota; Viridiplantae; Rosaceae; Rosa",
            source="ncbi_sync",
            is_active=1,
        ),
        BreedingTaxonomyCache(
            tax_id=999999,
            scientific_name="Unknown rose",
            common_name=None,
            rank="species",
            parent_tax_id=3764,
            lineage="cellular organisms; Eukaryota",
            source="manual",
            is_active=1,
        ),
        BreedingTaxonomyCache(
            tax_id=888888,
            scientific_name="Broken taxonomy",
            common_name=None,
            rank="species",
            parent_tax_id=3764,
            lineage="cellular organisms; Eukaryota",
            source="manual",
            is_active=1,
        ),
    ]
    db_session.add_all(cache_rows)
    db_session.flush()

    batch = BreedingGermplasmImportBatch(
        batch_code="BATCH-AUDIT-1",
        template_profile="rose_core",
        taxonomy_tax_id=74636,
        taxonomy_name_snapshot="Rosa chinensis",
        source_filename="rose.xlsx",
        source_file_path="/tmp/rose.xlsx",
        status="committed",
        total_rows=1,
        valid_rows=1,
        error_rows=0,
        warning_rows=0,
    )
    db_session.add(batch)
    db_session.flush()
    db_session.add(
        BreedingGermplasm(
            batch_id=batch.id,
            taxonomy_tax_id=74636,
            accession_id="RH-AUDIT-01",
            display_name="Audit Rose",
            status="active",
        )
    )
    db_session.commit()

    def fake_fetch_taxon(tax_id):
        tax_id = int(tax_id)
        if tax_id == 74636:
            return {
                "tax_id": 74636,
                "scientific_name": "Rosa rubiginosa",
                "common_name": "Sweet briar",
                "rank": "species",
                "parent_tax_id": 3764,
                "lineage": "cellular organisms; Eukaryota; Viridiplantae; Rosaceae; Rosa",
                "source": "ncbi_sync",
            }
        if tax_id == 74649:
            return {
                "tax_id": 74649,
                "scientific_name": "Rosa chinensis",
                "common_name": "China rose",
                "rank": "species",
                "parent_tax_id": 3764,
                "lineage": "cellular organisms; Eukaryota; Viridiplantae; Rosaceae; Rosa",
                "source": "ncbi_sync",
            }
        if tax_id == 999999:
            return None
        if tax_id == 888888:
            raise RuntimeError("ncbi timeout")
        return None

    import apps.breeding.services as breeding_services_module

    monkeypatch.setattr(
        breeding_services_module.ncbi_taxonomy_client,
        "fetch_taxon",
        fake_fetch_taxon,
    )

    audit_result = breeding_domain_service.audit_germplasm_taxonomy_cache(
        db=db_session,
        request_data=type(
            "TaxonomyAuditReq",
            (),
            {"tax_id": None, "keyword": None, "limit": 20, "active_only": 1},
        )(),
    )
    assert audit_result["total"] == 4
    assert audit_result["summary"] == {
        "matched": 1,
        "mismatch": 1,
        "not_found": 1,
        "error": 1,
    }

    audit_map = {item["tax_id"]: item for item in audit_result["items"]}
    assert audit_map[74636]["status"] == "mismatch"
    assert audit_map[74636]["germplasm_count"] == 1
    assert {entry["field"] for entry in audit_map[74636]["mismatches"]} >= {"scientific_name", "common_name"}
    assert audit_map[74649]["status"] == "matched"
    assert audit_map[999999]["status"] == "not_found"
    assert audit_map[888888]["status"] == "error"


def test_breeding_service_local_taxonomy_dump_search_and_projection(db_session, tmp_path):
    dump_dir = tmp_path / "taxdump"
    dump_dir.mkdir()
    (dump_dir / "nodes.dmp").write_text(
        "1\t|\t1\t|\tno rank\t|\n"
        "2759\t|\t1\t|\tsuperkingdom\t|\n"
        "33090\t|\t2759\t|\tkingdom\t|\n"
        "3745\t|\t33090\t|\tgenus\t|\n"
        "74649\t|\t3745\t|\tspecies\t|\n",
        encoding="utf-8",
    )
    (dump_dir / "names.dmp").write_text(
        "1\t|\troot\t|\t\t|\tscientific name\t|\n"
        "2759\t|\tEukaryota\t|\t\t|\tscientific name\t|\n"
        "33090\t|\tViridiplantae\t|\t\t|\tscientific name\t|\n"
        "3745\t|\tRosa\t|\t\t|\tscientific name\t|\n"
        "74649\t|\tRosa chinensis\t|\t\t|\tscientific name\t|\n"
        "74649\t|\tChina rose\t|\t\t|\tcommon name\t|\n"
        "74649\t|\t月季\t|\t\t|\tsynonym\t|\n",
        encoding="utf-8",
    )

    load_taxonomy_dump(
        db=db_session,
        dump_path=str(dump_dir),
        source_name="ncbi_taxdump",
        source_version="test-1",
        reset_existing=True,
    )

    options = breeding_domain_service.list_germplasm_taxonomy_options(
        db=db_session,
        request_data=type(
            "TaxonomySearchReq",
            (),
            {"keyword": "月季", "limit": 20, "active_only": 1, "tax_id": None},
        )(),
    )
    assert options["source_mode"] == "local_dump"
    assert options["total"] == 1
    assert options["items"][0]["tax_id"] == 74649
    assert options["items"][0]["scientific_name"] == "Rosa chinensis"
    assert "Viridiplantae" in (options["items"][0]["lineage"] or "")

    projected_cache = db_session.query(BreedingTaxonomyCache).filter(BreedingTaxonomyCache.tax_id == 74649).first()
    assert projected_cache is not None
    assert projected_cache.source == "local_dump"


def test_breeding_service_program_overview_and_program_scoped_lists(db_session):
    user = make_user(1005)

    program = breeding_domain_service.create_program(
        db=db_session,
        request_data=type("ProgramReq", (), {"model_dump": lambda self, exclude_none=True: {"code": "P5", "name": "Program 5", "status": "active"}})(),
        user=user,
    )
    other_program = breeding_domain_service.create_program(
        db=db_session,
        request_data=type("ProgramReq", (), {"model_dump": lambda self, exclude_none=True: {"code": "P6", "name": "Program 6", "status": "active"}})(),
        user=user,
    )

    material = breeding_domain_service.create_material(
        db=db_session,
        request_data=type(
            "MaterialReq",
            (),
            {"model_dump": lambda self, exclude_none=True: {"program_id": program["id"], "material_code": "M5", "material_name": "Material 5", "material_type": "line", "status": "active", "is_check": 0}},
        )(),
        user=user,
    )
    breeding_domain_service.create_material(
        db=db_session,
        request_data=type(
            "MaterialReq",
            (),
            {"model_dump": lambda self, exclude_none=True: {"program_id": other_program["id"], "material_code": "M6", "material_name": "Material 6", "material_type": "line", "status": "active", "is_check": 0}},
        )(),
        user=user,
    )

    trial = breeding_domain_service.create_trial(
        db=db_session,
        request_data=type(
            "TrialReq",
            (),
            {"model_dump": lambda self, exclude_none=True: {"program_id": program["id"], "trial_code": "T5", "trial_name": "Trial 5", "trial_type": "field", "status": "active"}},
        )(),
        user=user,
    )
    plot = breeding_domain_service.create_plot(
        db=db_session,
        request_data=type(
            "PlotReq",
            (),
            {"model_dump": lambda self, exclude_none=True: {"trial_id": trial["id"], "material_id": material["id"], "plot_code": "PLOT-5", "status": "active"}},
        )(),
        user=user,
    )
    breeding_domain_service.create_observation(
        db=db_session,
        request_data=type(
            "ObservationReq",
            (),
            {
                "model_dump": lambda self, exclude_none=True: {
                    "trial_id": trial["id"],
                    "plot_id": plot["id"],
                    "material_id": material["id"],
                    "observation_level": "plot",
                    "trait_code": "PETAL_COUNT_2023",
                    "trait_name": "2023年花瓣数量",
                    "obs_value_num": 37.33,
                    "obs_date": "2023-05-20",
                    "qc_status": "reviewed",
                    "source_row_key": "RH00013",
                }
            },
        )(),
        user=user,
    )
    biosample = breeding_domain_service.create_biosample(
        db=db_session,
        request_data=type(
            "BioSampleReq",
            (),
            {"model_dump": lambda self, exclude_none=True: {"sample_code": "BS-005", "material_id": material["id"], "plot_id": plot["id"], "sample_type": "RNA", "status": "active"}},
        )(),
        user=user,
    )
    assay = breeding_domain_service.create_assay(
        db=db_session,
        request_data=type(
            "AssayReq",
            (),
            {"model_dump": lambda self, exclude_none=True: {"assay_code": "AS-005", "biosample_id": biosample["id"], "assay_type": "RNAseq", "status": "active"}},
        )(),
        user=user,
    )

    dataset = DatasetRegistry(
        database_id=13,
        dataset_code="expr-5",
        dataset_type="transcriptome",
        version="v1",
        title="expression 5",
        lifecycle_state="draft",
        visibility="private",
        create_time=1,
        update_time=1,
    )
    db_session.add(dataset)
    db_session.commit()
    db_session.refresh(dataset)

    version = DatasetVersion(
        database_id=dataset.database_id,
        version="v1",
        title="v1",
        dataset_type="transcriptome",
        lifecycle_state="draft",
        visibility="private",
        release_state="unreleased",
        create_time=1,
        update_time=1,
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(version)

    asset = DatasetAsset(
        database_id=dataset.database_id,
        dataset_version_id=version.id,
        asset_code="expr_matrix",
        asset_name="expr_matrix",
        asset_type="expression_matrix",
        workflow_state="ready",
        status="active",
        is_required=1,
        is_query_entry=1,
        display_order=0,
        create_time=1,
        update_time=1,
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)

    asset_file = AssetFile(
        database_id=dataset.database_id,
        dataset_asset_id=asset.id,
        file_role="primary",
        file_name="expr5.h5",
        storage_uri="file:///tmp/expr5.h5",
        local_path="/tmp/expr5.h5",
        file_format="h5",
        status="active",
        create_time=1,
        update_time=1,
    )
    db_session.add(asset_file)
    db_session.commit()
    db_session.refresh(asset_file)

    breeding_domain_service.create_data_file(
        db=db_session,
        request_data=type(
            "DataFileReq",
            (),
            {
                "model_dump": lambda self, exclude_none=True: {
                    "assay_id": assay["id"],
                    "source_mode": "dataset_file",
                    "dataset_id": dataset.id,
                    "version_id": version.id,
                    "asset_id": asset.id,
                    "asset_file_id": asset_file.id,
                    "file_role": "quantification",
                    "file_name": "expr5.h5",
                    "status": "active",
                }
            },
        )(),
        user=user,
    )
    breeding_domain_service.create_dataset_subject_link(
        db=db_session,
        request_data=type(
            "DatasetSubjectReq",
            (),
            {
                "model_dump": lambda self, exclude_none=True: {
                    "dataset_id": dataset.id,
                    "version_id": version.id,
                    "asset_id": asset.id,
                    "material_id": material["id"],
                    "role": "about",
                    "mapping_status": "reviewed",
                    "mapping_method": "manual",
                    "is_primary": 1,
                }
            },
        )(),
        user=user,
    )
    breeding_domain_service.create_dataset_assay_link(
        db=db_session,
        request_data=type(
            "DatasetAssayReq",
            (),
            {
                "model_dump": lambda self, exclude_none=True: {
                    "dataset_id": dataset.id,
                    "version_id": version.id,
                    "asset_id": asset.id,
                    "assay_id": assay["id"],
                    "role": "expression_matrix",
                    "mapping_status": "reviewed",
                    "mapping_method": "manual",
                    "is_primary": 1,
                }
            },
        )(),
        user=user,
    )

    overview = breeding_domain_service.get_program_overview(db=db_session, program_id=program["id"])
    assert overview["counts"]["materials"] == 1
    assert overview["counts"]["trials"] == 1
    assert overview["counts"]["plots"] == 1
    assert overview["counts"]["observations"] == 1
    assert overview["counts"]["biosamples"] == 1
    assert overview["counts"]["assays"] == 1
    assert overview["counts"]["data_files"] == 1
    assert overview["counts"]["dataset_subject_links"] == 1
    assert overview["counts"]["dataset_assay_links"] == 1
    assert overview["counts"]["dataset_links"] == 2

    plot_list = breeding_domain_service.list_plots(
        db=db_session,
        request_data=type("PlotListReq", (), {"page": 1, "size": 10, "program_id": program["id"], "trial_id": None, "material_id": None, "replicate_no": None, "block_no": None, "status": "active", "keyword": "PLOT"})(),
    )
    observation_list = breeding_domain_service.list_observations(
        db=db_session,
        request_data=type(
            "ObservationListReq",
            (),
            {
                "page": 1,
                "size": 10,
                "program_id": program["id"],
                "trial_id": None,
                "plot_id": None,
                "material_id": None,
                "trait_code": "PETAL_COUNT_2023",
                "qc_status": "reviewed",
                "keyword": "RH00013",
            },
        )(),
    )
    biosample_list = breeding_domain_service.list_biosamples(
        db=db_session,
        request_data=type("BioSampleListReq", (), {"page": 1, "size": 10, "program_id": program["id"], "material_id": None, "plot_id": None, "sample_type": "RNA", "status": "active", "keyword": "BS-005"})(),
    )
    assay_list = breeding_domain_service.list_assays(
        db=db_session,
        request_data=type("AssayListReq", (), {"page": 1, "size": 10, "program_id": program["id"], "biosample_id": None, "assay_type": "RNAseq", "platform": None, "status": "active", "keyword": "AS-005"})(),
    )
    data_file_list = breeding_domain_service.list_data_files(
        db=db_session,
        request_data=type(
            "DataFileListReq",
            (),
            {
                "page": 1,
                "size": 10,
                "program_id": program["id"],
                "assay_id": None,
                "dataset_id": None,
                "version_id": None,
                "asset_id": None,
                "source_mode": "dataset_file",
                "file_role": "quantification",
                "status": "active",
                "keyword": "expr5",
            },
        )(),
    )

    assert plot_list["total"] == 1
    assert observation_list["total"] == 1
    assert biosample_list["total"] == 1
    assert assay_list["total"] == 1
    assert data_file_list["total"] == 1
