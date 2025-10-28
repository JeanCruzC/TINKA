"""Wrapper para ejecutar la app principal desde la raíz del repositorio."""
from __future__ import annotations

import os
import runpy

import streamlit as st


def _maybe_connect_snowflake() -> None:
    """Muestra mensajes informativos si hay credenciales para Snowflake."""

    sf_env = {
        k: os.getenv(k)
        for k in [
            "SF_ACCOUNT",
            "SF_USER",
            "SF_PASSWORD",
            "SF_ROLE",
            "SF_WAREHOUSE",
            "SF_DATABASE",
            "SF_SCHEMA",
        ]
    }
    if not all(sf_env.values()):
        st.info("Configura Secrets en el Space si deseas conectar Snowflake.")
        return

    try:
        import snowflake.connector as sf  # type: ignore

        conn = sf.connect(
            account=sf_env["SF_ACCOUNT"],
            user=sf_env["SF_USER"],
            password=sf_env["SF_PASSWORD"],
            role=sf_env["SF_ROLE"],
            warehouse=sf_env["SF_WAREHOUSE"],
            database=sf_env["SF_DATABASE"],
            schema=sf_env["SF_SCHEMA"],
        )
    except ImportError:
        st.warning("Instala 'snowflake-connector-python' para habilitar la conexión a Snowflake.")
        return
    except Exception as exc:  # pragma: no cover - solo informativo
        st.warning(f"No se pudo conectar a Snowflake: {exc}")
        return

    conn.close()
    st.success("Conectado a Snowflake")


if __name__ == "__main__":
    _maybe_connect_snowflake()
    runpy.run_module("proyecto_tinka_ml.proyecto_tinka_ml.streamlit_app", run_name="__main__")
