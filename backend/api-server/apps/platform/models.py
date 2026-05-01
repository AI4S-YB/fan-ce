import time

from sqlalchemy import Boolean, Column, Integer, String, Text
from sqlalchemy.orm import relationship

from db.database import Base


class News(Base):
    __tablename__ = "pf_news"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(100), comment='标题')
    type = Column(String(3), default='1', comment='类型')
    content = Column(String(500), comment='内容')
    author = Column(String(100), default=0, comment='作者')
    is_public = Column(Boolean, default=0, comment='是否公共')
    create_time = Column(Integer, comment='创建时间')
    user_id = Column(Integer, comment='用户ID')
    is_delete = Column(Boolean, default=0, comment='是否删除')

    def to_dict(self):
        model_dict = dict(self.__dict__)
        del model_dict['_sa_instance_state']
        return model_dict

    @classmethod
    def get_field(cls):
        return {column.name: column.comment for column in cls.__table__.columns}


class PlatformSiteSetting(Base):
    __tablename__ = "pf_site_setting"

    id = Column(Integer, primary_key=True, index=True)
    site_name = Column(String(255), default="", comment="网站名称")
    site_title = Column(String(255), default="", comment="网站标题")
    filing_no = Column(String(255), default="", comment="备案信息")
    domain = Column(String(255), default="", comment="网站域名")
    ip_address = Column(String(255), default="", comment="服务IP地址")
    port = Column(Integer, default=0, comment="通信端口")
    extra_json = Column(Text, default="{}", comment="扩展配置JSON")
    create_time = Column(Integer, default=lambda: int(time.time()), comment="创建时间")
    update_time = Column(Integer, default=lambda: int(time.time()), comment="更新时间")
    user_id = Column(Integer, default=0, comment="操作用户ID")

    def to_dict(self):
        model_dict = dict(self.__dict__)
        del model_dict["_sa_instance_state"]
        return model_dict


class PlatformModelApiSetting(Base):
    __tablename__ = "pf_model_api_setting"

    id = Column(Integer, primary_key=True, index=True)
    provider_code = Column(String(64), default="", comment="模型平台编码")
    provider_name = Column(String(128), default="", comment="模型平台名称")
    model_name = Column(String(255), default="", comment="模型名称")
    api_base_url = Column(String(500), default="", comment="API基地址")
    api_key = Column(String(500), default="", comment="API密钥")
    is_primary = Column(Boolean, default=False, comment="是否主模型")
    is_active = Column(Boolean, default=True, comment="是否启用")
    sort_order = Column(Integer, default=0, comment="排序值")
    remark = Column(String(500), default="", comment="备注")
    extra_json = Column(Text, default="{}", comment="扩展配置JSON")
    create_time = Column(Integer, default=lambda: int(time.time()), comment="创建时间")
    update_time = Column(Integer, default=lambda: int(time.time()), comment="更新时间")
    user_id = Column(Integer, default=0, comment="操作用户ID")

    def to_dict(self):
        model_dict = dict(self.__dict__)
        del model_dict["_sa_instance_state"]
        return model_dict
