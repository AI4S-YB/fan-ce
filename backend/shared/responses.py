"""
@File    :   lib.response.py
@Time    :   2023/06/09 15:20:00
@Author  :   kentnf
@Version :   1.0
@Desc    :   None
"""

from typing import Type, Union, Any, List, TypeVar
from starlette import status
from starlette.responses import Response
from fastapi.responses import ORJSONResponse

SchemasType = TypeVar("SchemasType")


def response_200(code: int = 2000, data: Union[Type[SchemasType], List[Type[SchemasType]], str, dict, Any] = None, msg: str = "Success"):
    # logger.info(msg)
    return {'code': code, 'data': data, 'msg': msg}


def response_400(code: int = 4000, data: str = None, msg: str = "BAD REQUEST") -> Response:
    return ORJSONResponse(
        status_code=status.HTTP_200_OK,
        content={'code': code, 'msg': msg, 'data': data}
    )


def response_403(*, data: str = None, msg: str = "Forbidden") -> Response:
    return ORJSONResponse(
        status_code=status.HTTP_200_OK,
        content={'code': 4003, 'msg': msg, 'data': data}
    )


def response_404(*, data: str = None, msg: str = "Page Not Found") -> Response:
    return ORJSONResponse(
        status_code=status.HTTP_200_OK,
        content={'code': 4004, 'msg': msg, 'data': data}
    )


def response_422(*, data: str = None, msg: Union[list, dict, str] = "UNPROCESSABLE_ENTITY") -> Response:
    return ORJSONResponse(
        status_code=status.HTTP_200_OK,
        content={'code': 4022, 'msg': msg, 'data': data}
    )


def response_500(*, data: str = None, msg: Union[list, dict, str] = "Server Internal Error") -> Response:
    return ORJSONResponse(
        status_code=status.HTTP_200_OK,
        content={'code': 5000, 'msg': msg, 'data': data}
    )


def response_except(code: int = 2000, data: Union[str, list, dict] = None, msg: Union[list, dict, str] = "Server Internal Error") -> Response:
    return ORJSONResponse(
        status_code=status.HTTP_200_OK,
        content={'code': code, 'msg': msg, 'data': data}
    )
