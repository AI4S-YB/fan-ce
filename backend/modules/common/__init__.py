# -*- coding: utf-8 -*-
"""
@author :  llq
@file   :  __init__.py
@time   :  2023/7/5  19:48
@version:  1.0
@Desc   :  None
"""
from modules.system.user.crud import users_db
from modules.system.user.models import User

__all__ = ['User', 'users_db']
