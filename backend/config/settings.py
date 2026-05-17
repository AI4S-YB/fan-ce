#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    :   config.py
@Time    :   2023/06/07 16:51:52
@Author  :   kentnf
@Version :   1.0
@Desc    :   配置文件
"""

import os
import sys
from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional

# from pydantic import BaseSettings
from shared.config_loader import Registry, ConfigFile


class Settings(BaseSettings):
    # 接口文档
    PROJECT_TITLE: str = "FAN-CE"
    PROJECT_DESCRIPTION: str = "FAN Community Edition"
    PROJECT_VERSION: str = "1.0"
    PROJECT_DIR: str = "/docs"
    BASE_PATH: str = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    # 接口前缀
    API_STR: str = "/api/v1"
    # 路径
    AVATAR_PATH: str = os.path.join(BASE_PATH, 'static', 'avatar')
    STATIC_PATH: str = os.path.join(BASE_PATH, 'static')
    IMG_PATH: str = os.path.join(BASE_PATH, 'static', 'img')
    os.makedirs(AVATAR_PATH, exist_ok=True)
    os.makedirs(IMG_PATH, exist_ok=True)
    # 跨域
    CORS_ORIGINS: List[AnyHttpUrl] = (
        "http://localhost:4000",
    )
    # token — 生产部署请通过环境变量覆盖: export FANCE_SECRET_KEY="..."
    SECRET_KEY: str = os.environ.get("FANCE_SECRET_KEY", "fan-ce-dev-jwt-secret-key-not-for-production-use")
    # 过期时间: 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    TOKEN_TYPE: str = 'Bearer'
    # cookie
    COOKIE_KEY: str = "sessionId"
    # 生产部署请通过环境变量覆盖: export FANCE_MD5_SALT="..."
    MD5_SALT: str = os.environ.get("FANCE_MD5_SALT", "fan-ce-dev-md5-salt-not-for-production")
    COOKIE_MAX_AGE: int = 24 * 60 * 60
    # logs日志
    LOGGER_DIR: str = "logs"
    LOGGER_NAME: str = '{time:YYYY-MM-DD_HH-mm-ss}.log'
    LOGGER_LEVEL: str = 'DEBUG'
    LOGGER_ROTATION: str = "500 MB"
    LOGGER_RETENTION: str = "1 days"
    # 日志
    LOGGER_FOLDER: str = "logs"
    # 全局编码
    GLOBAL_ENCODING: str = 'utf-8'

    # 数据库
    DATABASE_ECHO: bool = False

    # 是否区分大小写
    model_config = SettingsConfigDict(case_sensitive=True, extra="allow")

    # 获取当前环境，默认为开发环境
    ENV: str = os.environ.get("APP_ENV", "dev")
    
    # 预先声明这些属性，以便后续可以设置
    GlobalConfigFile: Optional[ConfigFile] = None
    app_options: Optional[Registry] = None
    
    @classmethod
    def get_config_name(cls):
        """获取配置文件名称"""
        env = os.environ.get("APP_ENV", "dev")
        config_dir = os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(__file__))), "config")
        candidate = f"config.{env}"
        if os.path.exists(os.path.join(config_dir, f"{candidate}.yaml")):
            return candidate
        if env == "prod":
            return "config.prod"
        return "config.dev"

# 先创建 settings 实例
settings = Settings()

# 然后在实例创建后设置 app_options 属性
# 服务配置，根据环境加载不同的配置文件
settings.GlobalConfigFile = ConfigFile(os.path.join(settings.BASE_PATH, "config"))
settings.app_options = Registry(settings.GlobalConfigFile.get_app_config(settings.get_config_name()))
