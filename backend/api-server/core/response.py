# @desc : 封装 统一的JSON格式
from typing import Type, Union, Any, List
from starlette import status
from starlette.responses import Response
from fastapi.responses import ORJSONResponse




# 因为 data 数据要符合 SchemasType 模型，不符合JSONResponse的序列化
def respon_200(code: int = 2000, data: Union[Type[SchemasType], List[Type[SchemasType]], str, dict, Any] = None, msg: str = "Success"):
    # logger.info(msg)
    return {'code': code, 'data': data, 'msg': msg}


def respon_2000(code: int = 2000, data: Any = None, msg: str = "Success"):
    return ORJSONResponse(
        status_code=status.HTTP_200_OK,
        content={'code': code, 'msg': msg, 'data': data}
    )


def respon_400(code: int = 4000, data: str = None, msg: str = "BAD REQUEST") -> Response:
    return ORJSONResponse(
        status_code=status.HTTP_200_OK,
        content={'code': code, 'msg': msg, 'data': data}
    )


def respon_403(*, data: str = None, msg: str = "Forbidden") -> Response:
    return ORJSONResponse(
        status_code=status.HTTP_200_OK,
        content={'code': 4003, 'msg': msg, 'data': data}
    )


def respon_404(*, data: str = None, msg: str = "Page Not Found") -> Response:
    return ORJSONResponse(
        status_code=status.HTTP_200_OK,
        content={'code': 4004, 'msg': msg, 'data': data}
    )


def respon_422(*, data: str = None, msg: Union[list, dict, str] = "UNPROCESSABLE_ENTITY") -> Response:
    return ORJSONResponse(
        status_code=status.HTTP_200_OK,
        content={'code': 4022, 'msg': msg, 'data': data}
    )


def respon_500(*, data: str = None, msg: Union[list, dict, str] = "Server Internal Error") -> Response:
    return ORJSONResponse(
        status_code=status.HTTP_200_OK,
        content={'code': 5000, 'msg': msg, 'data': data}
    )


def respon_exce(code: int = 2000, data: Union[str, list, dict] = None, msg: Union[list, dict, str] = "Server Internal Error") -> Response:
    return ORJSONResponse(
        status_code=status.HTTP_200_OK,
        content={'code': code, 'msg': msg, 'data': data}
    )
