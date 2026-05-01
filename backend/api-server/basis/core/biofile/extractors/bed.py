from .core.base_extractor import BaseExtractor
from .core.extractor_factory import register_extractor_class
from typing import Dict, Any
import os
import re
from collections import defaultdict
from pathlib import Path

# 有效的BED列数
VALID_COL_COUNTS = [3, 4, 5, 6, 8, 9, 12]

@register_extractor_class("BED")
class BEDExtractor(BaseExtractor):
    """基于现有bed.py实现的BED文件元数据提取器"""
    
    def __init__(self):
        # 使用BED模板文件路径
        template_path = "bed.json"
        super().__init__(template_path)
    
    def extract(self, path: str, sniff: Dict[str, Any]) -> Dict[str, Any]:
        """提取BED文件元数据"""
        try:
            # 使用原始bed.py的核心解析逻辑
            metadata = self._parse_bed_metadata(path)
            
            # 转换为biofile系统格式
            self._set_fields({
                'file_info': metadata.get('file_info', {}),
                'source_info': {
                    'source': metadata.get('source', 'unknown'),
                    'database': metadata.get('database'),
                    'genome_build': metadata.get('genome_build'),
                    'track_name': metadata.get('track_name')
                },
                'content_stats': {
                    'feature_count': metadata.get('feature_count', 0),
                    'bed_type': metadata.get('type', 'unknown'),
                    'chromosome_distribution': self._get_chromosome_distribution(metadata.get('features', []))
                },
                'format_info': {
                    'valid_col_counts': VALID_COL_COUNTS,
                    'detected_format': self._detect_bed_format(metadata.get('features', []))
                },
                'sidecars': sniff.get('sidecars', [])
            })
            
            return self._build_result()
            
        except Exception as e:
            # 返回错误信息
            return {
                "type": {"value": "BED", "desc": "文件类型标识"},
                "error": {"value": str(e), "desc": "处理错误信息"},
                "sidecars": {"value": sniff.get('sidecars', []), "desc": "关联文件"}
            }
    
    def _is_database_download(self, file_path):
        """判断是否为数据库下载文件（复制自原始bed.py）"""
        file_path = Path(file_path)
        filename = file_path.name.lower()
        
        # 数据库文件名模式
        db_patterns = [
            r'ucsc.*\.bed',
            r'ensembl.*\.bed', 
            r'gencode.*\.bed',
            r'refseq.*\.bed',
            r'.*_hg\d+.*\.bed',
            r'.*_mm\d+.*\.bed',
            r'.*_dm\d+.*\.bed'
        ]
        
        # 检查文件名是否匹配数据库模式
        for pattern in db_patterns:
            if re.match(pattern, filename):
                return True
        
        # 检查是否包含数据库ID
        if any(keyword in filename for keyword in ['ucsc', 'ensembl', 'gencode', 'refseq']):
            return True
            
        return False
    
    def _get_database_metadata(self, file_path):
        """从数据库文件ID获取元数据（复制自原始bed.py）"""
        file_path = Path(file_path)
        filename = file_path.name
        
        metadata = {
            'source': 'database',
            'database': None,
            'genome_build': None,
            'track_name': None,
            'file_info': {
                'filename': filename,
                'size': file_path.stat().st_size if file_path.exists() else 0
            }
        }
        
        # 解析数据库类型
        if 'ucsc' in filename.lower():
            metadata['database'] = 'UCSC'
        elif 'ensembl' in filename.lower():
            metadata['database'] = 'Ensembl'
        elif 'gencode' in filename.lower():
            metadata['database'] = 'GENCODE'
        elif 'refseq' in filename.lower():
            metadata['database'] = 'RefSeq'
        
        # 解析基因组版本
        genome_patterns = {
            r'hg(\d+)': 'hg{}',
            r'mm(\d+)': 'mm{}',
            r'dm(\d+)': 'dm{}',
            r'ce(\d+)': 'ce{}'
        }
        
        for pattern, format_str in genome_patterns.items():
            match = re.search(pattern, filename.lower())
            if match:
                metadata['genome_build'] = format_str.format(match.group(1))
                break
        
        # 尝试解析track名称
        track_match = re.search(r'([^_/]+)_[hm][gm]\d+', filename)
        if track_match:
            metadata['track_name'] = track_match.group(1)
        
        return metadata
    
    def _get_external_records(self, file_path):
        """读取外部记录文件的基本信息（复制自原始bed.py）"""
        file_path = Path(file_path)
        
        metadata = {
            'source': 'external',
            'file_info': {
                'filename': file_path.name,
                'size': file_path.stat().st_size if file_path.exists() else 0,
                'path': str(file_path.absolute())
            }
        }
        
        return metadata
    
    def _parse_block_fields(self, block_fields):
        """解析BED12格式的区块字段（复制自原始bed.py）"""
        try:
            block_count = int(block_fields[0])
            block_sizes = [int(x) for x in block_fields[1].rstrip(',').split(',') if x]
            block_starts = [int(x) for x in block_fields[2].rstrip(',').split(',') if x]
            
            # 验证区块数据一致性
            if len(block_sizes) != block_count or len(block_starts) != block_count:
                return None
                
            blocks = []
            for i in range(block_count):
                blocks.append({
                    'size': block_sizes[i],
                    'start': block_starts[i]
                })
                
            return {
                'block_count': block_count,
                'blocks': blocks,
                'total_block_size': sum(block_sizes)
            }
            
        except (ValueError, IndexError):
            return None
    
    def _infer_bed_type(self, features):
        """根据特征推断BED文件类型（复制自原始bed.py）"""
        if not features:
            return 'unknown'
        
        # 统计区间长度分布
        lengths = []
        has_blocks = False
        
        for feature in features:
            length = feature['end'] - feature['start']
            lengths.append(length)
            
            if feature.get('blocks'):
                has_blocks = True
        
        if not lengths:
            return 'unknown'
        
        avg_length = sum(lengths) / len(lengths)
        
        # 基于长度和特征推断类型
        if has_blocks:
            return 'gene_structure'  # 包含外显子结构
        elif avg_length < 1000:
            return 'regulatory_elements'  # 调控元件
        elif avg_length < 10000:
            return 'genomic_features'  # 基因组特征
        else:
            return 'large_regions'  # 大区域
    
    def _parse_bed_metadata(self, file_path):
        """解析BED文件元数据的主函数（基于原始bed.py）"""
        # 步骤1: 处理来源
        if self._is_database_download(file_path):
            metadata = self._get_database_metadata(file_path)
        else:
            metadata = self._get_external_records(file_path)
        
        # 步骤2: 内容解析
        features = []
        with self._open_maybe_gz(file_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                    
                # UCSC头过滤
                if line.startswith(('track', 'browser', '#')):
                    continue
                    
                # 列数识别
                cols = line.split('\t')
                if len(cols) not in VALID_COL_COUNTS:
                    continue
                    
                # 坐标转换
                chrom = cols[0]
                try:
                    start = int(cols[1])
                    end = int(cols[2])
                except ValueError:
                    continue
                    
                # 区块识别
                if len(cols) >= 12:
                    block_meta = self._parse_block_fields(cols[9:12])
                else:
                    block_meta = None
                    
                features.append({
                    'chrom': chrom,
                    'start': start,
                    'end': end,
                    'blocks': block_meta
                })
        
        # 步骤3: 类型识别
        metadata['type'] = self._infer_bed_type(features)
        metadata['features'] = features
        metadata['feature_count'] = len(features)
        
        return metadata
    
    def _get_chromosome_distribution(self, features):
        """获取染色体分布统计"""
        if not features:
            return {}
        
        chroms = defaultdict(int)
        for feature in features:
            chroms[feature['chrom']] += 1
        
        # 按计数降序排序，只返回前10个
        sorted_chroms = sorted(chroms.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_chroms[:10])
    
    def _detect_bed_format(self, features):
        """检测BED格式"""
        if not features:
            return 'BED3'
        
        # 检查是否有区块信息
        has_blocks = any(feature.get('blocks') for feature in features)
        if has_blocks:
            return 'BED12'
        
        # 根据特征数量推断格式
        max_cols = 3  # 默认最少3列
        # 这里可以根据实际解析的列数来判断，简化处理
        return f'BED{max_cols}'