#!/usr/bin/env python3
# _*_ coding: utf-8 _*_
# @desc : response model

from typing import TypeVar, Generic, Optional
# from pydantic.generics import GenericModel
from pydantic import BaseModel

SchemasType = TypeVar("SchemasType", bound=BaseModel)


# 普通结果验证
class ResultModel(BaseModel, Generic[SchemasType]):
    """ 普通结果验证 """
    code: int = 2000
    msg: Optional[str] = 'Success'
    data: SchemasType


class ResultPlus(BaseModel, Generic[SchemasType]):
    """自定义结果分页,二层数据结构"""
    total: Optional[int] = None
    dataList: SchemasType


class ResultPlusModel(BaseModel, Generic[SchemasType]):
    """ 自定义结分页数据结构 """
    code: int = 2000
    msg: Optional[str] = 'Success'
    data: ResultPlus[SchemasType]


# 自定义结果验证
class ResultPlusModel2(BaseModel, Generic[SchemasType]):
    """ 自定义结果验证 """
    code: int = 2000
    msg: Optional[str] = 'Success'
    data: SchemasType
