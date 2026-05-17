from sqlalchemy import BigInteger, Boolean, Column, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint

from shared.database import Base


class DatasetKindRegistry(Base):
    __tablename__ = "dataset_kind_registry"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(128), unique=True, index=True, comment="类型编码")
    base_code = Column(String(128), index=True, comment="系统标准基础编码")
    name = Column(String(320), comment="显示名称")
    description = Column(Text, comment="类型描述")
    is_system = Column(Integer, default=0, comment="是否系统内置")
    is_active = Column(Integer, default=1, comment="是否启用")
    sort_order = Column(Integer, default=0, comment="排序")
    meta_json = Column(Text, comment="扩展元数据")
    create_time = Column(Integer, comment="创建时间")
    update_time = Column(Integer, comment="更新时间")


class AssetTypeRegistry(Base):
    __tablename__ = "asset_type_registry"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(128), unique=True, index=True, comment="资产类型编码")
    base_code = Column(String(128), index=True, comment="系统标准基础编码")
    name = Column(String(320), comment="显示名称")
    description = Column(Text, comment="类型描述")
    allowed_dataset_types = Column(Text, comment="允许挂载的 dataset_kind 列表 JSON")
    is_system = Column(Integer, default=0, comment="是否系统内置")
    is_active = Column(Integer, default=1, comment="是否启用")
    sort_order = Column(Integer, default=0, comment="排序")
    meta_json = Column(Text, comment="扩展元数据")
    create_time = Column(Integer, comment="创建时间")
    update_time = Column(Integer, comment="更新时间")


class AssetFileTypeRegistry(Base):
    __tablename__ = "asset_file_type_registry"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(128), unique=True, index=True, comment="资产文件类型编码")
    base_code = Column(String(128), index=True, comment="系统标准基础编码")
    name = Column(String(320), comment="显示名称")
    description = Column(Text, comment="类型描述")
    file_role = Column(String(32), index=True, comment="默认文件角色")
    supported_file_formats = Column(Text, comment="支持的文件格式列表 JSON")
    allowed_asset_types = Column(Text, comment="允许挂载的 asset_type 列表 JSON")
    is_system = Column(Integer, default=0, comment="是否系统内置")
    is_active = Column(Integer, default=1, comment="是否启用")
    sort_order = Column(Integer, default=0, comment="排序")
    meta_json = Column(Text, comment="扩展元数据")
    create_time = Column(Integer, comment="创建时间")
    update_time = Column(Integer, comment="更新时间")


class DatasetScanRoot(Base):
    __tablename__ = "dataset_scan_root"

    id = Column(Integer, primary_key=True, index=True)
    root_code = Column(String(128), unique=True, index=True, comment="扫描目录编码")
    name = Column(String(320), comment="目录名称")
    root_path = Column(String(1024), unique=True, index=True, comment="根目录路径")
    description = Column(Text, comment="目录说明")
    scan_recursive = Column(Integer, default=1, comment="是否递归扫描")
    include_hidden = Column(Integer, default=0, comment="是否包含隐藏文件")
    is_active = Column(Integer, default=1, comment="是否启用")
    last_scan_time = Column(Integer, comment="最近扫描时间")
    create_user_id = Column(Integer, comment="创建人")
    create_time = Column(Integer, comment="创建时间")
    update_time = Column(Integer, comment="更新时间")


class DatasetScanJob(Base):
    __tablename__ = "dataset_scan_job"

    id = Column(Integer, primary_key=True, index=True)
    root_id = Column(Integer, index=True, comment="扫描目录 ID")
    job_code = Column(String(128), unique=True, index=True, comment="扫描任务编码")
    status = Column(String(64), default="pending", comment="任务状态")
    scanned_dir_count = Column(Integer, default=0, comment="扫描目录数")
    scanned_file_count = Column(Integer, default=0, comment="扫描文件数")
    staged_file_count = Column(Integer, default=0, comment="写入暂存区文件数")
    skipped_file_count = Column(Integer, default=0, comment="跳过文件数")
    changed_file_count = Column(Integer, default=0, comment="更新的暂存文件数")
    missing_file_count = Column(Integer, default=0, comment="标记缺失文件数")
    skipped_registered_count = Column(Integer, default=0, comment="已注册文件跳过数")
    error_message = Column(Text, comment="错误信息")
    started_at = Column(Integer, comment="开始时间")
    finished_at = Column(Integer, comment="结束时间")
    create_user_id = Column(Integer, comment="创建人")
    create_time = Column(Integer, comment="创建时间")
    update_time = Column(Integer, comment="更新时间")


class DatasetStagingFile(Base):
    __tablename__ = "dataset_staging_file"

    id = Column(Integer, primary_key=True, index=True)
    staging_code = Column(String(128), unique=True, index=True, comment="暂存编码")
    source_name = Column(String(255), comment="原始上传文件名")
    file_name = Column(String(255), comment="暂存文件名")
    storage_uri = Column(String(1024), comment="统一存储 URI")
    local_path = Column(String(1024), comment="本地暂存路径")
    file_format = Column(String(128), comment="文件格式")
    file_size = Column(BigInteger, comment="文件大小")
    dataset_type = Column(String(128), comment="建议的数据集类型")
    source_mode = Column(String(32), default="upload", comment="来源模式")
    scan_root_id = Column(Integer, index=True, comment="来源扫描目录 ID")
    scan_job_id = Column(Integer, index=True, comment="来源扫描任务 ID")
    relative_path = Column(String(1024), comment="相对扫描目录路径")
    file_mtime = Column(BigInteger, comment="文件修改时间")
    discovered_at = Column(Integer, comment="发现时间")
    last_seen_at = Column(Integer, comment="最近扫描看到时间")
    stage_status = Column(String(64), default="uploaded", comment="暂存状态")
    linked_dataset_id = Column(Integer, index=True, comment="已注册关联的 dataset id")
    create_user_id = Column(Integer, comment="上传人")
    meta_json = Column(Text, comment="扩展元数据")
    create_time = Column(Integer, comment="创建时间")
    update_time = Column(Integer, comment="更新时间")


class DatasetRegistrationCandidate(Base):
    __tablename__ = "dataset_registration_candidate"
    __table_args__ = (
        UniqueConstraint("candidate_code", name="uq_dataset_registration_candidate_code"),
        Index("ix_dataset_registration_candidate_dataset_type", "dataset_type"),
        Index("ix_dataset_registration_candidate_scan_root", "scan_root_id"),
        Index("ix_dataset_registration_candidate_reference", "reference_dataset_id", "reference_version_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    candidate_code = Column(String(128), comment="候选编码")
    scan_root_id = Column(Integer, comment="来源扫描目录 ID")
    dataset_type = Column(String(128), comment="目标数据类型")
    recipe_code = Column(String(128), comment="注册 recipe 编码")
    registration_mode = Column(String(64), default="recipe_build", comment="注册模式")
    candidate_name = Column(String(320), comment="候选名称")
    version_name = Column(String(128), comment="目标版本名")
    organism = Column(String(255), comment="物种")
    assembly = Column(String(255), comment="组装版本")
    reference_dataset_id = Column(Integer, comment="绑定参考 dataset ID")
    reference_version_id = Column(Integer, comment="绑定参考版本 ID")
    status = Column(String(64), default="draft", comment="候选状态")
    validation_status = Column(String(64), default="pending", comment="校验状态")
    build_status = Column(String(64), default="not_required", comment="构建状态")
    registration_status = Column(String(64), default="pending", comment="注册状态")
    source_kind = Column(String(64), default="source_candidate", comment="候选来源类型")
    meta_json = Column(Text, comment="扩展元数据")
    create_user_id = Column(Integer, comment="创建人")
    create_time = Column(Integer, comment="创建时间")
    update_time = Column(Integer, comment="更新时间")


class DatasetRegistrationCandidateFile(Base):
    __tablename__ = "dataset_registration_candidate_file"
    __table_args__ = (
        UniqueConstraint("candidate_id", "staging_file_id", name="uq_dataset_registration_candidate_file_candidate_staging"),
        Index("ix_dataset_registration_candidate_file_candidate", "candidate_id"),
        Index("ix_dataset_registration_candidate_file_staging", "staging_file_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, comment="候选 ID")
    staging_file_id = Column(Integer, comment="来源 staging_file ID")
    source_role = Column(String(128), comment="输入角色")
    asset_type = Column(String(128), comment="目标资产类型")
    asset_file_type_code = Column(String(128), comment="目标资产文件类型编码")
    file_role = Column(String(64), comment="目标文件角色")
    is_primary = Column(Integer, default=0, comment="是否主文件")
    is_required = Column(Integer, default=1, comment="是否必需")
    validation_status = Column(String(64), default="pending", comment="校验状态")
    confidence = Column(Float, comment="识别置信度")
    origin_type = Column(String(64), default="user_supplied", comment="文件来源类型")
    sort_order = Column(Integer, default=0, comment="排序")
    meta_json = Column(Text, comment="扩展元数据")
    create_time = Column(Integer, comment="创建时间")
    update_time = Column(Integer, comment="更新时间")


class DatasetRegistry(Base):
    __tablename__ = "dataset_registry"
    __table_args__ = (
        Index(
            "ix_dataset_registry_description_md_trgm",
            "description_md",
            postgresql_using="gin",
            postgresql_ops={"description_md": "gin_trgm_ops"},
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    database_id = Column(Integer, index=True, comment="legacy database ID")
    dataset_code = Column(String(128), index=True, comment="稳定数据集编码")
    dataset_type = Column(String(128), comment="数据集类型")
    version = Column(String(64), default="v1", comment="版本号")
    title = Column(String(320), comment="显示标题")
    lifecycle_state = Column(String(64), default="draft", comment="生命周期状态")
    visibility = Column(String(32), default="private", comment="可见性")
    owner_id = Column(Integer, comment="所有者用户 ID")
    is_public = Column(Boolean, default=False, comment="是否公开")
    organism = Column(String(128), comment="物种")
    file_format = Column(String(128), comment="文件格式")
    query_engine = Column(String(128), comment="查询引擎")
    validation_summary = Column(Text, comment="校验摘要")
    index_summary = Column(Text, comment="索引摘要")
    description_md = Column(Text, comment="Markdown 格式的数据描述文档")
    extra_json = Column(Text, comment="扩展元数据")
    default_public_version_id = Column(Integer, index=True, comment="默认公开版本 ID")
    create_time = Column(Integer, comment="创建时间")
    update_time = Column(Integer, comment="更新时间")

    def to_dict(self):
        model_dict = dict(self.__dict__)
        del model_dict["_sa_instance_state"]
        return model_dict


class DatasetWorkflowTask(Base):
    __tablename__ = "dataset_workflow_task"

    id = Column(Integer, primary_key=True, index=True)
    database_id = Column(Integer, index=True, comment="legacy database ID")
    task_type = Column(String(64), comment="任务类型")
    task_status = Column(String(64), default="pending", comment="任务状态")
    from_state = Column(String(64), comment="起始状态")
    to_state = Column(String(64), comment="目标状态")
    operator_id = Column(Integer, comment="操作人")
    detail = Column(Text, comment="任务详情")
    create_time = Column(Integer, comment="创建时间")
    finish_time = Column(Integer, comment="完成时间")


class DatasetPublishRecord(Base):
    __tablename__ = "dataset_publish_record"

    id = Column(Integer, primary_key=True, index=True)
    database_id = Column(Integer, index=True, comment="legacy database ID")
    action = Column(String(64), comment="发布动作")
    visibility_before = Column(String(32), comment="变更前可见性")
    visibility_after = Column(String(32), comment="变更后可见性")
    lifecycle_before = Column(String(64), comment="变更前状态")
    lifecycle_after = Column(String(64), comment="变更后状态")
    operator_id = Column(Integer, comment="操作人")
    note = Column(Text, comment="说明")
    create_time = Column(Integer, comment="创建时间")


class DatasetVersion(Base):
    __tablename__ = "dataset_version"

    id = Column(Integer, primary_key=True, index=True)
    database_id = Column(Integer, index=True, comment="legacy database ID")
    version = Column(String(64), index=True, comment="版本号")
    title = Column(String(320), comment="版本标题")
    dataset_type = Column(String(128), comment="数据集类型")
    lifecycle_state = Column(String(64), default="draft", comment="生命周期状态")
    visibility = Column(String(32), default="private", comment="可见性")
    release_state = Column(String(32), default="unreleased", comment="发布状态")
    file_path = Column(String(1024), comment="版本主文件路径")
    file_format = Column(String(128), comment="文件格式")
    query_engine = Column(String(128), comment="查询引擎")
    validation_summary = Column(Text, comment="校验摘要")
    index_summary = Column(Text, comment="索引摘要")
    extra_json = Column(Text, comment="扩展元数据")
    is_current = Column(Integer, default=0, comment="是否当前版本")
    is_default_public = Column(Integer, default=0, comment="是否默认公开版本")
    create_time = Column(Integer, comment="创建时间")
    update_time = Column(Integer, comment="更新时间")

    dataset_id = Column(
        Integer,
        ForeignKey("dataset.id", ondelete="RESTRICT"),
        index=True,
        comment="dataset 主表 ID",
    )


class DatasetAsset(Base):
    __tablename__ = "dataset_asset"

    id = Column(Integer, primary_key=True, index=True)
    database_id = Column(Integer, index=True, comment="legacy database ID")
    dataset_version_id = Column(Integer, index=True, comment="dataset version ID")
    asset_code = Column(String(128), index=True, comment="资产编码")
    asset_name = Column(String(320), comment="资产名称")
    asset_type = Column(String(128), comment="资产类型")
    file_format = Column(String(128), comment="主文件格式")
    query_engine = Column(String(128), comment="查询引擎")
    storage_backend = Column(String(64), comment="存储后端")
    workflow_state = Column(String(64), default="draft", comment="资产工作流状态")
    status = Column(String(64), default="active", comment="资产状态")
    is_required = Column(Integer, default=1, comment="是否必需资产")
    is_query_entry = Column(Integer, default=0, comment="是否默认查询入口")
    display_order = Column(Integer, default=0, comment="展示顺序")
    meta_json = Column(Text, comment="扩展元数据")
    create_time = Column(Integer, comment="创建时间")
    update_time = Column(Integer, comment="更新时间")


class AssetFile(Base):
    __tablename__ = "asset_file"

    id = Column(Integer, primary_key=True, index=True)
    database_id = Column(Integer, index=True, comment="legacy database ID")
    dataset_asset_id = Column(Integer, index=True, comment="dataset asset ID")
    asset_file_type_code = Column(String(128), index=True, comment="资产文件类型编码")
    file_role = Column(String(32), comment="文件角色")
    file_name = Column(String(255), comment="文件名")
    storage_uri = Column(String(1024), comment="统一存储 URI")
    local_path = Column(String(1024), comment="本地路径")
    file_format = Column(String(128), comment="文件格式")
    mime_type = Column(String(128), comment="MIME 类型")
    checksum_type = Column(String(32), comment="校验类型")
    checksum_value = Column(String(255), comment="校验值")
    file_size = Column(BigInteger, comment="文件大小")
    compress_type = Column(String(32), comment="压缩类型")
    index_of_file_id = Column(Integer, index=True, comment="索引对应主文件 ID")
    status = Column(String(64), default="active", comment="文件状态")
    meta_json = Column(Text, comment="扩展元数据")
    is_downloadable = Column(Boolean, default=False, comment="是否允许公开下载")
    create_time = Column(Integer, comment="创建时间")
    update_time = Column(Integer, comment="更新时间")


class DatasetLineageEdge(Base):
    __tablename__ = "dataset_lineage_edge"
    __table_args__ = (
        UniqueConstraint(
            "src_dataset_version_id", "dst_dataset_version_id", "relation_type",
            name="uq_dataset_lineage_edge_src_dst_relation",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    database_id = Column(Integer, index=True, comment="legacy database ID")
    src_dataset_version_id = Column(Integer, index=True, comment="来源版本 ID")
    src_asset_id = Column(Integer, index=True, comment="来源资产 ID")
    dst_dataset_version_id = Column(Integer, index=True, comment="目标版本 ID")
    dst_asset_id = Column(Integer, index=True, comment="目标资产 ID")
    relation_type = Column(String(64), index=True, comment="关系类型")
    direction = Column(String(16), default="forward", comment="关系方向")
    detail_json = Column(Text, comment="关系详情")
    create_user_id = Column(Integer, comment="创建人")
    create_time = Column(Integer, comment="创建时间")


class DatasetVersionPublishRecord(Base):
    __tablename__ = "dataset_version_publish_record"

    id = Column(Integer, primary_key=True, index=True)
    database_id = Column(Integer, index=True, comment="legacy database ID")
    dataset_version_id = Column(Integer, index=True, comment="dataset version ID")
    version = Column(String(64), index=True, comment="版本号")
    action = Column(String(64), comment="发布动作")
    visibility_before = Column(String(32), comment="变更前可见性")
    visibility_after = Column(String(32), comment="变更后可见性")
    lifecycle_before = Column(String(64), comment="变更前状态")
    lifecycle_after = Column(String(64), comment="变更后状态")
    operator_id = Column(Integer, comment="操作人")
    note = Column(Text, comment="说明")
    create_time = Column(Integer, comment="创建时间")


class FunctionalGene(Base):
    __tablename__ = "functional_gene"
    __table_args__ = (
        UniqueConstraint("dataset_id", "version_id", "asset_id", "gene_id", name="uq_functional_gene_scope_gene"),
        Index("ix_functional_gene_scope", "dataset_id", "version_id", "asset_id"),
        Index("ix_functional_gene_scope_gene", "dataset_id", "version_id", "asset_id", "gene_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, index=True, comment="dataset ID")
    version_id = Column(Integer, index=True, comment="dataset version ID")
    asset_id = Column(Integer, index=True, comment="functional_annotation asset ID")
    gene_id = Column(String(255), index=True, comment="gene identifier")
    canonical_transcript_id = Column(String(255), comment="canonical transcript identifier")
    chrom = Column(String(255), comment="chromosome or contig")
    start = Column(Integer, comment="gene start")
    end = Column(Integer, comment="gene end")
    strand = Column(String(16), comment="strand")
    description = Column(Text, comment="gene description")
    family = Column(Text, comment="gene family summary")
    extra_json = Column(Text, comment="extra structured payload")
    create_time = Column(Integer, comment="创建时间")
    update_time = Column(Integer, comment="更新时间")


class FunctionalTerm(Base):
    __tablename__ = "functional_term"
    __table_args__ = (
        UniqueConstraint(
            "dataset_id",
            "version_id",
            "asset_id",
            "term_source",
            "term_id",
            name="uq_functional_term_scope_term",
        ),
        Index("ix_functional_term_scope", "dataset_id", "version_id", "asset_id"),
        Index("ix_functional_term_scope_source", "dataset_id", "version_id", "asset_id", "term_source"),
        Index("ix_functional_term_scope_source_term", "dataset_id", "version_id", "asset_id", "term_source", "term_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, index=True, comment="dataset ID")
    version_id = Column(Integer, index=True, comment="dataset version ID")
    asset_id = Column(Integer, index=True, comment="functional_annotation asset ID")
    term_source = Column(String(64), index=True, comment="term source, such as go/kegg/interpro/itak/family")
    term_id = Column(String(255), index=True, comment="term identifier")
    term_name = Column(Text, comment="term display name")
    term_type = Column(String(255), comment="term subtype")
    description = Column(Text, comment="term description")
    assignment_count = Column(Integer, default=0, comment="assignment count in current scope")
    gene_count = Column(Integer, default=0, comment="distinct gene count in current scope")
    extra_json = Column(Text, comment="example or structured metadata")
    create_time = Column(Integer, comment="创建时间")
    update_time = Column(Integer, comment="更新时间")


class FunctionalTermAssignment(Base):
    __tablename__ = "functional_term_assignment"
    __table_args__ = (
        Index("ix_functional_assignment_scope", "dataset_id", "version_id", "asset_id"),
        Index("ix_functional_assignment_scope_gene", "dataset_id", "version_id", "asset_id", "gene_id"),
        Index("ix_functional_assignment_scope_transcript", "dataset_id", "version_id", "asset_id", "transcript_id"),
        Index("ix_functional_assignment_scope_term", "dataset_id", "version_id", "asset_id", "term_source", "term_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, index=True, comment="dataset ID")
    version_id = Column(Integer, index=True, comment="dataset version ID")
    asset_id = Column(Integer, index=True, comment="functional_annotation asset ID")
    gene_id = Column(String(255), index=True, comment="gene identifier")
    transcript_id = Column(String(255), index=True, comment="transcript identifier")
    term_source = Column(String(64), index=True, comment="term source")
    term_id = Column(String(255), index=True, comment="term identifier")
    term_name = Column(Text, comment="term display name")
    term_type = Column(String(255), comment="term subtype")
    attributes_json = Column(Text, comment="raw assignment payload")
    create_time = Column(Integer, comment="创建时间")


class PhenomeImportRun(Base):
    __tablename__ = "phn_import_run"
    __table_args__ = (
        Index("ix_phn_import_run_scope", "dataset_id", "version_id", "asset_id"),
        Index("ix_phn_import_run_scope_created", "dataset_id", "version_id", "asset_id", "create_time"),
    )

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, index=True, comment="dataset ID")
    version_id = Column(Integer, index=True, comment="dataset version ID")
    asset_id = Column(Integer, index=True, comment="phenome asset ID")
    source_file_path = Column(String(1024), comment="source file path")
    source_checksum = Column(String(255), comment="source checksum")
    parser_name = Column(String(64), comment="parser name")
    parser_version = Column(String(64), comment="parser version")
    sheet_count = Column(Integer, comment="sheet count")
    row_count = Column(Integer, comment="row count")
    trait_count = Column(Integer, comment="trait count")
    observation_count = Column(Integer, comment="observation count")
    status = Column(String(32), comment="import status")
    summary_json = Column(Text, comment="summary json")
    create_time = Column(Integer, comment="创建时间")
    update_time = Column(Integer, comment="更新时间")


class PhenomeSubject(Base):
    __tablename__ = "phn_subject"
    __table_args__ = (
        UniqueConstraint("asset_id", "subject_id", "source_row_key", name="uq_phn_subject_asset_subject_row"),
        Index("ix_phn_subject_scope", "dataset_id", "version_id", "asset_id"),
        Index("ix_phn_subject_scope_subject", "dataset_id", "version_id", "asset_id", "subject_id"),
        Index("ix_phn_subject_asset_row", "asset_id", "source_row_key"),
    )

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, index=True, comment="dataset ID")
    version_id = Column(Integer, index=True, comment="dataset version ID")
    asset_id = Column(Integer, index=True, comment="phenome asset ID")
    import_run_id = Column(Integer, index=True, comment="import run ID")
    subject_id = Column(String(128), index=True, comment="subject identifier")
    subject_name = Column(String(255), comment="subject display name")
    subject_name_cn = Column(String(255), comment="subject chinese name")
    subject_name_en = Column(String(255), comment="subject english name")
    subject_type = Column(String(32), comment="subject type")
    source_sheet = Column(String(128), comment="source sheet")
    source_row_key = Column(String(255), comment="source row key")
    meta_json = Column(Text, comment="extra structured payload")
    create_time = Column(Integer, comment="创建时间")
    update_time = Column(Integer, comment="更新时间")


class PhenomeTrait(Base):
    __tablename__ = "phn_trait"
    __table_args__ = (
        UniqueConstraint("asset_id", "trait_code", name="uq_phn_trait_asset_code"),
        Index("ix_phn_trait_scope", "dataset_id", "version_id", "asset_id"),
        Index("ix_phn_trait_scope_code", "dataset_id", "version_id", "asset_id", "trait_code"),
        Index("ix_phn_trait_scope_name", "dataset_id", "version_id", "asset_id", "trait_name"),
    )

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, index=True, comment="dataset ID")
    version_id = Column(Integer, index=True, comment="dataset version ID")
    asset_id = Column(Integer, index=True, comment="phenome asset ID")
    import_run_id = Column(Integer, index=True, comment="import run ID")
    trait_code = Column(String(128), index=True, comment="trait code")
    trait_name = Column(String(255), comment="trait name")
    trait_name_cn = Column(String(255), comment="trait chinese name")
    trait_name_en = Column(String(255), comment="trait english name")
    value_type = Column(String(32), comment="value type")
    unit = Column(String(64), comment="trait unit")
    time_axis_type = Column(String(32), comment="time axis type")
    category_group = Column(String(128), comment="category group")
    display_order = Column(Integer, comment="display order")
    meta_json = Column(Text, comment="extra structured payload")
    create_time = Column(Integer, comment="创建时间")
    update_time = Column(Integer, comment="更新时间")


class PhenomeSourceColumn(Base):
    __tablename__ = "phn_source_column"
    __table_args__ = (
        UniqueConstraint("asset_id", "source_sheet", "source_column_name", name="uq_phn_source_column_asset_sheet_column"),
        Index("ix_phn_source_column_scope", "dataset_id", "version_id", "asset_id"),
        Index("ix_phn_source_column_trait_timepoint", "asset_id", "trait_code", "timepoint"),
    )

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, index=True, comment="dataset ID")
    version_id = Column(Integer, index=True, comment="dataset version ID")
    asset_id = Column(Integer, index=True, comment="phenome asset ID")
    import_run_id = Column(Integer, index=True, comment="import run ID")
    source_sheet = Column(String(128), comment="source sheet")
    source_column_name = Column(String(255), comment="source column name")
    source_column_index = Column(Integer, comment="source column index")
    trait_id = Column(Integer, index=True, comment="trait ID")
    trait_code = Column(String(128), index=True, comment="trait code")
    timepoint = Column(String(64), comment="timepoint")
    parse_rule = Column(String(128), comment="parse rule")
    meta_json = Column(Text, comment="extra structured payload")
    create_time = Column(Integer, comment="创建时间")


class PhenomeTrial(Base):
    __tablename__ = "phn_trial"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, index=True, comment="dataset ID")
    version_id = Column(Integer, index=True, comment="version ID")
    asset_id = Column(Integer, index=True, comment="asset ID")
    trial_name = Column(String(256), comment="试验名称")
    location = Column(String(128), comment="地点")
    year = Column(Integer, comment="年份")
    season = Column(String(64), comment="季节")
    trial_type = Column(String(64), comment="试验类型")
    design_type = Column(String(64), comment="设计类型")
    program_id = Column(Integer, nullable=True, index=True, comment="关联育种项目 ID")
    meta_json = Column(Text, comment="扩展元数据")
    create_time = Column(Integer, comment="创建时间")
    update_time = Column(Integer, comment="更新时间")


class PhenomePlot(Base):
    __tablename__ = "phn_plot"

    id = Column(Integer, primary_key=True, index=True)
    trial_id = Column(Integer, ForeignKey("phn_trial.id", ondelete="RESTRICT"), nullable=False, index=True, comment="试验 ID")
    dataset_id = Column(Integer, index=True, comment="dataset ID")
    version_id = Column(Integer, index=True, comment="version ID")
    asset_id = Column(Integer, index=True, comment="asset ID")
    plot_code = Column(String(64), comment="Plot 编码")
    block_no = Column(Integer, comment="区组编号")
    replicate_no = Column(Integer, comment="重复编号")
    subject_id = Column(Integer, ForeignKey("phn_subject.id", ondelete="SET NULL"), nullable=True, index=True, comment="品种 ID")
    meta_json = Column(Text, comment="扩展元数据")
    create_time = Column(Integer, comment="创建时间")
    update_time = Column(Integer, comment="更新时间")


class PhenomeObservation(Base):
    __tablename__ = "phn_observation"
    __table_args__ = (
        Index("ix_phn_observation_scope", "dataset_id", "version_id", "asset_id"),
        Index("ix_phn_observation_scope_subject", "dataset_id", "version_id", "asset_id", "subject_pk"),
        Index("ix_phn_observation_scope_trait", "dataset_id", "version_id", "asset_id", "trait_code"),
        Index("ix_phn_observation_scope_trait_timepoint", "dataset_id", "version_id", "asset_id", "trait_code", "timepoint"),
        Index("ix_phn_observation_asset_row", "asset_id", "source_sheet", "source_row_key"),
    )

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, index=True, comment="dataset ID")
    version_id = Column(Integer, index=True, comment="dataset version ID")
    asset_id = Column(Integer, index=True, comment="phenome asset ID")
    import_run_id = Column(Integer, index=True, comment="import run ID")
    subject_pk = Column(Integer, index=True, comment="subject primary key")
    trait_id = Column(Integer, index=True, comment="trait ID")
    trait_code = Column(String(128), index=True, comment="trait code")
    timepoint = Column(String(64), comment="timepoint")
    obs_date = Column(String(32), comment="observation date")
    value_numeric = Column(Float, comment="normalized numeric value")
    value_text = Column(Text, comment="normalized text value")
    value_category = Column(String(255), comment="normalized category value")
    raw_value = Column(Text, comment="raw value")
    is_missing = Column(Integer, default=0, comment="is missing")
    source_sheet = Column(String(128), comment="source sheet")
    source_row_key = Column(String(255), comment="source row key")
    source_column_name = Column(String(255), comment="source column name")
    qc_status = Column(String(32), comment="qc status")
    meta_json = Column(Text, comment="extra structured payload")
    create_time = Column(Integer, comment="创建时间")
