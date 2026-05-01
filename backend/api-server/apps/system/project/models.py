from sqlalchemy import Boolean, Column, Integer, String, Text

from db.database import Base


class Project(Base):
    __tablename__ = "system_project"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(320), comment='项目名称')
    code = Column(String(320), comment='项目code,唯一')
    user_id = Column(Integer, comment='用户ID')
    type = Column(String(320), comment='类型')
    sort = Column(Integer, comment='显示顺序')
    status = Column(Integer, default=0, comment='状态')
    is_public = Column(Boolean, default=0, comment='是否激活')
    is_active = Column(Boolean, default=0, comment='是否激活')
    is_delete = Column(Boolean, default=0, comment='是否删除')
    create_time = Column(Integer, comment='创建时间')
    remark = Column(String(320), comment='备注')
    meta_json = Column(Text, comment="元数据json")

    def to_dict(self):
        model_dict = dict(self.__dict__)
        del model_dict['_sa_instance_state']
        return model_dict

    @classmethod
    def get_field(cls):
        return {column.name: column.comment for column in cls.__table__.columns}


class ProjectMeta(Base):
    __tablename__ = "system_project_meta"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, comment="项目ID")
    term_id = Column(String(250), comment="# 术语名称")
    term_name = Column(String(250), comment='# 术语名称')
    term_description = Column(Text, comment="# 术语描述")
    value = Column(Text, comment="# 值")
    category = Column(String(250))

    def to_dict(self):
        model_dict = dict(self.__dict__)
        del model_dict['_sa_instance_state']
        return model_dict

    @classmethod
    def get_field(cls):
        return {column.name: column.comment for column in cls.__table__.columns}
