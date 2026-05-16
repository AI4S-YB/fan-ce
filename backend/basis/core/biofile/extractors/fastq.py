# app/extractors/fastq.py
from .core.base_extractor import BaseExtractor
from .core.extractor_factory import register_extractor
import gzip
import os
import json
import statistics
import random
import re
from typing import Dict, Any, List, Tuple, Optional
from collections import Counter, defaultdict
from pathlib import Path

def _open_maybe_gz(path: str):
    return gzip.open(path, "rt") if path.endswith(".gz") else open(path, "rt", encoding="utf-8", errors="replace")

def _detect_sequence_type(sequences: list) -> str:
    """
    检测序列类型：核酸(DNA/RNA)或蛋白质
    
    Args:
        sequences: 序列列表
    
    Returns:
        "nucleic" 表示核酸，"protein" 表示蛋白质
    """
    if not sequences:
        return "unknown"
    
    # 核酸字符集 (DNA: ATCG, RNA: AUCG, 还包括一些模糊字符)
    nucleic_chars = set("ATCGURYSWKMBDHVN")
    # 蛋白质字符集 (20种标准氨基酸)
    protein_chars = set("ACDEFGHIKLMNPQRSTVWY")
    
    total_chars = 0
    nucleic_count = 0
    protein_count = 0
    
    # 取前几条序列进行检测，避免全文件扫描
    sample_sequences = sequences[:min(10, len(sequences))]
    
    for seq in sample_sequences:
        seq_upper = seq.upper().replace("-", "").replace(".", "")  # 移除gap字符
        if not seq_upper:
            continue
            
        for char in seq_upper:
            if char.isalpha():
                total_chars += 1
                if char in nucleic_chars:
                    nucleic_count += 1
                if char in protein_chars:
                    protein_count += 1
    
    if total_chars == 0:
        return "unknown"
    
    # 如果90%以上的字符都是核酸字符，且核酸字符比例明显高于蛋白质特有字符
    nucleic_ratio = nucleic_count / total_chars
    protein_specific_chars = total_chars - nucleic_count  # 非核酸字符
    
    if nucleic_ratio >= 0.9 and protein_specific_chars / total_chars < 0.2:
        return "nucleic"
    else:
        return "protein"

class FastqExtractor(BaseExtractor):
    def __init__(self):
        template_path = "fastq.json"
        super().__init__(template_path)
        
        # 初始化 adapter 配置和平台检测模式
        self.adapter_config_path = "adapters.json"
        self.known_adapters, self.sequencing_types = self._load_adapter_config()
        
        # 预编译正则表达式模式以提高性能
        self.platform_patterns = {
            'Illumina': [re.compile(pattern) for pattern in [r'@.*:.*:.*:.*:', r'@.*HWI-', r'@.*M[0-9]+:', r'@.*NS[0-9]+:', r'@.*NB[0-9]+:']],
            'PacBio': [re.compile(pattern) for pattern in [r'@.*m[0-9]+_[0-9]+_[0-9]+', r'@.*movie']],
            'Oxford Nanopore': [re.compile(pattern) for pattern in [r'@.*read_[0-9]+', r'@.*ch[0-9]+_read[0-9]+']],
            'Ion Torrent': [re.compile(pattern) for pattern in [r'@.*IonXpress', r'@.*R_[0-9]+']],
            'MGI': [re.compile(pattern) for pattern in [r'@.*V[0-9]+L[0-9]+C[0-9]+R[0-9]+', r'@.*CL[0-9]+L[0-9]+R[0-9]+']],
            'BGI': [re.compile(pattern) for pattern in [r'@.*CL[0-9]+L[0-9]+R[0-9]+', r'@.*V[0-9]+L[0-9]+C[0-9]+R[0-9]+']]
        }
        
        # 更精确的平台识别模式
        self.advanced_patterns = {
            'Illumina': {
                'header_patterns': ['@M', '@HWI', '@NB', '@NS', '@A0', '@D0', '@EAS', '@FC', '@SN'],
                'format_check': lambda h: h.startswith('@') and ':' in h and len(h.split(':')) >= 7
            },
            'PacBio': {
                'header_patterns': ['@m'],
                'format_check': lambda h: (h.startswith('@m') and ('/' in h) and 
                                          (h.endswith('/ccs') or '/subreads' in h or 
                                           any(x in h.lower() for x in ['pacbio', 'sequel'])))
            },
            'Nanopore': {
                'header_patterns': ['@read', '@channel'],
                'format_check': lambda h: h.startswith('@') and ('read_' in h or 'channel_' in h)
            },
            'Ion Torrent': {
                'header_patterns': ['@IonXpress', '@IONTORRENT'],
                'format_check': lambda h: 'ion' in h.lower() or 'torrent' in h.lower()
            }
        }
        
        # 添加缓存机制
        self._adapter_cache = {}
        self._platform_cache = {}
    
    def _load_adapter_config(self) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
        """从配置文件加载adapter序列信息"""
        config_path = Path(self.adapter_config_path)
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return config.get('adapters', {}), config.get('sequencing_types', {})
        except FileNotFoundError:
            print(f"警告: 配置文件 {config_path} 未找到，使用默认adapter配置")
            return self._get_default_adapters()
        except json.JSONDecodeError as e:
            print(f"警告: 配置文件 {config_path} 格式错误: {e}，使用默认adapter配置")
            return self._get_default_adapters()
    
    def _get_default_adapters(self) -> Tuple[Dict[str, str], Dict[str, List[str]]]:
        """返回默认的adapter配置"""
        default_adapters = {
            "AATGATACGGCGACCACCGAGATCTACACTCTTTCCCTACACGACGCTCTTCCGATCT": "Illumina_TruSeq_Universal_Adapter",
            "GATCGGAAGAGCACACGTCTGAACTCCAGTCAC": "Illumina_TruSeq_Adapter_Read2",
            "AGATCGGAAGAGCGTCGTGTAGGGAAAGAGTGTAGATCTCGGTGGTCGCCGTATCATT": "Illumina_TruSeq_Adapter_Read1"
        }
        default_types = {
            "Illumina_TruSeq": ["TruSeq", "Illumina_TruSeq"]
        }
        return default_adapters, default_types
    
    def detect_adapters_in_sequence(self, sequence: str) -> List[Tuple[str, str]]:
        """在序列中检测adapter - 优化版本，减少冗余匹配"""
        # 使用序列的哈希值作为缓存键（只取前100和后100字符）
        seq_len = len(sequence)
        cache_key = hash(sequence[:min(100, seq_len)] + sequence[max(0, seq_len-100):])
        
        if cache_key in self._adapter_cache:
            return self._adapter_cache[cache_key]
        
        detected = []
        seq_upper = sequence.upper()
        matched_adapters = set()  # 用于去重相似adapter
        
        # 按adapter长度排序，优先检测长adapter
        sorted_adapters = sorted(self.known_adapters.items(), key=lambda x: len(x[0]), reverse=True)
        
        for adapter_seq, adapter_name in sorted_adapters:
            adapter_len = len(adapter_seq)
            
            # 跳过已经匹配过的相似adapter
            adapter_key = adapter_seq[:min(20, adapter_len)]  # 使用前20bp作为唯一标识
            if adapter_key in matched_adapters:
                continue
            
            # 检测完整匹配 - 使用find方法更高效
            if adapter_seq in seq_upper:
                detected.append((adapter_name, "full_match"))
                matched_adapters.add(adapter_key)
                continue  # 找到完整匹配就跳过部分匹配检测
            
            # 检测部分匹配（至少20bp，提高准确性）
            if adapter_len >= 20:
                # 只检查序列的前后部分，减少搜索范围
                search_regions = [
                    seq_upper[:min(50, seq_len)],  # 序列开头50bp
                    seq_upper[max(0, seq_len-50):]  # 序列结尾50bp
                ]
                
                found = False
                for region in search_regions:
                    if len(region) < 20:
                        continue
                    # 检查adapter的前20bp和后20bp
                    for substr_len in [20, min(25, adapter_len)]:
                        if substr_len > adapter_len:
                            continue
                        # 检查adapter开头
                        if adapter_seq[:substr_len] in region:
                            detected.append((adapter_name, "partial_match"))
                            matched_adapters.add(adapter_key)
                            found = True
                            break
                        # 检查adapter结尾
                        if adapter_seq[-substr_len:] in region:
                            detected.append((adapter_name, "partial_match"))
                            matched_adapters.add(adapter_key)
                            found = True
                            break
                    if found:
                        break
        
        # 进一步去重：如果检测到多个相似的adapter，只保留最具代表性的
        if len(detected) > 5:  # 如果检测到太多adapter，进行筛选
            # 优先保留完整匹配
            full_matches = [d for d in detected if d[1] == "full_match"]
            partial_matches = [d for d in detected if d[1] == "partial_match"]
            
            # 对部分匹配进行去重，优先保留TruSeq和Nextera
            filtered_partial = []
            seen_types = set()
            for adapter_name, match_type in partial_matches:
                adapter_type = self._get_adapter_type(adapter_name)
                if adapter_type not in seen_types:
                    filtered_partial.append((adapter_name, match_type))
                    seen_types.add(adapter_type)
                if len(filtered_partial) >= 3:  # 最多保留3个不同类型的部分匹配
                    break
            
            detected = full_matches + filtered_partial
        
        # 缓存结果（限制缓存大小）
        if len(self._adapter_cache) < 1000:
            self._adapter_cache[cache_key] = detected
        
        return detected
    
    def _get_adapter_type(self, adapter_name: str) -> str:
        """获取adapter的类型分类"""
        adapter_name_upper = adapter_name.upper()
        if "TRUSEQ" in adapter_name_upper:
            return "TruSeq"
        elif "NEXTERA" in adapter_name_upper:
            return "Nextera"
        elif "RNA" in adapter_name_upper:
            return "RNA"
        elif "SMALL" in adapter_name_upper:
            return "SmallRNA"
        elif "MGI" in adapter_name_upper:
            return "MGI"
        elif "ILLUMINA" in adapter_name_upper:
            return "Illumina"
        else:
            return "Other"
    
    def detect_sequencing_type_by_adapters(self, adapters: List[Tuple[str, str]], file_path: str = "") -> Tuple[str, str]:
        """基于adapter推断测序平台和测序类型，返回唯一确定的结果"""
        platform = "Unknown"
        seq_type = "Unknown"
        
        # 收集检测到的adapter信息
        adapter_names = [adapter[0] for adapter in adapters if adapter[0] != 'unknown']
        
        if not adapter_names:
            return platform, seq_type
        
        # 定义测序类型检测规则，按优先级排序
        sequencing_rules = [
            # 高特异性规则（优先级最高）
            {
                'patterns': ['small', 'rna'],
                'all_required': True,
                'platform': 'Illumina',
                'seq_type': 'Small RNA-seq',
                'priority': 1
            },
            {
                'patterns': ['nextera'],
                'all_required': False,
                'platform': 'Illumina', 
                'seq_type': 'Nextera',
                'priority': 2
            },
            {
                'patterns': ['truseq', 'rna'],
                'all_required': True,
                'platform': 'Illumina',
                'seq_type': 'RNA-seq',
                'priority': 3
            },
            {
                'patterns': ['chip'],
                'all_required': False,
                'platform': 'Illumina',
                'seq_type': 'ChIP-seq',
                'priority': 4
            },
            {
                'patterns': ['atac'],
                'all_required': False,
                'platform': 'Illumina',
                'seq_type': 'ATAC-seq',
                'priority': 5
            },
            # 中等特异性规则
            {
                'patterns': ['truseq'],
                'all_required': False,
                'platform': 'Illumina',
                'seq_type': 'WGS/WES',
                'priority': 6
            },
            {
                'patterns': ['mgi', 'bgi'],
                'all_required': False,
                'platform': 'MGI/BGI',
                'seq_type': 'WGS/WES',
                'priority': 7
            },
            # 低特异性规则（通用规则）
            {
                'patterns': ['illumina'],
                'all_required': False,
                'platform': 'Illumina',
                'seq_type': 'WGS/WES',
                'priority': 8
            }
        ]
        
        # 将adapter名称转换为小写用于匹配
        adapter_text = ' '.join(adapter_names).lower()
        
        # 按优先级检测测序类型
        best_match = None
        best_priority = float('inf')
        
        for rule in sequencing_rules:
            patterns = rule['patterns']
            all_required = rule['all_required']
            
            if all_required:
                # 所有模式都必须匹配
                if all(pattern in adapter_text for pattern in patterns):
                    if rule['priority'] < best_priority:
                        best_match = rule
                        best_priority = rule['priority']
            else:
                # 任一模式匹配即可
                if any(pattern in adapter_text for pattern in patterns):
                    if rule['priority'] < best_priority:
                        best_match = rule
                        best_priority = rule['priority']
        
        # 应用最佳匹配规则
        if best_match:
            platform = best_match['platform']
            seq_type = best_match['seq_type']
        
        # 基于文件名的补充检测（仅在adapter检测失败时使用）
        if seq_type == "Unknown" and file_path:
            filename_lower = file_path.lower()
            
            # 文件名中的类型指示
            if 'rna' in filename_lower and 'seq' in filename_lower:
                seq_type = "RNA-seq"
                platform = "Illumina" if platform == "Unknown" else platform
            elif 'chip' in filename_lower and 'seq' in filename_lower:
                seq_type = "ChIP-seq"
                platform = "Illumina" if platform == "Unknown" else platform
            elif 'atac' in filename_lower and 'seq' in filename_lower:
                seq_type = "ATAC-seq"
                platform = "Illumina" if platform == "Unknown" else platform
            elif 'wgs' in filename_lower:
                seq_type = "WGS"
                platform = "Illumina" if platform == "Unknown" else platform
            elif 'wes' in filename_lower or 'exome' in filename_lower:
                seq_type = "WES"
                platform = "Illumina" if platform == "Unknown" else platform
            elif 'mirna' in filename_lower or 'small' in filename_lower:
                seq_type = "Small RNA-seq"
                platform = "Illumina" if platform == "Unknown" else platform
        
        # 最终检查：如果仍然无法确定，基于adapter数量推断
        if seq_type == "Unknown" and adapter_names:
            if platform == "Unknown":
                platform = "Illumina"  # 默认平台
            
            # 基于adapter数量的简单推断
            if len(adapter_names) >= 2:
                seq_type = "WGS/WES"  # 多个adapter通常表示标准测序
            else:
                seq_type = "Unknown"  # 单个adapter无法确定类型
                    
        return platform, seq_type
    
    def detect_platform(self, header: str, sequence: str = "") -> str:
        """检测测序平台（基于序列标识符的精确识别）- 优化版本"""
        # 使用缓存避免重复计算
        cache_key = header[:50]  # 使用header前50个字符作为缓存键
        if cache_key in self._platform_cache:
            return self._platform_cache[cache_key]
        
        header_upper = header.upper()
        
        # 使用高级模式进行精确识别
        for platform, config in self.advanced_patterns.items():
            # 首先检查header模式
            pattern_match = False
            for pattern in config['header_patterns']:
                if pattern.upper() in header_upper:
                    pattern_match = True
                    break
            
            # 如果模式匹配，进一步检查格式
            if pattern_match and config['format_check'](header):
                self._platform_cache[cache_key] = platform
                return platform
        
        # 如果高级模式未匹配，使用基础模式检测（使用预编译的正则表达式）
        header_platform = None
        for platform, compiled_patterns in self.platform_patterns.items():
            for pattern in compiled_patterns:
                if pattern.search(header):
                    header_platform = platform
                    break
            if header_platform:
                break
        
        # 基于adapter序列进一步确认平台
        adapter_platform = None
        if sequence:
            detected_adapters = self.detect_adapters_in_sequence(sequence)
            if detected_adapters:
                # 根据检测到的adapter推断平台
                for adapter_name, _ in detected_adapters:
                    if "Illumina" in adapter_name or "TruSeq" in adapter_name:
                        adapter_platform = "Illumina"
                        break
                    elif "Nextera" in adapter_name:
                        adapter_platform = "Illumina"  # Nextera也是Illumina技术
                        break
                    elif "MGI" in adapter_name or "BGI" in adapter_name:
                        adapter_platform = "MGI/BGI"
                        break
                    elif "Solid" in adapter_name:
                        adapter_platform = "ABI SOLiD"
                        break
        
        # 综合判断
        result = None
        if header_platform and adapter_platform:
            if header_platform == adapter_platform:
                result = header_platform
            else:
                result = f"{header_platform} (adapter suggests {adapter_platform})"
        elif header_platform:
            result = header_platform
        elif adapter_platform:
            result = adapter_platform
        else:
            # 最后的格式判断
            if header.startswith('@') and ':' in header:
                parts = header.split(':')
                if len(parts) >= 7:  # Illumina典型格式
                    result = 'Illumina'
                else:
                    result = 'Unknown'
            else:
                result = 'Unknown'
        
        # 缓存结果
        self._platform_cache[cache_key] = result
        return result
    
    def analyze_quality_scores_enhanced(self, quality_strings: List[str]) -> Dict:
        """分析测序质量分数 - 增强版本"""
        if not quality_strings:
            return {
                'q20_percentage': 0.0,
                'q30_percentage': 0.0,
                'mean_quality': 0.0,
                'median_quality': 0.0,
                'total_bases': 0
            }
        
        # 使用更高效的计算方法，避免存储所有质量分数
        q20_count = 0
        q30_count = 0
        total_bases = 0
        quality_sum = 0
        quality_scores = []
        
        # 只对部分质量字符串进行详细分析，减少计算量
        sample_strings = quality_strings[:1000] if len(quality_strings) > 1000 else quality_strings
        
        for qual_str in sample_strings:
            for char in qual_str:
                # 转换ASCII字符为质量分数（Phred+33编码）
                quality = ord(char) - 33
                quality_sum += quality
                quality_scores.append(quality)
                total_bases += 1
                
                if quality >= 20:
                    q20_count += 1
                if quality >= 30:
                    q30_count += 1
        
        # 计算统计值
        q20_percentage = (q20_count / total_bases * 100) if total_bases > 0 else 0.0
        q30_percentage = (q30_count / total_bases * 100) if total_bases > 0 else 0.0
        mean_quality = quality_sum / total_bases if total_bases > 0 else 0.0
        
        # 计算中位数
        median_quality = statistics.median(quality_scores) if quality_scores else 0.0
        
        return {
            'q20_percentage': round(q20_percentage, 2),
            'q30_percentage': round(q30_percentage, 2),
            'mean_quality': round(mean_quality, 2),
            'median_quality': round(median_quality, 2),
            'total_bases': total_bases
        }
    
    def analyze_adapters(self, sequences: List[str]) -> Dict:
        """分析adapter统计信息 - 随机抽取1000条reads进行检测"""
        adapter_stats = defaultdict(int)
        total_with_adapters = 0
        has_adapters = False
        
        # 随机抽取1000条reads进行检测
        sample_size = min(1000, len(sequences))
        if len(sequences) > sample_size:
            sampled_sequences = random.sample(sequences, sample_size)
        else:
            sampled_sequences = sequences
        
        for seq in sampled_sequences:
            detected = self.detect_adapters_in_sequence(seq)
            if detected:
                total_with_adapters += 1
                has_adapters = True
                for adapter_name, match_type in detected:
                    adapter_stats[f"{adapter_name}_{match_type}"] += 1
        
        # 如果没有检测到任何adapter，返回unknown
        if not has_adapters:
            adapter_stats['unknown'] = sample_size
        
        return {
            'detected_adapters': dict(adapter_stats),
            'contamination_rate': round(total_with_adapters / sample_size * 100, 2) if sample_size > 0 else 0.0,
            'total_analyzed': sample_size
        }
    
    def extract(self, path: str, sniff: Dict[str, Any]) -> Dict[str, Any]:
        """提取 FASTQ 文件的所有信息 - 增强版本，集成高级功能"""
        # sidecars需要从sniff中获取，其他字段已通过JSON模板自动初始化
        self.sidecars = sniff.get("sidecars", []) if sniff else []
        self.isCompressed = path.endswith(".gz")
        self.totalReads = 0
        self.totalBases = 0
        
        # 初始化统计变量
        quality_encoding = "Phred+33"  # 默认编码
        total_quality = 0
        quality_count = 0
        read_lengths = []
        quality_scores = []
        sequences_sample = []
        all_sequences = []  # 用于重复检测
        per_base_qualities = []  # 每个位置的质量值
        
        # 新增：平台和测序类型检测
        detected_platforms = set()
        all_adapters = []
        headers_sample = []
        
        with _open_maybe_gz(path) as fh:
            fh_lines = list(fh)
            
            # 从前几行获取头部信息
            if len(fh_lines) >= 4:
                self.firstReadId = fh_lines[0].strip()[1:] if fh_lines[0].startswith('@') else None
                
                # 质量编码检测
                quality_line = fh_lines[3].strip()
                if quality_line and min(ord(c) for c in quality_line) < 64:
                    quality_encoding = "Phred+33"
                    quality_offset = 33
                else:
                    quality_encoding = "Phred+64"
                    quality_offset = 64
            else:
                quality_offset = 33
            
            # 一次遍历完成所有统计
            i = -1
            max_read_length = 0
            
            for ln in fh_lines:
                i = (i + 1) % 4
                if i == 0:  # @header
                    self.totalReads += 1
                    header = ln.strip()
                    
                    # 新增：收集header样本用于平台检测
                    if len(headers_sample) < 100:
                        headers_sample.append(header)
                        
                elif i == 1:  # sequence
                    s = ln.strip().upper()
                    seq_len = len(s)
                    
                    # 收集样本序列用于类型检测
                    if len(sequences_sample) < 10:
                        sequences_sample.append(s)
                    
                    # 收集序列用于重复检测（限制数量避免内存问题）
                    if len(all_sequences) < 10000:
                        all_sequences.append(s)
                    
                    # 新增：检测adapter（只对前1000条reads进行检测以提高性能）
                    if self.totalReads <= 1000:
                        detected_adapters = self.detect_adapters_in_sequence(s)
                        all_adapters.extend(detected_adapters)
                    
                    # 统计总碱基数和长度
                    self.totalBases += seq_len
                    read_lengths.append(seq_len)
                    max_read_length = max(max_read_length, seq_len)
                    
                elif i == 3:  # quality
                    quality_line = ln.strip()
                    read_qualities = []
                    
                    # 计算平均质量值和收集质量分数
                    for pos, q_char in enumerate(quality_line):
                        q_score = ord(q_char) - quality_offset
                        total_quality += q_score
                        quality_count += 1
                        quality_scores.append(q_score)
                        read_qualities.append(q_score)
                        
                        # 收集每个位置的质量值（限制长度避免内存问题）
                        if pos < 200:  # 只统计前200个位置
                            while len(per_base_qualities) <= pos:
                                per_base_qualities.append([])
                            per_base_qualities[pos].append(q_score)
            
            # 新增：检测测序平台
            for header in headers_sample:
                platform = self.detect_platform(header)
                if platform != "Unknown":
                    detected_platforms.add(platform)
            
            # 检测序列类型
            self.sequenceType = _detect_sequence_type(sequences_sample)
            
            # 只有核酸序列才统计GC含量
            if self.sequenceType == "nucleic":
                gc_count = 0
                i = -1
                for ln in fh_lines:
                    i = (i + 1) % 4
                    if i == 1:  # sequence
                        s = ln.strip().upper()
                        gc_count += s.count("G") + s.count("C")
                self.gc = round(gc_count / max(1, self.totalBases), 4)
            else:
                self.gc = None
            
            # 质量值统计
            if quality_scores:
                self.avgQuality = round(total_quality / quality_count, 2)
                self.minQuality = min(quality_scores)
                self.maxQuality = max(quality_scores)
                self.medianQuality = round(statistics.median(quality_scores), 2)
                
                # 计算低质量碱基比例
                below_q20 = sum(1 for q in quality_scores if q < 20)
                below_q30 = sum(1 for q in quality_scores if q < 30)
                self.percentBelowQ20 = round(below_q20 / quality_count * 100, 2)
                self.percentBelowQ30 = round(below_q30 / quality_count * 100, 2)
            else:
                self.avgQuality = self.minQuality = self.maxQuality = self.medianQuality = None
                self.percentBelowQ20 = self.percentBelowQ30 = None
            
            # 计算长度统计
            if read_lengths:
                self.avgReadLength = round(sum(read_lengths) / len(read_lengths), 2)
                self.minReadLength = min(read_lengths)
                self.maxReadLength = max(read_lengths)
                
                # 读长分布统计
                self.readLengthDistribution = {}
                for length in read_lengths:
                    if length < 50:
                        bucket = "0-50"
                    elif length < 100:
                        bucket = "50-100"
                    elif length < 150:
                        bucket = "100-150"
                    elif length < 300:
                        bucket = "150-300"
                    else:
                        bucket = "300+"
                    self.readLengthDistribution[bucket] = self.readLengthDistribution.get(bucket, 0) + 1
            else:
                self.avgReadLength = self.minReadLength = self.maxReadLength = 0
                self.readLengthDistribution = {}
            
            # 质量分数分布
            self.qualityDistribution = {}
            if quality_scores:
                for q in quality_scores:
                    if q < 10:
                        bucket = "0-10"
                    elif q < 20:
                        bucket = "10-20"
                    elif q < 30:
                        bucket = "20-30"
                    elif q < 40:
                        bucket = "30-40"
                    else:
                        bucket = "40+"
                    self.qualityDistribution[bucket] = self.qualityDistribution.get(bucket, 0) + 1
            
            # 每个位置的质量值统计
            self.perBaseQuality = []
            for pos_qualities in per_base_qualities:
                if pos_qualities:
                    avg_qual = round(sum(pos_qualities) / len(pos_qualities), 2)
                    self.perBaseQuality.append(avg_qual)
            
            # 重复读段检测
            if all_sequences:
                sequence_counts = Counter(all_sequences)
                unique_sequences = len(sequence_counts)
                total_sequences = len(all_sequences)
                duplicate_sequences = sum(count - 1 for count in sequence_counts.values() if count > 1)
                
                self.uniqueReadCount = unique_sequences
                self.duplicateReadCount = duplicate_sequences
                self.duplicateReadFraction = round(duplicate_sequences / total_sequences, 4) if total_sequences > 0 else 0
            else:
                self.uniqueReadCount = None
                self.duplicateReadCount = None
                self.duplicateReadFraction = None
            
            # 设置质量编码
            self.qualityEncoding = quality_encoding
            
            # 新增：分析adapter信息
            adapter_analysis = self.analyze_adapters(sequences_sample)
            
            # 新增：基于adapter推断平台和测序类型
            inferred_platform, inferred_seq_type = self.detect_sequencing_type_by_adapters(all_adapters, path)
            
            # 综合平台信息
            final_platform = "Unknown"
            if detected_platforms:
                # 如果检测到多个平台，选择最常见的
                platform_list = list(detected_platforms)
                final_platform = platform_list[0] if len(platform_list) == 1 else ", ".join(platform_list)
            
            # 如果基于header的检测失败，使用adapter推断的结果
            if final_platform == "Unknown" and inferred_platform != "Unknown":
                final_platform = inferred_platform
            
            # 新增：设置平台和测序类型信息
            self.platform = final_platform
            self.sequencingType = inferred_seq_type
            self.adapterAnalysis = adapter_analysis
            
            # 组织读长统计信息
            if read_lengths:
                self.readLengths = {
                    "avgReadLength": self.avgReadLength,
                    "minReadLength": self.minReadLength,
                    "maxReadLength": self.maxReadLength,
                    "readLengthDistribution": self.readLengthDistribution
                }
            
            # 组织GC含量分析信息
            if self.gc is not None:
                self.gcContent = {
                    "gcPercentage": self.gc * 100,  # 转换为百分比
                    "totalBases": self.totalBases,
                    "gcCount": int(self.gc * self.totalBases),
                    "atCount": self.totalBases - int(self.gc * self.totalBases)
                }
            
            # 组织质量分析信息
            if quality_scores:
                self.qualityAnalysis = {
                    "avgQuality": self.avgQuality,
                    "minQuality": self.minQuality,
                    "maxQuality": self.maxQuality,
                    "medianQuality": self.medianQuality,
                    "percentBelowQ20": self.percentBelowQ20,
                    "percentBelowQ30": self.percentBelowQ30
                }
            
            # 组织文件信息
            file_size_mb = round(self._get_file_size(path) / (1024 * 1024), 2)
            self.fileInfo = {
                "fileSizeMB": file_size_mb,
                "qualityEncoding": self.qualityEncoding,
                "sequenceType": self.sequenceType
            }
            
            # 添加重复读段信息到质量分析中（如果存在）
            if hasattr(self, 'uniqueReadCount') and self.uniqueReadCount is not None:
                if not hasattr(self, 'qualityAnalysis') or not self.qualityAnalysis:
                    self.qualityAnalysis = {}
                self.qualityAnalysis.update({
                    "uniqueReadCount": self.uniqueReadCount,
                    "duplicateReadCount": self.duplicateReadCount,
                    "duplicateReadFraction": self.duplicateReadFraction
                })
            
            return self._build_result()


# 注册提取器
register_extractor("FASTQ", FastqExtractor())