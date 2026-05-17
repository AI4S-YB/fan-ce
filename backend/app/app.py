#!/usr/bin/env python3
# _*_ coding: utf-8 _*_
# @desc : 挂载其他app
from fastapi import FastAPI, applications
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html

from config.settings import settings


def swagger_ui_patch(*args, **kwargs):
    return get_swagger_ui_html(
        *args, **kwargs,
        swagger_js_url='/static/swagger-ui/swagger-ui-bundle.js',
        swagger_css_url='/static/swagger-ui/swagger-ui.css',
        swagger_favicon_url='/static/swagger-ui/favicon.png',
    )


def redoc_ui_path(*args, **kwargs):
    return get_redoc_html(*args, **kwargs,
                          redoc_js_url='/static/swagger-ui/redoc.standalone.js',
                          redoc_favicon_url='/static/swagger-ui/favicon.png',
                          )


applications.get_swagger_ui_html = swagger_ui_patch
applications.get_redoc_html = redoc_ui_path
# Test接口文档配置
test = FastAPI(
    title='test11',
    description='aaa',
    version=settings.PROJECT_VERSION,
    docs_url='/test/docs',
)
# Admin接口文档配置
zabbix = FastAPI(
    title=settings.PROJECT_TITLE,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.PROJECT_VERSION,
    docs_url='/docs',
)
# Admin接口文档配置
user = FastAPI(
    title=settings.PROJECT_TITLE,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.PROJECT_VERSION,
    docs_url='/docs',
)


def register_app(app: FastAPI):
    """ 挂在app """
    # app.mount("/zabbix", zabbix, name='zabbix')
    # app.mount("/user", user)
    pass
