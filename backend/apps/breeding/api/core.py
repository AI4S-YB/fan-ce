from fastapi import APIRouter, Depends, File, Form, UploadFile

from apps.common.depends import ensure_taxonomy_ready, get_active_user
from db.database import get_db
from libs.responses.response import response_200, response_403, response_404

from ..germplasm_import import persist_uploaded_excel
from ..schemas import (
    BreedingAssayCreateRequest,
    BreedingDatasetAssayLinkCreateRequest,
    BreedingDatasetAssayLinkListRequest,
    BreedingDatasetAssayLinkUpdateRequest,
    BreedingDatasetSubjectLinkCreateRequest,
    BreedingDatasetSubjectLinkListRequest,
    BreedingDatasetSubjectLinkUpdateRequest,
    BreedingAssayListRequest,
    BreedingAssayUpdateRequest,
    BreedingBioSampleCreateRequest,
    BreedingBioSampleListRequest,
    BreedingBioSampleUpdateRequest,
    BreedingDataFileCreateRequest,
    BreedingDataFileListRequest,
    BreedingDataFileUpdateRequest,
    BreedingGermplasmImportCommitRequest,
    BreedingGermplasmImportBatchDeleteRequest,
    BreedingGermplasmImportBatchListRequest,
    BreedingGermplasmInfoRequest,
    BreedingGermplasmBatchRelationshipRequest,
    BreedingGermplasmListRequest,
    BreedingGermplasmRelationshipRequest,
    BreedingGermplasmStatisticsRequest,
    BreedingGermplasmSetPublicRequest,
    BreedingGermplasmBatchSetPublicRequest,
    BreedingGermplasmTaxonomySearchRequest,
    BreedingGermplasmTaxonomyAuditRequest,
    BreedingGermplasmTaxonomySyncRequest,
    BreedingPhenotypeSubjectMapCreateRequest,
    BreedingPhenotypeSubjectMapListRequest,
    BreedingPhenotypeSubjectMapUpdateRequest,
    BreedingInfoRequest,
    BreedingMaterialCreateRequest,
    BreedingMaterialListRequest,
    BreedingMaterialUpdateRequest,
    LinkDatasetRequest,
    ProgramDatasetsRequest,
    BreedingObservationCreateRequest,
    BreedingObservationListRequest,
    BreedingObservationUpdateRequest,
    BreedingPlotCreateRequest,
    BreedingPlotListRequest,
    BreedingPlotUpdateRequest,
    BreedingProgramCreateRequest,
    BreedingProgramListRequest,
    BreedingProgramUpdateRequest,
    BreedingTrialCreateRequest,
    BreedingTrialListRequest,
    BreedingTrialUpdateRequest,
    BreedingVariantSampleMapCreateRequest,
    BreedingVariantSampleMapListRequest,
    BreedingVariantSampleMapUpdateRequest,
    ExpressionSampleMapRequest,
    VariantSampleSyncRequest,
)
from ..models import BreedingProgram
from ..services import breeding_domain_service

breeding_router = APIRouter(tags=["app:breeding"])


@breeding_router.post(
    "/germplasm/import/validate",
    summary="校验种质资源导入文件",
    dependencies=[Depends(ensure_taxonomy_ready)],
)
async def breeding_germplasm_import_validate(
    template_profile: str = Form(...),
    taxonomy_tax_id: int = Form(...),
    file: UploadFile = File(...),
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    validation_token, source_path = persist_uploaded_excel(file)
    data = breeding_domain_service.validate_germplasm_import(
        db=db,
        template_profile=template_profile,
        taxonomy_tax_id=taxonomy_tax_id,
        source_path=source_path,
        source_filename=file.filename or "uploaded.xlsx",
        user=_user,
        validation_token=validation_token,
    )
    return response_200(data=data)


@breeding_router.post(
    "/germplasm/import/commit",
    summary="提交种质资源导入",
    dependencies=[Depends(ensure_taxonomy_ready)],
)
async def breeding_germplasm_import_commit(
    request_data: BreedingGermplasmImportCommitRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    return response_200(
        data=breeding_domain_service.commit_germplasm_import(
            db=db,
            validation_token=request_data.validation_token,
            user=_user,
        )
    )


@breeding_router.post(
    "/germplasm/import/batches",
    summary="种质资源导入批次列表",
    dependencies=[Depends(ensure_taxonomy_ready)],
)
async def breeding_germplasm_import_batches(
    request_data: BreedingGermplasmImportBatchListRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    return response_200(data=breeding_domain_service.list_germplasm_import_batches(db=db, request_data=request_data))


@breeding_router.post(
    "/germplasm/import/batch-info",
    summary="种质资源导入批次详情",
    dependencies=[Depends(ensure_taxonomy_ready)],
)
async def breeding_germplasm_import_batch_info(
    request_data: BreedingInfoRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    return response_200(data=breeding_domain_service.get_germplasm_import_batch(db=db, batch_id=request_data.id))


@breeding_router.post(
    "/germplasm/import/batch-delete",
    summary="删除种质资源导入批次数据",
    dependencies=[Depends(ensure_taxonomy_ready)],
)
async def breeding_germplasm_import_batch_delete(
    request_data: BreedingGermplasmImportBatchDeleteRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    return response_200(
        data=breeding_domain_service.delete_germplasm_import_batch(
            db=db,
            batch_id=request_data.id,
            user=_user,
        )
    )


@breeding_router.post(
    "/germplasm/taxonomy/options",
    summary="种质资源 taxonomy 选项",
    dependencies=[Depends(ensure_taxonomy_ready)],
)
async def breeding_germplasm_taxonomy_options(
    request_data: BreedingGermplasmTaxonomySearchRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    return response_200(data=breeding_domain_service.list_germplasm_taxonomy_options(db=db, request_data=request_data))


@breeding_router.post(
    "/germplasm/taxonomy/search",
    summary="搜索种质资源 taxonomy",
    dependencies=[Depends(ensure_taxonomy_ready)],
)
async def breeding_germplasm_taxonomy_search(
    request_data: BreedingGermplasmTaxonomySearchRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    return response_200(data=breeding_domain_service.list_germplasm_taxonomy_options(db=db, request_data=request_data))


@breeding_router.post(
    "/germplasm/taxonomy/sync",
    summary="同步种质资源 taxonomy 缓存",
    dependencies=[Depends(ensure_taxonomy_ready)],
)
async def breeding_germplasm_taxonomy_sync(
    request_data: BreedingGermplasmTaxonomySyncRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    return response_200(data=breeding_domain_service.sync_germplasm_taxonomy_cache(db=db, request_data=request_data))


@breeding_router.post(
    "/germplasm/taxonomy/audit",
    summary="审计种质资源 taxonomy 缓存",
    dependencies=[Depends(ensure_taxonomy_ready)],
)
async def breeding_germplasm_taxonomy_audit(
    request_data: BreedingGermplasmTaxonomyAuditRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    return response_200(data=breeding_domain_service.audit_germplasm_taxonomy_cache(db=db, request_data=request_data))


@breeding_router.post(
    "/germplasm/list",
    summary="种质资源列表",
    dependencies=[Depends(ensure_taxonomy_ready)],
)
async def breeding_germplasm_list(
    request_data: BreedingGermplasmListRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    return response_200(data=breeding_domain_service.list_germplasms(db=db, request_data=request_data))


@breeding_router.post(
    "/germplasm/info",
    summary="种质资源详情",
    dependencies=[Depends(ensure_taxonomy_ready)],
)
async def breeding_germplasm_info(
    request_data: BreedingGermplasmInfoRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    return response_200(
        data=breeding_domain_service.get_germplasm(
            db=db,
            accession_id=request_data.accession_id,
            taxonomy_tax_id=request_data.taxonomy_tax_id,
        )
    )


@breeding_router.post(
    "/germplasm/set-public",
    summary="设置种质资源公开状态",
    dependencies=[Depends(ensure_taxonomy_ready)],
)
async def breeding_germplasm_set_public(
    request_data: BreedingGermplasmSetPublicRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    breeding_domain_service.set_germplasm_public(
        db=db,
        accession_id=request_data.accession_id,
        taxonomy_tax_id=request_data.taxonomy_tax_id,
        is_public=request_data.is_public,
    )
    return response_200(data={"ok": True})


@breeding_router.post(
    "/germplasm/import/set-public",
    summary="设置导入批次公开状态",
    dependencies=[Depends(ensure_taxonomy_ready)],
)
async def breeding_germplasm_batch_set_public(
    request_data: BreedingGermplasmBatchSetPublicRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    breeding_domain_service.set_germplasm_batch_public(
        db=db,
        batch_id=request_data.id,
        is_public=request_data.is_public,
    )
    return response_200(data={"ok": True})


@breeding_router.post(
    "/germplasm/statistics",
    summary="种质资源谱系统计",
    dependencies=[Depends(ensure_taxonomy_ready)],
)
async def breeding_germplasm_statistics(
    request_data: BreedingGermplasmStatisticsRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    return response_200(data=breeding_domain_service.get_germplasm_statistics(db=db, request_data=request_data))


@breeding_router.post(
    "/germplasm/relationship",
    summary="种质资源关系比较",
    dependencies=[Depends(ensure_taxonomy_ready)],
)
async def breeding_germplasm_relationship(
    request_data: BreedingGermplasmRelationshipRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    return response_200(data=breeding_domain_service.get_germplasm_relationship(db=db, request_data=request_data))


@breeding_router.post(
    "/germplasm/relationships/batch",
    summary="种质资源批量图谱关系",
    dependencies=[Depends(ensure_taxonomy_ready)],
)
async def breeding_germplasm_relationships_batch(
    request_data: BreedingGermplasmBatchRelationshipRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    return response_200(data=breeding_domain_service.get_germplasm_batch_relationships(db=db, request_data=request_data))


@breeding_router.post("/program/list", summary="育种 Program 列表")
async def breeding_program_list(request_data: BreedingProgramListRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.list_programs(db=db, request_data=request_data))


@breeding_router.post("/program/info", summary="育种 Program 详情")
async def breeding_program_info(request_data: BreedingInfoRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.get_program(db=db, program_id=request_data.id))


@breeding_router.post("/program/overview", summary="育种 Program 总览")
async def breeding_program_overview(request_data: BreedingInfoRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.get_program_overview(db=db, program_id=request_data.id))


@breeding_router.post("/program/create", summary="创建育种 Program")
async def breeding_program_create(request_data: BreedingProgramCreateRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.create_program(db=db, request_data=request_data, user=_user))


@breeding_router.post("/program/update", summary="更新育种 Program")
async def breeding_program_update(request_data: BreedingProgramUpdateRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.update_program(db=db, program_id=request_data.id, request_data=request_data, user=_user))


@breeding_router.post("/program/options", summary="获取育种项目选项列表")
async def breeding_program_options(
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    """Return lightweight program list for dropdowns (id, name, code)."""
    programs = db.query(BreedingProgram).filter(
        BreedingProgram.status == "active"
    ).order_by(BreedingProgram.name).all()
    options = [
        {"label": p.name, "value": p.id, "code": p.code}
        for p in programs
    ]
    return response_200(data=options)


@breeding_router.post("/material/list", summary="育种 Material 列表")
async def breeding_material_list(request_data: BreedingMaterialListRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.list_materials(db=db, request_data=request_data))


@breeding_router.post("/material/info", summary="育种 Material 详情")
async def breeding_material_info(request_data: BreedingInfoRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.get_material(db=db, material_id=request_data.id))


@breeding_router.post("/material/create", summary="创建育种 Material")
async def breeding_material_create(request_data: BreedingMaterialCreateRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.create_material(db=db, request_data=request_data, user=_user))


@breeding_router.post("/material/update", summary="更新育种 Material")
async def breeding_material_update(request_data: BreedingMaterialUpdateRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.update_material(db=db, material_id=request_data.id, request_data=request_data, user=_user))


@breeding_router.post("/material/overview", summary="育种 Material 总览")
async def breeding_material_overview(
    request_data: BreedingInfoRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    overview = breeding_domain_service.get_material_overview(
        db=db, material_id=request_data.id
    )
    if overview is None:
        return response_404(msg="Material not found")
    return response_200(data=overview)


@breeding_router.post("/trial/list", summary="育种 Trial 列表")
async def breeding_trial_list(request_data: BreedingTrialListRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.list_trials(db=db, request_data=request_data))


@breeding_router.post("/trial/info", summary="育种 Trial 详情")
async def breeding_trial_info(request_data: BreedingInfoRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.get_trial(db=db, trial_id=request_data.id))


@breeding_router.post("/trial/create", summary="创建育种 Trial")
async def breeding_trial_create(request_data: BreedingTrialCreateRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.create_trial(db=db, request_data=request_data, user=_user))


@breeding_router.post("/trial/update", summary="更新育种 Trial")
async def breeding_trial_update(request_data: BreedingTrialUpdateRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.update_trial(db=db, trial_id=request_data.id, request_data=request_data, user=_user))


@breeding_router.post("/trial/overview")
async def breeding_trial_overview(
    request_data: BreedingInfoRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    overview = breeding_domain_service.get_trial_overview(
        db=db, trial_id=request_data.id
    )
    if overview is None:
        return response_404(msg="Trial not found")
    return response_200(data=overview)


@breeding_router.post("/plot/list", summary="育种 Plot 列表")
async def breeding_plot_list(request_data: BreedingPlotListRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.list_plots(db=db, request_data=request_data))


@breeding_router.post("/plot/info", summary="育种 Plot 详情")
async def breeding_plot_info(request_data: BreedingInfoRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.get_plot(db=db, plot_id=request_data.id))


@breeding_router.post("/plot/create", summary="创建育种 Plot")
async def breeding_plot_create(request_data: BreedingPlotCreateRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.create_plot(db=db, request_data=request_data, user=_user))


@breeding_router.post("/plot/update", summary="更新育种 Plot")
async def breeding_plot_update(request_data: BreedingPlotUpdateRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.update_plot(db=db, plot_id=request_data.id, request_data=request_data, user=_user))


@breeding_router.post("/observation/list", summary="育种 Observation 列表")
async def breeding_observation_list(request_data: BreedingObservationListRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.list_observations(db=db, request_data=request_data))


@breeding_router.post("/observation/info", summary="育种 Observation 详情")
async def breeding_observation_info(request_data: BreedingInfoRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.get_observation(db=db, observation_id=request_data.id))


@breeding_router.post("/observation/create", summary="创建育种 Observation")
async def breeding_observation_create(request_data: BreedingObservationCreateRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.create_observation(db=db, request_data=request_data, user=_user))


@breeding_router.post("/observation/update", summary="更新育种 Observation")
async def breeding_observation_update(request_data: BreedingObservationUpdateRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.update_observation(db=db, observation_id=request_data.id, request_data=request_data, user=_user))


@breeding_router.post("/biosample/list", summary="育种 BioSample 列表")
async def breeding_biosample_list(request_data: BreedingBioSampleListRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.list_biosamples(db=db, request_data=request_data))


@breeding_router.post("/biosample/info", summary="育种 BioSample 详情")
async def breeding_biosample_info(request_data: BreedingInfoRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.get_biosample(db=db, biosample_id=request_data.id))


@breeding_router.post("/biosample/create", summary="创建育种 BioSample")
async def breeding_biosample_create(request_data: BreedingBioSampleCreateRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.create_biosample(db=db, request_data=request_data, user=_user))


@breeding_router.post("/biosample/update", summary="更新育种 BioSample")
async def breeding_biosample_update(request_data: BreedingBioSampleUpdateRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.update_biosample(db=db, biosample_id=request_data.id, request_data=request_data, user=_user))


@breeding_router.post("/assay/list", summary="育种 Assay 列表")
async def breeding_assay_list(request_data: BreedingAssayListRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.list_assays(db=db, request_data=request_data))


@breeding_router.post("/assay/info", summary="育种 Assay 详情")
async def breeding_assay_info(request_data: BreedingInfoRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.get_assay(db=db, assay_id=request_data.id))


@breeding_router.post("/assay/create", summary="创建育种 Assay")
async def breeding_assay_create(request_data: BreedingAssayCreateRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.create_assay(db=db, request_data=request_data, user=_user))


@breeding_router.post("/assay/update", summary="更新育种 Assay")
async def breeding_assay_update(request_data: BreedingAssayUpdateRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.update_assay(db=db, assay_id=request_data.id, request_data=request_data, user=_user))


@breeding_router.post("/data-file/list", summary="育种 DataFile 列表")
async def breeding_data_file_list(request_data: BreedingDataFileListRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.list_data_files(db=db, request_data=request_data))


@breeding_router.post("/data-file/info", summary="育种 DataFile 详情")
async def breeding_data_file_info(request_data: BreedingInfoRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.get_data_file(db=db, data_file_id=request_data.id))


@breeding_router.post("/data-file/create", summary="创建育种 DataFile")
async def breeding_data_file_create(request_data: BreedingDataFileCreateRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.create_data_file(db=db, request_data=request_data, user=_user))


@breeding_router.post("/data-file/update", summary="更新育种 DataFile")
async def breeding_data_file_update(request_data: BreedingDataFileUpdateRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.update_data_file(db=db, data_file_id=request_data.id, request_data=request_data, user=_user))


@breeding_router.post("/dataset-subject-link/list", summary="Dataset Subject Link 列表")
async def breeding_dataset_subject_link_list(request_data: BreedingDatasetSubjectLinkListRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.list_dataset_subject_links(db=db, request_data=request_data))


@breeding_router.post("/dataset-subject-link/info", summary="Dataset Subject Link 详情")
async def breeding_dataset_subject_link_info(request_data: BreedingInfoRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.get_dataset_subject_link(db=db, link_id=request_data.id))


@breeding_router.post("/dataset-subject-link/create", summary="创建 Dataset Subject Link")
async def breeding_dataset_subject_link_create(request_data: BreedingDatasetSubjectLinkCreateRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.create_dataset_subject_link(db=db, request_data=request_data, user=_user))


@breeding_router.post("/dataset-subject-link/update", summary="更新 Dataset Subject Link")
async def breeding_dataset_subject_link_update(request_data: BreedingDatasetSubjectLinkUpdateRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.update_dataset_subject_link(db=db, link_id=request_data.id, request_data=request_data, user=_user))


@breeding_router.post("/dataset-assay-link/list", summary="Dataset Assay Link 列表")
async def breeding_dataset_assay_link_list(request_data: BreedingDatasetAssayLinkListRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.list_dataset_assay_links(db=db, request_data=request_data))


@breeding_router.post("/dataset-assay-link/info", summary="Dataset Assay Link 详情")
async def breeding_dataset_assay_link_info(request_data: BreedingInfoRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.get_dataset_assay_link(db=db, link_id=request_data.id))


@breeding_router.post("/dataset-assay-link/create", summary="创建 Dataset Assay Link")
async def breeding_dataset_assay_link_create(request_data: BreedingDatasetAssayLinkCreateRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.create_dataset_assay_link(db=db, request_data=request_data, user=_user))


@breeding_router.post("/dataset-assay-link/update", summary="更新 Dataset Assay Link")
async def breeding_dataset_assay_link_update(request_data: BreedingDatasetAssayLinkUpdateRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.update_dataset_assay_link(db=db, link_id=request_data.id, request_data=request_data, user=_user))


@breeding_router.post("/variant-sample-map/list", summary="Variant Sample Map 列表")
async def breeding_variant_sample_map_list(request_data: BreedingVariantSampleMapListRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.list_variant_sample_maps(db=db, request_data=request_data))


@breeding_router.post("/variant-sample-map/info", summary="Variant Sample Map 详情")
async def breeding_variant_sample_map_info(request_data: BreedingInfoRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.get_variant_sample_map(db=db, map_id=request_data.id))


@breeding_router.post("/variant-sample-map/create", summary="创建 Variant Sample Map")
async def breeding_variant_sample_map_create(request_data: BreedingVariantSampleMapCreateRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.create_variant_sample_map(db=db, request_data=request_data, user=_user))


@breeding_router.post("/variant-sample-map/update", summary="更新 Variant Sample Map")
async def breeding_variant_sample_map_update(request_data: BreedingVariantSampleMapUpdateRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.update_variant_sample_map(db=db, map_id=request_data.id, request_data=request_data, user=_user))


@breeding_router.post("/phenotype-subject-map/list", summary="Phenotype Subject Map 列表")
async def breeding_phenotype_subject_map_list(request_data: BreedingPhenotypeSubjectMapListRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.list_phenotype_subject_maps(db=db, request_data=request_data))


@breeding_router.post("/phenotype-subject-map/info", summary="Phenotype Subject Map 详情")
async def breeding_phenotype_subject_map_info(request_data: BreedingInfoRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.get_phenotype_subject_map(db=db, map_id=request_data.id))


@breeding_router.post("/phenotype-subject-map/create", summary="创建 Phenotype Subject Map")
async def breeding_phenotype_subject_map_create(request_data: BreedingPhenotypeSubjectMapCreateRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.create_phenotype_subject_map(db=db, request_data=request_data, user=_user))


@breeding_router.post("/phenotype-subject-map/update", summary="更新 Phenotype Subject Map")
async def breeding_phenotype_subject_map_update(request_data: BreedingPhenotypeSubjectMapUpdateRequest, db=Depends(get_db), _user=Depends(get_active_user)):
    return response_200(data=breeding_domain_service.update_phenotype_subject_map(db=db, map_id=request_data.id, request_data=request_data, user=_user))


@breeding_router.post("/program/link-dataset")
async def breeding_program_link_dataset(
    request_data: LinkDatasetRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    from apps.datasets.services import DatasetDomainService
    from apps.datasets.dataset_model import Dataset

    dataset = db.query(Dataset).filter_by(id=request_data.dataset_id).first()
    if not dataset:
        return response_404(msg="Dataset not found")

    # Check cross-domain permission
    user_team_ids = getattr(_user, "team_ids", []) or []
    user_project_ids = getattr(_user, "project_ids", []) or []
    can_access = DatasetDomainService.can_access_dataset(
        db=db,
        dataset_visibility=dataset.visibility or "private",
        dataset_team_id=dataset.team_id or 0,
        dataset_project_id=dataset.project_id,
        user_team_ids=user_team_ids,
        user_project_ids=user_project_ids,
    )
    if not can_access:
        return response_403(msg="Access denied: dataset is not accessible to your team/project scope")

    result = breeding_domain_service.link_dataset_to_program(
        db=db,
        program_id=request_data.program_id,
        dataset_id=request_data.dataset_id,
        version_id=request_data.version_id,
        link_type=request_data.link_type,
        role=request_data.role,
        material_id=request_data.material_id,
        note=request_data.note,
    )
    return response_200(data=result)


@breeding_router.post("/material/datasets")
async def breeding_material_datasets(
    request_data: BreedingInfoRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    from apps.datasets.cross_domain import CrossDomainDatasetLookup

    lookup = CrossDomainDatasetLookup()
    datasets = lookup.get_datasets_for_material(db=db, material_id=request_data.id)
    return response_200(data={"material_id": request_data.id, "datasets": datasets, "total": len(datasets)})


@breeding_router.post("/program/datasets")
async def breeding_program_datasets(
    request_data: ProgramDatasetsRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    from apps.datasets.cross_domain import CrossDomainDatasetLookup

    lookup = CrossDomainDatasetLookup()
    datasets = lookup.get_datasets_for_program(
        db=db, program_id=request_data.program_id,
        dataset_type=request_data.dataset_type,
    )
    return response_200(data={"program_id": request_data.program_id, "datasets": datasets, "total": len(datasets)})


@breeding_router.post("/variant-samples/sync")
async def breeding_variant_samples_sync(
    request_data: VariantSampleSyncRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    result = breeding_domain_service.sync_variant_samples_to_catalog(
        db=db,
        dataset_id=request_data.dataset_id,
        version_id=request_data.version_id,
        asset_id=request_data.asset_id,
        sample_names=request_data.sample_names,
    )
    return response_200(data=result)


@breeding_router.post("/expression-samples/map")
async def breeding_expression_samples_map(
    request_data: ExpressionSampleMapRequest,
    db=Depends(get_db),
    _user=Depends(get_active_user),
):
    result = breeding_domain_service.map_expression_samples_to_biosamples(
        db=db,
        dataset_id=request_data.dataset_id,
        version_id=request_data.version_id,
        asset_id=request_data.asset_id,
        sample_names=request_data.sample_names,
    )
    return response_200(data=result)
