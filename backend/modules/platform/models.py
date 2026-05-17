import time

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import relationship

from shared.database import Base


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
    site_code = Column(String(64), unique=True, nullable=False, comment="站点编码")
    site_name = Column(String(255), default="", comment="网站名称")
    site_title = Column(String(255), default="", comment="网站标题")
    domain = Column(String(255), default="", comment="正式域名")
    test_port = Column(String(8), default="", comment="测试端口")
    logo_text = Column(String(255), default="", comment="Logo 文字")
    filing_no = Column(String(255), default="", comment="备案信息")
    contact_email = Column(String(255), default="", comment="联系邮箱")
    footer_copyright = Column(String(255), default="", comment="Footer 版权信息")
    extra_json = Column(Text, default="{}", comment="扩展配置JSON")
    frp_enabled = Column(Boolean, default=False, comment="是否启用隧道共享")
    frp_server_addr = Column(String(255), default=None, comment="云服务器IP地址")
    frp_server_port = Column(Integer, default=7000, comment="frps绑定端口")
    frp_token = Column(String(255), default=None, comment="frps与frpc认证密钥")
    frp_public_port = Column(Integer, default=80, comment="对外HTTP端口")
    frp_status = Column(String(32), default="stopped", comment="stopped/running/error")
    frp_config_json = Column(Text, default=None, comment="高级自定义frpc配置")
    public_ai_chat_enabled = Column(Boolean, default=False, comment="是否启用公共AI对话")
    create_time = Column(Integer, default=lambda: int(time.time()), comment="创建时间")
    update_time = Column(Integer, default=lambda: int(time.time()), comment="更新时间")
    user_id = Column(Integer, default=0, comment="操作用户ID")

    def to_dict(self):
        model_dict = dict(self.__dict__)
        del model_dict["_sa_instance_state"]
        return model_dict


class PlatformSiteDatasetLink(Base):
    __tablename__ = "pf_site_dataset_link"

    id = Column(Integer, primary_key=True, index=True)
    site_code = Column(String(64), ForeignKey("pf_site_setting.site_code", ondelete="CASCADE"), nullable=False, comment="站点编码")
    dataset_id = Column(Integer, ForeignKey("dataset_registry.id", ondelete="CASCADE"), nullable=False, comment="数据集ID")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")

    __table_args__ = (
        UniqueConstraint("site_code", "dataset_id", name="uq_site_dataset_link"),
    )

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
