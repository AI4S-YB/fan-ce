from sqlalchemy import Column, DateTime, Integer, String, Text, func

from shared.database import Base


class Dataset(Base):
    __tablename__ = "dataset"

    id = Column(Integer, primary_key=True, index=True)
    dataset_code = Column(String(128), unique=True, index=True, nullable=False, comment="稳定数据集编码")
    dataset_type = Column(String(128), index=True, comment="数据集类型")
    organism = Column(String(128), index=True, comment="物种")
    assembly = Column(String(128), comment="组装版本")
    visibility = Column(String(32), nullable=False, default="private", comment="可见性")
    lifecycle_state = Column(String(64), nullable=False, default="draft", comment="生命周期状态")
    team_id = Column(Integer, index=True, comment="团队 ID")
    meta_json = Column(Text, comment="扩展元数据")
    create_time = Column(DateTime, server_default=func.now(), comment="创建时间")
    update_time = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
