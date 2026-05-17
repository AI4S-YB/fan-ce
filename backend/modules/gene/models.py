"""
@Author  : llq
@Time    : 2024/10/8 17:34
@Function:
@version :  1.0
@Desc    :  None
"""
from sqlalchemy import Boolean, Column, Integer, String, Text

from shared.database import Base


class GeneSet(Base):
    __tablename__ = "gene_set"
    id = Column(Integer, primary_key=True)
    name = Column(String(320), comment='基因集名称', nullable=False)
    description = Column(Text, comment="基因集描述")
    user_id = Column(Integer, comment='创建用户ID')
    project_id = Column(Integer, comment='项目ID')
    create_time = Column(DateTime(timezone=True), comment='创建时间')
    is_delete = Column(Boolean, default=0, comment='是否删除')


    def to_dict(self):
        model_dict = dict(self.__dict__)
        del model_dict['_sa_instance_state']
        return model_dict

    @classmethod
    def get_field(cls):
        return {column.name: column.comment for column in cls.__table__.columns}



class GeneSetLink(Base):
    __tablename__ = "gene_set_link"
    id = Column(Integer, primary_key=True)
    file_path = Column(String(500), comment="基因组文件路径", nullable=False)
    geneset_id = Column(Integer, comment="基因集ID", nullable=False)
    gene_id = Column(String(320), comment="基因ID", nullable=False)
    create_time = Column(DateTime(timezone=True), comment='创建时间')
    added_at = Column(Integer, comment='添加时间')
    is_delete = Column(Boolean, default=0, comment='是否删除')


    def to_dict(self):
        model_dict = dict(self.__dict__)
        del model_dict['_sa_instance_state']
        return model_dict

    @classmethod
    def get_field(cls):
        return {column.name: column.comment for column in cls.__table__.columns}
