from sqlalchemy import Boolean, Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from db.database import Base


class Team(Base):
    __tablename__ = "system_team"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(320), comment='团队名称')
    code = Column(String(320), comment='团队编号,唯一')
    user_id = Column(Integer, comment='用户ID')
    type = Column(String(320), comment='类型')
    status = Column(Integer, default=0, comment='状态')
    is_public = Column(Boolean, default=0, comment='是否激活')
    is_active = Column(Boolean, default=0, comment='是否激活')
    is_delete = Column(Boolean, default=0, comment='是否删除')
    database_path = Column(String(300),comment="database_path")
    create_time = Column(Integer, comment='创建时间')
    remark = Column(String(320), comment='备注')
    users = relationship("TeamUserLink", back_populates="team", cascade="all, delete-orphan",lazy="selectin")
    projects = relationship("TeamProjectLink", back_populates="team", cascade="all, delete-orphan", lazy="selectin")
    roles = relationship("TeamRoleLink", back_populates="team", cascade="all, delete-orphan", lazy="selectin")

    def to_dict(self):
        model_dict = dict(self.__dict__)
        del model_dict['_sa_instance_state']
        return model_dict

    @classmethod
    def get_field(cls):
        return {column.name: column.comment for column in cls.__table__.columns}


class TeamUserLink(Base):
    __tablename__ = "system_team_user"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('system_users.id'))
    team_id = Column(Integer, ForeignKey('system_team.id'))
    role_id = Column(Integer, ForeignKey('system_role.id'))
    # user = relationship("User", back_populates="teams")
    team = relationship("Team", back_populates="users")



class TeamProjectLink(Base):
    __tablename__ = "system_team_project"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey('system_project.id'))
    team_id = Column(Integer, ForeignKey('system_team.id'))
    # project = relationship("Project", back_populates="teams")
    team = relationship("Team", back_populates="projects")


class TeamRoleLink(Base):
    __tablename__ = "system_team_role"
    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey('system_role.id'))
    team_id = Column(Integer, ForeignKey('system_team.id'))
    # role = relationship("Role", back_populates="teams")
    team = relationship("Team", back_populates="roles")
