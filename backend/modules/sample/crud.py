"""
@Author  : llq
@Time    : 2024/10/8 17:34
@Function:
@version :  1.0
@Desc    :  None
"""
from typing import TypeVar

from shared.crud_base import CRUDBase
from shared.database import Base
from .models import Sample,SampleMeta
from .schemas import CreateModel

ModelType = TypeVar("ModelType", bound=Base)


class CRUDSample(CRUDBase[Sample, CreateModel, CreateModel]):
    pass
class CRUDSampleMeta(CRUDBase[SampleMeta, CreateModel, CreateModel]):
    pass

sample_db = CRUDSample(Sample)
sample_meta_db = CRUDSampleMeta(SampleMeta)