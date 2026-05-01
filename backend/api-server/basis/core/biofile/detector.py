# core/detector.py
from typing import Dict
from pathlib import Path
from . import biofile_detect  # 直接复用你已有的模块

RULES_PATH = Path(__file__).resolve().parent / "biofile_rules.json"

def detect_path(path: str) -> Dict:
    """阶段①：类型判定（复用现有实现）"""
    return biofile_detect.detect(path, rules_path=str(RULES_PATH))