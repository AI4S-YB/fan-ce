import gzip
import os
import re
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict

from .core.base_extractor import BaseExtractor


class GFF3Extractor(BaseExtractor):
    """GFF3文件元数据提取器
    
    支持从GFF3文件中提取：
    - 文件名信息（物种代码、登录号、装配类型等）
    - 头部元数据（版本、基因组构建信息等）
    - 特征统计（基因、mRNA、外显子等数量）
    - 文件统计（大小、压缩状态等）
    """
    
    def __init__(self):
        template_path = "gff3.json"
        super().__init__(template_path)
        self.template_name = "gff3"
        
        # 文件名解析正则表达式
        self.filename_pattern = re.compile(
            r'^([^-]+)-([^-]+)-([^-]+)-([^_]+)_([^.]+)\.([^.]+)\.gff3(?:\.gz)?$'
        )
        
        # 版本号提取正则表达式
        self.version_pattern = re.compile(r'v?(\d+(?:\.\d+)*)')
        
        # 最大处理行数（性能考虑）
        self.max_lines_to_process = 100000
        
        # 大小估算采样行数
        self.sample_lines_for_size = 1000
    
    def extract(self, file_path: str, sniff: Dict[str, Any]) -> Dict[str, Any]:
        """提取GFF3文件元数据
        
        Args:
            file_path: GFF3文件路径
            sniff: 文件检测信息
            
        Returns:
            包含所有元数据字段的字典
        """
        try:
            # 解析文件名
            filename_metadata = self._parse_filename(file_path)
            
            # 提取头部信息
            header_metadata = self._extract_header_metadata(file_path)
            
            # 统计特征
            feature_metadata = self._count_features(file_path)
            
            # 获取文件统计信息
            file_stats = self._get_file_stats(file_path)
            
            # 合并所有元数据
            metadata = self._merge_metadata(
                filename_metadata, 
                header_metadata, 
                feature_metadata, 
                file_stats
            )
            
            # 设置字段值
            self._set_fields(metadata)
            
            return self._build_result()
            
        except Exception as e:
            # 记录错误但不中断处理
            error_metadata = {'otherHeaders': [f"Error: {str(e)}"]}
            self._set_fields(error_metadata)
            return self._build_result()
    
    def _parse_filename(self, file_path: str) -> Dict[str, Any]:
        """解析GFF3文件名获取元数据
        
        期望格式: {species}-{accession}-{assembly_type}-{assembly_name}_{gene_model}.{version}.gff3.gz
        例如: homo_sapiens-GRCh38-REFERENCE-GRCh38_p14_genomic.v110.gff3.gz
        """
        filename = os.path.basename(file_path)
        
        match = self.filename_pattern.match(filename)
        if not match:
            return {
                'speciesCode': None,
                'accession': None,
                'assemblyType': None,
                'assemblyName': None,
                'geneModelId': None,
                'version': None
            }
        
        species_code, accession, assembly_type, assembly_name, gene_model, version_str = match.groups()
        
        # 提取版本号
        version_match = self.version_pattern.search(version_str)
        version = version_match.group(1) if version_match else version_str
        
        return {
            'speciesCode': species_code,
            'accession': accession,
            'assemblyType': assembly_type,
            'assemblyName': assembly_name,
            'geneModelId': gene_model,
            'version': version
        }
    
    def _extract_header_metadata(self, file_path: str) -> Dict[str, Any]:
        """提取GFF3文件头部元数据"""
        metadata = {
            'gffVersion': None,
            'genomeBuild': None,
            'genomeVersion': None,
            'genomeDate': None,
            'genebuildLastUpdated': None,
            'sequenceRegions': [],
            'sequenceRegionsCount': 0,
            'otherHeaders': []
        }
        
        try:
            open_func = gzip.open if file_path.endswith('.gz') else open
            with open_func(file_path, 'rt', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line.startswith('#'):
                        break
                    
                    # 解析各种头部信息
                    if line.startswith('##gff-version'):
                        metadata['gffVersion'] = line.split()[-1]
                    elif line.startswith('##genome-build'):
                        metadata['genomeBuild'] = line.split('##genome-build')[-1].strip()
                    elif line.startswith('##genome-version'):
                        metadata['genomeVersion'] = line.split('##genome-version')[-1].strip()
                    elif line.startswith('##genome-date'):
                        metadata['genomeDate'] = line.split('##genome-date')[-1].strip()
                    elif line.startswith('##genebuild-last-updated'):
                        metadata['genebuildLastUpdated'] = line.split('##genebuild-last-updated')[-1].strip()
                    elif line.startswith('##sequence-region'):
                        # 解析序列区域信息
                        parts = line.split()
                        if len(parts) >= 4:
                            region_info = {
                                'name': parts[1],
                                'start': int(parts[2]),
                                'end': int(parts[3])
                            }
                            metadata['sequenceRegions'].append(region_info)
                    else:
                        # 记录其他头部信息
                        if line.startswith('##') and line not in ['##FASTA', '###']:
                            metadata['otherHeaders'].append(line)
                
                metadata['sequenceRegionsCount'] = len(metadata['sequenceRegions'])
                
        except Exception as e:
            metadata['otherHeaders'].append(f"Header parsing error: {str(e)}")
        
        return metadata
    
    def _count_features(self, file_path: str) -> Dict[str, Any]:
        """统计GFF3文件中的特征类型和数量"""
        feature_counts = defaultdict(int)
        chromosomes = set()
        sources = set()
        total_features = 0
        lines_processed = 0
        
        try:
            open_func = gzip.open if file_path.endswith('.gz') else open
            with open_func(file_path, 'rt', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    
                    # 跳过注释行和空行
                    if not line or line.startswith('#'):
                        continue
                    
                    # 性能限制：避免处理过大文件
                    lines_processed += 1
                    if lines_processed > self.max_lines_to_process:
                        break
                    
                    # 解析GFF3行
                    parts = line.split('\t')
                    if len(parts) >= 3:
                        seqid = parts[0]
                        source = parts[1]
                        feature_type = parts[2]
                        
                        chromosomes.add(seqid)
                        sources.add(source)
                        feature_counts[feature_type] += 1
                        total_features += 1
        
        except Exception as e:
            # 记录错误但继续处理
            pass
        
        return {
            'numFeatures': total_features,
            'featureTypes': dict(feature_counts),
            'geneCount': feature_counts.get('gene', 0),
            'mRNACount': feature_counts.get('mRNA', 0),
            'exonCount': feature_counts.get('exon', 0),
            'CDSCount': feature_counts.get('CDS', 0),
            'chromosomes': sorted(list(chromosomes)),
            'sources': sorted(list(sources))
        }
    
    def _get_file_stats(self, file_path: str) -> Dict[str, Any]:
        """获取文件统计信息"""
        is_compressed = file_path.endswith('.gz')
        
        # 获取文件大小
        file_size_bytes = os.path.getsize(file_path)
        compressed_size_mb = file_size_bytes / (1024 * 1024)
        
        # 估算解压后大小
        estimated_size_mb = compressed_size_mb
        if is_compressed:
            estimated_size_mb = self._estimate_uncompressed_size(file_path, file_size_bytes)
        
        return {
            'isCompressed': is_compressed,
            'compressedSizeMB': round(compressed_size_mb, 2),
            'estimatedSizeMB': round(estimated_size_mb, 2)
        }
    
    def _estimate_uncompressed_size(self, file_path: str, compressed_size: int) -> float:
        """估算压缩文件的解压后大小"""
        try:
            sample_compressed = 0
            sample_uncompressed = 0
            lines_sampled = 0
            
            with gzip.open(file_path, 'rt', encoding='utf-8') as f:
                for line in f:
                    if lines_sampled >= self.sample_lines_for_size:
                        break
                    
                    sample_uncompressed += len(line.encode('utf-8'))
                    lines_sampled += 1
            
            if lines_sampled > 0:
                # 估算压缩比
                sample_compressed = compressed_size * (lines_sampled / self.sample_lines_for_size)
                if sample_compressed > 0:
                    compression_ratio = sample_uncompressed / sample_compressed
                    return (compressed_size * compression_ratio) / (1024 * 1024)
            
            # 默认压缩比（如果无法计算）
            return (compressed_size * 3) / (1024 * 1024)
            
        except Exception:
            # 使用默认压缩比
            return (compressed_size * 3) / (1024 * 1024)
    
    def _merge_metadata(self, filename_meta: Dict, header_meta: Dict, 
                       feature_meta: Dict, file_stats: Dict) -> Dict[str, Any]:
        """合并所有元数据"""
        merged = {}
        merged.update(filename_meta)
        merged.update(header_meta)
        merged.update(feature_meta)
        merged.update(file_stats)
        
        # 设置文件类型
        merged['type'] = 'GFF3'
        
        return merged


# 注册提取器到工厂
from .core.extractor_factory import factory
factory.register_extractor('gff3', GFF3Extractor)