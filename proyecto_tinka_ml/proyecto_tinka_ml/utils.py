"""Funciones auxiliares y utilidades comunes."""
from __future__ import annotations
from typing import List
from pathlib import Path
from math import sqrt
import json, os

def ensure_dirs(path: Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)

def parse_numbers(s: str) -> List[int]:
    nums = []
    for token in s.replace(',', ' ').split():
        token = token.strip()
        if token.isdigit():
            nums.append(int(token))
    return nums

def is_prime(n: int) -> bool:
    if n < 2: return False
    if n in (2,3): return True
    if n % 2 == 0: return False
    r = int(sqrt(n)); f = 3
    while f <= r:
        if n % f == 0: return False
        f += 2
    return True

def ascii_bar(label: str, value: int, max_value: int, width: int = 40) -> str:
    if max_value <= 0:
        bar = ""
    else:
        fill = int((value / max_value) * width)
        bar = "█" * fill + "·" * (width - fill)
    return f"{label:>2}: {bar} {value}"

def save_json(path: Path, data) -> None:
    ensure_dirs(path)
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    os.replace(tmp, path)

def load_json(path: Path, default=None):
    p = Path(path)
    if not p.exists():
        return default
    try:
        txt = p.read_text(encoding="utf-8").strip()
        if not txt:
            return default
        return json.loads(txt)
    except Exception:
        return default
