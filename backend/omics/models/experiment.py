from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from omics.db.db import Base
from datetime import datetime

class Experiment(Base):
    __tablename__ = "experiment"

    id = Column(Integer, primary_key=True)
    accession = Column(String, unique=True, index=True)  # 实验编号，如SRX123456
    title = Column(String, nullable=False)  # 实验标题
    description = Column(Text)  # 实验描述
    experiment_type = Column(String, nullable=False)  # 实验类型：RNA-Seq, DNA-Seq, ChIP-Seq等
    library_strategy = Column(String)  # 文库策略：WGS, RNA-Seq, ChIP-Seq等
    library_source = Column(String)  # 文库来源：GENOMIC, TRANSCRIPTOMIC, METAGENOMIC等
    library_selection = Column(String)  # 文库选择：RANDOM, PCR, ChIP等
    library_layout = Column(String)  # 文库布局：SINGLE, PAIRED
    platform = Column(String)  # 测序平台：ILLUMINA, PACBIO, OXFORD_NANOPORE等
    instrument_model = Column(String)  # 仪器型号：HiSeq 2500, NovaSeq 6000等
    design_description = Column(Text)  # 设计描述
    library_construction_protocol = Column(Text)  # 文库构建协议
    read_length = Column(Integer)  # 读长
    insert_size = Column(Integer)  # 插入片段大小
    total_reads = Column(Integer)  # 总读数
    total_bases = Column(Integer)  # 总碱基数
    gc_content = Column(Float)  # GC含量
    quality_score = Column(Float)  # 质量分数
    adapter_sequence = Column(String)  # 接头序列
    primer_sequence = Column(String)  # 引物序列
    target_gene = Column(String)  # 目标基因
    target_region = Column(String)  # 目标区域
    enrichment_method = Column(String)  # 富集方法
    amplification_method = Column(String)  # 扩增方法
    sequencing_center = Column(String)  # 测序中心
    run_date = Column(DateTime)  # 运行日期
    submission_date = Column(DateTime, default=datetime.utcnow)  # 提交日期
    last_update = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  # 最后更新
    status = Column(String, default="active")  # 状态
    is_public = Column(Boolean, default=True)  # 是否公开
    
    # 外键关联
    sample_id = Column(Integer, ForeignKey("biosample.id"), nullable=False)
    
    # 关联关系
    sample = relationship("BioSample", back_populates="experiments")
    runs = relationship("ExperimentRun", back_populates="experiment", cascade="all, delete")
    enhancements = relationship("ExperimentEnhancement", back_populates="experiment", cascade="all, delete")

class ExperimentRun(Base):
    __tablename__ = "experiment_run"

    id = Column(Integer, primary_key=True)
    accession = Column(String, unique=True, index=True)  # 运行编号，如SRR123456
    file_name = Column(String)  # 文件名
    file_path = Column(String)  # 文件路径
    file_size = Column(Integer)  # 文件大小
    file_type = Column(String)  # 文件类型：fastq, sra, bam等
    md5_checksum = Column(String)  # MD5校验和
    read_count = Column(Integer)  # 读数
    base_count = Column(Integer)  # 碱基数
    run_date = Column(DateTime)  # 运行日期
    submission_date = Column(DateTime, default=datetime.utcnow)  # 提交日期
    
    # 外键关联
    experiment_id = Column(Integer, ForeignKey("experiment.id"), nullable=False)
    
    # 关联关系
    experiment = relationship("Experiment", back_populates="runs")

class ExperimentEnhancement(Base):
    __tablename__ = "experiment_enhancement"

    id = Column(Integer, primary_key=True)
    experiment_id = Column(Integer, ForeignKey("experiment.id"))
    term_id = Column(String)  # 术语ID
    term_name = Column(String)  # 术语名称
    term_description = Column(Text)  # 术语描述
    value = Column(String)  # 值
    category = Column(String)  # 分类：protocol, quality_control, analysis等

    experiment = relationship("Experiment", back_populates="enhancements")