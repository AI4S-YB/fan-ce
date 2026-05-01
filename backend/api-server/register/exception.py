"""
@File    :   lib.exception.py
@Time    :   2023/06/09 15:20:00
@Author  :   kentnf
@Version :   1.0
@Desc    :   None
"""

import traceback
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.orm.exc import UnmappedInstanceError
from starlette.requests import Request
from starlette.exceptions import HTTPException

from libs.logger.loggers import logger
from libs.responses.response import response_400, response_except


def register_exception(app: FastAPI):
    """
    全局异常捕获
    :param app:
    :return:
    """

    # HTTPException异常
    @app.exception_handler(HTTPException)
    async def http_exception_handle(request: Request, exc: Exception):
        """ HTTPException异常 """
        status_code = exc.status_code
        msg = str(exc.detail)
        if status_code == 401:
            code = 4001
        else:
            msg = str(exc.detail)
            code = status_code
        logger.warning(f"{msg} |  IP {request.client.host} | {request.method} {request.url} ")
        return response_except(code=code, msg=msg, data='')

    # redis连接错误
    @app.exception_handler(ConnectionError)
    async def connection_error_handler(request: Request, exc: ConnectionError):
        """ redis连接错误 """
        logger.warning(f"redis连接错误\nURL:{request.method}-{request.url}\nHeaders:{request.headers}\n{exc}")
        return response_400(msg=str(exc))

    @app.exception_handler(ValidationError)
    async def inner_validation_exception_handler(request: Request, exc: ValidationError):
        """ 内部参数验证异常 """
        logger.error(f"内部参数验证错误\nURL:{request.method}-{request.url}\nHeaders:{request.headers}\nerror:{exc.errors()}")
        return response_except(code=5001, msg='内部参数验证错误')

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
        """ 请求参数验证异常 """
        logger.error(f"请求参数格式错误\nURL:{request.method}-{request.url}\nHeaders:{request.headers}\nerror:{exc.errors()}")
        return response_except(code=4022, msg='请求参数格式错误或缺少必要参数')

    @app.exception_handler(ProgrammingError)
    async def programming_error_handle(request: Request, exc: ProgrammingError):
        """ 请求参数丢失 """
        logger.error(
            f"请求参数丢失\nURL:{request.method}-{request.url}\nHeaders:{request.headers}\nerror:{exc}")
        return response_except(code=4023, msg='请求参数缺少')

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError):
        """ 添加数据的值与数据冲突 """
        code: str = str(exc.orig)[1:5]
        if code == "1062":
            text: str = "添加的数据已存在, 执行失败!"
        elif code == "1452" and request.method == "POST":
            text: str = "添加数据的外键不存在, 执行失败!"
        elif code == "1452" and request.method == "PUT":
            text: str = "更新数据的外键不存在, 执行失败!"
        elif code == "1048":
            text: str = "缺少参数或参数为空!"
        else:
            text: str = "数据的值与数据库中数据冲突, 执行失败"
        logger.warning(f"{text} | URL:{request.method}-{request.url}| error:{exc.orig}")
        return response_except(code=4030, msg=text)

    @app.exception_handler(UnmappedInstanceError)
    async def un_mapped_instance_error_handler(request: Request, exc: UnmappedInstanceError):
        """ 删除数据的id在数据库中不存在 """
        text: str = "传递数据不存在"
        logger.warning(f"{text}\nURL:{request.method}-{request.url}\nHeaders:{request.headers}")
        return response_except(code=4051, msg=text)

    @app.exception_handler(Exception)
    async def all_exception_handler(request: Request, exc: Exception):
        """ 全局所有异常 """
        logger.error(f"全局异常\n{request.method}URL:{request.url}\nHeaders:{request.headers}\n{traceback.format_exc()}")
        return response_except(code=5000, msg="服务器内部错误")
