#!/usr/bin/env python3
# _*_ coding: utf-8 _*_

# @desc : 跨域请求
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from config.settings import settings


def register_cors(app: FastAPI):
    """ 跨域请求 """
    if settings.CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            # allow_origins=[str(origin) for origin in settings.CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        # app.add_middleware(
        #     TrustedHostMiddleware,
        #     allowed_hosts=settings.ALLOWED_HOST
        # )
