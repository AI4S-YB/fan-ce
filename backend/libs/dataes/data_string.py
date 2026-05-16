#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project: oma
@File   : data_string.py
@IDE    : PyCharm
@Author: llq
@Date   : 2024/12/3 14:54
@version:  1.0
@Desc   : 
"""
import secrets
import base64
import random


def random_str(num: int):
    """随机数据生成"""
    hh = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    salt = ''
    for i in range(num):
        salt += random.choice(hh)
    return salt


def generate_random_string(length):
    # 生成随机字节流
    random_bytes = secrets.token_bytes(length)
    random_string = base64.b64encode(random_bytes).decode("utf-8")
    return random_string[:length]
