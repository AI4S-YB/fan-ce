"""
@File    :   user.models.py
@Time    :   2023/06/09 15:20:00
@Author  :   kentnf
@Version :   1.0
@Desc    :   None
"""
import time
from sqlalchemy import DateTime, Boolean, Column, Integer, String, BigInteger, Enum
from shared.database import Base


class User(Base):
    """用户表"""
    __tablename__ = "system_users"
    id = Column(Integer, primary_key=True,comment="唯一ID")
    user_name = Column(String(350), unique=True, nullable=False, comment='用户名称')
    nickname = Column(String(350), comment='用户昵称')
    user_email = Column(String(320), comment='用户邮箱')
    user_phone = Column(BigInteger, comment='用户手机')
    user_password = Column(String(300), comment='用户密码')
    user_salt = Column(String(300), comment='盐')
    user_type = Column(Integer, default=0, comment='用户类型')
    user_status = Column(Integer, default=1, comment='用户状态')
    user_avatar = Column(String(255), default='default.jpg', comment='用户头像')
    is_active = Column(Boolean, default=True,comment='是否激活')
    is_superman = Column(Boolean, default=0, comment='是否超管')
    is_deleted = Column(Boolean, default=0, comment='是否删除')
    create_time = Column(DateTime(timezone=True), comment='创建时间')
    update_time = Column(DateTime(timezone=True), comment='修改时间')
    remark = Column(String(320), default='', comment='备注')
    
    # 认证密钥相关字段
    auth_key = Column(String(64), unique=True, nullable=True, index=True, comment='认证密钥')
    key_status = Column(
        Enum(
            'active',
            'disabled',
            name='system_user_key_status_enum',
            native_enum=False,
        ),
        default='active',
        nullable=True,
        comment='密钥状态',
    )

    @classmethod
    def get_field(cls):
        return {column.name: column.comment for column in cls.__table__.columns}



class Role(Base):
    __tablename__ = "system_role"
    id = Column(Integer, primary_key=True)
    name = Column(String(320), comment='角色名称')
    code = Column(String(320), comment='角色表示')
    sort = Column(Integer, comment='角色顺序')
    type = Column(Integer, comment='角色类型')
    is_active = Column(Boolean, default=False, comment='是否激活')
    is_deleted = Column(Boolean, default=0, comment='是否删除')
    status = Column(Integer, default=0, comment='状态')
    create_time = Column(DateTime(timezone=True), comment='创建时间')
    remark = Column(String(320), comment='备注')


    def to_dict(self):
        model_dict = dict(self.__dict__)
        del model_dict['_sa_instance_state']
        return model_dict

    @classmethod
    def get_field(cls):
        return {column.name: column.comment for column in cls.__table__.columns}
