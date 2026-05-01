from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from basis.db.db import Base
from datetime import datetime

class BioProject(Base):
    __tablename__ = "bioproject"

    # 基础属性
    id = Column(Integer, primary_key=True, index=True)
    accession = Column(String, unique=True, index=True)  # 项目编号，如PRJNA123456
    title = Column(String, nullable=False)  # 项目标题
    description = Column(Text)  # 项目描述
    status = Column(String, default="active")  # 状态：active, inactive, pending
    is_public = Column(Boolean, default=True)  # 是否公开
    last_update = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 最后更新
    
    # 关联关系
    samples = relationship("BioSample", back_populates="project", cascade="all, delete")
    enhancements = relationship("BioProjectEnhancement", back_populates="project", cascade="all, delete")

class BioProjectEnhancement(Base):
    __tablename__ = "bioproject_enhancement"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("bioproject.id"))
    term_id = Column(String)  # 术语ID
    term_name = Column(String)  # 术语名称
    term_description = Column(Text)  # 术语描述
    value = Column(String)  # 值
    category = Column(String)  # 分类：organism, project_type, data_type, methodology, objective, relevance, submitter_info, dates等

    project = relationship("BioProject", back_populates="enhancements")