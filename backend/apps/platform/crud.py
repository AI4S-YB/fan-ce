# -*- coding: utf-8 -*-
"""
@Author  : Clark
@Time    : 2025-07-31
@Function:
@version :  1.0
@Desc    :  None
"""
from typing import TypeVar

from db.base import CRUDBase
from db.database import Base
from .models import News
from .schemas import CreateModel

ModelType = TypeVar("ModelType", bound=Base)


class CRUDDatabase(CRUDBase[News, CreateModel, CreateModel]):
    pass

news_db = CRUDDatabase(News)