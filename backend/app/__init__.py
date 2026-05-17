#!/usr/bin/env python3
# _*_ coding: utf-8 _*_
# @desc : 加载注册中心
from app.cors import register_cors
from app.exception import register_exception
from app.middleware import register_middleware
from app.app import register_app
from app.router import register_router
from app.app_init import register_init
