from sqlalchemy import Boolean, Column, Integer, String, Text, BigInteger, ForeignKey
from sqlalchemy.orm import relationship

from db.database import Base


class Databases(Base):
    __tablename__ = "databases"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(320), comment='名称')
    user_id = Column(Integer, comment='用户ID')
    type = Column(String(320), default='1', comment='数据类型')
    status = Column(Integer, default=0, comment='状态')
    is_public = Column(Boolean, default=0, comment='是否公共')
    is_active = Column(Boolean, default=0, comment='是否激活')
    is_delete = Column(Boolean, default=0, comment='是否删除')
    create_time = Column(Integer, comment='创建时间')
    remark = Column(String(320), comment='备注')
    file = relationship("DatabasesFile", back_populates="databases",uselist=False, cascade="all, delete-orphan",lazy="selectin")
    metas = relationship("DatabasesMeta", back_populates="databases", uselist=False, cascade="all, delete-orphan", lazy="selectin")

    def to_dict(self):
        model_dict = dict(self.__dict__)
        del model_dict['_sa_instance_state']
        return model_dict

    @classmethod
    def get_field(cls):
        return {column.name: column.comment for column in cls.__table__.columns}


class DatabasesMeta(Base):
    __tablename__ = "databases_metadata"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(250), comment="元数据名称")
    value = Column(String(250), comment="元数据值")
    code = Column(String(250), comment="元数据值")
    type = Column(String(250), comment="类型")
    description = Column(Text, comment="描述")
    create_time = Column(Integer, comment='创建时间')
    database_id = Column(Integer, ForeignKey('databases.id'), comment='database ID')
    databases = relationship("Databases", back_populates="metas")

    def to_dict(self):
        model_dict = dict(self.__dict__)
        del model_dict['_sa_instance_state']
        return model_dict

    @classmethod
    def get_field(cls):
        return {column.name: column.comment for column in cls.__table__.columns}


class DatabasesFile(Base):
    __tablename__ = "databases_file"
    id = Column(Integer, primary_key=True, index=True)
    uid = Column(String(320), comment='UID')
    size = Column(BigInteger, default=0, comment='size')
    name = Column(String(320), comment='文件名称')
    file_name = Column(String(320), comment='备注')
    url = Column(String(320), comment='url')
    path = Column(String(320), comment='路径')
    type = Column(String(320), comment='类型')
    data_type = Column(String(320), comment='数据类型')
    database_id = Column(Integer, ForeignKey('databases.id'), comment='database ID')
    status = Column(Integer, default=0, comment='状态')
    create_time = Column(Integer, comment='创建时间')
    meta_json = Column(Text, comment='元数据Json')
    databases = relationship("Databases", back_populates="file")
    # databases = relationship("Databases", back_populates="file",primaryjoin="DatabasesFile.database_id == Databases.id") # 手动关联

    def to_dict(self):
        model_dict = dict(self.__dict__)
        del model_dict['_sa_instance_state']
        return model_dict

    @classmethod
    def get_field(cls):
        return {column.name: column.comment for column in cls.__table__.columns}


class ProjectDatabasesLink(Base):
    """数据集表"""
    __tablename__ = "project_database"
    id = Column(Integer, primary_key=True, index=True)
    database_id = Column(Integer, comment='database ID')
    project_id = Column(Integer, comment='project ID')
