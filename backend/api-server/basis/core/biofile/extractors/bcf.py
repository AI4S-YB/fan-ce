# app/extractors/bcf.py
from .core.base_extractor import BaseExtractor
from .core.extractor_factory import register_extractor
from typing import Dict, Any, List

try:
    import pysam
    PYSAM_AVAILABLE = True
except ImportError:
    PYSAM_AVAILABLE = False

def _variant_type(ref: str, alts: List[str]) -> str:
    """
    根据 ref/alt 判断变异类型：
    - snv: 单核苷酸多态
    - indel: 插入/删除
    - multiallelic: 多等位
    - other: 其他
    """
    if not alts:
        return "other"
    if len(alts) > 1:
        return "multiallelic"
    alt = alts[0]
    if len(ref) == 1 and len(alt) == 1:
        return "snv"
    if len(ref) != len(alt):
        return "indel"
    return "other"

def _get_generic(hdr, key: str):
    # 遍历 VariantHeaderRecord，取通用键（如 fileDate、source）
    for r in hdr.records:
        # pysam 的 VariantHeaderRecord 提供 .type / .key / .value 等属性
        # （可在文档索引中找到这些属性的条目）
        if getattr(r, "type", None) == "GENERIC" and getattr(r, "key", None) == key:
            return getattr(r, "value", None)
    return None

class BcfExtractor(BaseExtractor):
    def __init__(self):
        template_path = "bcf.json"
        super().__init__(template_path)
        if not PYSAM_AVAILABLE:
            raise ImportError("pysam is required for BCF extraction")
    
    def extract(self, path: str, sniff: Dict[str, Any]) -> Dict[str, Any]:
        """提取BCF文件的所有固定字段"""
        vf = pysam.VariantFile(path)
        hdr = vf.header
        
        # sidecars需要从sniff中获取，其他字段已通过JSON模板自动初始化
        self.sidecars = sniff.get("sidecars", []) if sniff else []
        
        # 提取头部信息
        # contigs
        for name in list(hdr.contigs):
            rec = hdr.contigs[name]
            length = getattr(rec, "length", None)
            self.contigs.append({"id": name, "length": int(length) if length is not None else None})
        
        # filters
        for name in list(hdr.filters):
            rec = hdr.filters[name]
            self.filters[name] = {
                "Description": getattr(rec, "description", None)
            }
        
        # info
        for name in list(hdr.info):
            rec = hdr.info[name]
            self.info[name] = {
                "Number": getattr(rec, "number", None),
                "Type": getattr(rec, "type", None),
                "Description": getattr(rec, "description", None)
            }
        
        # formats
        for name in list(hdr.formats):
            rec = hdr.formats[name]
            self.format[name] = {
                "Number": getattr(rec, "number", None),
                "Type": getattr(rec, "type", None),
                "Description": getattr(rec, "description", None)
            }
        
        # samples
        self.samples = list(hdr.samples)
        
        # 提取摘要信息
        # fileformat版本
        ver = getattr(hdr, "version", None)
        if isinstance(ver, tuple) and len(ver) == 2:
            self.fileformat = f"VCFv{ver[0]}.{ver[1]}"
        else:
            self.fileformat = str(ver) if ver is not None else None
        
        # 通用键
        self.fileDate = _get_generic(hdr, "fileDate")
        self.source = _get_generic(hdr, "source")
        
        # 基础统计
        self.numContigs = len(self.contigs)
        self.numSamples = len(self.samples)
        
        # 变异统计和内容统计（一次遍历完成）
        missing_gt_total = 0
        variant_density = {}
        
        for rec in vf.fetch():
            self.numRecords += 1
            
            # 变异类型统计
            vt = _variant_type(rec.ref or "", list(rec.alts or []))
            self.variantTypes[vt] += 1
            
            # 缺失基因型统计
            for s in self.samples:
                gt = rec.samples[s].get("GT")
                if gt is None or any(g is None for g in gt):
                    missing_gt_total += 1
            
            # 变异密度统计
            contig = rec.contig
            if contig not in variant_density:
                variant_density[contig] = 0
            variant_density[contig] += 1
        
        # 设置最终统计结果
        self.missingGenotypeTotal = missing_gt_total
        self.variantDensityPerContig = variant_density
        
        vf.close()
        return self._build_result()


# 注册提取器
if PYSAM_AVAILABLE:
    register_extractor("BCF", BcfExtractor())