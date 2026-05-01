# -*- coding: utf-8 -*-
"""
@Author  : llq
@Time    : 2024/9/22 14:47
@Function: 
@version :  1.0
@Desc    :  None
"""
import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict

import aiofiles
from tqdm import tqdm

from db.database import get_dbs
from libs.logger import logger


def is_int_regex(s):
    return bool(re.match(r'^[+-]?[0-9]+$', s.strip()))


class FileAction:
    def __init__(self):
        pass

    @staticmethod
    def format_size(size):
        """
        智能转换文件大小单位
        :param size: 字节数
        :return: 带单位的格式化字符串
        """
        units = ('B', 'K', 'M', 'G', 'T')
        unit_index = 0

        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        precision = 1 if size < 100 else 0
        if unit_index == 0:  # 字节数不需要小数
            precision = 0

        return f"{size:.{precision}f}{units[unit_index]}"

    @staticmethod
    def get_dir_size(path, follow_symlinks=False):
        total = 0
        if not os.path.exists(path):
            return total
        for entry in os.scandir(path):
            try:
                if entry.is_file(follow_symlinks=follow_symlinks):
                    total += entry.stat().st_size
                elif entry.is_dir(follow_symlinks=follow_symlinks):
                    total += get_dir_size(entry.path)
            except (PermissionError, FileNotFoundError):
                continue
        return total

    @staticmethod
    def get_dir_size2(directory):
        path = Path(directory)
        if os.path.isdir(directory):
            size = sum(f.stat().st_size for f in path.glob("**/*") if f.is_file())
        else:
            size = path.stat().st_size
        return size

    def get_dir_one(self, path, follow_symlinks=False):
        result = []
        if path is None:
            return result
        if not os.path.exists(path):
            return result

        if os.path.isfile(path):
            return result

        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            stat_info = os.stat(item_path)
            item_info = {
                'name': item,
                'path': item_path,
                'size': self.get_dir_size2(item_path),
                'modified_time': datetime.fromtimestamp(stat_info.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                'file_type': 'file' if os.path.isfile(item_path) else 'dir'
            }
            result.append(item_info)
        return result


file_action = FileAction()


def get_file_info(path: str) -> List[Dict]:
    """
    获取目录下所有文件和子目录的信息
    
    Args:
        path: 目录路径
        extensions: 需要过滤的文件后缀名列表，如['.txt', '.csv']
    Returns:
        List[Dict]: 包含文件/目录信息的字典列表
    """
    result = []

    if path is None:
        return result
    if not os.path.exists(path):
        return result

    if os.path.isfile(path):
        return result

    for item in os.listdir(path):
        item_path = os.path.join(path, item)
        stat_info = os.stat(item_path)

        item_info = {
            'name': item,
            'path': item_path,
            'size': stat_info.st_size,
            'modified_time': datetime.fromtimestamp(stat_info.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            'file_type': 'file' if os.path.isfile(item_path) else 'dir'
        }
        result.append(item_info)

    return result


def file_in_dir(path, fast1_end):
    print(path)
    for item in os.listdir(path):
        item_path = os.path.join(path, item)
        if os.path.isdir(item_path):
            for i in os.listdir(item_path):
                pp_path = os.path.join(item_path, i)
                if os.path.isfile(pp_path):
                    if any(i.endswith(ext) for ext in fast1_end):
                        return True
    return False


def get_fast_file(path: str, fast1_end: List[str] = None, fast2_end: List[str] = None, root_dir='/', type=''):
    fast1 = []
    fast2 = []
    file_info = get_file_info(path)
    for i in file_info:
        if type == 'nanopore':
            if i.get('file_type') == 'dir' and fast1_end and fast2_end:
                if file_in_dir(os.path.dirname(i.get('path')), fast1_end):
                    print(222)
                    fast1.append(os.path.relpath(i.get('path'), root_dir))
        else:
            if i.get('file_type') == "file" and fast1_end and fast2_end:
                if any(i['name'].endswith(ext) for ext in fast1_end):
                    fast1.append(os.path.relpath(i.get('path'), root_dir))
                if any(i['name'].endswith(ext) for ext in fast2_end):
                    fast2.append(os.path.relpath(i.get('path'), root_dir))
    data = {'fastq1': fast1, 'fastq2': fast2, 'file_info': file_info}
    return data


def get_dir_info(path: str) -> List[Dict]:
    """
    获取目录下所有文件和子目录的信息
    
    Args:
        path: 目录路径
    Returns:
        List[Dict]: 包含文件/目录信息的字典列表
    """
    result = []

    if path is None:
        return result
    if not os.path.exists(path):
        return result

    if os.path.isfile(path):
        return result

    for item in os.listdir(path):
        item_path = os.path.join(path, item)
        stat_info = os.stat(item_path)
        item_info = {
            'name': item,
            'size': stat_info.st_size,
            'modified_time': datetime.fromtimestamp(stat_info.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            'file_type': 'file' if os.path.isfile(item_path) else 'dir'
        }
        result.append(item_info)

    return result


def get_dir_size(path, follow_symlinks=False):
    total = 0
    if not os.path.exists(path):
        return total
    for entry in os.scandir(path):
        try:
            if entry.is_file(follow_symlinks=follow_symlinks):
                total += entry.stat().st_size
            elif entry.is_dir(follow_symlinks=follow_symlinks):
                total += get_dir_size(entry.path)
        except (PermissionError, FileNotFoundError):
            continue
    return total


def format_size(size):
    """
    智能转换文件大小单位
    :param size: 字节数
    :return: 带单位的格式化字符串
    """
    units = ('B', 'K', 'M', 'G', 'T')
    unit_index = 0

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    precision = 1 if size < 100 else 0
    if unit_index == 0:  # 字节数不需要小数
        precision = 0

    return f"{size:.{precision}f}{units[unit_index]}"


async def copy_file_with_progress1(src, dst):
    copy_progress = {"progress": 0.0}
    total_size = os.path.getsize(src)
    copied_size = 0

    async with aiofiles.open(src, 'rb') as src_file:
        async with aiofiles.open(dst, 'wb') as dst_file:
            while True:
                chunk = await src_file.read(8192)  # 8KB chunk size
                if not chunk:
                    break
                await dst_file.write(chunk)
                copied_size += len(chunk)
                progress = (copied_size / total_size) * 100
                copy_progress["progress"] = progress
                print(copy_progress)


async def copy_file_with_progress(src, dst, pbar, dbobj):
    """
    异步拷贝单个文件并更新进度条
    :param src: 源文件路径
    :param dst: 目标文件路径
    :param pbar: tqdm 进度条对象
    """
    db = get_dbs()
    async with aiofiles.open(src, 'rb') as f_src:
        async with aiofiles.open(dst, 'wb') as f_dst:
            bytes_since_last_save = 0
            while True:
                chunk = await f_src.read(1024 * 1024 * 100)  # 每次读取 1MB
                if not chunk:
                    break
                await f_dst.write(chunk)
                pbar.update(len(chunk))
                bytes_since_last_save += len(chunk)
                percent_complete = (pbar.n / pbar.total) * 100
                if percent_complete > 99.9:
                    dbobj.status = 2
                dbobj.percent = round(percent_complete)
                db.add(dbobj)
                db.commit()

                # if bytes_since_last_save >= 10 * 1024 * 1024:
                #     print(22222222)
                #     percent_complete = (pbar.n / pbar.total) * 100
                #     dbobj.percent = round(percent_complete)
                #     db.add(dbobj)
                #     db.commit()
                #     bytes_since_last_save = 0
            # if bytes_since_last_save > 0:
            #     percent_complete = (pbar.n / pbar.total) * 100
            #     dbobj.percent = round(percent_complete)
            #     db.add(dbobj)


async def copy_directory_with_progress(src, dst, dbobj):
    """
    异步拷贝目录并显示进度条
    :param src: 源目录路径
    :param dst: 目标目录路径
    """
    if not os.path.exists(dst):
        os.makedirs(dst)

    # 获取源目录中的所有文件
    items = []
    for root, dirs, files in os.walk(src):
        for name in files:
            items.append(os.path.join(root, name))
        for name in dirs:
            items.append(os.path.join(root, name))

    # 计算总大小（仅文件）
    total_size = sum(os.path.getsize(item) for item in items if os.path.isfile(item))

    # 使用 tqdm 显示进度条
    with tqdm(total=total_size, unit='B', unit_scale=True, desc='Copying') as pbar:
        for item in items:
            # 计算相对路径
            rel_path = os.path.relpath(item, src)
            dst_path = os.path.join(dst, rel_path)

            # 如果是文件，异步拷贝并更新进度条
            if os.path.isfile(item):
                await copy_file_with_progress(item, dst_path, pbar, dbobj)
            # 如果是目录，创建目录
            elif os.path.isdir(item):
                os.makedirs(dst_path, exist_ok=True)
        progress = (total_size / total_size) * 100


async def copy_with_progress(src, dst, dbobj):
    """
    异步拷贝文件或目录并显示进度条
    :param src: 源文件或目录路径
    :param dst: 目标文件或目录路径
    """
    try:
        if os.path.isfile(src):
            # 获取文件大小
            total_size = os.path.getsize(src)
            # 使用 tqdm 显示进度条
            with tqdm(total=total_size, unit='B', unit_scale=True, desc='Copying') as pbar:
                await copy_file_with_progress(src, dst, pbar, dbobj)
                progress = (total_size / total_size) * 100
        elif os.path.isdir(src):
            await copy_directory_with_progress(src, dst, dbobj)
        else:
            db = get_dbs()
            dbobj.status = 3
            db.add(dbobj)
            db.commit()
            raise ValueError(f"Source path '{src}' is neither a file nor a directory.")
    except Exception as e:
        db = get_dbs()
        dbobj.status = 3
        db.add(dbobj)
        db.commit()
        logger.error(f'上传数据异常:{dst}:{e}:')
# async def main():
#     src = "/opt/aa.sh"  # 源文件路径
#     dst = "/home/gpas/aa.sh"  # 目标文件路径
#     await copy_file_with_progress(src, dst)
#     print("File copy completed!")
#
# if __name__ == "__main__":
#     import asyncio
#     asyncio.run(main())
