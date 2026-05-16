# -*- coding: utf-8 -*-
"""
@Author  : llq
@Time    : 2024/10/8 17:34
@Function:
@version :  1.0
@Desc    :  None
"""
from typing import Any, Dict, Union, Optional, TypeVar
from db.base import CRUDBase
from db.database import Base
from .models import SystemDictData, SystemDictField
from ..base.schemas import SystemDictCreate

ModelType = TypeVar("ModelType", bound=Base)


class CRUDSystemDict(CRUDBase[SystemDictData, SystemDictCreate, SystemDictCreate]):
    pass


class CRUDSystemDictField(CRUDBase[SystemDictField, SystemDictCreate, SystemDictCreate]):
    pass


system_dict_db = CRUDSystemDict(SystemDictData)
system_dict_field_db = CRUDSystemDictField(SystemDictField)
