-- 育种实验设计域数据库 DDL 草案
--
-- 目标：
-- 1. 为 Breeding 业务域提供第一版 PostgreSQL 落地骨架
-- 2. 保持与当前 Dataset 域解耦
-- 3. 通过外键引用现有 dataset_registry / dataset_version / dataset_asset / asset_file
--
-- 假设：
-- - 当前 Dataset 域表名为：
--   - dataset_registry
--   - dataset_version
--   - dataset_asset
--   - asset_file
-- - Dataset 域主键当前是 integer，因此本草案中的 dataset 侧外键统一使用 integer
-- - Breeding 域新表主键使用 bigserial

begin;

create table if not exists brd_program (
    id bigserial primary key,
    code varchar(64) not null,
    name varchar(256) not null,
    species_name varchar(128),
    breeding_goal text,
    start_year integer,
    status varchar(32) not null default 'active',
    owner_name varchar(128),
    meta_json jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    created_by bigint,
    updated_by bigint,
    constraint uq_brd_program_code unique (code),
    constraint ck_brd_program_start_year check (start_year is null or start_year between 1900 and 3000)
);

create index if not exists ix_brd_program_status on brd_program (status);
create index if not exists ix_brd_program_species_name on brd_program (species_name);

create table if not exists brd_material (
    id bigserial primary key,
    program_id bigint not null,
    material_code varchar(64) not null,
    material_name varchar(256) not null,
    material_type varchar(32) not null,
    generation_code varchar(32),
    origin varchar(128),
    status varchar(32) not null default 'active',
    is_check boolean not null default false,
    meta_json jsonb,
    remarks text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    created_by bigint,
    updated_by bigint,
    constraint uq_brd_material_code unique (material_code),
    constraint fk_brd_material_program
        foreign key (program_id) references brd_program (id) on delete restrict
);

create index if not exists ix_brd_material_program_type_status
    on brd_material (program_id, material_type, status);
create index if not exists ix_brd_material_name on brd_material (material_name);

create table if not exists brd_trial (
    id bigserial primary key,
    program_id bigint not null,
    trial_code varchar(64) not null,
    trial_name varchar(256) not null,
    trial_type varchar(32) not null,
    objective text,
    location_name varchar(128),
    season_label varchar(64),
    design_type varchar(32),
    replicate_count integer,
    status varchar(32) not null default 'active',
    sowing_date date,
    harvest_date date,
    meta_json jsonb,
    remarks text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    created_by bigint,
    updated_by bigint,
    constraint uq_brd_trial_code unique (trial_code),
    constraint fk_brd_trial_program
        foreign key (program_id) references brd_program (id) on delete restrict,
    constraint ck_brd_trial_replicate_count check (replicate_count is null or replicate_count >= 0),
    constraint ck_brd_trial_date_order check (
        sowing_date is null or harvest_date is null or sowing_date <= harvest_date
    )
);

create index if not exists ix_brd_trial_program_status on brd_trial (program_id, status);
create index if not exists ix_brd_trial_location_season on brd_trial (location_name, season_label);

create table if not exists brd_plot (
    id bigserial primary key,
    trial_id bigint not null,
    material_id bigint not null,
    plot_code varchar(64) not null,
    replicate_no integer,
    block_no integer,
    row_no integer,
    col_no integer,
    treatment_code varchar(32),
    area numeric(12, 2),
    plant_count_planned integer,
    plant_count_actual integer,
    status varchar(32) not null default 'active',
    meta_json jsonb,
    remarks text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    created_by bigint,
    updated_by bigint,
    constraint uq_brd_plot_code unique (plot_code),
    constraint fk_brd_plot_trial
        foreign key (trial_id) references brd_trial (id) on delete restrict,
    constraint fk_brd_plot_material
        foreign key (material_id) references brd_material (id) on delete restrict,
    constraint ck_brd_plot_replicate_no check (replicate_no is null or replicate_no >= 0),
    constraint ck_brd_plot_block_no check (block_no is null or block_no >= 0),
    constraint ck_brd_plot_row_no check (row_no is null or row_no >= 0),
    constraint ck_brd_plot_col_no check (col_no is null or col_no >= 0),
    constraint ck_brd_plot_area check (area is null or area >= 0),
    constraint ck_brd_plot_plant_count_planned check (plant_count_planned is null or plant_count_planned >= 0),
    constraint ck_brd_plot_plant_count_actual check (plant_count_actual is null or plant_count_actual >= 0)
);

create index if not exists ix_brd_plot_trial_material on brd_plot (trial_id, material_id);
create index if not exists ix_brd_plot_trial_replicate_block on brd_plot (trial_id, replicate_no, block_no);

create table if not exists brd_observation (
    id bigserial primary key,
    trial_id bigint not null,
    plot_id bigint,
    material_id bigint,
    observation_level varchar(32) not null,
    trait_code varchar(32) not null,
    trait_name varchar(128),
    protocol_name varchar(128),
    obs_value_num numeric(18, 6),
    obs_value_text text,
    obs_value_score varchar(32),
    obs_date date,
    observer varchar(128),
    qc_status varchar(32) not null default 'draft',
    source_dataset_id integer,
    source_version_id integer,
    source_asset_id integer,
    source_row_key varchar(128),
    meta_json jsonb,
    remarks text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    created_by bigint,
    updated_by bigint,
    constraint fk_brd_observation_trial
        foreign key (trial_id) references brd_trial (id) on delete restrict,
    constraint fk_brd_observation_plot
        foreign key (plot_id) references brd_plot (id) on delete set null,
    constraint fk_brd_observation_material
        foreign key (material_id) references brd_material (id) on delete set null,
    constraint fk_brd_observation_source_dataset
        foreign key (source_dataset_id) references dataset_registry (id) on delete restrict,
    constraint fk_brd_observation_source_version
        foreign key (source_version_id) references dataset_version (id) on delete restrict,
    constraint fk_brd_observation_source_asset
        foreign key (source_asset_id) references dataset_asset (id) on delete restrict,
    constraint ck_brd_observation_level check (
        observation_level in ('trial', 'plot', 'material', 'plant')
    ),
    constraint ck_brd_observation_level_plot check (
        observation_level <> 'plot' or plot_id is not null
    ),
    constraint ck_brd_observation_level_material check (
        observation_level <> 'material' or material_id is not null
    ),
    constraint ck_brd_observation_has_value check (
        num_nonnulls(obs_value_num, obs_value_text, obs_value_score) >= 1
    )
);

create index if not exists ix_brd_observation_trial_trait_date
    on brd_observation (trial_id, trait_code, obs_date);
create index if not exists ix_brd_observation_plot_trait
    on brd_observation (plot_id, trait_code);
create index if not exists ix_brd_observation_material_trait
    on brd_observation (material_id, trait_code);
create index if not exists ix_brd_observation_source
    on brd_observation (source_dataset_id, source_version_id, source_asset_id);

create table if not exists brd_biosample (
    id bigserial primary key,
    sample_code varchar(64) not null,
    material_id bigint not null,
    plot_id bigint,
    sample_type varchar(32),
    tissue_type varchar(32),
    timepoint varchar(64),
    treatment_label varchar(128),
    collection_date date,
    collector varchar(128),
    storage_location varchar(128),
    status varchar(32) not null default 'active',
    meta_json jsonb,
    remarks text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    created_by bigint,
    updated_by bigint,
    constraint uq_brd_biosample_code unique (sample_code),
    constraint fk_brd_biosample_material
        foreign key (material_id) references brd_material (id) on delete restrict,
    constraint fk_brd_biosample_plot
        foreign key (plot_id) references brd_plot (id) on delete set null
);

create index if not exists ix_brd_biosample_material_collection_date
    on brd_biosample (material_id, collection_date);
create index if not exists ix_brd_biosample_plot on brd_biosample (plot_id);
create index if not exists ix_brd_biosample_status on brd_biosample (status);

create table if not exists brd_assay (
    id bigserial primary key,
    assay_code varchar(64) not null,
    biosample_id bigint not null,
    assay_type varchar(32) not null,
    platform varchar(64),
    vendor varchar(128),
    run_date date,
    status varchar(32) not null default 'active',
    meta_json jsonb,
    remarks text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    created_by bigint,
    updated_by bigint,
    constraint uq_brd_assay_code unique (assay_code),
    constraint fk_brd_assay_biosample
        foreign key (biosample_id) references brd_biosample (id) on delete restrict
);

create index if not exists ix_brd_assay_biosample_type
    on brd_assay (biosample_id, assay_type);
create index if not exists ix_brd_assay_status_run_date
    on brd_assay (status, run_date);

create table if not exists brd_data_file (
    id bigserial primary key,
    assay_id bigint not null,
    source_mode varchar(32) not null,
    dataset_id integer,
    version_id integer,
    asset_id integer,
    asset_file_id integer,
    file_role varchar(32) not null,
    file_name varchar(256),
    file_format varchar(32),
    uri_snapshot text,
    checksum_value varchar(128),
    file_size bigint,
    status varchar(32) not null default 'active',
    meta_json jsonb,
    remarks text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    created_by bigint,
    updated_by bigint,
    constraint fk_brd_data_file_assay
        foreign key (assay_id) references brd_assay (id) on delete restrict,
    constraint fk_brd_data_file_dataset
        foreign key (dataset_id) references dataset_registry (id) on delete restrict,
    constraint fk_brd_data_file_version
        foreign key (version_id) references dataset_version (id) on delete restrict,
    constraint fk_brd_data_file_asset
        foreign key (asset_id) references dataset_asset (id) on delete restrict,
    constraint fk_brd_data_file_asset_file
        foreign key (asset_file_id) references asset_file (id) on delete restrict,
    constraint ck_brd_data_file_source_mode check (
        source_mode in ('dataset_file', 'external_uri')
    ),
    constraint ck_brd_data_file_source_requirements check (
        (source_mode = 'dataset_file' and asset_file_id is not null)
        or
        (source_mode = 'external_uri' and uri_snapshot is not null)
    ),
    constraint ck_brd_data_file_file_size check (file_size is null or file_size >= 0)
);

create index if not exists ix_brd_data_file_assay_role on brd_data_file (assay_id, file_role);
create index if not exists ix_brd_data_file_dataset_scope
    on brd_data_file (dataset_id, version_id, asset_id);
create unique index if not exists uq_brd_data_file_asset_file_id
    on brd_data_file (asset_file_id)
    where asset_file_id is not null;

create table if not exists brd_dataset_subject_link (
    id bigserial primary key,
    dataset_id integer not null,
    version_id integer not null,
    asset_id integer,
    program_id bigint,
    material_id bigint,
    trial_id bigint,
    plot_id bigint,
    biosample_id bigint,
    role varchar(32) not null,
    mapping_status varchar(32) not null default 'draft',
    mapping_method varchar(32) not null default 'manual',
    confidence varchar(16),
    is_primary boolean not null default false,
    note text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    created_by bigint,
    updated_by bigint,
    constraint fk_brd_dataset_subject_link_dataset
        foreign key (dataset_id) references dataset_registry (id) on delete restrict,
    constraint fk_brd_dataset_subject_link_version
        foreign key (version_id) references dataset_version (id) on delete restrict,
    constraint fk_brd_dataset_subject_link_asset
        foreign key (asset_id) references dataset_asset (id) on delete restrict,
    constraint fk_brd_dataset_subject_link_program
        foreign key (program_id) references brd_program (id) on delete set null,
    constraint fk_brd_dataset_subject_link_material
        foreign key (material_id) references brd_material (id) on delete set null,
    constraint fk_brd_dataset_subject_link_trial
        foreign key (trial_id) references brd_trial (id) on delete set null,
    constraint fk_brd_dataset_subject_link_plot
        foreign key (plot_id) references brd_plot (id) on delete set null,
    constraint fk_brd_dataset_subject_link_biosample
        foreign key (biosample_id) references brd_biosample (id) on delete set null,
    constraint ck_brd_dataset_subject_link_one_subject check (
        num_nonnulls(program_id, material_id, trial_id, plot_id, biosample_id) = 1
    ),
    constraint ck_brd_dataset_subject_link_mapping_status check (
        mapping_status in ('draft', 'matched', 'reviewed', 'rejected')
    ),
    constraint ck_brd_dataset_subject_link_mapping_method check (
        mapping_method in ('manual', 'rule', 'import', 'inferred')
    ),
    constraint ck_brd_dataset_subject_link_confidence check (
        confidence is null or confidence in ('low', 'medium', 'high')
    )
);

create index if not exists ix_brd_dataset_subject_link_scope
    on brd_dataset_subject_link (version_id, asset_id, role);
create index if not exists ix_brd_dataset_subject_link_material
    on brd_dataset_subject_link (material_id);
create index if not exists ix_brd_dataset_subject_link_plot
    on brd_dataset_subject_link (plot_id);
create index if not exists ix_brd_dataset_subject_link_biosample
    on brd_dataset_subject_link (biosample_id);
create unique index if not exists uq_brd_dataset_subject_link_asset_subject
    on brd_dataset_subject_link (
        asset_id, role, program_id, material_id, trial_id, plot_id, biosample_id
    )
    where asset_id is not null;
create unique index if not exists uq_brd_dataset_subject_link_version_subject
    on brd_dataset_subject_link (
        version_id, role, program_id, material_id, trial_id, plot_id, biosample_id
    )
    where asset_id is null;

create table if not exists brd_dataset_assay_link (
    id bigserial primary key,
    dataset_id integer not null,
    version_id integer not null,
    asset_id integer not null,
    assay_id bigint not null,
    role varchar(32) not null,
    mapping_status varchar(32) not null default 'draft',
    mapping_method varchar(32) not null default 'manual',
    confidence varchar(16),
    is_primary boolean not null default false,
    note text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    created_by bigint,
    updated_by bigint,
    constraint fk_brd_dataset_assay_link_dataset
        foreign key (dataset_id) references dataset_registry (id) on delete restrict,
    constraint fk_brd_dataset_assay_link_version
        foreign key (version_id) references dataset_version (id) on delete restrict,
    constraint fk_brd_dataset_assay_link_asset
        foreign key (asset_id) references dataset_asset (id) on delete restrict,
    constraint fk_brd_dataset_assay_link_assay
        foreign key (assay_id) references brd_assay (id) on delete restrict,
    constraint ck_brd_dataset_assay_link_mapping_status check (
        mapping_status in ('draft', 'matched', 'reviewed', 'rejected')
    ),
    constraint ck_brd_dataset_assay_link_mapping_method check (
        mapping_method in ('manual', 'rule', 'import', 'inferred')
    ),
    constraint ck_brd_dataset_assay_link_confidence check (
        confidence is null or confidence in ('low', 'medium', 'high')
    )
);

create unique index if not exists uq_brd_dataset_assay_link_asset_assay_role
    on brd_dataset_assay_link (asset_id, assay_id, role);
create index if not exists ix_brd_dataset_assay_link_assay_role
    on brd_dataset_assay_link (assay_id, role);
create index if not exists ix_brd_dataset_assay_link_version_asset
    on brd_dataset_assay_link (version_id, asset_id);

create table if not exists brd_variant_sample_map (
    id bigserial primary key,
    dataset_id integer not null,
    version_id integer not null,
    asset_id integer not null,
    vcf_sample_name varchar(256) not null,
    normalized_sample_name varchar(256),
    sample_alias varchar(256),
    material_id bigint,
    biosample_id bigint,
    plot_id bigint,
    mapping_status varchar(32) not null default 'draft',
    mapping_method varchar(32) not null default 'manual',
    confidence varchar(16),
    is_primary boolean not null default false,
    note text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    created_by bigint,
    updated_by bigint,
    constraint fk_brd_variant_sample_map_dataset
        foreign key (dataset_id) references dataset_registry (id) on delete restrict,
    constraint fk_brd_variant_sample_map_version
        foreign key (version_id) references dataset_version (id) on delete restrict,
    constraint fk_brd_variant_sample_map_asset
        foreign key (asset_id) references dataset_asset (id) on delete restrict,
    constraint fk_brd_variant_sample_map_material
        foreign key (material_id) references brd_material (id) on delete set null,
    constraint fk_brd_variant_sample_map_biosample
        foreign key (biosample_id) references brd_biosample (id) on delete set null,
    constraint fk_brd_variant_sample_map_plot
        foreign key (plot_id) references brd_plot (id) on delete set null,
    constraint ck_brd_variant_sample_map_mapping_status check (
        mapping_status in ('draft', 'matched', 'reviewed', 'rejected')
    ),
    constraint ck_brd_variant_sample_map_mapping_method check (
        mapping_method in ('manual', 'rule', 'import', 'inferred')
    ),
    constraint ck_brd_variant_sample_map_confidence check (
        confidence is null or confidence in ('low', 'medium', 'high')
    )
);

create unique index if not exists uq_brd_variant_sample_map_asset_sample
    on brd_variant_sample_map (asset_id, vcf_sample_name);
create index if not exists ix_brd_variant_sample_map_material
    on brd_variant_sample_map (material_id);
create index if not exists ix_brd_variant_sample_map_biosample
    on brd_variant_sample_map (biosample_id);
create index if not exists ix_brd_variant_sample_map_status
    on brd_variant_sample_map (mapping_status);

create table if not exists brd_phenotype_subject_map (
    id bigserial primary key,
    dataset_id integer not null,
    version_id integer not null,
    asset_id integer not null,
    row_key varchar(128) not null,
    trial_id bigint,
    plot_id bigint,
    material_id bigint,
    trait_code varchar(32),
    obs_date date,
    mapping_status varchar(32) not null default 'draft',
    mapping_method varchar(32) not null default 'manual',
    confidence varchar(16),
    is_primary boolean not null default false,
    note text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    created_by bigint,
    updated_by bigint,
    constraint fk_brd_phenotype_subject_map_dataset
        foreign key (dataset_id) references dataset_registry (id) on delete restrict,
    constraint fk_brd_phenotype_subject_map_version
        foreign key (version_id) references dataset_version (id) on delete restrict,
    constraint fk_brd_phenotype_subject_map_asset
        foreign key (asset_id) references dataset_asset (id) on delete restrict,
    constraint fk_brd_phenotype_subject_map_trial
        foreign key (trial_id) references brd_trial (id) on delete set null,
    constraint fk_brd_phenotype_subject_map_plot
        foreign key (plot_id) references brd_plot (id) on delete set null,
    constraint fk_brd_phenotype_subject_map_material
        foreign key (material_id) references brd_material (id) on delete set null,
    constraint ck_brd_phenotype_subject_map_mapping_status check (
        mapping_status in ('draft', 'matched', 'reviewed', 'rejected')
    ),
    constraint ck_brd_phenotype_subject_map_mapping_method check (
        mapping_method in ('manual', 'rule', 'import', 'inferred')
    ),
    constraint ck_brd_phenotype_subject_map_confidence check (
        confidence is null or confidence in ('low', 'medium', 'high')
    )
);

create unique index if not exists uq_brd_phenotype_subject_map_asset_row
    on brd_phenotype_subject_map (asset_id, row_key);
create index if not exists ix_brd_phenotype_subject_map_plot_trait
    on brd_phenotype_subject_map (plot_id, trait_code);
create index if not exists ix_brd_phenotype_subject_map_material_trait
    on brd_phenotype_subject_map (material_id, trait_code);
create index if not exists ix_brd_phenotype_subject_map_status
    on brd_phenotype_subject_map (mapping_status);

commit;
