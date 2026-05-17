"""
@File    :   libs.loger.py
@Time    :   2023/06/09 15:20:00
@Author  :   kentnf
@Version :   1.0
@Desc    :   None
"""
import os
from loguru import logger
from config.settings import settings

current_path = os.path.dirname(__file__)
base_path = os.path.dirname(current_path)
log_path = base_path + os.sep + settings.LOGGER_FOLDER + os.sep
os.makedirs(log_path, exist_ok=True)

file_list = os.listdir(log_path)
if len(file_list) > 4:
    os.remove(os.path.join(log_path, file_list[0]))

# 日志输出路径
log_path_name = os.path.join(log_path, settings.LOGGER_NAME)

logger.add(log_path_name,
           encoding=settings.GLOBAL_ENCODING,
           level=settings.LOGGER_LEVEL,
           rotation=settings.LOGGER_ROTATION,
           retention=settings.LOGGER_RETENTION,
           enqueue=True)


