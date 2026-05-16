#!/usr/bin/env python3
# _*_ coding: utf-8 _*_
# @desc : 加载注册中心
from register.cors import register_cors
from register.exception import register_exception
from register.middleware import register_middleware
from register.app import register_app
from register.router import register_router
from register.app_init import register_init
