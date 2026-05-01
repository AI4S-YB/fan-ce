"""
@File    :   user.models.py
@Time    :   2023/06/09 15:20:00
@Author  :   kentnf
@Version :   1.0
@Desc    :   None
"""
import time
from sqlalchemy import Boolean, Column, Integer, String, BigInteger, Enum
from db.database import Base


class User(Base):
    """用户表"""
    __tablename__ = "system_users"
    id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String(350), unique=True, nullable=False, comment='用户名称')
    nickname = Column(String(350), comment='用户昵称')
    user_email = Column(String(320), comment='用户邮箱')
    user_phone = Column(BigInteger, comment='用户手机')
    user_password = Column(String(300), comment='用户密码')
    user_salt = Column(String(300), comment='盐')
    user_type = Column(Integer, default=0, comment='用户类型')
    user_status = Column(Integer, default=1, comment='用户状态')
    user_avatar = Column(String(255), default='default.jpg', comment='用户头像')
    is_active = Column(Boolean, default=True)
    is_superman = Column(Integer, default=0, comment='是否超管')
    is_deleted = Column(Boolean, default=False, comment='是否删除')
    create_time = Column(Integer, default=int(time.time()), comment='创建时间')
    update_time = Column(Integer, default=int(time.time()), comment='修改时间')
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
        nullable=True,
        default='active',
        comment='密钥状态',
    )

    @classmethod
    def get_field(cls):
        return {column.name: column.comment for column in cls.__table__.columns}
