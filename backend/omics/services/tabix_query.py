import subprocess
import tempfile
from pathlib import Path
from typing import Optional
from uuid import uuid4

OUTPUT_ROOT = Path("output_results")
OUTPUT_ROOT.mkdir(exist_ok=True)

def run_tabix_extract(
    peak_file: Path,
    bed_text: Optional[str] = None,
    bed_path: Optional[str] = None,
    return_type: str = "text"  # "text" or "file"
) -> str:
    """
    从指定 peak 文件中，使用 tabix 提取 BED 区域对应数据。

    Args:
        peak_file: 被查询的 peak 文件路径（必须为 .gz 且已 tabix 索引）
        bed_text: 输入区域（字符串形式的 BED）
        bed_path: 输入区域（文件路径形式）
        return_type: 返回内容类型：'text' 或 'file'

    Returns:
        str: 查询结果（文本或保存路径）
    """
    if not peak_file.exists() or not Path(str(peak_file) + ".tbi").exists():
        raise FileNotFoundError("peak 文件或其 .tbi 索引文件不存在")

    if not (bed_text or bed_path):
        raise ValueError("必须提供 bed_text 或 bed_path 之一")

    # 准备 region 文件
    if bed_text:
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp_bed:
            tmp_bed.write(bed_text)
            region_file = Path(tmp_bed.name)
    else:
        region_file = Path(bed_path)
        if not region_file.exists():
            raise FileNotFoundError("bed_path 指定的文件不存在")

    try:
        result = subprocess.run(
            ["tabix", "-R", str(region_file), str(peak_file)],
            capture_output=True, text=True, check=True
        )
        output = result.stdout
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"tabix 查询失败: {e.stderr.strip()}")
    finally:
        if bed_text and region_file.exists():
            region_file.unlink(missing_ok=True)

    if return_type == "text":
        return output
    elif return_type == "file":
        out_file = OUTPUT_ROOT / f"extracted_peaks_{uuid4().hex[:8]}.bed"
        with open(out_file, "w") as f:
            f.write(output)
        return str(out_file)
    else:
        raise ValueError("return_type 只能是 'text' 或 'file'")
