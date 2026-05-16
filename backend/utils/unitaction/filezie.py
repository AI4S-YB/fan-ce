#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""
@Project: oma
@File   : filezie.py
@IDE    : PyCharm
@Author: llq
@Date   : 2024/12/24 23:17
@version:  1.0
@Desc   : 
"""
import math
import re


def convert_size(size_data, min_units="B", unit='B'):
    """
    result
    min_units 最小单位 size_result
    unit 强转的单位  unit_result
    size_data: 1000,1000M,1000MB
    """
    size = 0
    result = {'size': 0, 'unit': 'M'}
    size_result = {'size': 0, 'unit': 'M'}
    unit_result = {'size': 0, 'unit': 'M'}
    units = {
        'B': 1,
        'KB': 1024,
        'MB': 1024 ** 2,
        'GB': 1024 ** 3,
        'TB': 1024 ** 4,
        'PB': 1024 ** 5,
        'EB': 1024 ** 6,
        'ZB': 1024 ** 7,
        'YB': 1024 ** 8,
        'K': 1024,
        'M': 1024 ** 2,
        'G': 1024 ** 3,
        'T': 1024 ** 4,
        'P': 1024 ** 5,
        'E': 1024 ** 6,
        'Z': 1024 ** 7,
        'Y': 1024 ** 8,
    }
    if isinstance(size_data, str):
        match = re.match(r'(\d+\.?\d*)\s*([a-zA-Z]+)', size_data)
        if match:
            value = float(match.group(1))
            unit_t1 = match.group(2)
            size = value * units.get(unit_t1)
    if isinstance(size_data, int):
        size = size_data
    if size == 0 or not size_data:
        return result, size_result, unit_result
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    size_name2 = ("B", "K", "M", "G", "T", "P", "E", "Z", "Y")
    i = int(math.floor(math.log(size, 1024)))
    p = math.pow(1024, i)
    s = size / p
    if unit:
        if unit in size_name2:
            size_name = size_name2
        unit_index = size_name.index(unit)
        if unit_index > i:
            unit_result['size'] = round(s / 1024 ** (unit_index - i), 2)
        elif unit_index < i:
            unit_result['size'] = round(s * (1024 ** (i - unit_index)), 2)
        else:
            unit_result['size'] = round(s, 2)
        unit_result['unit'] = unit
    if min_units:
        if min_units in size_name2:
            size_name = size_name2
        min_i = size_name.index(min_units)
        if min_i > i:
            min_t = min_i - i
            size_result['size'] = round(s / 1024 ** min_t, 2)
            size_result['unit'] = min_units
        else:
            size_result['size'] = round(s, 2)
            size_result['unit'] = size_name[i]
    result['size'] = round(s, 1)
    result['unit'] = size_name[i]
    return result, size_result, unit_result
