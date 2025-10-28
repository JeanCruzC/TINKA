"""Funciones auxiliares y utilidades comunes."""
from __future__ import annotations

from math import sqrt
from pathlib import Path
from typing import Dict, List, Optional
import json
import os

try:  # Importación opcional para la app Streamlit dentro de Snowflake.
    import streamlit as st
except Exception:  # pragma: no cover
    st = None


def ensure_dirs(path: Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def _virtual_store() -> Optional[Dict[str, object]]:
    """Almacén en memoria cuando no es posible escribir en disco."""

    if st is None:
        return None
    return st.session_state.setdefault("_virtual_files", {})

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
    try:
        ensure_dirs(path)
        tmp = str(path) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        os.replace(tmp, path)
    except OSError:
        store = _virtual_store()
        if store is None:
            raise
        store[str(path)] = data

def load_json(path: Path, default=None):
    p = Path(path)
    if p.exists():
        try:
            txt = p.read_text(encoding="utf-8").strip()
            if not txt:
                return default
            return json.loads(txt)
        except Exception:
            return default

    store = _virtual_store()
    if store is not None and str(path) in store:
        return store[str(path)]
    return default
