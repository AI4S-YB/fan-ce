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
from .models import Project,ProjectMeta
from .schemas import CreateModel,UpdateModel

ModelType = TypeVar("ModelType", bound=Base)

class CRUDProject(CRUDBase[Project, CreateModel, UpdateModel]):
    pass

class CRUDProjectMeta(CRUDBase[Project, CreateModel, UpdateModel]):
    pass

project_db = CRUDProject(Project)
project_meta_db = CRUDProjectMeta(ProjectMeta)