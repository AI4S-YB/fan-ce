-- phenome 平台索引层 PostgreSQL DDL 草案
--
-- 目标：
-- 1. 为 phenome dataset 提供第一版平台级结构化索引表
-- 2. 保持与 Dataset 域、Breeding 域解耦
-- 3. 支持从 phenotype 宽表文件重建 subject / trait / observation 索引
--
-- 假设：
-- - Dataset 域表名为：
--   - dataset_registry
--   - dataset_version
--   - dataset_asset
-- - Dataset 域主键当前为 integer
-- - phenome 索引表主键使用 bigserial

begin;

create table if not exists phn_import_run (
    id bigserial primary key,
    dataset_id integer not null,
    version_id integer not null,
    asset_id integer not null,
    source_file_path text,
    source_checksum varchar(128),
    parser_name varchar(64) not null default 'phenome-importer',
    parser_version varchar(64),
    sheet_count integer,
    row_count integer,
    trait_count integer,
    observation_count integer,
    status varchar(32) not null default 'success',
    summary_json jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    created_by bigint,
    updated_by bigint,
    constraint fk_phn_import_run_dataset
        foreign key (dataset_id) references dataset_registry (id) on delete restrict,
    constraint fk_phn_import_run_version
        foreign key (version_id) references dataset_version (id) on delete restrict,
    constraint fk_phn_import_run_asset
        foreign key (asset_id) references dataset_asset (id) on delete restrict,
    constraint ck_phn_import_run_sheet_count check (sheet_count is null or sheet_count >= 0),
    constraint ck_phn_import_run_row_count check (row_count is null or row_count >= 0),
    constraint ck_phn_import_run_trait_count check (trait_count is null or trait_count >= 0),
    constraint ck_phn_import_run_observation_count check (observation_count is null or observation_count >= 0),
    constraint ck_phn_import_run_status check (
        status in ('running', 'success', 'failed', 'replaced')
    )
);

create index if not exists ix_phn_import_run_dataset_version_asset_created
    on phn_import_run (dataset_id, version_id, asset_id, created_at desc);


create table if not exists phn_subject (
    id bigserial primary key,
    dataset_id integer not null,
    version_id integer not null,
    asset_id integer not null,
    import_run_id bigint not null,
    subject_id varchar(128) not null,
    subject_name varchar(256),
    subject_name_cn varchar(256),
    subject_name_en varchar(256),
    subject_type varchar(32) not null default 'material_candidate',
    source_sheet varchar(128),
    source_row_key varchar(256) not null,
    meta_json jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint fk_phn_subject_dataset
        foreign key (dataset_id) references dataset_registry (id) on delete restrict,
    constraint fk_phn_subject_version
        foreign key (version_id) references dataset_version (id) on delete restrict,
    constraint fk_phn_subject_asset
        foreign key (asset_id) references dataset_asset (id) on delete restrict,
    constraint fk_phn_subject_import_run
        foreign key (import_run_id) references phn_import_run (id) on delete cascade,
    constraint uq_phn_subject_asset_subject_row unique (asset_id, subject_id, source_row_key),
    constraint ck_phn_subject_type check (
        subject_type in ('material_candidate', 'plot_candidate', 'trial_candidate', 'sample_candidate', 'generic_subject')
    )
);

create index if not exists ix_phn_subject_dataset_version_subject
    on phn_subject (dataset_id, version_id, subject_id);
create index if not exists ix_phn_subject_asset_row_key
    on phn_subject (asset_id, source_row_key);


create table if not exists phn_trait (
    id bigserial primary key,
    dataset_id integer not null,
    version_id integer not null,
    asset_id integer not null,
    import_run_id bigint not null,
    trait_code varchar(128) not null,
    trait_name varchar(256) not null,
    trait_name_cn varchar(256),
    trait_name_en varchar(256),
    value_type varchar(32) not null,
    unit varchar(64),
    time_axis_type varchar(32) not null default 'none',
    category_group varchar(128),
    display_order integer,
    meta_json jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint fk_phn_trait_dataset
        foreign key (dataset_id) references dataset_registry (id) on delete restrict,
    constraint fk_phn_trait_version
        foreign key (version_id) references dataset_version (id) on delete restrict,
    constraint fk_phn_trait_asset
        foreign key (asset_id) references dataset_asset (id) on delete restrict,
    constraint fk_phn_trait_import_run
        foreign key (import_run_id) references phn_import_run (id) on delete cascade,
    constraint uq_phn_trait_asset_code unique (asset_id, trait_code),
    constraint ck_phn_trait_value_type check (
        value_type in ('numeric', 'categorical', 'text')
    ),
    constraint ck_phn_trait_time_axis_type check (
        time_axis_type in ('none', 'year', 'date', 'season', 'timepoint')
    ),
    constraint ck_phn_trait_display_order check (
        display_order is null or display_order >= 0
    )
);

create index if not exists ix_phn_trait_dataset_version_name
    on phn_trait (dataset_id, version_id, trait_name);
create index if not exists ix_phn_trait_dataset_version_category
    on phn_trait (dataset_id, version_id, category_group);


create table if not exists phn_source_column (
    id bigserial primary key,
    dataset_id integer not null,
    version_id integer not null,
    asset_id integer not null,
    import_run_id bigint not null,
    source_sheet varchar(128) not null,
    source_column_name varchar(256) not null,
    source_column_index integer,
    trait_id bigint not null,
    trait_code varchar(128) not null,
    timepoint varchar(64),
    parse_rule varchar(128),
    meta_json jsonb,
    created_at timestamptz not null default now(),
    constraint fk_phn_source_column_dataset
        foreign key (dataset_id) references dataset_registry (id) on delete restrict,
    constraint fk_phn_source_column_version
        foreign key (version_id) references dataset_version (id) on delete restrict,
    constraint fk_phn_source_column_asset
        foreign key (asset_id) references dataset_asset (id) on delete restrict,
    constraint fk_phn_source_column_import_run
        foreign key (import_run_id) references phn_import_run (id) on delete cascade,
    constraint fk_phn_source_column_trait
        foreign key (trait_id) references phn_trait (id) on delete cascade,
    constraint uq_phn_source_column_asset_sheet_column unique (asset_id, source_sheet, source_column_name),
    constraint ck_phn_source_column_index check (
        source_column_index is null or source_column_index >= 0
    )
);

create index if not exists ix_phn_source_column_asset_trait_timepoint
    on phn_source_column (asset_id, trait_code, timepoint);


create table if not exists phn_observation (
    id bigserial primary key,
    dataset_id integer not null,
    version_id integer not null,
    asset_id integer not null,
    import_run_id bigint not null,
    subject_pk bigint not null,
    trait_id bigint not null,
    trait_code varchar(128) not null,
    timepoint varchar(64),
    obs_date date,
    value_numeric numeric(20, 6),
    value_text text,
    value_category varchar(256),
    raw_value text,
    is_missing boolean not null default false,
    source_sheet varchar(128),
    source_row_key varchar(256) not null,
    source_column_name varchar(256) not null,
    qc_status varchar(32) not null default 'raw',
    meta_json jsonb,
    created_at timestamptz not null default now(),
    constraint fk_phn_observation_dataset
        foreign key (dataset_id) references dataset_registry (id) on delete restrict,
    constraint fk_phn_observation_version
        foreign key (version_id) references dataset_version (id) on delete restrict,
    constraint fk_phn_observation_asset
        foreign key (asset_id) references dataset_asset (id) on delete restrict,
    constraint fk_phn_observation_import_run
        foreign key (import_run_id) references phn_import_run (id) on delete cascade,
    constraint fk_phn_observation_subject
        foreign key (subject_pk) references phn_subject (id) on delete cascade,
    constraint fk_phn_observation_trait
        foreign key (trait_id) references phn_trait (id) on delete cascade,
    constraint ck_phn_observation_qc_status check (
        qc_status in ('raw', 'parsed', 'reviewed', 'rejected')
    ),
    constraint ck_phn_observation_value_presence check (
        is_missing
        or num_nonnulls(value_numeric, value_text, value_category, raw_value) >= 1
    )
);

create index if not exists ix_phn_observation_dataset_version_subject
    on phn_observation (dataset_id, version_id, subject_pk);
create index if not exists ix_phn_observation_dataset_version_trait
    on phn_observation (dataset_id, version_id, trait_code);
create index if not exists ix_phn_observation_dataset_version_trait_timepoint
    on phn_observation (dataset_id, version_id, trait_code, timepoint);
create index if not exists ix_phn_observation_asset_sheet_row
    on phn_observation (asset_id, source_sheet, source_row_key);
create index if not exists ix_phn_observation_dataset_version_qc
    on phn_observation (dataset_id, version_id, qc_status);

commit;
