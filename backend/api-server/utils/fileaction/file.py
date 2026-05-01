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
import configparser


class ConfigFile:
    def __init__(self, config_dir="", file=""):
        self.config_dir = config_dir
        self.file = file
        self.config = {}
        self.file_type = ""

    def load_config(self, filename):
        """加载指定应用的配置文件"""
        config_path = os.path.join(self.config_dir, filename)
        try:
            config = configparser.RawConfigParser()
            config.read(config_path)
            self.config['config'] = config
            self.config['file_path'] = config_path
            self.config['file_type'] = 'ini'
            return
        except Exception as e:
            pass
        try:
            with open(config_path, 'r') as file:
                self.config['config'] = yaml.safe_load(file) or {}
                self.config['file_path'] = config_path
                self.config['file_type'] = 'yaml'
            return
        except Exception as e:
            pass

    def get_app_config(self, filename):
        self.load_config(filename)
        return self.config


class Registry:
    def __init__(self, options):
        self.config = options.get('config')
        self.file_path = options.get('file_path')
        self.file_type = options.get('file_type')

    def get_ini(self, key, default=None):
        v = default
        keys = key.split('.')
        section = keys[0]
        option = '.'.join(keys[1:])
        if self.config.has_section(section):
            if self.config.has_option(section, option):
                v = self.config[section][option]
        return v

    def get_yaml(self, key, default=None):
        """获取配置项"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            value = value.get(k, default)
            if value == default:
                break
        return value

    def get(self, key, default=None):
        if self.file_type == "ini":
            return self.get_ini(key, default)
        if self.file_type == "yaml":
            return self.get_yaml(key, default)
        return None

    def set(self, key, value):
        """设置配置项并保存"""
        if self.file_type == "ini":
            keys = key.split('.')
            section = keys[0]
            option = '.'.join(keys[1:])
            if not self.get(key) is None:
                if self.get(key) != value:
                    self.config[section][option] = value
            else:
                if not self.config.has_section(section):
                    self.config.add_section(section)
                self.config[section][option] = value
        if self.file_type == "yaml":
            keys = key.split('.')
            config = self.config
            for k in keys[:-1]:
                config = config.setdefault(k, {})
            config[keys[-1]] = value

    def save(self):
        """保存配置到文件"""
        if self.file_type == "ini":
            with open(self.file_path, 'w') as configfile:
                self.config.write(configfile)
        if self.file_type == "yaml":
            with open(self.file_path, 'w') as file:
                yaml.dump(self.config, file)


def file_update(file, filed, value):
    GlobalConfigFile: ConfigFile = ConfigFile(file=file)
    app_options: Registry = Registry(GlobalConfigFile.get_app_config(file))
    app_options.set(filed, value)
    app_options.save()
