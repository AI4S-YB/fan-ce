#!/usr/bin/env python3
# _*_ coding: utf-8 _*_
# @desc : 请求响应拦截
import time
from fastapi import FastAPI, Request, status
from libs.logger.loggers import logger


def register_middleware(app: FastAPI):
    """ 请求响应拦截"""

    @app.middleware("http")
    async def logger_request(request: Request, call_next):
        start_time = time.time()
        client_host = request.headers.get('x-real-ip', request.client.host)
        # print(request.headers)
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(round(process_time, 5))
        logger.info(f"访问记录:{request.method} url:{request.url} client:{client_host} time:{str(round(process_time, 5))}")
        return response
