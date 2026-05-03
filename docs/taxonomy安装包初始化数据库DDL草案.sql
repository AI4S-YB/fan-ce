-- taxonomy 安装包与系统初始化数据库 DDL 草案
-- 说明：
-- 1. 本草案只覆盖“安装层”表，不重复定义已存在的 brd_taxonomy_* 主数据表
-- 2. 命名采用 sys_* 前缀，表示平台级系统初始化设施
-- 3. 默认目标数据库为 PostgreSQL

CREATE TABLE IF NOT EXISTS sys_install_package (
    id BIGSERIAL PRIMARY KEY,
    package_code VARCHAR(64) NOT NULL UNIQUE,
    package_type VARCHAR(32) NOT NULL,
    package_name VARCHAR(256) NOT NULL,
    source VARCHAR(32) NOT NULL,
    source_version VARCHAR(128),
    storage_path TEXT NOT NULL,
    file_size BIGINT,
    sha256 VARCHAR(128),
    manifest_json TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'ready',
    created_by BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_sys_install_package_type_status
    ON sys_install_package (package_type, status);

CREATE INDEX IF NOT EXISTS ix_sys_install_package_source_version
    ON sys_install_package (source, source_version);


CREATE TABLE IF NOT EXISTS sys_install_job (
    id BIGSERIAL PRIMARY KEY,
    job_type VARCHAR(32) NOT NULL,
    package_id BIGINT REFERENCES sys_install_package(id) ON DELETE RESTRICT,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    stage VARCHAR(64),
    progress_percent NUMERIC(5, 2) NOT NULL DEFAULT 0,
    processed_count BIGINT,
    total_count BIGINT,
    message TEXT,
    error_message TEXT,
    result_json TEXT,
    created_by BIGINT,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_sys_install_job_type_status
    ON sys_install_job (job_type, status);

CREATE INDEX IF NOT EXISTS ix_sys_install_job_created_at
    ON sys_install_job (created_at DESC);

CREATE INDEX IF NOT EXISTS ix_sys_install_job_package_id
    ON sys_install_job (package_id);


CREATE TABLE IF NOT EXISTS sys_install_lock (
    lock_code VARCHAR(64) PRIMARY KEY,
    is_locked INTEGER NOT NULL DEFAULT 1,
    reason VARCHAR(256),
    required_action VARCHAR(128),
    payload_json TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- taxonomy 初始化的默认锁
INSERT INTO sys_install_lock (lock_code, is_locked, reason, required_action)
VALUES ('taxonomy_required', 1, 'taxonomy 未安装', 'install_taxonomy')
ON CONFLICT (lock_code) DO NOTHING;


-- 可选：平台级安装状态视图
CREATE OR REPLACE VIEW vw_taxonomy_install_status AS
SELECT
    l.lock_code,
    l.is_locked,
    l.reason,
    l.required_action,
    p.id AS current_package_id,
    p.package_code,
    p.package_name,
    p.package_type,
    p.source,
    p.source_version,
    j.id AS latest_job_id,
    j.status AS latest_job_status,
    j.stage AS latest_job_stage,
    j.progress_percent AS latest_job_progress_percent,
    s.id AS snapshot_id,
    s.source_name,
    s.source_version AS snapshot_source_version,
    s.node_count,
    s.name_count,
    s.loaded_at
FROM sys_install_lock l
LEFT JOIN LATERAL (
    SELECT *
    FROM sys_install_package
    WHERE package_type IN ('taxonomy_bundle', 'taxonomy_raw_dump')
    ORDER BY id DESC
    LIMIT 1
) p ON TRUE
LEFT JOIN LATERAL (
    SELECT *
    FROM sys_install_job
    WHERE job_type = 'taxonomy_import'
    ORDER BY id DESC
    LIMIT 1
) j ON TRUE
LEFT JOIN LATERAL (
    SELECT *
    FROM brd_taxonomy_source_snapshot
    ORDER BY id DESC
    LIMIT 1
) s ON TRUE
WHERE l.lock_code = 'taxonomy_required';


-- 可选：更新时间触发器函数
CREATE OR REPLACE FUNCTION set_row_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_sys_install_package_updated_at ON sys_install_package;
CREATE TRIGGER trg_sys_install_package_updated_at
BEFORE UPDATE ON sys_install_package
FOR EACH ROW
EXECUTE FUNCTION set_row_updated_at();

DROP TRIGGER IF EXISTS trg_sys_install_job_updated_at ON sys_install_job;
CREATE TRIGGER trg_sys_install_job_updated_at
BEFORE UPDATE ON sys_install_job
FOR EACH ROW
EXECUTE FUNCTION set_row_updated_at();

DROP TRIGGER IF EXISTS trg_sys_install_lock_updated_at ON sys_install_lock;
CREATE TRIGGER trg_sys_install_lock_updated_at
BEFORE UPDATE ON sys_install_lock
FOR EACH ROW
EXECUTE FUNCTION set_row_updated_at();
