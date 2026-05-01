# -*- coding: utf-8 -*-
"""
@Author  : llq
@Time    : 2024/10/8 17:34
@Function:
@version :  1.0
@Desc    :  None
"""
from typing import TypeVar

from db.base import CRUDBase
from db.database import Base
from .models import Databases, DatabasesFile, DatabasesMeta, ProjectDatabasesLink
from apps.system.project.models import Project
from apps.sample.models import Sample
from apps.experiment.models import Experiment
from .schemas import CreateModel, DatabasesFileCreate, DatabasesFileUpdate

ModelType = TypeVar("ModelType", bound=Base)


class CRUDDatabase(CRUDBase[Databases, CreateModel, CreateModel]):
    pass


class CRUDPDatabaseFile(CRUDBase[DatabasesFile, DatabasesFileCreate, DatabasesFileUpdate]):
    pass




class CRUDDatabaseProject(CRUDBase[ProjectDatabasesLink, CreateModel, CreateModel]):
    pass


class CRUDDatabaseMeta(CRUDBase[DatabasesMeta, CreateModel, CreateModel]):
    pass


database_db = CRUDDatabase(Databases)
database_meta_db = CRUDDatabaseMeta(DatabasesMeta)
database_file_db = CRUDPDatabaseFile(DatabasesFile)

project_database_db = CRUDDatabaseProject(ProjectDatabasesLink)
"""
#10【数据资产】-【数据管理】-构建关联并保存增强元数据：服务端 
Clark 2025-07-24
"""
project_db = CRUDDatabase(Project)
sample_db = CRUDDatabase(Sample)
experiment_db = CRUDDatabase(Experiment)
