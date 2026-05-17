import time

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text, func

from shared.database import Base


def _sys_bigint():
    return BigInteger().with_variant(Integer, "sqlite")


class SystemDictData(Base):
    """系统字典表"""
    __tablename__ = "system_dict_data"
    id = Column(Integer, primary_key=True)
    name = Column(String(320), default='', comment='名称')
    key = Column(String(320), default='', comment='唯一表示')
    type = Column(String(320), default='', comment='类型')
    status = Column(String(320), default=1, comment='状态')
    create_time = Column(DateTime(timezone=True), comment='创建时间')
    update_time = Column(DateTime(timezone=True), comment='修改时间')
    remark = Column(String(320), default='', comment='备注')

    @classmethod
    def get_field(cls):
        return {column.name: column.comment for column in cls.__table__.columns}


class SystemDictField(Base):
    """系统字典表"""
    __tablename__ = "system_dict_field"
    id = Column(Integer, primary_key=True)
    type_id = Column(Integer, default=0, comment="父ID")
    name = Column(String(320), default='', comment='名称')
    type = Column(String(320), default='', comment='类型唯一')
    label = Column(String(320), default='', comment='label')
    value = Column(String(320), default='', comment='label值')
    icon = Column(String(320), default='', comment='icon')
    sort = Column(Integer, default=0, comment="排序")
    color = Column(String(320), default='', comment='color')
    is_default = Column(Boolean, default=0, comment="是否默认选择")
    status = Column(String(320), default=1, comment='状态')
    create_time = Column(DateTime(timezone=True), comment='创建时间')
    remark = Column(String(320), default='', comment='备注')

    @classmethod
    def get_field(cls):
        return {column.name: column.comment for column in cls.__table__.columns}


class SysLog(Base):
    __tablename__ = "system_log"
    id = Column(Integer, primary_key=True)
    name = Column(String(320), comment='名称')
    model = Column(String(320), comment='模块')
    type = Column(String(320), comment='类型')
    method = Column(String(320), comment='方法')
    message = Column(Text, comment='内容')
    ip = Column(String(320), comment='客户端IP地址')
    addr = Column(String(320), comment='客户端IP地址')
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


class SystemInstallPackage(Base):
    __tablename__ = "sys_install_package"

    id = Column(_sys_bigint(), primary_key=True)
    package_code = Column(String(64), unique=True, nullable=False, comment="安装包编码")
    package_type = Column(String(32), nullable=False, comment="安装包类型")
    package_name = Column(String(256), nullable=False, comment="安装包名称")
    source = Column(String(32), nullable=False, comment="来源")
    source_version = Column(String(128), comment="来源版本")
    storage_path = Column(Text, nullable=False, comment="安装包路径")
    file_size = Column(_sys_bigint(), comment="文件大小")
    sha256 = Column(String(128), comment="SHA256")
    manifest_json = Column(Text, comment="manifest JSON")
    status = Column(String(32), nullable=False, default="ready", comment="状态")
    created_by = Column(_sys_bigint(), comment="创建人")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="更新时间")

    def to_dict(self):
        model_dict = dict(self.__dict__)
        del model_dict["_sa_instance_state"]
        return model_dict


class SystemInstallJob(Base):
    __tablename__ = "sys_install_job"

    id = Column(_sys_bigint(), primary_key=True)
    job_type = Column(String(32), nullable=False, comment="任务类型")
    package_id = Column(
        _sys_bigint(),
        ForeignKey("sys_install_package.id", ondelete="RESTRICT"),
        comment="安装包ID",
    )
    status = Column(String(32), nullable=False, default="pending", comment="任务状态")
    stage = Column(String(64), comment="任务阶段")
    progress_percent = Column(Numeric(5, 2), nullable=False, default=0, comment="进度百分比")
    processed_count = Column(_sys_bigint(), comment="已处理数量")
    total_count = Column(_sys_bigint(), comment="总数量")
    message = Column(Text, comment="任务消息")
    error_message = Column(Text, comment="错误信息")
    result_json = Column(Text, comment="结果JSON")
    created_by = Column(_sys_bigint(), comment="创建人")
    started_at = Column(DateTime(timezone=True), comment="开始时间")
    finished_at = Column(DateTime(timezone=True), comment="结束时间")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="更新时间")

    def to_dict(self):
        model_dict = dict(self.__dict__)
        del model_dict["_sa_instance_state"]
        return model_dict


class SystemInstallLock(Base):
    __tablename__ = "sys_install_lock"

    lock_code = Column(String(64), primary_key=True, comment="锁编码")
    is_locked = Column(Integer, nullable=False, default=1, comment="是否锁定")
    reason = Column(String(256), comment="锁定原因")
    required_action = Column(String(128), comment="要求动作")
    payload_json = Column(Text, comment="附加信息JSON")
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), comment="更新时间")

    def to_dict(self):
        model_dict = dict(self.__dict__)
        del model_dict["_sa_instance_state"]
        return model_dict
