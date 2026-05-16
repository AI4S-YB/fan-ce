# app/extractors/fasta_new.py
from .core.base_extractor import BaseExtractor
from .core.extractor_factory import register_extractor
from typing import Dict, Any
from collections import Counter
import re

class FastaExtractor(BaseExtractor):
    """
    简化的FASTA文件提取器 - 直接返回所有固定字段
    """
    
    def __init__(self):
        template_path = "fasta.json"
        super().__init__(template_path)
    
    def _detect_sequence_type(self, sequences: list) -> str:
        """
        检测序列类型：核酸(DNA/RNA)或蛋白质
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
    
    def _parse_header_metadata(self, header_line: str) -> Dict[str, Any]:
        """解析FASTA header中的metadata信息"""
        metadata = {}
        
        # 常见的metadata模式
        patterns = {
            'accession': r'\b([A-Z]{1,2}_?\d{6,})\b',  # GenBank accession
            'gi': r'gi\|(\d+)',  # GI number
            'species': r'\[([^\]]+)\]',  # 物种信息通常在方括号中
            'gene': r'gene=([^\s,;]+)',  # 基因名
            'protein': r'protein=([^\s,;]+)',  # 蛋白质名
            'chromosome': r'chromosome[\s=:]([^\s,;]+)',  # 染色体
            'location': r'(\d+\.\.\.?\d+)',  # 位置信息
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, header_line, re.IGNORECASE)
            if match:
                metadata[key] = match.group(1)
        
        return metadata
    

    
    def _validate_fasta_format(self, sequences: list, headers: list) -> bool:
        """验证FASTA格式是否正确"""
        try:
            # 检查是否有序列和header
            if not sequences or not headers:
                return False
            
            # 检查序列数量是否匹配
            if len(sequences) != len(headers):
                return False
            
            # 检查序列字符是否合法
            valid_chars = set('ACGTUNRYSWKMBDHV-.*acgtunryswkmbdhv')
            for seq in sequences[:10]:  # 检查前10条序列
                if not all(c in valid_chars for c in seq):
                    return False
            
            return True
        except Exception:
            return False
    
    def extract(self, path: str, sniff: Dict[str, Any]) -> Dict[str, Any]:
        """提取FASTA文件信息并给对应属性赋值"""
        # 初始化属性
        self.sidecars = sniff.get("sidecars", []) if sniff else []
        self.isCompressed = self._is_compressed(path)
        self.totalBases = 0
        
        # 一次性提取所有数据
        sequence_ids = []
        sequence_lengths = []
        sequences_sample = []
        all_sequences = []  # 用于重复检测
        headers = []
        base_counts = Counter()
        gc_count = 0
        n_count = 0
        
        with self._open_maybe_gz(path) as fh:
            current_seq = ""
            current_seq_len = 0
            current_header = ""
            
            for line in fh:
                if line.startswith(">"):
                    # 处理上一条序列
                    if current_seq_len > 0:
                        sequence_lengths.append(current_seq_len)
                        if len(all_sequences) < 1000:  # 限制内存使用
                            all_sequences.append(current_seq)
                    if current_seq and len(sequences_sample) < 10:
                        sequences_sample.append(current_seq)
                    
                    # 新序列header
                    current_header = line.strip()
                    headers.append(current_header)
                    
                    # 提取序列ID
                    seq_id = line[1:].strip().split()[0]
                    sequence_ids.append(seq_id)
                    
                    # 设置第一个序列信息
                    if self.firstSequenceId is None:
                        self.firstSequenceId = seq_id
                        self.firstHeaderLine = current_header
                        self.parsedMeta = self._parse_header_metadata(current_header)
                    
                    current_seq = ""
                    current_seq_len = 0
                    
                    # 限制序列ID数量，避免内存占用过大
                    if len(sequence_ids) >= 1000:
                        # 继续读取剩余序列内容进行统计
                        for remaining_line in fh:
                            if remaining_line.startswith(">"):
                                if current_seq_len > 0:
                                    sequence_lengths.append(current_seq_len)
                                current_seq_len = 0
                            else:
                                s = remaining_line.strip().upper()
                                current_seq_len += len(s)
                                self.totalBases += len(s)
                                # 统计碱基
                                for char in s:
                                    base_counts[char] += 1
                                    if char in 'GC':
                                        gc_count += 1
                                    elif char in 'NX':
                                        n_count += 1
                        break
                else:
                    s = line.strip().upper()
                    current_seq += s
                    current_seq_len += len(s)
                    self.totalBases += len(s)
                    
                    # 统计碱基组成
                    for char in s:
                        base_counts[char] += 1
                        if char in 'GC':
                            gc_count += 1
                        elif char in 'NX':
                            n_count += 1
            
            # 处理最后一条序列
            if current_seq_len > 0:
                sequence_lengths.append(current_seq_len)
                if len(all_sequences) < 1000:
                    all_sequences.append(current_seq)
            if current_seq and len(sequences_sample) < 10:
                sequences_sample.append(current_seq)
        
        # 计算序列类型
        self.sequenceType = self._detect_sequence_type(sequences_sample)
        
        # 计算GC含量（仅核酸序列）
        if self.sequenceType == "nucleic" and self.totalBases > 0:
            self.gc = round(gc_count / self.totalBases, 4)
        else:
            self.gc = None
        
        # 设置序列相关属性
        self.sequenceIds = sequence_ids[:100]  # 限制返回的ID数量
        self.numSeqs = len(sequence_lengths)
        
        # 计算长度统计
        if sequence_lengths:
            self.avgSequenceLength = round(sum(sequence_lengths) / len(sequence_lengths), 2)
            self.minSequenceLength = min(sequence_lengths)
            self.maxSequenceLength = max(sequence_lengths)
            
            # 长度分布统计
            self.sequenceLengthDistribution = {}
            for length in sequence_lengths:
                if length < 1000:
                    bucket = "0-1000"
                elif length < 5000:
                    bucket = "1000-5000"
                elif length < 10000:
                    bucket = "5000-10000"
                else:
                    bucket = "10000+"
                self.sequenceLengthDistribution[bucket] = self.sequenceLengthDistribution.get(bucket, 0) + 1
        else:
            self.avgSequenceLength = None
            self.minSequenceLength = None
            self.maxSequenceLength = None
            self.sequenceLengthDistribution = {}
        
        # 碱基组成统计
        if self.totalBases > 0:
            self.baseComposition = {}
            for base in ['A', 'C', 'G', 'T', 'U', 'N', '-']:
                count = base_counts.get(base, 0)
                self.baseComposition[base] = {
                    'count': count,
                    'percentage': round(count / self.totalBases * 100, 2)
                }
        else:
            self.baseComposition = {}
        
        # 模糊碱基统计
        self.nCount = n_count
        self.percentAmbiguous = round(n_count / self.totalBases * 100, 2) if self.totalBases > 0 else 0
        
        # 重复序列检测
        if all_sequences:
            sequence_counts = Counter(all_sequences)
            unique_sequences = len(sequence_counts)
            total_sequences = len(all_sequences)
            duplicate_sequences = sum(1 for count in sequence_counts.values() if count > 1)
            
            self.uniqueSeqCount = unique_sequences
            self.duplicateSeqCount = duplicate_sequences
            self.duplicateFraction = round(duplicate_sequences / total_sequences, 4) if total_sequences > 0 else 0
        else:
            self.uniqueSeqCount = None
            self.duplicateSeqCount = None
            self.duplicateFraction = None
        
        # 格式验证
        self.isValidFormat = self._validate_fasta_format(sequences_sample, headers[:10])
        
        return self._build_result()

# 创建提取器实例
# Register the extractor with the factory
register_extractor("FASTA", FastaExtractor())