"""
@File    :   tools.py
@Time    :   2023/06/09 15:20:00
@Author  :   kentnf
@Version :   1.0
@Desc    :   None
"""

import random
import subprocess
import requests
import threading


def run_in_background(func, args):
    """封装一个多进程后台运行任务的函数"""
    background_thread = threading.Thread(target=func, args=args)
    background_thread.start()
