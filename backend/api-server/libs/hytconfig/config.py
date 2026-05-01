# -*- coding: utf-8 -*-
"""
@Author  : llq
@Time    : 2024/9/22 14:47
@Function: 
@version :  1.0
@Desc    :  None
"""
import os
import yaml


class ConfigFile:
    def __init__(self, config_dir):
        self.config_dir = config_dir
        self.config = {}

    def load_config(self, app_name):
        """加载指定应用的配置文件"""
        config_path = os.path.join(self.config_dir, f"{app_name}.yaml")
        try:
            with open(config_path, 'r') as file:
                self.config['config'] = yaml.safe_load(file) or {}
                self.config['file_path'] = config_path
        except FileNotFoundError:
            self.config['config'] = {}
            self.config['file_path'] = ""
        except Exception as e:
            self.config['config'] = {}
            self.config['file_path'] = ""

    def get_app_config(self, app_name):
        self.load_config(app_name)
        return self.config


class Registry:
    def __init__(self, options):
        self.options = options.get('config')
        self.file_path = options.get('file_name')

    def get(self, key, default=None):
        """获取配置项"""
        keys = key.split('.')
        value = self.options
        for k in keys:
            value = value.get(k, default)
            if value == default:
                break
        return value

    def set(self, key, value):
        """设置配置项并保存"""
        keys = key.split('.')
        config = self.options
        for k in keys[:-1]:
            config = config.setdefault(k, {})
        config[keys[-1]] = value

    def save(self, app_name):
        """保存配置到文件"""
        with open(self.file_path, 'w') as file:
            yaml.dump(self.options, file)