# core/extractors/gtf_example.py
"""
GTF文件提取器示例

这是一个完整的提取器实现示例，展示了如何为新的文件类型创建提取器。
GTF (Gene Transfer Format) 是用于描述基因注释的标准格式。

注意：这是一个示例文件，不会自动注册。如果要使用，请重命名为 gtf.py
"""

from .core.base_extractor import BaseExtractor
from .core.extractor_factory import register_extractor
from typing import Dict, Any, Set, List
import re

class GtfExtractor(BaseExtractor):
    """
    GTF文件提取器
    
    GTF格式包含9个制表符分隔的字段：
    1. seqname - 序列名称（染色体）
    2. source - 注释来源
    3. feature - 特征类型（gene, transcript, exon等）
    4. start - 起始位置
    5. end - 结束位置
    6. score - 分数
    7. strand - 链方向
    8. frame - 阅读框
    9. attribute - 属性信息
    """
    
    def __init__(self):
        template_path = "gtf.json"
        super().__init__(template_path)
    
    def extract(self, path: str, sniff: Dict[str, Any]) -> Dict[str, Any]:
        """
        提取GTF文件的所有信息
        
        Args:
            path: 文件路径
            sniff: 文件检测结果字典
            
        Returns:
            包含所有提取信息的字典
        """
        # 初始化所有统计变量
        version = None
        first_feature = None
        attributes = set()
        num_features = 0
        feature_types = {}
        chromosomes = set()
        sources = set()
        feature_lengths = []
        feature_type_counts = {}
        chromosome_counts = {}
        
        with self._open_maybe_gz(path) as fh:
            line_count = 0
            for line in fh:
                line = line.strip()
                line_count += 1
                
                # 跳过空行
                if not line:
                    continue
                
                # 解析版本信息（通常在注释中）
                if line.startswith('#'):
                    if 'gtf-version' in line.lower() or 'version' in line.lower():
                        # 简单的版本提取
                        version_match = re.search(r'version\s+([\d\.]+)', line, re.IGNORECASE)
                        if version_match:
                            version = version_match.group(1)
                    continue
                
                # 解析特征行
                fields = line.split('\t')
                if len(fields) >= 9:
                    try:
                        # 解析第一个特征行（头部信息）
                        if not first_feature:
                            first_feature = {
                                "chromosome": fields[0],
                                "source": fields[1],
                                "feature": fields[2],
                                "start": int(fields[3]) if fields[3].isdigit() else None,
                                "end": int(fields[4]) if fields[4].isdigit() else None,
                                "strand": fields[6] if fields[6] in ['+', '-', '.'] else None
                            }
                            
                            # 提取属性名称
                            attributes.update(self._extract_attribute_names(fields[8]))
                        
                        # 统计特征数量
                        num_features += 1
                        
                        # 收集基本信息
                        chromosome = fields[0]
                        source = fields[1]
                        feature_type = fields[2]
                        start = int(fields[3])
                        end = int(fields[4])
                        
                        chromosomes.add(chromosome)
                        sources.add(source)
                        
                        # 统计特征类型
                        feature_types[feature_type] = feature_types.get(feature_type, 0) + 1
                        
                        # 计算特征长度
                        length = end - start + 1
                        feature_lengths.append(length)
                        
                        # 统计特征类型分布
                        feature_type_counts[feature_type] = feature_type_counts.get(feature_type, 0) + 1
                        
                        # 统计染色体分布
                        chromosome_counts[chromosome] = chromosome_counts.get(chromosome, 0) + 1
                        
                    except (ValueError, IndexError):
                        # 跳过格式错误的行
                        continue
        
        # 计算长度统计
        if feature_lengths:
            avg_length = sum(feature_lengths) / len(feature_lengths)
            min_length = min(feature_lengths)
            max_length = max(feature_lengths)
        else:
            avg_length = min_length = max_length = 0
        
        # 直接设置各个字段
        self.sidecars = sniff.get("sidecars", []) if sniff else []
        self.version = version
        self.firstFeature = first_feature
        self.attributes = sorted(list(attributes))
        self.numFeatures = num_features
        self.featureTypes = feature_types
        self.chromosomes = sorted(list(chromosomes))
        self.sources = sorted(list(sources))
        self.isCompressed = self._is_compressed(path)
        self.avgFeatureLength = round(avg_length, 2)
        self.minFeatureLength = min_length
        self.maxFeatureLength = max_length
        self.featureTypeDistribution = feature_type_counts
        self.chromosomeDistribution = chromosome_counts
        
        return self._build_result()
    
    def _extract_attribute_names(self, attribute_string: str) -> Set[str]:
        """
        从属性字符串中提取属性名称
        
        GTF属性格式: key1 "value1"; key2 "value2";
        
        Args:
            attribute_string: 属性字符串
            
        Returns:
            属性名称集合
        """
        attributes = set()
        
        # 使用正则表达式提取属性名
        # 匹配 key "value" 或 key value 格式
        pattern = r'(\w+)\s+"[^"]*"|([\w]+)\s+[^;]+'
        matches = re.findall(pattern, attribute_string)
        
        for match in matches:
            # match是元组，取非空的组
            attr_name = match[0] or match[1]
            if attr_name:
                attributes.add(attr_name)
        
        return attributes

# 注册提取器
register_extractor("GTF", GtfExtractor())