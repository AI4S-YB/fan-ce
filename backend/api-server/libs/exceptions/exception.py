"""
@File    :   libs.exception.py
@Time    :   2023/06/09 15:20:00
@Author  :   kentnf
@Version :   1.0
@Desc    :   None
"""
from fastapi import HTTPException


class ExceptionStatus:
    """自定义异常状态值"""
    CODE_2000_Success = {"code": 2000, "msg": "Success"}
    # 用户认证
    CODE_4001 = {"code": 4001, "msg": "无认证"}
    CODE_4002 = {"code": 4002, "msg": "用户或密码错误"}
    CODE_4003 = {"code": 4003, "msg": "用户认证已过期"}
    CODE_4004 = {"code": 4004, "msg": "当前用户不存在"}
    CODE_4005 = {"code": 4005, "msg": "用户认证失败"}
    CODE_4007 = {"code": 4007, "msg": "无相关权限"}
    CODE_4009 = {"code": 4009, "msg": "用户已存在"}
    CODE_4010 = {"code": 4009, "msg": "用户已禁用"}
    CODE_4011 = {"code": 4011, "msg": "用户无任务权限,请联系管理"}
    # 传参
    CODE_4051 = {"code": 4051, "msg": "传入数据不存在"}
    CODE_4052 = {"code": 4052, "msg": "传入用户ID不存在"}
    CODE_4022 = {"code": 4022, "msg": "请求参数格式错误或缺少必要参数"}
    CODE_4023 = {"code": 4022, "msg": "请求参数格值不能为空"}
    CODE_4024 = {"code": 4024, "msg": "不能为空"}
    CODE_4025 = {"code": 4025, "msg": "已存在"}
    CODE_4026 = {"code": 4026, "msg": "选择为空"}
    CODE_4027 = {"code": 4027, "msg": "选择数据不存在"}
    CODE_4028 = {"code": 4028, "msg": "项目名称已存在"}
    CODE_4030 = {"code": 4030, "msg": "添加的数据异常"}
    CODE_4034 = {"code": 4034, "msg": "无任务结果"}


exceptions = ExceptionStatus


def raise_http():
    raise HTTPException(status_code=exceptions.CODE_4003['code'], detail=exceptions.CODE_4003['msg'])


# @desc : 自定义异常
class IdNotExist(Exception):
    """ 查询id不存在 """

    def __init__(self, err_desc: str = "查询id不存在"):
        self.err_desc = err_desc
