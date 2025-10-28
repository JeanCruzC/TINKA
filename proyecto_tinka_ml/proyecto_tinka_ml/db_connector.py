"""Conexión y consultas a MySQL (XAMPP) con caché local robusto."""
from __future__ import annotations
from pathlib import Path
from urllib.parse import quote_plus
import pandas as pd
from sqlalchemy import create_engine

from config import DB_CONFIG, TABLE_NAME, CACHE_FILE
from utils import load_json, save_json

SQL_BASE = f"""SELECT id_sorteo, fecha_sorteo, numeros, boliyapa, jackpot,
       COALESCE(created_at, NOW()) AS created_at
FROM {TABLE_NAME}
WHERE numeros IS NOT NULL AND numeros <> ''
ORDER BY fecha_sorteo ASC, id_sorteo ASC
"""

def get_engine():
    user = DB_CONFIG.get("user", "")
    pwd = quote_plus(DB_CONFIG.get("password", ""))
    host = DB_CONFIG.get("host", "localhost")
    port = DB_CONFIG.get("port", 3306)
    db   = DB_CONFIG.get("database", "")
    url = f"mysql+mysqlconnector://{user}:{pwd}@{host}:{port}/{db}"
    return create_engine(url, pool_pre_ping=True, pool_recycle=1800)

def fetch_from_db() -> pd.DataFrame:
    eng = get_engine()
    try:
        df = pd.read_sql_query(SQL_BASE, eng)
        return df
    finally:
        eng.dispose()

def load_cached():
    data = load_json(CACHE_FILE, default=None)
    if not data: return None
    try:
        df = pd.DataFrame(data)
        if "fecha_sorteo" in df.columns:
            df["fecha_sorteo"] = pd.to_datetime(df["fecha_sorteo"]).dt.date
        return df
    except Exception:
        return None

def save_cache(df: pd.DataFrame) -> None:
    df = df.copy()
    for col in ("fecha_sorteo", "created_at"):
        if col in df.columns:
            df[col] = df[col].astype(str)
    save_json(CACHE_FILE, df.to_dict(orient="records"))

def get_data(use_cache: bool = True):
    if use_cache:
        cached = load_cached()
        if cached is not None and len(cached) > 0:
            return cached.copy()
    df = fetch_from_db()
    if "fecha_sorteo" in df.columns:
        df["fecha_sorteo"] = pd.to_datetime(df["fecha_sorteo"]).dt.date
    save_cache(df)
    return df

def refresh_cache():
    df = fetch_from_db()
    if "fecha_sorteo" in df.columns:
        df["fecha_sorteo"] = pd.to_datetime(df["fecha_sorteo"]).dt.date
    save_cache(df)
    return df
