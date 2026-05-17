from sqlalchemy import ARRAY, BigInteger, CheckConstraint, Column, Date, DateTime, Index, Integer, Numeric, String, Text, ForeignKey, func

from shared.database import Base


def _brd_bigint():
    return BigInteger().with_variant(Integer, "sqlite")


class BreedingProgram(Base):
    __tablename__ = "brd_program"
    __table_args__ = (
        Index("ix_brd_program_status", "status"),
        Index("ix_brd_program_species_name", "species_name"),
        CheckConstraint("start_year is null or start_year between 1900 and 3000", name="ck_brd_program_start_year"),
    )

    id = Column(_brd_bigint(), primary_key=True, index=True)
    code = Column(String(64), unique=True, nullable=False, comment="项目编码")
    name = Column(String(256), nullable=False, comment="项目名称")
    species_name = Column(String(128), comment="物种名称")
    breeding_goal = Column(Text, comment="育种目标")
    start_year = Column(Integer, comment="启动年份")
    status = Column(String(32), nullable=False, default="active", comment="状态")
    owner_name = Column(String(128), comment="负责人名称")
    meta_json = Column(Text, comment="扩展元数据")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="更新时间")
    created_by = Column(_brd_bigint(), comment="创建人")
    updated_by = Column(_brd_bigint(), comment="更新人")


class BreedingMaterial(Base):
    __tablename__ = "brd_material"
    __table_args__ = (
        Index("ix_brd_material_program_type_status", "program_id", "material_type", "status"),
        Index("ix_brd_material_name", "material_name"),
        Index("ix_brd_material_germplasm_accession", "germplasm_accession"),
    )

    id = Column(_brd_bigint(), primary_key=True, index=True)
    program_id = Column(_brd_bigint(), ForeignKey("brd_program.id", ondelete="RESTRICT"), nullable=False, index=True, comment="所属项目")
    material_code = Column(String(64), unique=True, nullable=False, comment="材料编码")
    material_name = Column(String(256), nullable=False, comment="材料名称")
    material_type = Column(String(32), nullable=False, comment="材料类型")
    generation_code = Column(String(32), comment="世代编码")
    origin = Column(String(128), comment="来源")
    germplasm_accession = Column(String(128), comment="关联种质编号")
    germplasm_name = Column(String(256), comment="关联种质名称快照")
    germplasm_source_file = Column(Text, comment="关联种质来源文件")
    status = Column(String(32), nullable=False, default="active", comment="状态")
    is_check = Column(Integer, nullable=False, default=0, comment="是否对照")
    meta_json = Column(Text, comment="扩展元数据")
    remarks = Column(Text, comment="备注")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="更新时间")
    created_by = Column(_brd_bigint(), comment="创建人")
    updated_by = Column(_brd_bigint(), comment="更新人")



class BreedingTaxonomyNode(Base):
    __tablename__ = "brd_taxonomy_node"
    __table_args__ = (
        Index("ix_brd_taxonomy_node_parent_tax_id", "parent_tax_id"),
        Index("ix_brd_taxonomy_node_rank", "rank"),
    )

    tax_id = Column(_brd_bigint(), primary_key=True, index=True, comment="NCBI taxonomy ID")
    parent_tax_id = Column(_brd_bigint(), comment="父 taxonomy ID")
    rank = Column(String(64), comment="分类等级")
    scientific_name = Column(String(256), nullable=False, comment="学名")
    common_name = Column(String(256), comment="常用名")
    lineage_ids = Column(ARRAY(Integer), nullable=False, default=list, comment="祖先 tax_id 数组")
    lineage = Column(Text, comment="lineage 展示文本")
    source = Column(String(32), nullable=False, default="plant_dump", comment="来源")
    is_active = Column(Integer, nullable=False, default=1, comment="是否启用")
    ncbi_sync_time = Column(DateTime(timezone=True), comment="NCBI 同步时间")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="更新时间")


class BreedingTaxonomyName(Base):
    __tablename__ = "brd_taxonomy_name"
    __table_args__ = (
        Index("ix_brd_taxonomy_name_tax_id", "tax_id"),
        Index("ix_brd_taxonomy_name_name_txt", "name_txt"),
        Index("ix_brd_taxonomy_name_name_class", "name_class"),
        Index("ix_brd_taxonomy_name_tax_id_class", "tax_id", "name_class"),
    )

    id = Column(_brd_bigint(), primary_key=True, index=True)
    tax_id = Column(_brd_bigint(), ForeignKey("brd_taxonomy_node.tax_id", ondelete="CASCADE"), nullable=False, comment="NCBI taxonomy ID")
    name_txt = Column(String(512), nullable=False, comment="名称")
    unique_name = Column(String(512), comment="唯一名称")
    name_class = Column(String(128), nullable=False, comment="名称类别")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间")



class BreedingGermplasmImportBatch(Base):
    __tablename__ = "brd_germplasm_import_batch"
    __table_args__ = (
        Index("uq_brd_germplasm_import_batch_code", "batch_code", unique=True),
        Index("ix_brd_germplasm_import_batch_taxonomy_time", "taxonomy_tax_id", "created_at"),
        Index("ix_brd_germplasm_import_batch_status_time", "status", "created_at"),
    )

    id = Column(_brd_bigint(), primary_key=True, index=True)
    batch_code = Column(String(64), nullable=False, comment="导入批次号")
    template_profile = Column(String(64), nullable=False, comment="模板 profile")
    taxonomy_tax_id = Column(_brd_bigint(), ForeignKey("brd_taxonomy_node.tax_id", ondelete="RESTRICT"), nullable=False, index=True, comment="taxonomy 锚点")
    taxonomy_name_snapshot = Column(String(256), comment="导入时学名快照")
    source_filename = Column(String(512), nullable=False, comment="原始文件名")
    source_file_path = Column(Text, comment="服务器存储路径")
    status = Column(String(32), nullable=False, default="validated", comment="状态")
    total_rows = Column(Integer, nullable=False, default=0, comment="总行数")
    valid_rows = Column(Integer, nullable=False, default=0, comment="有效行数")
    error_rows = Column(Integer, nullable=False, default=0, comment="错误行数")
    warning_rows = Column(Integer, nullable=False, default=0, comment="警告行数")
    field_schema_json = Column(Text, comment="本批次字段结构快照 JSON")
    validation_report_json = Column(Text, comment="校验报告 JSON")
    is_public = Column(Integer, nullable=False, default=0, comment="批次是否公开 0否1是")
    created_by = Column(_brd_bigint(), comment="创建人")
    updated_by = Column(_brd_bigint(), comment="更新人")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="更新时间")


class BreedingGermplasm(Base):
    __tablename__ = "brd_germplasm"
    __table_args__ = (
        Index("uq_brd_germplasm_taxonomy_accession", "taxonomy_tax_id", "accession_id", unique=True),
        Index("ix_brd_germplasm_taxonomy_name", "taxonomy_tax_id", "display_name"),
        Index("ix_brd_germplasm_batch", "batch_id"),
        Index("ix_brd_germplasm_father_accession", "father_accession"),
        Index("ix_brd_germplasm_mother_accession", "mother_accession"),
    )

    id = Column(_brd_bigint(), primary_key=True, index=True)
    batch_id = Column(_brd_bigint(), ForeignKey("brd_germplasm_import_batch.id", ondelete="RESTRICT"), nullable=False, index=True, comment="来源批次")
    taxonomy_tax_id = Column(_brd_bigint(), ForeignKey("brd_taxonomy_node.tax_id", ondelete="RESTRICT"), nullable=False, index=True, comment="taxonomy 锚点")
    accession_id = Column(String(128), nullable=False, comment="种质编号")
    display_name = Column(String(256), nullable=False, comment="显示名称")
    scientific_name_snapshot = Column(String(256), comment="学名快照")
    common_name_snapshot = Column(String(256), comment="常用名快照")
    english_name = Column(String(256), comment="英文名称")
    father_accession = Column(String(128), comment="父本 accession")
    mother_accession = Column(String(128), comment="母本 accession")
    father_name_snapshot = Column(String(256), comment="父本名称快照")
    mother_name_snapshot = Column(String(256), comment="母本名称快照")
    source_row_no = Column(Integer, comment="Excel 行号")
    status = Column(String(32), nullable=False, default="active", comment="状态")
    attributes_json = Column(Text, comment="扩展属性 JSON")
    search_text = Column(Text, comment="搜索文本")
    is_public = Column(Integer, nullable=False, default=0, comment="是否公开 0否1是")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="更新时间")


class BreedingGermplasmLineage(Base):
    __tablename__ = "brd_germplasm_lineage"
    __table_args__ = (
        Index(
            "uq_brd_germplasm_lineage_edge",
            "taxonomy_tax_id",
            "child_accession",
            "parent_accession",
            "parent_role",
            unique=True,
        ),
        Index("ix_brd_germplasm_lineage_child", "taxonomy_tax_id", "child_accession"),
        Index("ix_brd_germplasm_lineage_parent", "taxonomy_tax_id", "parent_accession"),
    )

    id = Column(_brd_bigint(), primary_key=True, index=True)
    taxonomy_tax_id = Column(_brd_bigint(), ForeignKey("brd_taxonomy_node.tax_id", ondelete="RESTRICT"), nullable=False, index=True, comment="taxonomy 锚点")
    child_accession = Column(String(128), nullable=False, comment="子代 accession")
    parent_accession = Column(String(128), nullable=False, comment="亲本 accession")
    parent_role = Column(String(16), nullable=False, comment="亲本角色")
    batch_id = Column(_brd_bigint(), ForeignKey("brd_germplasm_import_batch.id", ondelete="RESTRICT"), nullable=False, index=True, comment="来源批次")
    source_row_no = Column(Integer, comment="Excel 行号")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间")


class BreedingTrial(Base):
    __tablename__ = "brd_trial"
    __table_args__ = (
        Index("ix_brd_trial_program_status", "program_id", "status"),
        Index("ix_brd_trial_location_season", "location_name", "season_label"),
        CheckConstraint("replicate_count is null or replicate_count >= 0", name="ck_brd_trial_replicate_count"),
        CheckConstraint(
            "sowing_date is null or harvest_date is null or sowing_date <= harvest_date",
            name="ck_brd_trial_date_order",
        ),
    )

    id = Column(_brd_bigint(), primary_key=True, index=True)
    program_id = Column(_brd_bigint(), ForeignKey("brd_program.id", ondelete="RESTRICT"), nullable=False, index=True, comment="所属项目")
    trial_code = Column(String(64), unique=True, nullable=False, comment="试验编号")
    trial_name = Column(String(256), nullable=False, comment="试验名称")
    trial_type = Column(String(32), nullable=False, comment="试验类型")
    objective = Column(Text, comment="试验目的")
    location_name = Column(String(128), comment="地点名称")
    season_label = Column(String(64), comment="季节标签")
    design_type = Column(String(32), comment="设计类型")
    replicate_count = Column(Integer, comment="重复数")
    status = Column(String(32), nullable=False, default="active", comment="状态")
    sowing_date = Column(Date, comment="播种日期")
    harvest_date = Column(Date, comment="收获日期")
    meta_json = Column(Text, comment="扩展元数据")
    remarks = Column(Text, comment="备注")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="更新时间")
    created_by = Column(_brd_bigint(), comment="创建人")
    updated_by = Column(_brd_bigint(), comment="更新人")


class BreedingPlot(Base):
    __tablename__ = "brd_plot"
    __table_args__ = (
        Index("ix_brd_plot_trial_material", "trial_id", "material_id"),
        Index("ix_brd_plot_trial_replicate_block", "trial_id", "replicate_no", "block_no"),
        CheckConstraint("replicate_no is null or replicate_no >= 0", name="ck_brd_plot_replicate_no"),
        CheckConstraint("block_no is null or block_no >= 0", name="ck_brd_plot_block_no"),
        CheckConstraint("row_no is null or row_no >= 0", name="ck_brd_plot_row_no"),
        CheckConstraint("col_no is null or col_no >= 0", name="ck_brd_plot_col_no"),
        CheckConstraint("area is null or area >= 0", name="ck_brd_plot_area"),
        CheckConstraint(
            "plant_count_planned is null or plant_count_planned >= 0",
            name="ck_brd_plot_plant_count_planned",
        ),
        CheckConstraint(
            "plant_count_actual is null or plant_count_actual >= 0",
            name="ck_brd_plot_plant_count_actual",
        ),
    )

    id = Column(_brd_bigint(), primary_key=True, index=True)
    trial_id = Column(_brd_bigint(), ForeignKey("brd_trial.id", ondelete="RESTRICT"), nullable=False, index=True, comment="试验ID")
    material_id = Column(_brd_bigint(), ForeignKey("brd_material.id", ondelete="RESTRICT"), nullable=False, index=True, comment="材料ID")
    plot_code = Column(String(64), unique=True, nullable=False, comment="Plot 编码")
    replicate_no = Column(Integer, comment="重复编号")
    block_no = Column(Integer, comment="区组编号")
    row_no = Column(Integer, comment="行号")
    col_no = Column(Integer, comment="列号")
    treatment_code = Column(String(32), comment="处理编码")
    area = Column(Numeric(12, 2), comment="面积")
    plant_count_planned = Column(Integer, comment="计划株数")
    plant_count_actual = Column(Integer, comment="实际株数")
    status = Column(String(32), nullable=False, default="active", comment="状态")
    meta_json = Column(Text, comment="扩展元数据")
    remarks = Column(Text, comment="备注")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="更新时间")
    created_by = Column(_brd_bigint(), comment="创建人")
    updated_by = Column(_brd_bigint(), comment="更新人")


class BreedingObservation(Base):
    __tablename__ = "brd_observation"
    __table_args__ = (
        Index("ix_brd_observation_trial_trait_date", "trial_id", "trait_code", "obs_date"),
        Index("ix_brd_observation_plot_trait", "plot_id", "trait_code"),
        Index("ix_brd_observation_material_trait", "material_id", "trait_code"),
        Index("ix_brd_observation_source", "source_dataset_id", "source_version_id", "source_asset_id"),
        CheckConstraint(
            "observation_level in ('trial', 'plot', 'material', 'plant')",
            name="ck_brd_observation_level",
        ),
        CheckConstraint(
            "observation_level <> 'plot' or plot_id is not null",
            name="ck_brd_observation_level_plot",
        ),
        CheckConstraint(
            "observation_level <> 'material' or material_id is not null",
            name="ck_brd_observation_level_material",
        ),
        CheckConstraint(
            "obs_value_num is not null or obs_value_text is not null or obs_value_score is not null",
            name="ck_brd_observation_has_value",
        ),
    )

    id = Column(_brd_bigint(), primary_key=True, index=True)
    trial_id = Column(_brd_bigint(), ForeignKey("brd_trial.id", ondelete="RESTRICT"), nullable=False, index=True, comment="试验ID")
    plot_id = Column(_brd_bigint(), ForeignKey("brd_plot.id", ondelete="SET NULL"), index=True, comment="Plot ID")
    material_id = Column(_brd_bigint(), ForeignKey("brd_material.id", ondelete="SET NULL"), index=True, comment="材料ID")
    observation_level = Column(String(32), nullable=False, comment="观测层级")
    trait_code = Column(String(32), nullable=False, comment="性状编码")
    trait_name = Column(String(128), comment="性状名称快照")
    protocol_name = Column(String(128), comment="协议名称快照")
    obs_value_num = Column(Numeric(18, 6), comment="数值型观测值")
    obs_value_text = Column(Text, comment="文本型观测值")
    obs_value_score = Column(String(32), comment="评分值")
    obs_date = Column(Date, comment="观测日期")
    observer = Column(String(128), comment="观测人")
    qc_status = Column(String(32), nullable=False, default="draft", comment="质控状态")
    source_dataset_id = Column(Integer, ForeignKey("dataset_registry.id", ondelete="RESTRICT"), index=True, comment="来源 dataset")
    source_version_id = Column(Integer, ForeignKey("dataset_version.id", ondelete="RESTRICT"), index=True, comment="来源 version")
    source_asset_id = Column(Integer, ForeignKey("dataset_asset.id", ondelete="RESTRICT"), index=True, comment="来源 asset")
    source_row_key = Column(String(128), comment="来源行标识")
    meta_json = Column(Text, comment="扩展元数据")
    remarks = Column(Text, comment="备注")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="更新时间")
    created_by = Column(_brd_bigint(), comment="创建人")
    updated_by = Column(_brd_bigint(), comment="更新人")


class BreedingBioSample(Base):
    __tablename__ = "brd_biosample"
    __table_args__ = (
        Index("ix_brd_biosample_material_collection_date", "material_id", "collection_date"),
        Index("ix_brd_biosample_plot", "plot_id"),
        Index("ix_brd_biosample_status", "status"),
    )

    id = Column(_brd_bigint(), primary_key=True, index=True)
    sample_code = Column(String(64), unique=True, nullable=False, comment="样本编号")
    material_id = Column(_brd_bigint(), ForeignKey("brd_material.id", ondelete="RESTRICT"), nullable=False, index=True, comment="材料ID")
    plot_id = Column(_brd_bigint(), ForeignKey("brd_plot.id", ondelete="SET NULL"), index=True, comment="Plot ID")
    sample_type = Column(String(32), comment="样本类型")
    organism = Column(String(128), comment="物种")
    tissue_type = Column(String(32), comment="组织类型")
    timepoint = Column(String(64), comment="时间点")
    treatment_label = Column(String(128), comment="处理条件")
    collection_date = Column(Date, comment="采样日期")
    collector = Column(String(128), comment="采样人")
    storage_location = Column(String(128), comment="保存位置")
    status = Column(String(32), nullable=False, default="active", comment="状态")
    meta_json = Column(Text, comment="扩展元数据")
    remarks = Column(Text, comment="备注")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="更新时间")
    created_by = Column(_brd_bigint(), comment="创建人")
    updated_by = Column(_brd_bigint(), comment="更新人")


class BreedingAssay(Base):
    __tablename__ = "brd_assay"
    __table_args__ = (
        Index("ix_brd_assay_biosample_type", "biosample_id", "assay_type"),
        Index("ix_brd_assay_status_run_date", "status", "run_date"),
    )

    id = Column(_brd_bigint(), primary_key=True, index=True)
    assay_code = Column(String(64), unique=True, nullable=False, comment="实验编号")
    biosample_id = Column(_brd_bigint(), ForeignKey("brd_biosample.id", ondelete="RESTRICT"), nullable=False, index=True, comment="生物样本ID")
    assay_type = Column(String(32), nullable=False, comment="实验类型")
    platform = Column(String(64), comment="平台")
    vendor = Column(String(128), comment="执行方")
    library_strategy = Column(String(64), comment="文库策略: WGS, RNA-Seq, ChIP-Seq 等")
    library_source = Column(String(64), comment="文库来源: GENOMIC, TRANSCRIPTOMIC 等")
    library_selection = Column(String(64), comment="文库选择: PolyA, RANDOM, ChIP 等")
    library_layout = Column(String(32), comment="文库布局: SINGLE, PAIRED")
    instrument_model = Column(String(128), comment="仪器型号: HiSeq 4000, NovaSeq 6000 等")
    read_length = Column(Integer, comment="读长 bp")
    run_date = Column(Date, comment="实验日期")
    status = Column(String(32), nullable=False, default="active", comment="状态")
    meta_json = Column(Text, comment="扩展元数据")
    remarks = Column(Text, comment="备注")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="更新时间")
    created_by = Column(_brd_bigint(), comment="创建人")
    updated_by = Column(_brd_bigint(), comment="更新人")


class BreedingDataFile(Base):
    __tablename__ = "brd_data_file"
    __table_args__ = (
        Index("ix_brd_data_file_assay_role", "assay_id", "file_role"),
        Index("ix_brd_data_file_dataset_scope", "dataset_id", "version_id", "asset_id"),
        Index("uq_brd_data_file_asset_file_id", "asset_file_id", unique=True),
        CheckConstraint(
            "source_mode in ('dataset_file', 'external_uri')",
            name="ck_brd_data_file_source_mode",
        ),
        CheckConstraint(
            "(source_mode <> 'dataset_file' or asset_file_id is not null) and "
            "(source_mode <> 'external_uri' or uri_snapshot is not null)",
            name="ck_brd_data_file_source_requirements",
        ),
        CheckConstraint("file_size is null or file_size >= 0", name="ck_brd_data_file_file_size"),
    )

    id = Column(_brd_bigint(), primary_key=True, index=True)
    assay_id = Column(_brd_bigint(), ForeignKey("brd_assay.id", ondelete="RESTRICT"), nullable=False, index=True, comment="Assay ID")
    source_mode = Column(String(32), nullable=False, comment="来源模式")
    dataset_id = Column(Integer, ForeignKey("dataset_registry.id", ondelete="RESTRICT"), index=True, comment="dataset ID")
    version_id = Column(Integer, ForeignKey("dataset_version.id", ondelete="RESTRICT"), index=True, comment="version ID")
    asset_id = Column(Integer, ForeignKey("dataset_asset.id", ondelete="RESTRICT"), index=True, comment="asset ID")
    asset_file_id = Column(Integer, ForeignKey("asset_file.id", ondelete="RESTRICT"), index=True, comment="asset file ID")
    file_role = Column(String(32), nullable=False, comment="文件角色")
    file_name = Column(String(256), comment="文件名快照")
    file_format = Column(String(32), comment="文件格式")
    uri_snapshot = Column(Text, comment="外部 URI 或路径快照")
    checksum_value = Column(String(128), comment="校验值快照")
    file_size = Column(_brd_bigint(), comment="文件大小")
    status = Column(String(32), nullable=False, default="active", comment="状态")
    meta_json = Column(Text, comment="扩展元数据")
    remarks = Column(Text, comment="备注")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="更新时间")
    created_by = Column(_brd_bigint(), comment="创建人")
    updated_by = Column(_brd_bigint(), comment="更新人")


class BreedingDatasetSubjectLink(Base):
    __tablename__ = "brd_dataset_subject_link"
    __table_args__ = (
        Index("ix_brd_dataset_subject_link_scope", "version_id", "asset_id", "role"),
        Index("ix_brd_dataset_subject_link_material", "material_id"),
        Index("ix_brd_dataset_subject_link_plot", "plot_id"),
        Index("ix_brd_dataset_subject_link_biosample", "biosample_id"),
        CheckConstraint(
            "mapping_status in ('draft', 'matched', 'reviewed', 'rejected')",
            name="ck_brd_dataset_subject_link_mapping_status",
        ),
        CheckConstraint(
            "mapping_method in ('manual', 'rule', 'import', 'inferred')",
            name="ck_brd_dataset_subject_link_mapping_method",
        ),
        CheckConstraint(
            "confidence is null or confidence in ('low', 'medium', 'high')",
            name="ck_brd_dataset_subject_link_confidence",
        ),
        CheckConstraint(
            "("
            "case when program_id is null then 0 else 1 end + "
            "case when material_id is null then 0 else 1 end + "
            "case when trial_id is null then 0 else 1 end + "
            "case when plot_id is null then 0 else 1 end + "
            "case when biosample_id is null then 0 else 1 end"
            ") = 1",
            name="ck_brd_dataset_subject_link_one_subject",
        ),
    )

    id = Column(_brd_bigint(), primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("dataset_registry.id", ondelete="RESTRICT"), nullable=False, index=True, comment="dataset ID")
    version_id = Column(Integer, ForeignKey("dataset_version.id", ondelete="RESTRICT"), nullable=False, index=True, comment="version ID")
    asset_id = Column(Integer, ForeignKey("dataset_asset.id", ondelete="RESTRICT"), index=True, comment="asset ID")
    program_id = Column(_brd_bigint(), ForeignKey("brd_program.id", ondelete="SET NULL"), index=True, comment="Program ID")
    material_id = Column(_brd_bigint(), ForeignKey("brd_material.id", ondelete="SET NULL"), index=True, comment="Material ID")
    trial_id = Column(_brd_bigint(), ForeignKey("brd_trial.id", ondelete="SET NULL"), index=True, comment="Trial ID")
    plot_id = Column(_brd_bigint(), ForeignKey("brd_plot.id", ondelete="SET NULL"), index=True, comment="Plot ID")
    biosample_id = Column(_brd_bigint(), ForeignKey("brd_biosample.id", ondelete="SET NULL"), index=True, comment="BioSample ID")
    role = Column(String(32), nullable=False, comment="关系角色")
    mapping_status = Column(String(32), nullable=False, default="draft", comment="映射状态")
    mapping_method = Column(String(32), nullable=False, default="manual", comment="映射方式")
    confidence = Column(String(16), comment="置信度")
    is_primary = Column(Integer, nullable=False, default=0, comment="是否主关系")
    note = Column(Text, comment="备注")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="更新时间")
    created_by = Column(_brd_bigint(), comment="创建人")
    updated_by = Column(_brd_bigint(), comment="更新人")


class BreedingDatasetAssayLink(Base):
    __tablename__ = "brd_dataset_assay_link"
    __table_args__ = (
        Index("ix_brd_dataset_assay_link_assay_role", "assay_id", "role"),
        Index("ix_brd_dataset_assay_link_version_asset", "version_id", "asset_id"),
        CheckConstraint(
            "mapping_status in ('draft', 'matched', 'reviewed', 'rejected')",
            name="ck_brd_dataset_assay_link_mapping_status",
        ),
        CheckConstraint(
            "mapping_method in ('manual', 'rule', 'import', 'inferred')",
            name="ck_brd_dataset_assay_link_mapping_method",
        ),
        CheckConstraint(
            "confidence is null or confidence in ('low', 'medium', 'high')",
            name="ck_brd_dataset_assay_link_confidence",
        ),
    )

    id = Column(_brd_bigint(), primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("dataset_registry.id", ondelete="RESTRICT"), nullable=False, index=True, comment="dataset ID")
    version_id = Column(Integer, ForeignKey("dataset_version.id", ondelete="RESTRICT"), nullable=False, index=True, comment="version ID")
    asset_id = Column(Integer, ForeignKey("dataset_asset.id", ondelete="RESTRICT"), nullable=False, index=True, comment="asset ID")
    assay_id = Column(_brd_bigint(), ForeignKey("brd_assay.id", ondelete="RESTRICT"), nullable=False, index=True, comment="Assay ID")
    role = Column(String(32), nullable=False, comment="关系角色")
    mapping_status = Column(String(32), nullable=False, default="draft", comment="映射状态")
    mapping_method = Column(String(32), nullable=False, default="manual", comment="映射方式")
    confidence = Column(String(16), comment="置信度")
    is_primary = Column(Integer, nullable=False, default=0, comment="是否主关系")
    note = Column(Text, comment="备注")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="更新时间")
    created_by = Column(_brd_bigint(), comment="创建人")
    updated_by = Column(_brd_bigint(), comment="更新人")


class BreedingVariantSampleMap(Base):
    __tablename__ = "brd_variant_sample_map"
    __table_args__ = (
        Index("uq_brd_variant_sample_map_asset_sample", "asset_id", "vcf_sample_name", unique=True),
        Index("ix_brd_variant_sample_map_material", "material_id"),
        Index("ix_brd_variant_sample_map_biosample", "biosample_id"),
        Index("ix_brd_variant_sample_map_status", "mapping_status"),
        CheckConstraint(
            "mapping_status in ('draft', 'matched', 'reviewed', 'rejected')",
            name="ck_brd_variant_sample_map_mapping_status",
        ),
        CheckConstraint(
            "mapping_method in ('manual', 'rule', 'import', 'inferred')",
            name="ck_brd_variant_sample_map_mapping_method",
        ),
        CheckConstraint(
            "confidence is null or confidence in ('low', 'medium', 'high')",
            name="ck_brd_variant_sample_map_confidence",
        ),
    )

    id = Column(_brd_bigint(), primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("dataset_registry.id", ondelete="RESTRICT"), nullable=False, index=True, comment="dataset ID")
    version_id = Column(Integer, ForeignKey("dataset_version.id", ondelete="RESTRICT"), nullable=False, index=True, comment="version ID")
    asset_id = Column(Integer, ForeignKey("dataset_asset.id", ondelete="RESTRICT"), nullable=False, index=True, comment="asset ID")
    vcf_sample_name = Column(String(256), nullable=False, comment="VCF 原始样本名")
    normalized_sample_name = Column(String(256), comment="标准化样本名")
    sample_alias = Column(String(256), comment="样本别名")
    material_id = Column(_brd_bigint(), ForeignKey("brd_material.id", ondelete="SET NULL"), index=True, comment="Material ID")
    biosample_id = Column(_brd_bigint(), ForeignKey("brd_biosample.id", ondelete="SET NULL"), index=True, comment="BioSample ID")
    plot_id = Column(_brd_bigint(), ForeignKey("brd_plot.id", ondelete="SET NULL"), index=True, comment="Plot ID")
    mapping_status = Column(String(32), nullable=False, default="draft", comment="映射状态")
    mapping_method = Column(String(32), nullable=False, default="manual", comment="映射方式")
    confidence = Column(String(16), comment="置信度")
    is_primary = Column(Integer, nullable=False, default=0, comment="是否主映射")
    note = Column(Text, comment="备注")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="更新时间")
    created_by = Column(_brd_bigint(), comment="创建人")
    updated_by = Column(_brd_bigint(), comment="更新人")


class BreedingPhenotypeSubjectMap(Base):
    __tablename__ = "brd_phenotype_subject_map"
    __table_args__ = (
        Index("uq_brd_phenotype_subject_map_asset_row", "asset_id", "row_key", unique=True),
        Index("ix_brd_phenotype_subject_map_plot_trait", "plot_id", "trait_code"),
        Index("ix_brd_phenotype_subject_map_material_trait", "material_id", "trait_code"),
        Index("ix_brd_phenotype_subject_map_status", "mapping_status"),
        CheckConstraint(
            "mapping_status in ('draft', 'matched', 'reviewed', 'rejected')",
            name="ck_brd_phenotype_subject_map_mapping_status",
        ),
        CheckConstraint(
            "mapping_method in ('manual', 'rule', 'import', 'inferred')",
            name="ck_brd_phenotype_subject_map_mapping_method",
        ),
        CheckConstraint(
            "confidence is null or confidence in ('low', 'medium', 'high')",
            name="ck_brd_phenotype_subject_map_confidence",
        ),
    )

    id = Column(_brd_bigint(), primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("dataset_registry.id", ondelete="RESTRICT"), nullable=False, index=True, comment="dataset ID")
    version_id = Column(Integer, ForeignKey("dataset_version.id", ondelete="RESTRICT"), nullable=False, index=True, comment="version ID")
    asset_id = Column(Integer, ForeignKey("dataset_asset.id", ondelete="RESTRICT"), nullable=False, index=True, comment="asset ID")
    row_key = Column(String(128), nullable=False, comment="行稳定标识")
    trial_id = Column(_brd_bigint(), ForeignKey("brd_trial.id", ondelete="SET NULL"), index=True, comment="Trial ID")
    plot_id = Column(_brd_bigint(), ForeignKey("brd_plot.id", ondelete="SET NULL"), index=True, comment="Plot ID")
    material_id = Column(_brd_bigint(), ForeignKey("brd_material.id", ondelete="SET NULL"), index=True, comment="Material ID")
    trait_code = Column(String(32), comment="性状编码")
    obs_date = Column(Date, comment="观测日期")
    mapping_status = Column(String(32), nullable=False, default="draft", comment="映射状态")
    mapping_method = Column(String(32), nullable=False, default="manual", comment="映射方式")
    confidence = Column(String(16), comment="置信度")
    is_primary = Column(Integer, nullable=False, default=0, comment="是否主映射")
    note = Column(Text, comment="备注")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="更新时间")
    created_by = Column(_brd_bigint(), comment="创建人")
    updated_by = Column(_brd_bigint(), comment="更新人")
