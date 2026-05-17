import os
from pathlib import Path
import sys

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import modules.breeding.init as breeding_init_module
from modules.breeding.models import (
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
    BreedingTaxonomyName,
    BreedingTaxonomyNode,
    BreedingTrial,
    BreedingVariantSampleMap,
)
from modules.datasets.models import AssetFile, DatasetAsset, DatasetRegistry, DatasetVersion
from shared.database import Base


DATASET_CORE_TABLES = [
    DatasetRegistry.__table__,
    DatasetVersion.__table__,
    DatasetAsset.__table__,
    AssetFile.__table__,
]

BREEDING_TABLES = [
    BreedingProgram.__table__,
    BreedingMaterial.__table__,
    BreedingTaxonomyNode.__table__,
    BreedingTaxonomyName.__table__,
    BreedingGermplasmImportBatch.__table__,
    BreedingGermplasm.__table__,
    BreedingGermplasmLineage.__table__,
    BreedingTrial.__table__,
    BreedingPlot.__table__,
    BreedingObservation.__table__,
    BreedingBioSample.__table__,
    BreedingAssay.__table__,
    BreedingDataFile.__table__,
    BreedingDatasetSubjectLink.__table__,
    BreedingDatasetAssayLink.__table__,
    BreedingVariantSampleMap.__table__,
    BreedingPhenotypeSubjectMap.__table__,
]


@pytest.fixture()
def db_engine(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine, tables=DATASET_CORE_TABLES)
    monkeypatch.setattr(breeding_init_module, "engine", engine)
    breeding_init_module.init_breeding_tables()
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


def test_breeding_init_creates_all_tables_and_supports_minimal_chain(db_engine, db_session):
    table_names = set(inspect(db_engine).get_table_names())
    for table in BREEDING_TABLES:
        assert table.name in table_names
    material_columns = {column["name"] for column in inspect(db_engine).get_columns("brd_material")}
    assert "germplasm_accession" in material_columns
    assert "germplasm_name" in material_columns
    assert "germplasm_source_file" in material_columns

    dataset = DatasetRegistry(
        database_id=1,
        dataset_code="rose-variant",
        dataset_type="variant",
        version="v1",
        title="rose variant dataset",
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
        asset_code="vcf_primary",
        asset_name="vcf_primary",
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

    asset_file = AssetFile(
        database_id=dataset.database_id,
        dataset_asset_id=asset.id,
        file_role="primary",
        file_name="rose.vcf.gz",
        storage_uri="file:///tmp/rose.vcf.gz",
        local_path="/tmp/rose.vcf.gz",
        file_format="vcf.gz",
        status="active",
        create_time=1,
        update_time=1,
    )
    db_session.add(asset_file)
    db_session.commit()
    db_session.refresh(asset_file)

    program = BreedingProgram(code="rose-program", name="Rose Program", status="active")
    db_session.add(program)
    db_session.commit()
    db_session.refresh(program)

    material = BreedingMaterial(
        program_id=program.id,
        material_code="ROSE-001",
        material_name="Rose Line 001",
        material_type="line",
        germplasm_accession="RH00004",
        germplasm_name="蓝色奥塔",
        germplasm_source_file=os.environ.get("TEST_GERMPLASM_FILE", "test_data/germplasm/rose_germplasm_test.xlsx"),
        status="active",
        is_check=0,
    )
    db_session.add(material)
    db_session.commit()
    db_session.refresh(material)

    trial = BreedingTrial(
        program_id=program.id,
        trial_code="TRIAL-001",
        trial_name="Rose Trial",
        trial_type="field",
        status="active",
    )
    db_session.add(trial)
    db_session.commit()
    db_session.refresh(trial)

    plot = BreedingPlot(
        trial_id=trial.id,
        material_id=material.id,
        plot_code="PLOT-001",
        status="active",
    )
    db_session.add(plot)
    db_session.commit()
    db_session.refresh(plot)

    observation = BreedingObservation(
        trial_id=trial.id,
        plot_id=plot.id,
        material_id=material.id,
        observation_level="plot",
        trait_code="YLD",
        obs_value_num=1.23,
        qc_status="draft",
        source_dataset_id=dataset.id,
        source_version_id=version.id,
        source_asset_id=asset.id,
    )
    db_session.add(observation)

    biosample = BreedingBioSample(
        sample_code="SAMPLE-001",
        material_id=material.id,
        plot_id=plot.id,
        status="active",
    )
    db_session.add(biosample)
    db_session.commit()
    db_session.refresh(biosample)

    assay = BreedingAssay(
        assay_code="ASSAY-001",
        biosample_id=biosample.id,
        assay_type="genotyping",
        status="active",
    )
    db_session.add(assay)
    db_session.commit()
    db_session.refresh(assay)

    db_session.add(
        BreedingDataFile(
            assay_id=assay.id,
            source_mode="dataset_file",
            dataset_id=dataset.id,
            version_id=version.id,
            asset_id=asset.id,
            asset_file_id=asset_file.id,
            file_role="variant_calls",
            file_name="rose.vcf.gz",
            status="active",
        )
    )
    db_session.add(
        BreedingDatasetSubjectLink(
            dataset_id=dataset.id,
            version_id=version.id,
            asset_id=asset.id,
            material_id=material.id,
            role="about",
            mapping_status="reviewed",
            mapping_method="manual",
            is_primary=1,
        )
    )
    db_session.add(
        BreedingDatasetAssayLink(
            dataset_id=dataset.id,
            version_id=version.id,
            asset_id=asset.id,
            assay_id=assay.id,
            role="variant_calls",
            mapping_status="reviewed",
            mapping_method="manual",
            is_primary=1,
        )
    )
    db_session.add(
        BreedingVariantSampleMap(
            dataset_id=dataset.id,
            version_id=version.id,
            asset_id=asset.id,
            vcf_sample_name="ROSE-001",
            material_id=material.id,
            mapping_status="reviewed",
            mapping_method="manual",
            is_primary=1,
        )
    )
    db_session.add(
        BreedingPhenotypeSubjectMap(
            dataset_id=dataset.id,
            version_id=version.id,
            asset_id=asset.id,
            row_key="sheet1_row1",
            trial_id=trial.id,
            plot_id=plot.id,
            material_id=material.id,
            trait_code="YLD",
            mapping_status="reviewed",
            mapping_method="manual",
            is_primary=1,
        )
    )
    db_session.commit()

    assert db_session.query(BreedingProgram).count() == 1
    assert db_session.query(BreedingObservation).count() == 1
    assert db_session.query(BreedingDatasetSubjectLink).count() == 1


def test_germplasm_phase1_tables_support_basic_records_and_uniqueness(db_session):
    taxonomy = BreedingTaxonomyNode(
        tax_id=74636,
        scientific_name="Rosa chinensis",
        common_name="rose",
        rank="species",
        lineage="Eukaryota; Plantae; Rosaceae; Rosa",
        lineage_ids=[],
        source="manual",
        is_active=1,
    )
    db_session.add(taxonomy)
    db_session.commit()

    batch = BreedingGermplasmImportBatch(
        batch_code="GIP-20260405-001",
        template_profile="crop_germplasm_v1",
        taxonomy_tax_id=taxonomy.tax_id,
        taxonomy_name_snapshot="Rosa chinensis",
        source_filename="rose_germplasm_test.xlsx",
        source_file_path="/tmp/rose_germplasm_test.xlsx",
        status="imported",
        total_rows=10,
        valid_rows=10,
        error_rows=0,
        warning_rows=0,
        field_schema_json='[{"field_key":"attr_001","source_header":"育种历史"}]',
    )
    db_session.add(batch)
    db_session.commit()
    db_session.refresh(batch)

    germplasm = BreedingGermplasm(
        batch_id=batch.id,
        taxonomy_tax_id=taxonomy.tax_id,
        accession_id="RH00004",
        display_name="蓝色奥塔",
        scientific_name_snapshot="Rosa chinensis",
        common_name_snapshot="rose",
        english_name="Outta The Blue",
        father_accession="RH00010",
        mother_accession="RH00011",
        father_name_snapshot="绿色行星",
        mother_name_snapshot="丽娜",
        source_row_no=2,
        status="active",
        attributes_json='{"用途":"切花"}',
        search_text="RH00004 蓝色奥塔 Outta The Blue RH00010 RH00011",
    )
    db_session.add(germplasm)
    db_session.commit()

    lineage = BreedingGermplasmLineage(
        taxonomy_tax_id=taxonomy.tax_id,
        child_accession="RH00004",
        parent_accession="RH00010",
        parent_role="father",
        batch_id=batch.id,
        source_row_no=2,
    )
    db_session.add(lineage)
    db_session.commit()

    assert db_session.query(BreedingTaxonomyNode).count() == 1
    assert db_session.query(BreedingGermplasmImportBatch).count() == 1
    assert db_session.query(BreedingGermplasm).count() == 1
    assert db_session.query(BreedingGermplasmLineage).count() == 1

    db_session.add(
        BreedingGermplasm(
            batch_id=batch.id,
            taxonomy_tax_id=taxonomy.tax_id,
            accession_id="RH00004",
            display_name="蓝色奥塔重复",
            status="active",
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    db_session.add(
        BreedingGermplasmLineage(
            taxonomy_tax_id=taxonomy.tax_id,
            child_accession="RH00004",
            parent_accession="RH00010",
            parent_role="father",
            batch_id=batch.id,
            source_row_no=2,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_dataset_subject_link_requires_exactly_one_subject(db_session):
    dataset = DatasetRegistry(
        database_id=2,
        dataset_code="rose-phenotype",
        dataset_type="phenotype",
        version="v1",
        title="rose phenotype dataset",
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
        dataset_type="phenotype",
        lifecycle_state="draft",
        visibility="private",
        release_state="unreleased",
        create_time=1,
        update_time=1,
    )
    db_session.add(version)
    db_session.commit()
    db_session.refresh(version)

    program = BreedingProgram(code="rose-program-2", name="Rose Program 2", status="active")
    db_session.add(program)
    db_session.commit()
    db_session.refresh(program)

    material = BreedingMaterial(
        program_id=program.id,
        material_code="ROSE-002",
        material_name="Rose Line 002",
        material_type="line",
        status="active",
        is_check=0,
    )
    db_session.add(material)
    db_session.commit()
    db_session.refresh(material)

    db_session.add(
        BreedingDatasetSubjectLink(
            dataset_id=dataset.id,
            version_id=version.id,
            program_id=program.id,
            material_id=material.id,
            role="about",
            mapping_status="draft",
            mapping_method="manual",
            is_primary=1,
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
