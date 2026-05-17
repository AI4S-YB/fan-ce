"""
@File    :   db.base.py
@Time    :   2023/06/09 15:20:00
@Author  :   kentnf
@Version :   1.0
@Desc    :   None
"""
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy import func, distinct
from sqlalchemy import text
from sqlalchemy.orm import Session

from shared.database import Base
from shared.exceptions import ExceptionStatus
from shared.filter import apply_filters

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType]):
        """
        CRUD对象的默认方法去 增 查 改 删 (CRUD).
        * `model`: ORM模型类
        * `schema`: 数据验证模型类
        """
        self.model = model

    def get(self, db: Session, *, id: Any, filters: dict = None) -> Optional[ModelType]:
        """
        通过 ID 获取对象
        :param db: Session
        :param id: ID
        :param filters: 过滤
        :return: 查询到的orm模型对象
        """
        if filters:
            db_obj = db.query(self.model).filter(self.model.id == id).filter_by(**filters).first()
        else:
            db_obj = db.query(self.model).filter(self.model.id == id).first()
        if not db_obj:
            raise HTTPException(
                status_code=ExceptionStatus.CODE_4051['code'], detail=ExceptionStatus.CODE_4051['msg'])
        return db_obj

    def get_one(self, db: Session, *, id: Any, filters: dict = None) -> Optional[ModelType]:
        """
        通过 ID 获取对象
        :param db: Session
        :param id: ID
        :param filters: 过滤
        :return: 查询到的orm模型对象
        """
        if filters:
            db_obj = db.query(self.model).filter(self.model.id == id).filter_by(**filters).first()
        else:
            db_obj = db.query(self.model).filter(self.model.id == id).first()
        return db_obj

    def get_info(self, db: Session, *, id: Any, filters: dict = None) -> Optional[ModelType]:
        """
        通过 ID 获取对象
        :param db: Session
        :param id: ID
        :param filters: 过滤
        :return: 查询到的orm模型对象
        """
        if filters:
            db_obj = db.query(self.model).filter(
                self.model.id == id).filter_by(**filters).first()
        else:
            db_obj = db.query(self.model).filter(self.model.id == id).first()
        return db_obj

    def get_list(self, db: Session, *, page: int = 1, size: int = 10, filters: dict = None, fields: list = [], filters_exp: list = [],
                 search_exp: list = [], filter_exp_or: list = [], sort='') -> \
            Dict[
                str, List[ModelType]]:
        """
        获取 skip-limit 的对象集
        :param db: Session
        :param page: 页码 (默认值1)
        :param size: 页码 (默认10)
        :param filters
        :param fields
        :param filter_exp_or
        :return: 查询到的orm模型对象集
        """
        if filters is None:
            filters = {}
        if fields:
            fields_list = []
            for field in fields:
                fields_list.append(getattr(self.model, field))
            fields_select = fields_list
            data_query = db.query(
                *fields_select).filter_by(**filters).order_by(text(sort))
        else:
            fields_select = self.model
            data_query = db.query(fields_select).filter_by(**filters).order_by(text(sort))
        count_query = db.query(func.count(distinct(self.model.id))).filter_by(**filters)

        if filters_exp or search_exp:
            data_query = apply_filters(data_query, self.model, filters_exp, search_exp, filter_exp_or)
            count_query = apply_filters(count_query, self.model, filters_exp, search_exp, filter_exp_or)

        if page == 0 or size == 0:
            data_query = data_query
        else:
            data_query = data_query.offset((page - 1) * size).limit(size)
        count: int = count_query.scalar()
        return {'total': count, 'dataList': data_query.all()}

    def create_one(self, db: Session, *, obj_in: Union[CreateSchemaType, Dict[str, Any]]) -> ModelType:
        """
        添加对象

        :param db: Session
        :param obj_in: 创建模型
        :return: orm模型对象
        """
        new_data = {}
        if isinstance(obj_in, dict):
            obj_in_data = obj_in
        else:
            obj_in_data = jsonable_encoder(obj_in)
        for field in obj_in_data:
            if hasattr(self.model, field):
                new_data[field] = obj_in_data[field]
        db_obj = self.model(**new_data)  # type: ignore
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def create_batch(self, db: Session, *, add_data: list) -> ModelType:
        """
        添加对象
        :param db: Session
        :param add_data: 创建模型
        :return: orm模型对象
        """
        db_obj = db.execute(self.model.__table__.insert(), add_data)
        db.commit()
        return db_obj

    def update_one(self, db: Session, *, db_obj: ModelType, obj_in: Union[UpdateSchemaType, Dict[str, Any]]) -> ModelType:
        """
        更新对象
        :param db: Session
        :param db_obj: orm模型对象
        :param obj_in: 更新模型 或者 字典数据
        :return: orm模型对象
        """
        if isinstance(db_obj, dict):
            db_obj = self.get(db=db, id=db_obj['id'])
        obj_data = jsonable_encoder(db_obj)
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        for field in update_data:
            if field in obj_data:
                setattr(db_obj, field, update_data[field])
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update_batch(self, db: Session, *, filters: dict, update: dict) -> ModelType:
        """
        通过 过滤条件批量修改对象
        :param db: Session
        :param filters: 过滤条件
        :param update: 更新数据
        :return: orm模型对象
        """
        db_obj = db.query(self.model).filter_by(**filters).update(update)
        return db_obj

    def remove_batch(self, db: Session, *, filters: dict = {}) -> ModelType:
        """
        通过 过滤条件批量删除对象
        :param db: Session
        :param filters: 过滤条件
        :return: orm模型对象
        """
        obj = db.query(self.model).filter_by(**filters)
        if obj.all():
            obj.delete()
        db.commit()
        return obj
    def remove_batch_ids(self, db: Session, *, ids: list=None) -> ModelType:
        """
        通过 过滤条件批量删除对象
        :param db: Session
        :param ids: 过滤条件
        :return: orm模型对象
        """
        ids = ids or []
        obj = db.query(self.model).filter(self.model.id.in_(ids))
        if obj.all():
            obj.delete()
            db.commit()
        return obj

    def remove(self, db: Session, *, id: int = None, ids=[]) -> ModelType:
        """
        通过 ID 删除对象
        :param db: Session
        :param id: ID
        :return: orm模型对象
        """
        data = ''
        if id:
            obj = db.query(self.model).get(id)
            db.delete(obj)
            db.commit()
            data = obj
        if ids:
            for ii in ids:
                obj = db.query(self.model).get(ii)
                db.delete(obj)
                db.commit()
        return data

    def remove_all(self, db: Session):
        """
        清空数据
        :param db: Session
        :return: orm模型对象
        """
        obj = db.query(self.model).delete()
        db.commit()
        return obj

    def get_multi_relation(self, db: Session):
        """
        只获取关系字段
        :param db: Session
        :return: 查询到的关系字段
        """
        return db.query(self.model.id, self.model.name).distinct().all()

    def get_count(self, db: Session, filters: dict = None, filters_exp: list = []):
        count_query = db.query(func.count(distinct(self.model.id))).filter_by(**filters)
        if filters_exp:
            count_query = apply_filters(count_query, self.model, filters_exp)
        return count_query.scalar()

    def get_filter(self, db: Session, *, filters: dict = None) -> Optional[ModelType]:
        """
        通过 filters 获取对象
        :param db: Session
        :param filters: 过滤
        :return: 查询到的orm模型对象
        """
        db_obj = db.query(self.model).filter_by(**filters).first()
        return db_obj

    def get_filter_in(self, db: Session, *, name: str, value: []) -> Optional[ModelType]:
        """
        通过list 过滤包含的数据
        :param db:
        :param name:
        :param value:
        :return:
        """
        db_obj = db.query(self.model).filter(getattr(self.model, name).in_(value)).all()
        return db_obj

    def get_filter_all(self, db: Session, *, filters: dict = None):
        """
        通过 filters 获取对象
        :param db: Session
        :param filters: 过滤
        :return: 查询到的orm模型对象
        """
        db_obj = db.query(self.model).filter_by(**filters).all()
        return db_obj

    def get_data(self, db: Session, *, filters: dict = None) -> Optional[ModelType]:
        """
        通过 filters 获取对象
        :param db: Session
        :param filters: 过滤
        :return: 查询到的orm模型对象
        """
        db_obj = db.query(self.model).filter_by(**filters).all()
        return db_obj
