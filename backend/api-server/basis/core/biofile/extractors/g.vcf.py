# core/extractors/gvcf.py
from .core.base_extractor import BaseExtractor
from .core.extractor_factory import register_extractor
from typing import Dict, Any
import gzip
import os
import re
from datetime import datetime
from pathlib import Path

class GvcfExtractor(BaseExtractor):
    """
    GVCF (Genomic Variant Call Format) 文件提取器
    
    支持提取GVCF文件的详细元数据信息，包括：
    - 文件格式版本和基本信息
    - 参考基因组信息
    - 染色体/scaffold信息
    - INFO/FORMAT/FILTER字段定义
    - 样本信息
    - 统计信息（支持快速模式和完整模式）
    """
    
    def __init__(self):
        template_path = "gvcf.json"
        super().__init__(template_path)
    
    def extract(self, path: str, sniff: Dict[str, Any]) -> Dict[str, Any]:
        """
        提取GVCF文件元数据
        
        Args:
            path: GVCF文件路径
            sniff: 嗅探参数，可包含 'fast_mode' 控制提取模式
        
        Returns:
            包含元数据的字典
        """
        # 检查文件是否存在
        if not os.path.exists(path):
            raise FileNotFoundError(f"文件不存在: {path}")
        
        # 从sniff参数获取模式设置，默认为快速模式
        fast_mode = sniff.get('fast_mode', True)
        
        # 设置基本文件信息
        self._set_basic_file_info(path, fast_mode)
        
        # 根据文件扩展名选择打开方式
        if path.endswith('.gz'):
            file_handle = gzip.open(path, 'rt', encoding='utf-8')
        else:
            file_handle = open(path, 'r', encoding='utf-8')
        
        try:
            self._parse_header(file_handle)
            if not fast_mode:
                self._calculate_full_statistics(file_handle)
            else:
                self._calculate_basic_statistics()
        finally:
            file_handle.close()
        
        return self._build_result()
    
    def _set_basic_file_info(self, path: str, fast_mode: bool):
        """设置基本文件信息"""
        file_path = Path(path)
        
        self.fileSize = os.path.getsize(path)
        self.isCompressed = path.endswith('.gz')
        self.extractionTime = datetime.now().isoformat()
        self.fastMode = fast_mode
    
    def _parse_header(self, file_handle):
        """解析VCF头部信息"""
        contigs_list = []
        info_fields = {}
        format_fields = {}
        filter_fields = {}
        command_lines = []
        samples_list = []
        column_count = 0
        
        for line in file_handle:
            line = line.strip()
            
            # 跳过空行
            if not line:
                continue
            
            # 处理头部行
            if line.startswith('##'):
                self._parse_header_line(line, contigs_list, info_fields, 
                                      format_fields, filter_fields, command_lines)
            elif line.startswith('#CHROM'):
                # 解析列标题行，获取样本信息
                columns = line.split('\t')
                column_count = len(columns)
                if len(columns) > 9:
                    samples_list = columns[9:]
                break  # 头部结束
            else:
                # 遇到数据行，停止解析头部
                break
        
        # 设置解析结果
        self.contigs = contigs_list
        self.numContigs = len(contigs_list)
        self.infoFields = info_fields
        self.formatFields = format_fields
        self.filterFields = filter_fields
        self.samples = samples_list
        self.numSamples = len(samples_list)
        self.columnCount = column_count
        self.commandLines = command_lines
    
    def _parse_header_line(self, line: str, contigs_list: list, info_fields: dict,
                          format_fields: dict, filter_fields: dict, command_lines: list):
        """解析单个头部行"""
        # 文件格式版本
        if line.startswith('##fileformat='):
            self.fileformat = line.split('=', 1)[1]
        
        # 文件日期
        elif line.startswith('##fileDate='):
            self.fileDate = line.split('=', 1)[1]
        
        # 来源信息
        elif line.startswith('##source='):
            self.source = line.split('=', 1)[1]
        
        # 参考基因组
        elif line.startswith('##reference='):
            self.reference = line.split('=', 1)[1]
        
        # 染色体/scaffold信息
        elif line.startswith('##contig='):
            contig_info = self._parse_structured_field(line, '##contig=')
            contigs_list.append(contig_info)
        
        # INFO字段定义
        elif line.startswith('##INFO='):
            info_field = self._parse_structured_field(line, '##INFO=')
            if 'ID' in info_field:
                info_fields[info_field['ID']] = info_field
        
        # FORMAT字段定义
        elif line.startswith('##FORMAT='):
            format_field = self._parse_structured_field(line, '##FORMAT=')
            if 'ID' in format_field:
                format_fields[format_field['ID']] = format_field
        
        # FILTER字段定义
        elif line.startswith('##FILTER='):
            filter_field = self._parse_structured_field(line, '##FILTER=')
            if 'ID' in filter_field:
                filter_fields[filter_field['ID']] = filter_field
        
        # 命令行信息
        elif 'CommandLine=' in line or 'command=' in line.lower():
            command_lines.append(line)
    
    def _parse_structured_field(self, line: str, prefix: str) -> dict:
        """解析结构化字段（如contig, INFO, FORMAT等）"""
        # 移除前缀
        content = line[len(prefix):]
        
        # 移除外层的<>
        if content.startswith('<') and content.endswith('>'):
            content = content[1:-1]
        
        # 解析键值对
        field_dict = {}
        
        # 使用正则表达式解析键值对，处理引号内的逗号
        pattern = r'([^=,]+)=([^,]*(?:"[^"]*"[^,]*)*?)(?=,\w+=|$)'
        matches = re.findall(pattern, content)
        
        for key, value in matches:
            key = key.strip()
            value = value.strip()
            
            # 移除引号
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            
            # 尝试转换数值
            if value.isdigit():
                value = int(value)
            elif value.replace('.', '').replace('-', '').isdigit():
                try:
                    value = float(value)
                except ValueError:
                    pass
            
            field_dict[key] = value
        
        return field_dict
    
    def _calculate_basic_statistics(self):
        """计算基本统计信息（快速模式）"""
        # 计算基因组总长度
        if self.contigs:
            total_length = sum(contig.get('length', 0) for contig in self.contigs)
            self.totalGenomeLength = total_length
        
        # 快速模式下不统计变异数量
        self.variantCount = "未统计（快速模式）"
        self.headerLines = "未统计（快速模式）"
        self.totalLines = "未统计（快速模式）"
    
    def _calculate_full_statistics(self, file_handle):
        """计算完整文件统计信息（完整模式）"""
        # 重置文件指针到开头
        file_handle.seek(0)
        
        variant_count = 0
        header_lines = 0
        
        for line in file_handle:
            line = line.strip()
            if line.startswith('#'):
                header_lines += 1
            elif line:
                variant_count += 1
        
        self.headerLines = header_lines
        self.variantCount = variant_count
        self.totalLines = header_lines + variant_count
        
        # 计算基因组总长度
        if self.contigs:
            total_length = sum(contig.get('length', 0) for contig in self.contigs)
            self.totalGenomeLength = total_length

# 注册提取器
register_extractor("GVCF", GvcfExtractor())