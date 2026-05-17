"""
@File    :   user.crud.py
@Time    :   2023/06/09 15:20:00
@Author  :   kentnf
@Version :   1.0
@Desc    :   None
"""
from typing import Any, Dict, Union, Optional, TypeVar
from sqlalchemy.orm import Session
from sqlalchemy import or_
import time
import os
from shared.crud_base import CRUDBase
from .models import User
from .schemas import UserCreate, UserUpdate, UserRegister
from modules.common.security import get_password_hash, verify_password
from shared.string_utils import random_str
from shared.database import Base
from config.settings import settings
from fastapi.encoders import jsonable_encoder

ModelType = TypeVar("ModelType", bound=Base)


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    def get_user_by_username(self, db: Session, *, user_name: Any) -> Optional[ModelType]:
        """
        通过 ID 获取对象

        :param db: Session
        :param user_name:
        :return: 查询到的orm模型对象
        """
        db_obj = db.query(self.model).filter(or_(self.model.user_name == user_name, self.model.user_email == user_name)).first()
        return db_obj

    def create(self, db: Session, *, user_data: UserCreate) -> User:
        """
        添加用户
        :param db: Session
        :param user_data: UserCreate 输入的用户对象
        :return: 用户对象
        """
        salt = random_str(12)
        user_password = user_data.user_password + salt
        db_obj = User(
            user_name=user_data.user_name.strip(''),
            user_email=user_data.user_email,
            user_password=get_password_hash(user_password),
            user_salt=salt,
            user_status=1,
            nickname=user_data.nickname,
            user_phone=user_data.user_phone,
            create_time=int(time.time()),
            user_avatar='default.jpg'
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def register(self, db: Session, *, user_data: UserRegister) -> User:
        """
        添加用户
        :param db: Session
        :param user_data: UserCreate 输入的用户对象
        :return: 用户对象
        """
        salt = random_str(12)
        user_password = user_data.user_password + salt
        db_obj = User(
            user_name=user_data.user_name.strip(''),
            user_email=user_data.user_email,
            user_password=get_password_hash(user_password),
            user_salt=salt,
            create_time=int(time.time()),
            user_avatar='default.jpg',
        )
        db.add(db_obj)
        db.flush()
        db_obj.user_data = os.path.join(settings.USER_DATA, 'u' + str(db_obj.id))
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: User, obj_in: Union[UserUpdate, Dict[str, Any]]) -> User:
        """
        更新对象

        :param db: Session
        :param db_obj: User 用户对象
        :param obj_in: UpdateSchemaType schemas类型
        :param obj_in: Dict[str, Any] 字典数据
        :return: 用户对象
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        if update_data.get("user_password"):
            hashed_password = get_password_hash(update_data["user_password"])
            del update_data["user_password"]
            update_data["user_password"] = hashed_password
        return super().update_one(db, db_obj=db_obj, obj_in=update_data)

    def reset_password(self, db: Session, *, db_obj: User, obj_in: Union[UserUpdate, Dict[str, Any]]) -> Any:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict()
        hashed_password = get_password_hash(update_data["new_password"] + db_obj.user_salt)
        return super().update_one(db, db_obj=db_obj, obj_in={'user_password': hashed_password})

    def update_nubmer(self, db: Session, *, db_obj: Any, obj_in: Union[UserUpdate, Dict[str, Any]]) -> ModelType:
        """
        更新对象

        :param db: Session
        :param db_obj: orm模型对象
        :param obj_in: 更新模型 或者 字典数据
        :return: orm模型对象
        """
        obj_data = jsonable_encoder(db_obj)
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    # 通过名字得到用户
    def get_by_name(self, db: Session, *, name: str) -> Optional[User]:
        return db.query(User).filter(or_(User.user_name == name, User.user_email == name)).first()

    # 验证用户
    def authenticate(self, db: Session, *, user_name: str, user_password: str) -> Optional[User]:
        user = self.get_by_name(db, name=user_name)
        if not user:
            return None
        if not verify_password(user_password + user.user_salt, user.user_password):
            return None
        return user

    # 验证用户是否登录
    def is_active(self, user: User) -> bool:
        return user.is_active

    def is_superuser(self, user: User) -> bool:
        return bool(user.is_superman)


users_db = CRUDUser(User)
