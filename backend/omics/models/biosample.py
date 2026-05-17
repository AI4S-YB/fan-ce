from sqlalchemy import Column, Integer, String, DateTime, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from omics.db.db import Base
from datetime import datetime

class BioSample(Base):
    __tablename__ = "biosample"

    id = Column(Integer, primary_key=True)
    accession = Column(String, unique=True, index=True)  # 样本编号，如SAMN123456
    title = Column(String, nullable=False)  # 样本标题
    description = Column(Text)  # 样本描述
    organism = Column(String, nullable=False)  # 物种名称
    status = Column(String, default="active")  # 状态
    last_update = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 最后更新
    
    # 外键关联
    project_id = Column(Integer, ForeignKey("bioproject.id"), nullable=False)
    
    # 关联关系
    project = relationship("BioProject", back_populates="samples")
    experiments = relationship("Experiment", back_populates="sample", cascade="all, delete")
    enhancements = relationship("BioSampleEnhancement", back_populates="sample", cascade="all, delete")

class BioSampleEnhancement(Base):
    __tablename__ = "biosample_enhancement"

    id = Column(Integer, primary_key=True)
    sample_id = Column(Integer, ForeignKey("biosample.id"))
    key = Column(String, nullable=False)  # 属性键名
    value = Column(Text)  # 属性值
    category = Column(String)  # 分类：organism_info, location, environment, collection, treatment等

    sample = relationship("BioSample", back_populates="enhancements")