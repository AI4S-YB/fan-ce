#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    :   mail.py
@Time    :   2023/06/07 16:51:52
@Author  :   kentnf
@Version :   1.0
@Desc    :   配置文件
"""

import os
import uvicorn
import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from core import settings
from register import register_cors, register_exception, register_middleware, register_app, register_router, register_init

os.chdir(os.path.dirname(os.path.abspath(__file__)))
app = FastAPI(title=settings.PROJECT_TITLE, description=settings.PROJECT_DESCRIPTION)
app.mount("/static", StaticFiles(directory=settings.STATIC_PATH), name="static")
app.mount(f"{settings.API_STR}/avatar", StaticFiles(directory=settings.AVATAR_PATH), name="statics")


register_app(app)
register_router(app)
register_cors(app)
register_middleware(app)
register_exception(app)
register_init(app)

logging.getLogger("watchfiles").setLevel(logging.WARNING)


if __name__ == '__main__':
    uvicorn.run(app='main:app',workers=5, reload=True, host='0.0.0.0', port=8001)
    # uvicorn.run(app='main:app', workers=5, host='0.0.0.0', port=8001)

