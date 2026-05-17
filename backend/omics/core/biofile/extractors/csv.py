# CSV文件提取器
from .core.base_extractor import BaseExtractor
from .core.extractor_factory import register_extractor
from typing import Dict, Any
from pathlib import Path
import pandas as pd
import csv
import chardet
import os

class CsvExtractor(BaseExtractor):
    """
    CSV文件提取器
    提取CSV文件中的列名、行数、分隔符等信息
    """
    
    def __init__(self):
        template_path = "csv.json"
        super().__init__(template_path)
    
    def _detect_encoding(self, path: str) -> str:
        """检测文件编码"""
        try:
            with open(path, 'rb') as f:
                raw_data = f.read(10000)  # 读取前10KB用于检测编码
                result = chardet.detect(raw_data)
                return result.get('encoding', 'utf-8') or 'utf-8'
        except Exception:
            return 'utf-8'
    
    def _detect_delimiter(self, path: str, encoding: str) -> str:
        """检测CSV分隔符"""
        try:
            with open(path, 'r', encoding=encoding, errors='replace') as f:
                # 读取前几行来检测分隔符
                sample = f.read(1024)
                sniffer = csv.Sniffer()
                delimiter = sniffer.sniff(sample).delimiter
                return delimiter
        except Exception:
            return ','
    
    def _has_header(self, path: str, encoding: str, delimiter: str) -> bool:
        """检测是否有表头"""
        try:
            with open(path, 'r', encoding=encoding, errors='replace') as f:
                sample = f.read(1024)
                sniffer = csv.Sniffer()
                return sniffer.has_header(sample)
        except Exception:
            return True  # 默认假设有表头
    
    def extract(self, path: str, sniff: Dict[str, Any]) -> Dict[str, Any]:
        """
        提取CSV文件信息
        
        Args:
            path: CSV文件路径
            sniff: 文件检测信息
            
        Returns:
            包含CSV信息的字典
        """
        try:
            # 设置基础信息
            self.sidecars = sniff.get("sidecars", []) if sniff else []
            self.fileName = Path(path).name
            self.isCompressed = path.endswith(".gz")
            self.fileSize = self._get_file_size(path)
            
            # 检查文件是否存在
            if not Path(path).exists():
                raise FileNotFoundError(f"文件不存在: {path}")
            
            # 检测文件编码
            encoding = self._detect_encoding(path)
            self.encoding = encoding
            
            # 检测分隔符
            delimiter = self._detect_delimiter(path, encoding)
            self.delimiter = delimiter
            
            # 检测是否有表头
            has_header = self._has_header(path, encoding, delimiter)
            self.hasHeader = has_header
            
            # 使用pandas读取CSV文件
            try:
                if self.isCompressed:
                    df = pd.read_csv(path, compression='gzip', encoding=encoding, 
                                   sep=delimiter, nrows=0)  # 只读取表头
                else:
                    df = pd.read_csv(path, encoding=encoding, sep=delimiter, nrows=0)
                
                # 提取列信息
                column_names = df.columns.tolist()
                self.columnNames = column_names
                self.columnCount = len(column_names)
                
                # 计算行数（不包括表头）
                if self.isCompressed:
                    df_full = pd.read_csv(path, compression='gzip', encoding=encoding, sep=delimiter)
                else:
                    df_full = pd.read_csv(path, encoding=encoding, sep=delimiter)
                
                self.rowCount = len(df_full)
                
            except Exception as e:
                # 如果pandas读取失败，尝试使用csv模块
                with self._open_maybe_gz(path) if self.isCompressed else open(path, 'r', encoding=encoding, errors='replace') as f:
                    reader = csv.reader(f, delimiter=delimiter)
                    
                    rows = list(reader)
                    if not rows:
                        self.columnNames = []
                        self.columnCount = 0
                        self.rowCount = 0
                    else:
                        if has_header:
                            self.columnNames = rows[0]
                            self.columnCount = len(rows[0])
                            self.rowCount = len(rows) - 1
                        else:
                            # 如果没有表头，生成默认列名
                            self.columnCount = len(rows[0]) if rows else 0
                            self.columnNames = [f"Column_{i+1}" for i in range(self.columnCount)]
                            self.rowCount = len(rows)
            
            return self._build_result()
            
        except Exception as e:
            # 发生错误时返回基本信息
            self.sidecars = sniff.get("sidecars", []) if sniff else []
            self.fileName = Path(path).name
            self.isCompressed = path.endswith(".gz")
            self.fileSize = self._get_file_size(path) if Path(path).exists() else 0
            self.columnNames = []
            self.columnCount = 0
            self.rowCount = 0
            self.delimiter = ','
            self.hasHeader = True
            self.encoding = 'utf-8'
            
            return self._build_result()

# 注册提取器
register_extractor("CSV", CsvExtractor())