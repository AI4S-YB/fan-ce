"""Analysis framework database models."""
import time
from sqlalchemy import Column, Integer, String, Text, BigInteger
from shared.pgorm.connect import pgsql_db

Base = pgsql_db.Base


class BrdAnalysisJob(Base):
    __tablename__ = "brd_analysis_job"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tool_id = Column(String(128), nullable=False, comment="工具ID")
    status = Column(String(32), nullable=False, default="pending",
                    comment="pending|running|success|failed|timeout|cancelled")
    input_bindings = Column(Text, nullable=False, default="{}", comment="JSON: {param: asset_file_id}")
    param_overrides = Column(Text, nullable=False, default="{}", comment="JSON: {param: value}")
    output_files = Column(Text, comment="JSON: [{name, path, size}]")
    work_dir = Column(String(1024), comment="临时工作目录")
    command_log = Column(Text, comment="执行的命令")
    exit_code = Column(Integer, comment="进程退出码")
    error_message = Column(Text, comment="错误信息")
    created_by = Column(BigInteger, comment="创建者用户ID，NULL为匿名")
    created_at = Column(Integer, default=lambda: int(time.time()))
    started_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))
