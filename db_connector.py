"""Conectores de datos para MySQL y Snowflake con caché flexible."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional
from urllib.parse import quote_plus

import pandas as pd

from config import (
    DB_CONFIG,
    TABLE_NAME,
    CACHE_FILE,
    SNOWFLAKE_CONFIG,
    SNOWFLAKE_TABLE,
)
from utils import load_json, save_json

try:  # Importación opcional: sólo se necesita en despliegues Snowflake.
    from snowflake.snowpark import Session  # type: ignore
except Exception:  # pragma: no cover - la librería no siempre está instalada.
    Session = None

try:  # Streamlit aporta mecanismos de caché y secretos.
    import streamlit as st
except Exception:  # pragma: no cover
    st = None

try:
    from sqlalchemy import create_engine
except Exception:  # pragma: no cover - en Snowflake no siempre está disponible.
    create_engine = None


SQL_BASE = f"""SELECT id_sorteo, fecha_sorteo, numeros, boliyapa, jackpot,
       COALESCE(created_at, CURRENT_TIMESTAMP()) AS created_at
FROM {TABLE_NAME}
WHERE numeros IS NOT NULL AND numeros <> ''
ORDER BY fecha_sorteo ASC, id_sorteo ASC
"""


def _snowflake_configs() -> Optional[Dict[str, str]]:
    """Obtiene la configuración para Snowflake desde Streamlit o config local."""

    if st is not None:
        secrets = getattr(st, "secrets", None)
        if secrets is not None and "snowflake" in secrets:
            cfg = dict(secrets["snowflake"])
            # ``table`` puede venir en los secretos; si no, se completa abajo.
            return cfg

    # Configuración por defecto del archivo config.py
    if any(v for v in SNOWFLAKE_CONFIG.values()):
        return dict(SNOWFLAKE_CONFIG)

    return None


def _resolve_table(cfg: Dict[str, str]) -> str:
    table = cfg.get("table") or SNOWFLAKE_CONFIG.get("table") or SNOWFLAKE_TABLE
    database = cfg.get("database") or SNOWFLAKE_CONFIG.get("database")
    schema = cfg.get("schema") or SNOWFLAKE_CONFIG.get("schema")

    def _quote(identifier: Optional[str]) -> Optional[str]:
        if not identifier:
            return None
        return f'"{identifier}"'

    parts = [p for p in (_quote(database), _quote(schema), _quote(table)) if p]
    return ".".join(parts)


_SNOWFLAKE_SESSION: Optional[Session] = None


def get_snowflake_session() -> Session:
    """Crea o reutiliza una sesión de Snowflake."""

    global _SNOWFLAKE_SESSION

    if st is not None and "snowflake_session" in st.session_state:
        sess = st.session_state["snowflake_session"]
        if sess and getattr(sess, "_conn", None):
            return sess

    if _SNOWFLAKE_SESSION is not None and getattr(_SNOWFLAKE_SESSION, "_conn", None):
        return _SNOWFLAKE_SESSION

    if Session is None:
        raise RuntimeError(
            "snowflake.snowpark no está disponible. Instala 'snowflake-snowpark-python' "
            "o ejecuta la app dentro de Snowflake."
        )

    cfg = _snowflake_configs()
    if not cfg:
        raise RuntimeError(
            "No se encontró configuración de Snowflake. Define SNOWFLAKE_CONFIG en config.py "
            "o proporciona secrets['snowflake']."
        )

    session = Session.builder.configs(cfg).create()

    if st is not None:
        st.session_state["snowflake_session"] = session

    _SNOWFLAKE_SESSION = session
    return session


def fetch_from_snowflake() -> pd.DataFrame:
    session = get_snowflake_session()
    cfg = _snowflake_configs() or {}
    table_ident = _resolve_table(cfg)
    if not table_ident:
        raise RuntimeError(
            "Debe especificarse una tabla de Snowflake (config['table'] o SNOWFLAKE_TABLE)."
        )

    sql = f"""SELECT id_sorteo, fecha_sorteo, numeros, boliyapa, jackpot,
           COALESCE(created_at, CURRENT_TIMESTAMP()) AS created_at
    FROM {table_ident}
    WHERE numeros IS NOT NULL AND numeros <> ''
    ORDER BY fecha_sorteo ASC, id_sorteo ASC"""

    df = session.sql(sql).to_pandas()
    return df


def get_engine():
    if create_engine is None:
        raise RuntimeError(
            "SQLAlchemy no está disponible. Instala 'sqlalchemy' para usar MySQL o "
            "configura Snowflake."
        )
    user = DB_CONFIG.get("user", "")
    pwd = quote_plus(DB_CONFIG.get("password", ""))
    host = DB_CONFIG.get("host", "localhost")
    port = DB_CONFIG.get("port", 3306)
    db = DB_CONFIG.get("database", "")
    url = f"mysql+mysqlconnector://{user}:{pwd}@{host}:{port}/{db}"
    return create_engine(url, pool_pre_ping=True, pool_recycle=1800)


def fetch_from_mysql() -> pd.DataFrame:
    eng = get_engine()
    try:
        df = pd.read_sql_query(SQL_BASE, eng)
        return df
    finally:
        eng.dispose()


def fetch_from_db() -> pd.DataFrame:
    """Obtiene los datos desde Snowflake (preferido) o MySQL."""

    try:
        cfg = _snowflake_configs()
        if cfg:
            df = fetch_from_snowflake()
        else:
            df = fetch_from_mysql()
    except Exception:
        # Si hay cualquier problema con Snowflake, intentar caer a MySQL.
        if _snowflake_configs():
            raise
        df = fetch_from_mysql()
    return df

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
