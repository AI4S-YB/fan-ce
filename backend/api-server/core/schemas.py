from typing import TypeVar, Generic, Optional
from pydantic.generics import GenericModel

SchemasType = TypeVar("SchemasType")
#
#
# 普通结果验证


class ResultModel(GenericModel, Generic[SchemasType]):
    """ 普通结果验证 """
    code: int = 2000
    msg: Optional[str] = 'Success'
    data: SchemasType


# 自定义结果 --> data 数据
class ResultPlus(GenericModel, Generic[SchemasType]):
    noread_count: Optional[int] = None
    count: Optional[int] = None
    dataList: SchemasType


# 自定义结果验证
class ResultPlusModel(GenericModel, Generic[SchemasType]):
    """ 自定义结果验证 """
    code: int = 2000
    msg: Optional[str] = 'Success'
    data: ResultPlus[SchemasType]


# 自定义结果验证
class ResultPlusModel2(GenericModel, Generic[SchemasType]):
    """ 自定义结果验证 """
    code: int = 2000
    msg: Optional[str] = 'Success'
    data: SchemasType
