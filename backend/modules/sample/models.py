"""
@Author  : llq
@Time    : 2024/10/8 17:34
@Function:
@version :  1.0
@Desc    :  None
"""
from sqlalchemy import Boolean, Column, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from shared.database import Base


class Sample(Base):
    __tablename__ = "abd_sample"
    id = Column(Integer, primary_key=True)
    sample_name = Column(String(320), comment='名称')
    sample_code = Column(String(320), comment='样本编号')
    type = Column(String(320), default='1', comment='类型')
    is_public = Column(Boolean, default=True)
    project_id = Column(Integer,comment="项目ID")
    user_id = Column(Integer, comment="项目ID")
    status = Column(Integer, default=0, comment='状态')
    is_delete = Column(Boolean, default=0, comment='是否删除')
    create_time = Column(Integer, comment='创建时间')
    update_time = Column(Integer, comment='更新时间')
    description = Column(Text,comment="样本描述")
    meta_json = Column(JSONB, comment="元数据json")

    def to_dict(self):
        model_dict = dict(self.__dict__)
        del model_dict['_sa_instance_state']
        return model_dict

    @classmethod
    def get_field(cls):
        return {column.name: column.comment for column in cls.__table__.columns}


class SampleMeta(Base):
    __tablename__ = "abd_sample_meta"
    id = Column(Integer, primary_key=True)
    sample_id = Column(Integer, comment="样本ID")
    key = Column(String(320), comment='属性键名')
    value = Column(Text, comment='属性值')
    category = Column(String(250), comment="分类")
    create_time = Column(Integer, comment='创建时间')
    description = Column(Text, comment="样本描述")

    def to_dict(self):
        model_dict = dict(self.__dict__)
        del model_dict['_sa_instance_state']
        return model_dict

    @classmethod
    def get_field(cls):
        return {column.name: column.comment for column in cls.__table__.columns}
