from .core.base_extractor import BaseExtractor
from .core.extractor_factory import register_extractor
from typing import Dict, Any, List
import re

def _parse_sam_header_lines(lines: List[str]) -> Dict[str, Any]:
    hd, sq, rg, pg = {}, [], [], []
    for ln in lines:
        if not ln.startswith("@"):
            break
        tag = ln[1:3]
        fields = dict(kv.split(":", 1) for kv in ln.strip().split("\t")[1:] if ":" in kv)
        if tag == "HD":
            hd = fields
        elif tag == "SQ":
            sq.append({"SN": fields.get("SN"), "LN": int(fields.get("LN", "0") or 0)})
        elif tag == "RG":
            rg.append(fields)
        elif tag == "PG":
            pg.append(fields)
    return {"HD": hd, "SQ": sq, "RG": rg, "PG": pg}

class SamExtractor(BaseExtractor):
    def __init__(self):
        template_path = "sam.json"
        super().__init__(template_path)
    
    def extract(self, path: str, sniff: Dict[str, Any]) -> Dict[str, Any]:
        """提取 SAM 文件的所有信息"""
        # 初始化所有统计变量
        header = None
        num_alignments = 0
        mapped_reads = 0
        unmapped_reads = 0
        mapping_qualities = []
        insert_sizes = []
        flag_stats = {}
        
        with open(path, "rt", encoding="utf-8", errors="replace") as fh:
            # 首先读取头部信息
            head = []
            for _ in range(1000):
                ln = fh.readline()
                if not ln:
                    break
                head.append(ln)
                if not ln.startswith("@"):
                    # 将最后一行（非头部行）放回处理
                    fh.seek(fh.tell() - len(ln.encode('utf-8')))
                    break
            
            header = _parse_sam_header_lines(head)
            
            # 然后处理比对记录
            for line in fh:
                if line.startswith("@"):
                    continue  # 跳过任何剩余的头部行
                
                fields = line.strip().split("\t")
                if len(fields) >= 11:  # 标准SAM记录至少11列
                    num_alignments += 1
                    flag = int(fields[1]) if fields[1].isdigit() else 0
                    
                    # 检查是否为未比对读段 (flag & 4)
                    if flag & 4:
                        unmapped_reads += 1
                    else:
                        mapped_reads += 1
                    
                    # 比对质量 (MAPQ)
                    mapq = int(fields[4]) if fields[4].isdigit() else 0
                    mapping_qualities.append(mapq)
                    
                    # 插入片段大小 (TLEN)
                    tlen = int(fields[8]) if fields[8].lstrip('-').isdigit() else 0
                    if tlen != 0:
                        insert_sizes.append(abs(tlen))
                    
                    # FLAG统计
                    flag_stats[flag] = flag_stats.get(flag, 0) + 1
        
        # 计算分布
        mapq_distribution = {}
        for mapq in mapping_qualities:
            mapq_range = f"{(mapq//10)*10}-{(mapq//10)*10+9}"
            mapq_distribution[mapq_range] = mapq_distribution.get(mapq_range, 0) + 1
        
        insert_size_distribution = {}
        for size in insert_sizes:
            size_range = f"{(size//100)*100}-{(size//100)*100+99}"
            insert_size_distribution[size_range] = insert_size_distribution.get(size_range, 0) + 1
        
        # 直接设置各个字段
        self.sidecars = sniff.get("sidecars", []) if sniff else []
        self.HD = header.get("HD", {})
        self.SQ = header.get("SQ", [])
        self.RG = header.get("RG", [])
        self.PG = header.get("PG", [])
        self.numSQ = len(header.get("SQ", []))
        self.SO = header.get("HD", {}).get("SO")
        self.numAlignments = num_alignments
        self.mappedReads = mapped_reads
        self.unmappedReads = unmapped_reads
        self.isCompressed = path.endswith(".gz")
        self.mappingQualityDistribution = mapq_distribution
        self.insertSizeDistribution = insert_size_distribution
        self.flagStatistics = flag_stats
        
        return self._build_result()


# 注册提取器
register_extractor("SAM", SamExtractor())