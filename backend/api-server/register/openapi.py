#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@File    :   openapi.py
@Time    :   2023/06/12 12:11:06
@Author  :   kentnf
@Version :   1.0
@Desc    :   None
'''
from fastapi.openapi.utils import get_openapi


def custom_openapi(app):
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Custom title",
        version="3.0.0",
        description="This is a very custom OpenAPI schema",
        routes=app.routes,
    )
    # Update the servers list with all the available servers
    servers = [
        {"url": "http://localhost:8000", "description": "Local Server"},
        {"url": "https://remote-server.com", "description": "Remote Server"},
    ]
    openapi_schema["servers"] = servers
    app.openapi_schema = openapi_schema
    app.openapi = openapi_schema
    return ''
