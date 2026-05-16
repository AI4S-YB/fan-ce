import os
import re
import io
import json
import struct
import gzip
import zipfile
import tarfile
from typing import List, Dict, Any, Tuple, Optional

SAMPLE_BYTES = 64 * 1024
TEXT_MAX_PREVIEW_LINES = 100

def load_rules(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def read_head(path: str, n: int = SAMPLE_BYTES) -> bytes:
    with open(path, "rb") as f:
        return f.read(n)

def is_binary_bytes(b: bytes) -> bool:
    if not b:
        return False
    if b'\x00' in b:
        return True
    sample = b[:4096]
    nontext = sum(
        (ch < 9 or (13 < ch < 32)) for ch in sample
    )
    return (nontext / len(sample)) > 0.3


def bytes2hex(b: bytes, n: int = 16) -> str:
    return b[:n].hex()

def _match_magic(buf: bytes, rule: Dict[str, Any]) -> bool:
    def match_one(m):
        off = m.get("offset", 0)
        if "hex" in m:
            hx = bytes.fromhex(m["hex"])
            return buf[off:off+len(hx)] == hx
        if "ascii" in m:
            s = m["ascii"].encode("latin1").decode("unicode_escape").encode("latin1")
            return buf[off:off+len(s)] == s
        return False

    if "magic" in rule and match_one(rule["magic"]):
        return True
    if "magic_any_of" in rule:
        for m in rule["magic_any_of"]:
            if match_one(m):
                return True
    return False

def detect_hdf5_signature(path: str, head: bytes) -> bool:
    sig = bytes.fromhex("894844460D0A1A0A")
    if head.startswith(sig):
        return True
    with open(path, "rb") as f:
        for off in [512, 1024, 2048, 4096]:
            try:
                f.seek(off)
                if f.read(len(sig)) == sig:
                    return True
            except Exception:
                break
    return False

def parse_gzip_and_bgzf(path: str, head: bytes) -> Tuple[bool, bool, Optional[bytes], Dict[str, Any]]:
    ev = {}
    is_gzip = head[:2] == b"\x1f\x8b"
    if not is_gzip:
        return False, False, None, ev
    try:
        with open(path, "rb") as f:
            hdr = f.read(10)
            if len(hdr) < 10:
                return True, False, None, ev
            id1, id2, cm, flg, mtime, xfl, os_ = struct.unpack("<BBBBIBB", hdr)
            is_bgzf = False
            extra_len = 0
            if flg & 0x04:
                xlen_bytes = f.read(2)
                if len(xlen_bytes) == 2:
                    xlen = struct.unpack("<H", xlen_bytes)[0]
                    extra = f.read(xlen)
                    extra_len = xlen
                    i = 0
                    while i + 4 <= len(extra):
                        si1, si2, slen = struct.unpack("<BBH", extra[i:i+4])
                        i += 4
                        payload = extra[i:i+slen]
                        i += slen
                        if si1 == 66 and si2 == 67 and slen == 2:  # 'BC'
                            is_bgzf = True
                            ev["bgzf_bsize"] = struct.unpack("<H", payload)[0]
                            break
            ev["gzip_flags"] = flg
            ev["gzip_extra_len"] = extra_len
            f.seek(0)
            gz = gzip.GzipFile(fileobj=f)
            sample = gz.read(SAMPLE_BYTES)
            return True, is_bgzf, sample, ev
    except Exception as e:
        ev["error"] = f"gzip_parse_error: {e}"
        return True, False, None, ev

def sample_zip_member(path: str) -> Tuple[Optional[str], Optional[bytes], Dict[str, Any]]:
    ev = {}
    try:
        with zipfile.ZipFile(path, "r") as z:
            infos = [i for i in z.infolist() if not i.is_dir()]
            if not infos:
                return None, None, {"zip": "empty"}
            first = infos[0]
            with z.open(first, "r") as fp:
                data = fp.read(min(SAMPLE_BYTES, first.file_size))
            ev["zip_first_member"] = first.filename
            return first.filename, data, ev
    except Exception as e:
        ev["error"] = f"zip_error: {e}"
        return None, None, ev

def sample_tar_member(path: str) -> Tuple[Optional[str], Optional[bytes], Dict[str, Any]]:
    ev = {}
    try:
        with tarfile.open(path, "r:*") as t:
            for m in t.getmembers():
                if m.isfile():
                    f = t.extractfile(m)
                    if f:
                        data = f.read(min(SAMPLE_BYTES, m.size))
                        ev["tar_first_member"] = m.name
                        return m.name, data, ev
            return None, None, {"tar": "no file member"}
    except Exception as e:
        ev["error"] = f"tar_error: {e}"
        return None, None, ev

def decode_text(b: bytes) -> str:
    return b.decode("utf-8", errors="replace")

def split_lines(s: str, max_lines: int = TEXT_MAX_PREVIEW_LINES) -> List[str]:
    return s.splitlines()[:max_lines]

def count_tab_fields(line: str) -> int:
    return len(line.rstrip("\n\r").split("\t"))

def _record_header_hits(lines: List[str], patterns: List[str], startswith: bool) -> List[Dict[str, Any]]:
    hits = []
    for i, ln in enumerate(lines[:20]):
        for pat in patterns:
            if startswith:
                if re.match(pat, ln):
                    hits.append({"pattern": pat, "line_no": i+1, "line": ln})
            else:
                if re.search(pat, ln):
                    hits.append({"pattern": pat, "line_no": i+1, "line": ln})
    return hits

def score_text_table(lines: List[str], rule: Dict[str, Any]) -> Tuple[bool, float, Dict[str, Any]]:
    """对文本表格格式进行评分"""
    ev = {}
    header_hits = []

    # 头部模式检查
    if "header_startswith" in rule:
        hs = _record_header_hits(lines, rule["header_startswith"], startswith=True)
        if not hs:
            ev["header_startswith"] = "no hit"
            return False, 0.0, ev
        header_hits.extend(hs)

    if "header_any" in rule:
        hs = _record_header_hits(lines, rule["header_any"], startswith=False)
        if not hs:
            ev["header_any"] = "no hit"
            return False, 0.0, ev
        header_hits.extend(hs)

    if "header_must_have" in rule:
        need = rule["header_must_have"]
        ok_all = True
        for pat in need:
            rg = re.compile(pat)
            ok = any(rg.search(ln) for ln in lines[:50])
            if not ok:
                ok_all = False
                ev.setdefault("header_must_have_missing", []).append(pat)
        if not ok_all:
            return False, 0.0, ev

    # 字段数检查
    data_lines = [ln for ln in lines if ln and not ln.startswith("#") and not ln.startswith("track") and not ln.startswith("browser")]
    sample = data_lines[:20] if data_lines else lines[:20]
    mfields = []

    if "exact_fields" in rule:
        nf_ok = all(count_tab_fields(ln) == rule["exact_fields"] for ln in sample if "\t" in ln)
        if not nf_ok:
            ev["exact_fields"] = "mismatch"
            return False, 0.0, ev
        mfields.append("exact_fields")

    if "min_fields" in rule:
        nf_ok = all(count_tab_fields(ln) >= rule["min_fields"] for ln in sample if "\t" in ln)
        if not nf_ok:
            ev["min_fields"] = "mismatch"
            return False, 0.0, ev
        mfields.append("min_fields")

    if "max_fields" in rule:
        nf_ok = all(count_tab_fields(ln) <= rule["max_fields"] for ln in sample if "\t" in ln)
        if not nf_ok:
            ev["max_fields"] = "mismatch"
            return False, 0.0, ev
        mfields.append("max_fields")

    # 指定列为整数
    if "numeric_columns" in rule:
        num_cols = rule["numeric_columns"]
        int_ok_all = True
        for ln in sample:
            if "\t" not in ln:
                continue
            parts = ln.rstrip("\n\r").split("\t")
            for idx in num_cols:
                if idx <= len(parts):
                    if not re.fullmatch(r"[0-9]+", parts[idx-1]):
                        int_ok_all = False
                        ev.setdefault("numeric_columns_errors", []).append({
                            "line": ln, "col": idx, "val": parts[idx-1]
                        })
        if not int_ok_all:
            return False, 0.0, ev

    # 列间关系（如 col5 >= col4）
    def _as_int(parts, i):
        try:
            return int(parts[i-1]) if i <= len(parts) else None
        except Exception:
            return None

    if "relations_all" in rule:
        rel_ok_all = True
        for ln in sample:
            if "\t" not in ln:
                continue
            parts = ln.rstrip("\n\r").split("\t")
            for rel in rule["relations_all"]:
                lhs = _as_int(parts, rel.get("lhs", 0))
                rhs = _as_int(parts, rel.get("rhs", 0))
                op = rel.get("op")
                if lhs is None or (rhs is None and op not in ("exists", "missing")):
                    continue
                ok = True
                if op == ">":    ok = (lhs is not None and rhs is not None and lhs >  rhs)
                elif op == ">=": ok = (lhs is not None and rhs is not None and lhs >= rhs)
                elif op == "<":  ok = (lhs is not None and rhs is not None and lhs <  rhs)
                elif op == "<=": ok = (lhs is not None and rhs is not None and lhs <= rhs)
                elif op == "exists":  ok = (lhs is not None)
                elif op == "missing": ok = (lhs is None)
                if not ok:
                    rel_ok_all = False
                    ev.setdefault("relations_errors", []).append({"line": ln, "rule": rel})
        if not rel_ok_all:
            return False, 0.0, ev

    # 内容模式匹配
    if "pattern_any" in rule:
        pats = [re.compile(p) for p in rule["pattern_any"]]
        matched = []
        for p in pats:
            for i, ln in enumerate(lines[:50], start=1):
                if p.search(ln):
                    matched.append({"pattern": p.pattern, "line_no": i, "line": ln})
        if not matched:
            ev["pattern_any"] = "no hit"
            return False, 0.0, ev
        header_hits.extend(matched)

    # FASTQ 四行组校验
    if rule.get("line_groups_of") == 4 and "pattern_group" in rule:
        pats = [re.compile(p) for p in rule["pattern_group"]]
        L = lines[:8] if len(lines) >= 8 else lines
        ok = True
        for i in range(0, min(8, len(L)), 4):
            grp = L[i:i+4]
            if len(grp) < 4:
                continue
            for j, p in enumerate(pats):
                if not p.search(grp[j]):
                    ok = False
                    break
            if not ok:
                break
        if not ok:
            ev["fastq_group"] = "pattern mismatch"
            return False, 0.0, ev
        header_hits.append({"pattern": "FASTQ 4-line group", "line_no": 1, "line": "OK"})

    score = 0.7
    if header_hits:
        score += 0.15
    if mfields:
        score += 0.1
    score = min(score, 0.98)
    ev["header_hits"] = header_hits
    return True, score, ev

def match_format_from_bytes(buf: bytes, rule: Dict[str, Any], is_text_hint: Optional[bool]) -> Tuple[bool, float, Dict[str, Any]]:
    ev = {}
    if _match_magic(buf, rule):
        ev["magic"] = "hit"
        return True, 0.98, ev
    if rule.get("kind") == "binary":
        return False, 0.0, ev
    text = decode_text(buf)
    lines = split_lines(text)
    ok, score, tev = score_text_table(lines, rule)
    ev.update(tev)
    return ok, score, ev

def find_sidecars(path: str, rules: Dict[str, Any]) -> List[str]:
    dirname, basename = os.path.dirname(path), os.path.basename(path)
    sidecars = []
    
    for sc in rules.get("sidecar_indices", []):
        main_ext = sc.get("main_ext")
        # 检查文件名是否以指定的主扩展名结尾
        if basename.endswith(main_ext):
            for idxext in sc.get("indices", []):
                # 对于索引扩展名以主扩展名开头的情况（如.bam.bai），直接使用basename + 索引后缀
                if idxext.startswith(main_ext):
                    # 例如：sample.bam + .bai (从.bam.bai中去掉.bam前缀) = sample.bam.bai
                    suffix = idxext[len(main_ext):]
                    cand = os.path.join(dirname, basename + suffix)
                elif main_ext.endswith(".gz"):
                    # 对于压缩文件（如.vcf.gz + .tbi），直接在完整文件名后添加索引扩展名
                    cand = os.path.join(dirname, basename + idxext)
                else:
                    # 对于普通文件（如.fasta + .fai），去掉主扩展名后添加索引扩展名
                    name_without_ext = basename[:-len(main_ext)]
                    cand = os.path.join(dirname, name_without_ext + idxext)
                if os.path.exists(cand):
                    sidecars.append(cand)
    return sidecars

# --- biomolecule inference for FASTA/FASTQ ---
NUC_SET = set(list("ACGTUWSMKRYBDHVN"))
PROT_SET = set(list("ACDEFGHIKLMNPQRSTVWYBZX*"))

def infer_biomolecule_from_lines(lines: List[str]) -> Dict[str, Any]:
    seqchars = []
    for ln in lines:
        if ln.startswith(">") or ln.startswith("@") or ln.startswith("+"):
            continue
        letters = re.findall(r"[A-Za-z*]", ln)
        if letters:
            seqchars.extend([c.upper() for c in letters])
        if len(seqchars) > 5000:
            break
    if not seqchars:
        return {"type": "Unknown", "confidence": 0.0, "evidence": {"reason": "no sequence letters"}}

    total = len(seqchars)
    nuc = sum(1 for c in seqchars if c in NUC_SET)
    prot = sum(1 for c in seqchars if c in PROT_SET)
    frac_nuc = nuc / total
    frac_prot = prot / total
    u_count = sum(1 for c in seqchars if c == "U")
    t_count = sum(1 for c in seqchars if c == "T")

    if frac_nuc >= 0.90:
        tpe = "RNA" if u_count > t_count else "DNA"
        conf = min(0.99, 0.80 + 0.20 * (frac_nuc - 0.90) / 0.10)
        return {"type": tpe, "confidence": round(conf, 3), "evidence": {"letters": total, "nuc_frac": round(frac_nuc, 4), "U": u_count, "T": t_count}}
    if frac_prot >= 0.90:
        conf = min(0.99, 0.80 + 0.20 * (frac_prot - 0.90) / 0.10)
        return {"type": "Protein", "confidence": round(conf, 3), "evidence": {"letters": total, "prot_frac": round(frac_prot, 4)}}
    return {"type": "Unknown", "confidence": 0.4, "evidence": {"letters": total, "nuc_frac": round(frac_nuc,4), "prot_frac": round(frac_prot,4)}}

def rank_formats(sample_bytes: bytes, rules: Dict[str, Any], container_hint: Optional[str], inner_name: Optional[str] = None, filename: Optional[str] = None) -> List[Dict[str, Any]]:
    out = []
    is_text_hint = not is_binary_bytes(sample_bytes)
    for fr in rules["formats"]:
        # 不再跳过 index 类
        if fr.get("requires_container") and fr["requires_container"] != container_hint:
            continue
        if fr.get("container") and fr["container"] != container_hint:
            continue

        ok, score, ev = match_format_from_bytes(sample_bytes, fr, is_text_hint)
        if ok:
            bonus = 0.0
            if inner_name and fr.get("extensions"):
                if any(inner_name.lower().endswith(e.lower()) for e in fr["extensions"]):
                    bonus += 0.05
            # 扩展名加权（用于区分 .fai vs .bed 等）
            if filename and fr.get("extensions"):
                if any(filename.lower().endswith(e.lower()) for e in fr["extensions"]):
                    bonus += 0.20

            cand = {
                "type": fr["name"],
                "category": fr.get("category"),
                "represents": fr.get("represents"),
                "confidence": min(1.0, score + bonus),
                "evidence": ev
            }
            if "header_hits" in ev:
                cand["header_hits"] = ev["header_hits"]
            out.append(cand)
    out.sort(key=lambda x: x["confidence"], reverse=True)
    return out[:1]

def finalize_candidates(result: Dict[str, Any], rules: Dict[str, Any], sample_bytes: bytes) -> Dict[str, Any]:
    if result.get("candidates"):
        top = result["candidates"][0]
        path = result["tmp_path"]
        sidecars = find_sidecars(path, rules)
        if sidecars:
            result["sidecars"] = sidecars
            top["confidence"] = min(1.0, top["confidence"] + 0.05)
            top.setdefault("evidence", {})["sidecars"] = sidecars

        # 对序列类做生物分子类型推断
        rule = next((f for f in rules["formats"] if f.get("name") == top["type"]), None)
        if rule and rule.get("infer_biomolecule"):
            text = decode_text(sample_bytes)
            lines = split_lines(text)
            bm = infer_biomolecule_from_lines(lines)
            top["inferred_biomolecule"] = bm

        # 如果识别为 FAI，则尝试推断主文件名（存在的话）
        if top.get("type") == "FAI":
            fai_path = result["tmp_path"]
            if fai_path.lower().endswith(".fai"):
                base = fai_path[:-4]
                candidates = []
                for suf in (".fa", ".fasta", ".fna", ".fq", ".fastq"):
                    for gz in ("", ".gz"):
                        cand = base if base.lower().endswith(suf + gz) else None
                        if cand and os.path.exists(cand):
                            candidates.append(cand)
                if candidates:
                    top.setdefault("indexed_main", candidates)

    return result

def detect_file(path: str, rules: Dict[str, Any]) -> Dict[str, Any]:
    head = read_head(path)
    result = {
        "tmp_path": os.path.abspath(path),
        "container": None,
        "inner_name": None,
        "candidates": [],
        "sidecars": [],
        "notes": []
    }

    is_gzip, is_bgzf, gz_sample, gz_ev = parse_gzip_and_bgzf(path, head)
    if is_gzip:
        result["container"] = "bgzf" if is_bgzf else "gzip"
        inner_bytes = gz_sample or b""
        result["candidates"].extend(
            rank_formats(inner_bytes, rules, container_hint=result["container"], filename=os.path.basename(path))
        )
        result["evidence_container"] = gz_ev
        result["sidecars"] = find_sidecars(path, rules)
        return finalize_candidates(result, rules, inner_bytes)

    if head[:4] == b"PK\x03\x04":
        result["container"] = "zip"
        
        # 优先检查Excel格式（基于文件扩展名）
        ext = os.path.splitext(path)[1].lower()
        excel_extensions = [".xlsx", ".xlsm", ".xlsb", ".xls"]
        if ext in excel_extensions:
            result["candidates"].append({
                "type": "Excel",
                "category": "tabular",
                "represents": "Microsoft Excel 电子表格",
                "confidence": 0.95,
                "evidence": {"by": "zip+excel_extension", "extension": ext}
            })
            result["evidence_container"] = {"zip_excel": f"Excel file with extension {ext}"}
            return finalize_candidates(result, rules, head)
        
        inner_name, inner_bytes, zp_ev = sample_zip_member(path)
        result["inner_name"] = inner_name
        if inner_bytes:
            result["candidates"].extend(
                rank_formats(inner_bytes, rules, container_hint="zip", inner_name=inner_name, filename=inner_name)
            )
        else:
            result["candidates"].append({"type": "archive/zip", "confidence": 0.6, "evidence": zp_ev})
        result["evidence_container"] = zp_ev
        return finalize_candidates(result, rules, inner_bytes or b"")

    try:
        if tarfile.is_tarfile(path):
            result["container"] = "tar"
            inner_name, inner_bytes, tv = sample_tar_member(path)
            result["inner_name"] = inner_name
            if inner_bytes:
                result["candidates"].extend(
                    rank_formats(inner_bytes, rules, container_hint="tar", inner_name=inner_name, filename=inner_name)
                )
            else:
                result["candidates"].append({"type": "archive/tar", "confidence": 0.6, "evidence": tv})
            result["evidence_container"] = tv
            return finalize_candidates(result, rules, inner_bytes or b"")
    except Exception:
        pass

    if detect_hdf5_signature(path, head):
        result["container"] = "hdf5"
        ext = os.path.splitext(path)[1].lower()
        hdf5_formats = [f for f in rules["formats"] if f.get("container") == "hdf5"]
        for fr in hdf5_formats:
            if ext in [e.lower() for e in fr.get("extensions", [])]:
                result["candidates"].append({
                    "type": fr["name"],
                    "category": fr.get("category"),
                    "represents": fr.get("represents"),
                    "confidence": 0.9,
                    "evidence": {"by": "hdf5+extension"}
                })
                break
        if not result["candidates"]:
            result["candidates"].append({
                "type": "HDF5-container",
                "confidence": 0.7,
                "evidence": {"head_hex": bytes2hex(head)},
                "represents": "HDF5 容器（具体格式未知）"
            })
        return finalize_candidates(result, rules, head)

    candidates = rank_formats(head, rules, container_hint=None, filename=os.path.basename(path))
    if candidates:
        result["candidates"].extend(candidates)
    else:
        result["candidates"].append({
            "type": "unknown",
            "confidence": 0.1,
            "evidence": {"head_hex": bytes2hex(head)},
            "represents": "未知格式"
        })

    result["sidecars"] = find_sidecars(path, rules)
    return finalize_candidates(result, rules, head)

def detect(path: str, rules_path: str = None) -> Dict[str, Any]:
    if rules_path is None:
        from pathlib import Path
        rules_path = str(Path(__file__).resolve().parent / "biofile_rules.json")
    rules = load_rules(rules_path)
    return detect_file(path, rules)

if __name__ == "__main__":
    import argparse, pprint
    ap = argparse.ArgumentParser(description="Bio file detector (with content-type inference & explanations)")
    ap.add_argument("file", help="path to file")
    from pathlib import Path
    default_rules = str(Path(__file__).resolve().parent / "biofile_rules.json")
    ap.add_argument("--rules", default=default_rules, help="rules JSON path")
    args = ap.parse_args()
    rules = load_rules(args.rules)
    info = detect_file(args.file, rules)
    pprint.pprint(info)