# Excel文件提取器
from .core.base_extractor import BaseExtractor
from .core.extractor_factory import register_extractor
from typing import Dict, Any
from pathlib import Path
import pandas as pd
import os

class ExcelExtractor(BaseExtractor):
    """
    Excel文件提取器
    提取Excel文件中的sheet数量、名称和每个sheet的列名等信息
    """
    
    def __init__(self):
        template_path = "excel.json"
        super().__init__(template_path)
    
    def extract(self, path: str, sniff: Dict[str, Any]) -> Dict[str, Any]:
        """
        提取Excel文件信息
        
        Args:
            path: Excel文件路径
            sniff: 文件检测信息
            
        Returns:
            包含Excel信息的字典
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
            
            # 检查文件扩展名
            file_ext = Path(path).suffix.lower()
            if file_ext not in ['.xlsx', '.xls', '.xlsm']:
                raise ValueError(f"不支持的文件格式: {file_ext}，仅支持 .xlsx, .xls, .xlsm")
            
            # 读取Excel文件的所有sheet名称
            excel_file = pd.ExcelFile(path)
            sheet_names = excel_file.sheet_names
            
            # 设置基本信息
            self.sheetCount = len(sheet_names)
            self.sheetNames = sheet_names
            
            # 提取每个sheet的信息
            sheets_info = []
            total_columns = 0
            total_rows = 0
            
            for sheet_name in sheet_names:
                try:
                    # 读取sheet的前几行来获取列名
                    df = pd.read_excel(path, sheet_name=sheet_name, nrows=0)
                    columns = df.columns.tolist()
                    
                    # 获取sheet的基本信息
                    df_full = pd.read_excel(path, sheet_name=sheet_name)
                    row_count = len(df_full)
                    col_count = len(df_full.columns)
                    
                    sheet_info = {
                        'sheet_name': sheet_name,
                        'columns': columns,
                        'column_count': col_count,
                        'row_count': row_count
                    }
                    sheets_info.append(sheet_info)
                    
                    total_columns += col_count
                    total_rows += row_count
                    
                except Exception as e:
                    # 如果某个sheet读取失败，记录错误但继续处理其他sheet
                    sheet_info = {
                        'sheet_name': sheet_name,
                        'error': f'读取sheet失败: {str(e)}',
                        'columns': [],
                        'column_count': 0,
                        'row_count': 0
                    }
                    sheets_info.append(sheet_info)
            
            # 设置提取的信息
            self.sheetsInfo = sheets_info
            self.totalColumns = total_columns
            self.totalRows = total_rows
            
            # 构建并返回结果
            return self._build_result()
            
        except Exception as e:
            # 如果处理过程中出现错误，返回错误信息
            self.fileName = Path(path).name if Path(path).exists() else path
            self.sheetCount = 0
            self.sheetNames = []
            self.sheetsInfo = [{'error': f'处理文件时发生错误: {str(e)}'}]
            self.totalColumns = 0
            self.totalRows = 0
            self.isCompressed = path.endswith(".gz")
            self.fileSize = self._get_file_size(path) if Path(path).exists() else 0
            
            return self._build_result()

# 注册提取器
register_extractor("Excel", ExcelExtractor())