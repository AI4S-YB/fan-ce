from .core.base_extractor import BaseExtractor
from .core.extractor_factory import register_extractor
from typing import Dict, Any, Optional
import os
import pysam

class BamExtractor(BaseExtractor):
    def __init__(self):
        template_path = "bam.json"
        super().__init__(template_path)
    
    def extract(self, path: str, sniff: Dict[str, Any]) -> Dict[str, Any]:
        """提取BAM文件元数据"""
        try:
            # 解析BAM文件元数据
            metadata = self._parse_bam_metadata(path)
            
            # 设置基本字段
            basic_fields = {
                'filePath': path,
                'fileSize': os.path.getsize(path),
                'isCompressed': self._is_compressed(path)
            }
            self._set_fields(basic_fields)
            
            # 检查索引文件
            self._check_index_file(path)
            
            # 设置元数据字段
            self._set_fields(metadata)
            
            return self._build_result()
            
        except Exception as e:
            # 创建错误元数据
            return self._create_error_metadata(path, str(e))
    
    def _parse_bam_metadata(self, bam_path: str) -> Dict[str, Any]:
        """解析BAM文件的核心元数据"""
        # 创建pysam.AlignmentFile对象
        bam_file = pysam.AlignmentFile(bam_path, "rb")
        
        try:
            # 初始化元数据字典
            metadata = {}
            
            # 解析头部信息
            header_info = bam_file.header.to_dict()
            
            # 基本头部信息
            metadata['headerCount'] = len(header_info.get('HD', {}))
            metadata['isSorted'] = header_info.get('HD', {}).get('SO') == "coordinate"
            metadata['refGenome'] = bam_file.references[0] if bam_file.references else None
            
            # 读取read group信息
            rg_info = header_info.get('RG', [])
            if rg_info:
                rg = rg_info[0]
                metadata['sample'] = rg.get("SM")
                metadata['platform'] = rg.get("PL")
                metadata['sampleInfo'] = rg
                metadata['platformInfo'] = {
                    'platform': rg.get("PL"),
                    'library': rg.get("LB"),
                    'platform_unit': rg.get("PU")
                }
            
            # 计算读段统计信息
            read_stats = self._calculate_read_statistics(bam_file)
            metadata.update(read_stats)
            
            return metadata
            
        finally:
            bam_file.close()
    
    def _calculate_read_statistics(self, bam_file) -> Dict[str, Any]:
        """计算读段统计信息"""
        # 初始化统计变量
        total_reads = 0
        mapped_reads = 0
        unmapped_reads = 0
        total_length = 0
        total_mapq = 0
        has_secondary = False
        has_supplementary = False
        insert_sizes = []
        quality_scores = []
        flag_stats = {}
        
        try:
            # 尝试使用索引进行高效统计
            try:
                # 如果有索引，可以更高效地统计
                for read in bam_file.fetch():
                    total_reads += 1
                    
                    # 读段长度和质量统计
                    if read.query_length:
                        total_length += read.query_length
                    if read.mapping_quality is not None:
                        total_mapq += read.mapping_quality
                        quality_scores.append(read.mapping_quality)
                    
                    # 比对状态统计
                    if read.is_unmapped:
                        unmapped_reads += 1
                    else:
                        mapped_reads += 1
                        
                        # 插入片段大小统计（仅对正确配对的读段）
                        if read.is_proper_pair and read.template_length > 0:
                            insert_sizes.append(abs(read.template_length))
                    
                    # FLAG位统计
                    if read.is_secondary:
                        has_secondary = True
                    if read.is_supplementary:
                        has_supplementary = True
                    
                    # 收集FLAG统计
                    flag = read.flag
                    flag_stats[flag] = flag_stats.get(flag, 0) + 1
                    
                    # 对于大文件，采样策略
                    if total_reads >= 100000:  # 采样前10万条读段
                        break
                        
            except Exception:
                # 如果没有索引或其他错误，使用until_eof=True遍历整个文件
                for read in bam_file.fetch(until_eof=True):
                    total_reads += 1
                    
                    # 读段长度和质量统计
                    if read.query_length:
                        total_length += read.query_length
                    if read.mapping_quality is not None:
                        total_mapq += read.mapping_quality
                        quality_scores.append(read.mapping_quality)
                    
                    # 比对状态统计
                    if read.is_unmapped:
                        unmapped_reads += 1
                    else:
                        mapped_reads += 1
                        
                        # 插入片段大小统计（仅对正确配对的读段）
                        if read.is_proper_pair and read.template_length > 0:
                            insert_sizes.append(abs(read.template_length))
                    
                    # FLAG位统计
                    if read.is_secondary:
                        has_secondary = True
                    if read.is_supplementary:
                        has_supplementary = True
                    
                    # 收集FLAG统计
                    flag = read.flag
                    flag_stats[flag] = flag_stats.get(flag, 0) + 1
                    
                    # 对于大文件，采样策略
                    if total_reads >= 100000:  # 采样前10万条读段
                        break
            
            # 计算统计结果
            stats = {
                'numReads': total_reads,
                'numMapped': mapped_reads,
                'numUnmapped': unmapped_reads,
                'mappingRate': round(mapped_reads / total_reads, 4) if total_reads > 0 else 0,
                'avgReadLength': round(total_length / total_reads, 2) if total_reads > 0 else 0,
                'avgMappingQuality': round(total_mapq / total_reads, 2) if total_reads > 0 else 0,
                'hasSecondary': has_secondary,
                'hasSupplementary': has_supplementary,
                'flagStatistics': flag_stats
            }
            
            # 插入片段大小统计
            if insert_sizes:
                insert_sizes.sort()
                n = len(insert_sizes)
                stats['insertSizeStats'] = {
                    'mean': round(sum(insert_sizes) / n, 2),
                    'median': insert_sizes[n // 2],
                    'min': min(insert_sizes),
                    'max': max(insert_sizes),
                    'count': n
                }
            
            # 质量分布统计
            if quality_scores:
                quality_scores.sort()
                n = len(quality_scores)
                stats['qualityDistribution'] = {
                    'mean': round(sum(quality_scores) / n, 2),
                    'median': quality_scores[n // 2],
                    'min': min(quality_scores),
                    'max': max(quality_scores)
                }
            
            return stats
            
        except Exception as e:
            # 如果统计失败，返回默认值
            return {
                'numReads': 0,
                'numMapped': 0,
                'numUnmapped': 0,
                'mappingRate': 0,
                'avgReadLength': 0,
                'avgMappingQuality': 0,
                'hasSecondary': False,
                'hasSupplementary': False,
                'insertSizeStats': None,
                'qualityDistribution': None,
                'flagStatistics': {}
            }
    
    def _check_index_file(self, bam_path: str):
        """检查BAM索引文件"""
        # 检查常见的索引文件格式
        index_extensions = ['.bai', '.csi']
        index_info = None
        
        for ext in index_extensions:
            index_path = bam_path + ext
            if os.path.exists(index_path):
                index_info = {
                    'path': index_path,
                    'type': ext[1:],  # 去掉点号
                    'size': os.path.getsize(index_path),
                    'exists': True
                }
                break
        
        if index_info is None:
            index_info = {
                'exists': False,
                'type': None,
                'path': None,
                'size': 0
            }
        
        self._set_fields({'indexFile': index_info})
    
    def _create_error_metadata(self, file_path: str, error_message: str) -> Dict[str, Any]:
        """创建错误情况下的元数据"""
        error_data = {
            'filePath': file_path,
            'fileSize': os.path.getsize(file_path) if os.path.exists(file_path) else 0,
            'isCompressed': self._is_compressed(file_path) if os.path.exists(file_path) else False,
            'numReads': 0,
            'numMapped': 0,
            'numUnmapped': 0,
            'mappingRate': 0,
            'avgReadLength': 0,
            'avgMappingQuality': 0,
            'hasSecondary': False,
            'hasSupplementary': False,
            'headerCount': 0,
            'isSorted': False,
            'refGenome': None,
            'sample': None,
            'platform': None,
            'insertSizeStats': None,
            'sampleInfo': None,
            'platformInfo': None,
            'qualityDistribution': None,
            'flagStatistics': {},
            'indexFile': {'exists': False, 'type': None, 'path': None, 'size': 0}
        }
        
        self._set_fields(error_data)
        result = self._build_result()
        result['error'] = {'value': f'BAM文件解析失败: {error_message}', 'desc': '错误信息'}
        
        return result

# 注册BAM提取器
register_extractor("BAM", BamExtractor())