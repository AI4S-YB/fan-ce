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
from .models import Experiment,EnhancementMeta
from .schemas import CreateModel

ModelType = TypeVar("ModelType", bound=Base)


class CRUDExperiment(CRUDBase[Experiment, CreateModel, CreateModel]):
    pass
class CRUDExperimentMeta(CRUDBase[EnhancementMeta, CreateModel, CreateModel]):
    pass

experiment_db = CRUDExperiment(Experiment)
experiment_meta_db = CRUDExperimentMeta(EnhancementMeta)