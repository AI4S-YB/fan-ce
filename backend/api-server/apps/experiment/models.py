"""
@Author  : llq
@Time    : 2024/10/8 17:34
@Function:
@version :  1.0
@Desc    :  None
"""
from sqlalchemy import Boolean, Column, Integer, String, Text, ForeignKey, Float
import time
from db.database import Base


class Experiment(Base):
    __tablename__ = "abd_experiment"
    id = Column(Integer, primary_key=True, index=True)
    accession = Column(String(255), unique=True, index=True, comment='# 实验编号，如SRX123456')
    title = Column(String(255), comment=' # 实验标题')
    experiment_type = Column(String(255), comment=' # 实验类型：RNA-Seq, DNA-Seq, ChIP-Seq等')
    library_strategy = Column(String(255), comment=' # 文库策略：WGS, RNA-Seq, ChIP-Seq等')
    library_source = Column(String(255), comment='# 文库来源：GENOMIC, TRANSCRIPTOMIC, METAGENOMIC等')
    library_selection = Column(String(255), comment=' # 文库选择：RANDOM, PCR, ChIP等')
    library_layout = Column(String(255), comment='# 文库布局：SINGLE, PAIRED')
    platform = Column(String(255), comment='# 测序平台：ILLUMINA, PACBIO, OXFORD_NANOPORE等')
    instrument_model = Column(String(255), comment='# 仪器型号：HiSeq 2500, NovaSeq 6000等')
    design_description = Column(Text, comment='# 设计描述')
    library_construction_protocol = Column(Text, comment='# 文库构建协议')
    read_length = Column(Integer, comment='# 读长')
    insert_size = Column(Integer, comment='# 插入片段大小')
    total_reads = Column(Integer, comment=' # 总读数')
    total_bases = Column(Integer, comment='# 总碱基数')
    gc_content = Column(Float, comment='# GC含量')
    quality_score = Column(Float, comment='# 质量分数')
    adapter_sequence = Column(String(255), comment='# 接头序列')
    primer_sequence = Column(String(255), comment='# 引物序列')
    target_gene = Column(String(255), comment='# 目标基因')
    target_region = Column(String(255), comment='# 目标区域')
    enrichment_method = Column(String(255), comment='# 富集方法')
    amplification_method = Column(String(255), comment='# 扩增方法')
    sequencing_center = Column(String(255), comment='# 测序中心')
    run_date = Column(Integer, comment='# 运行日期')
    submission_date = Column(Integer, comment='提交日期')
    last_update = Column(Integer, comment='# 最后更新')
    status = Column(String(250), default=" # 状态")
    is_public = Column(Boolean, default=True, comment=' # 是否公开')
    user_id = Column(Integer, comment="用户ID")
    sample_id = Column(Integer, comment="样本ID")
    is_delete = Column(Boolean, default=0, comment='是否删除')
    create_time = Column(Integer,default=int(time.time()), comment='创建时间')
    update_time = Column(Integer, comment='更新时间')
    description = Column(Text, comment="样本描述")
    meta_json = Column(Text, comment="元数据json")


    def to_dict(self):
        model_dict = dict(self.__dict__)
        del model_dict['_sa_instance_state']
        return model_dict

    @classmethod
    def get_field(cls):
        return {column.name: column.comment for column in cls.__table__.columns}



class EnhancementMeta(Base):
    __tablename__ = "abd_experiment_meta"
    id = Column(Integer, primary_key=True, index=True)
    experiment_id = Column(Integer, comment="样本ID")
    key = Column(String(320), comment='属性键名')
    value = Column(Text, comment='属性值')
    category = Column(String(250), comment="分类")
    description = Column(Text, comment="样本描述")
    create_time = Column(Integer, comment='创建时间')

    def to_dict(self):
        model_dict = dict(self.__dict__)
        del model_dict['_sa_instance_state']
        return model_dict

    @classmethod
    def get_field(cls):
        return {column.name: column.comment for column in cls.__table__.columns}


