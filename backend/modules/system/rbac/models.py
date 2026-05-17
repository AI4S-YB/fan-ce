# -*- coding: utf-8 -*-
"""
@Author  : llq
@Time    : 2024/10/8 17:35
@Function:
@version :  1.0
@Desc    :  None
"""
from sqlalchemy import Boolean, Column, Integer, String, JSON,ForeignKey
from sqlalchemy.orm import relationship
from db.database import Base


class Menu(Base):
    __tablename__ = "system_menu"
    id = Column(Integer, primary_key=True, index=True, comment="ID")
    name = Column(String(320), comment='菜单名唯一')
    icon = Column(String(320), comment='图标')
    component = Column(String(320), comment='组件路径')
    title = Column(String(320), comment='路由名称')
    path = Column(String(320), comment='路由名称')
    redirect = Column(String(320), default='', comment='重定向')
    sort = Column(Integer, comment='显示顺序')
    type = Column(Integer, comment='菜单类型')
    api_url = Column(String(320), comment='api_url地址')
    web_url = Column(String(320), comment='web_url地址')
    status = Column(Integer, default=0, comment='状态')
    pid = Column(Integer, default=0, comment='父菜单')
    is_visible = Column(Boolean, default=1, comment='显示状态')
    is_frame = Column(Boolean, default=0, comment='是否外部菜单,外连接')
    is_cache = Column(Boolean, default=0, comment='是否缓存')
    is_hidden = Column(Boolean, default=0, comment='是否隐藏')
    is_deleted = Column(Boolean, default=0, comment='是否删除')
    meta = Column(JSON, comment="meta")
    create_time = Column(Integer, comment='创建时间')
    remark = Column(String(320), comment='备注')
    permissions = relationship("MenuPermissionLink", back_populates="menu", cascade="all, delete-orphan",lazy="selectin")

    def to_dict(self):
        model_dict = dict(self.__dict__)
        del model_dict['_sa_instance_state']
        return model_dict

    @classmethod
    def get_field(cls):
        return {column.name: column.comment for column in cls.__table__.columns}


class Permission(Base):
    __tablename__ = "system_permission"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(320), comment='权限名称')
    code = Column(String(320), comment='权限code')
    sort = Column(Integer, comment='显示顺序')
    type = Column(String(320), comment='服务类型')
    method = Column(String(320),comment="方法")
    status = Column(Integer, default=0, comment='状态')
    pid = Column(Integer, default=0, comment='父菜单')
    uri = Column(String(250),comment="URI")
    is_active = Column(Boolean, default=0, comment='是否激活')
    is_delete = Column(Boolean, default=0, comment='是否删除')
    create_time = Column(Integer, comment='创建时间')
    remark = Column(String(320), comment='备注')
    menus = relationship("MenuPermissionLink", back_populates="permission", cascade="all, delete-orphan",lazy="selectin")


    def to_dict(self):
        model_dict = dict(self.__dict__)
        del model_dict['_sa_instance_state']
        return model_dict

    @classmethod
    def get_field(cls):
        return {column.name: column.comment for column in cls.__table__.columns}


class UserRoleLink(Base):
    __tablename__ = "system_user_role"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, comment="用户ID")
    role_id = Column(Integer, comment="角色ID")


class RoleMenuLink(Base):
    __tablename__ = "system_user_menu"
    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, comment="角色ID")
    menu_id = Column(Integer, comment="菜单ID")


class MenuPermissionLink(Base):
    __tablename__ = "system_menu_permission"
    id = Column(Integer, primary_key=True, index=True)
    menu_id = Column(Integer,ForeignKey('system_menu.id'), comment="菜单ID")
    permission_id = Column(Integer,ForeignKey('system_permission.id'), comment="权限ID")
    menu = relationship("Menu", back_populates="permissions")
    permission = relationship("Permission", back_populates="menus")

class Service(Base):
    """服务表"""
    __tablename__ = "system_service"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(320), comment='名称')
    uri = Column(String(320), comment='访问地址')
