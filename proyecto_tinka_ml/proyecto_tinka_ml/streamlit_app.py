"""Aplicación Streamlit para Snowflake con todas las funciones del menú clásico."""
from __future__ import annotations

import json
from typing import List

import pandas as pd
import streamlit as st

from analizador import (
    analisis_completo,
    analisis_frecuencias,
    analisis_temporal,
)
from config import COMBOS_FILE
from db_connector import get_data, refresh_cache
from generador import (
    estrategia_equilibrio_hot_cold,
    estrategia_frecuencia_pura,
    estrategia_patrones_detectados,
    estrategia_random_ponderado,
    estrategia_temporal_inteligente,
    rankear_combos_ml,
)
from ml import (
    beta_binomial_posteriors,
    beta_binomial_posteriors_ewma,
    blend_probabilities,
    save_probabilities,
    thompson_sampling_pool,
)
from utils import load_json, parse_numbers, save_json
from visualizador import html_report, render_ascii_hist

st.set_page_config(
    page_title="Tinka Analytics Snowflake",
    page_icon="🎲",
    layout="wide",
)

st.title("Tinka Analytics — Snowflake + Streamlit")
st.caption(
    "Análisis histórico, generación de combinaciones y recomendaciones con el mismo motor del CLI original."
)


@st.cache_data(ttl=1800)
def load_dataset() -> pd.DataFrame:
    """Obtiene los datos desde la fuente configurada."""

    df = get_data(use_cache=True)
    if "fecha_sorteo" in df.columns:
        df["fecha_sorteo"] = pd.to_datetime(df["fecha_sorteo"])
    return df


def format_combo(combo: List[int]) -> str:
    return " ".join(f"{x:02d}" for x in combo)


def show_data_overview(df: pd.DataFrame) -> None:
    st.subheader("Datos disponibles")
    col1, col2, col3 = st.columns(3)
    col1.metric("Sorteos", len(df))
    col2.metric("Primer sorteo", str(df["fecha_sorteo"].min()) if len(df) else "-")
    col3.metric("Último sorteo", str(df["fecha_sorteo"].max()) if len(df) else "-")
    with st.expander("Vista previa de registros"):
        st.dataframe(df.tail(20), use_container_width=True)


MENU_OPTIONS = [
    "Dashboard de estadísticas",
    "Análisis por número",
    "Generar combinaciones",
    "Comparar mi combinación",
    "Mejores históricas",
    "Exportar análisis",
    "Actualizar datos",
    "Recomendación automática (ML)",
]

option = st.sidebar.radio("Menú principal", MENU_OPTIONS, index=0)
st.sidebar.divider()
if st.sidebar.button("Refrescar datos ahora", use_container_width=True):
    with st.spinner("Actualizando cache desde la base de datos..."):
        df_refresh = refresh_cache()
    load_dataset.clear()
    st.session_state["_last_refresh"] = len(df_refresh)
    st.sidebar.success(f"Cache actualizado ({len(df_refresh)} registros).")


def ensure_dataset() -> pd.DataFrame:
    df_loaded = load_dataset()
    if len(df_loaded) == 0:
        st.error("No hay datos disponibles. Verifica la conexión a Snowflake y la tabla configurada.")
    return df_loaded


def render_dashboard(df: pd.DataFrame) -> None:
    stats = analisis_completo(df)
    frec = stats["frecuencias"]
    chi2 = stats["chi_cuadrado"]
    show_data_overview(df)

    st.subheader("Top calientes y fríos")
    col1, col2 = st.columns(2)
    col1.write(pd.DataFrame({"Número": frec["hot_15"]}))
    col1.caption("15 números con mayor frecuencia histórica.")
    col2.write(pd.DataFrame({"Número": frec["cold_15"]}))
    col2.caption("15 números con menor frecuencia histórica.")

    st.subheader("Histograma de frecuencias")
    freq_df = pd.DataFrame(
        {
            "Número": list(frec["freq_abs"].keys()),
            "Frecuencia": list(frec["freq_abs"].values()),
        }
    )
    st.bar_chart(freq_df, x="Número", y="Frecuencia", use_container_width=True)
    with st.expander("Histograma ASCII"):
        st.text(render_ascii_hist(frec["freq_abs"]))

    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Dormidos >20 sorteos", len(frec["dormidos_mas20"]))
    col_b.metric("En racha (últimos 10)", len(frec["en_racha_ult10"]))
    col_c.metric("Chi²", f"{chi2.get('chi2', float('nan')):.2f}" if chi2.get("chi2") else "-")

    st.subheader("Detalle temporal (últimas ventanas)")
    temp = stats["temporal"]
    tabs = st.tabs([f"Últimos {win}" for win in temp["ventanas"].keys()])
    for tab, win in zip(tabs, temp["ventanas"].keys()):
        with tab:
            sub = temp["ventanas"][win]
            hot = pd.DataFrame({"Número": sub["hot_15"]})
            cold = pd.DataFrame({"Número": sub["cold_15"]})
            c1, c2 = st.columns(2)
            c1.write(hot)
            c2.write(cold)

    st.subheader("Co-ocurrencias")
    cooc = stats["coocurrencias"]
    c1, c2 = st.columns(2)
    c1.write(pd.DataFrame(cooc["pairs_top20"]))
    c2.write(pd.DataFrame(cooc["trios_top20"]))


def render_number_analysis(df: pd.DataFrame) -> None:
    frec = analisis_frecuencias(df)
    n = st.number_input("Selecciona número", min_value=1, max_value=45, value=1, step=1)
    fa = frec["freq_abs"].get(int(n), 0)
    fr = frec["freq_rel"].get(int(n), 0.0)
    in_hot = int(n) in frec["hot_15"]
    in_cold = int(n) in frec["cold_15"]
    in_streak = int(n) in frec["en_racha_ult10"]
    dormant = int(n) in frec["dormidos_mas20"]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Frecuencia absoluta", fa)
    col2.metric("Frecuencia relativa", f"{fr:.4f}")
    col3.metric("En racha", "Sí" if in_streak else "No")
    col4.metric("Dormido", "Sí" if dormant else "No")

    st.write(
        f"El número {int(n):02d} aparece en los HOT: **{in_hot}** · en los COLD: **{in_cold}**"
    )


def render_generator(df: pd.DataFrame) -> None:
    stats = analisis_completo(df)
    frec = stats["frecuencias"]
    temp = stats["temporal"]
    cooc = stats["coocurrencias"]
    last50 = temp["ventanas"].get("50", frec)

    estrategia = st.selectbox(
        "Selecciona estrategia",
        (
            "Frecuencia pura",
            "Equilibrio caliente-frío",
            "Temporal inteligente (últimos 50)",
            "Patrones detectados",
            "Random ponderado",
        ),
    )
    cantidad = st.slider("¿Cuántas combinaciones?", min_value=1, max_value=50, value=10)

    combos = []
    etiqueta = ""
    if st.button("Generar combinaciones", type="primary"):
        if estrategia == "Frecuencia pura":
            combos = estrategia_frecuencia_pura(frec["freq_abs"], n_combos=cantidad)
            etiqueta = "frecuencia_pura"
        elif estrategia == "Equilibrio caliente-frío":
            combos = estrategia_equilibrio_hot_cold(
                frec["freq_abs"], frec["hot_15"], frec["cold_15"], n_combos=cantidad
            )
            etiqueta = "equilibrio_hot_cold"
        elif estrategia == "Temporal inteligente (últimos 50)":
            combos = estrategia_temporal_inteligente(
                last50["freq_abs"], last50["hot_15"], n_combos=cantidad
            )
            etiqueta = "temporal_inteligente_50"
        elif estrategia == "Patrones detectados":
            combos = estrategia_patrones_detectados(
                cooc["pairs_top20"], cooc["trios_top20"], n_combos=cantidad
            )
            etiqueta = "patrones_detectados"
        elif estrategia == "Random ponderado":
            combos = estrategia_random_ponderado(frec["freq_abs"], n_combos=cantidad)
            etiqueta = "random_ponderado"

        if combos:
            st.success(f"Se generaron {len(combos)} combinaciones.")
            df_combos = pd.DataFrame({"#": range(1, len(combos) + 1), "Combinación": [format_combo(c) for c in combos]})
            st.dataframe(df_combos, hide_index=True, use_container_width=True)
            record = load_json(COMBOS_FILE, default=[])
            record.append({"estrategia": etiqueta, "n": cantidad, "combos": combos})
            save_json(COMBOS_FILE, record)
            st.download_button(
                "Descargar combinaciones (JSON)",
                data=json.dumps(combos, ensure_ascii=False, indent=2),
                file_name="combinaciones.json",
                mime="application/json",
            )
        else:
            st.warning("No se pudieron generar combinaciones, intenta con otra estrategia o refresca los datos.")


def render_compare(df: pd.DataFrame) -> None:
    st.write("Introduce tus números separados por espacios o comas.")
    entrada = st.text_input("Mis números", value="")
    if st.button("Evaluar combinación"):
        arr = sorted(parse_numbers(entrada))
        if len(arr) != 6 or min(arr, default=0) < 1 or max(arr, default=50) > 45 or len(set(arr)) != 6:
            st.error("Debes ingresar exactamente 6 números únicos entre 1 y 45.")
            return
        stats = analisis_completo(df)
        frec = stats["frecuencias"]
        hot = set(frec["hot_15"])
        cold = set(frec["cold_15"])
        score = sum(frec["freq_abs"].get(x, 0) for x in arr)
        suma = sum(arr)
        ev = sum(1 for x in arr if x % 2 == 0)
        od = 6 - ev
        in_hot = [x for x in arr if x in hot]
        in_cold = [x for x in arr if x in cold]

        col1, col2, col3 = st.columns(3)
        col1.metric("Suma", suma)
        col2.metric("Pares", ev)
        col3.metric("Impares", od)
        st.write("En HOT:", in_hot)
        st.write("En COLD:", in_cold)
        st.info(f"Puntuación heurística (sum freq_abs): {score}")


def render_best_history(df: pd.DataFrame) -> None:
    rows = []
    frec = analisis_frecuencias(df)["freq_abs"]
    for _, r in df.iterrows():
        arr = sorted(parse_numbers(r["numeros"]))
        s = sum(arr)
        score = sum(frec.get(x, 0) for x in arr)
        penal = abs(135 - s)
        rows.append(
            {
                "Fecha": r["fecha_sorteo"],
                "ID Sorteo": int(r["id_sorteo"]),
                "Combinación": format_combo(arr),
                "Suma": s,
                "Score": score - penal,
            }
        )
    top = sorted(rows, key=lambda x: x["Score"], reverse=True)[:10]
    st.write(pd.DataFrame(top))


def render_export(df: pd.DataFrame) -> None:
    stats = analisis_completo(df)
    html = html_report(stats)
    st.download_button(
        "Descargar reporte HTML",
        data=html.encode("utf-8"),
        file_name="reporte_tinka.html",
        mime="text/html",
    )
    st.download_button(
        "Descargar estadísticas (JSON)",
        data=json.dumps(stats, ensure_ascii=False, indent=2, default=str),
        file_name="estadisticas.json",
        mime="application/json",
    )


def render_update(df: pd.DataFrame) -> None:
    st.info(
        "El conjunto de datos se almacena en caché durante 30 minutos. Puedes forzar la recarga utilizando el botón de la barra lateral."
    )
    st.write(f"Registros en cache actual: **{len(df)}**")
    if "_last_refresh" in st.session_state:
        st.write(f"Última recarga manual: {st.session_state['_last_refresh']} filas")


def render_ml(df: pd.DataFrame) -> None:
    n = st.slider("¿Cuántas recomendaciones ML?", min_value=1, max_value=20, value=3)
    if st.button("Calcular recomendaciones ML", type="primary"):
        with st.spinner("Calculando probabilidades bayesianas..."):
            posts_global = beta_binomial_posteriors(df, prior_strength=30.0, p0=(6.0 / 45.0))
            posts_recent = beta_binomial_posteriors_ewma(df, halflife_draws=50, prior_strength=15.0, p0=(6.0 / 45.0))
            probs_blend = blend_probabilities(posts_global, posts_recent, w_recent=0.30)
            save_probabilities(posts_global, posts_recent, probs_blend)

            stats = analisis_completo(df)
            frec = stats["frecuencias"]
            cooc = stats["coocurrencias"]
            temp = analisis_temporal(df)
            last50 = temp["ventanas"].get("50", frec)

            pool = []
            N = max(10, n * 12)
            pool += estrategia_equilibrio_hot_cold(
                frec["freq_abs"], frec["hot_15"], frec["cold_15"], n_combos=N
            )
            pool += estrategia_temporal_inteligente(last50["freq_abs"], last50["hot_15"], n_combos=N)
            pool += estrategia_random_ponderado(frec["freq_abs"], n_combos=max(5, N // 2))
            pool += estrategia_patrones_detectados(
                cooc["pairs_top20"], cooc["trios_top20"], n_combos=max(5, n * 6)
            )
            pool += thompson_sampling_pool(posts_recent, n_combos=max(10, n * 10), k=6)

            if not pool:
                st.warning("No se pudieron generar combinaciones candidatas. Refresca los datos e inténtalo nuevamente.")
                return

            ranked = rankear_combos_ml(pool, probs_blend)[:n]
            df_ranked = pd.DataFrame(
                {
                    "#": range(1, len(ranked) + 1),
                    "Combinación": [format_combo(c) for c, _ in ranked],
                    "Score": [round(float(s), 2) for _, s in ranked],
                }
            )
            st.dataframe(df_ranked, use_container_width=True, hide_index=True)
            st.download_button(
                "Descargar recomendaciones (JSON)",
                data=df_ranked.to_json(orient="records"),
                file_name="recomendaciones_ml.json",
                mime="application/json",
            )


if option == "Dashboard de estadísticas":
    data = ensure_dataset()
    if len(data):
        render_dashboard(data)
elif option == "Análisis por número":
    data = ensure_dataset()
    if len(data):
        render_number_analysis(data)
elif option == "Generar combinaciones":
    data = ensure_dataset()
    if len(data):
        render_generator(data)
elif option == "Comparar mi combinación":
    data = ensure_dataset()
    if len(data):
        render_compare(data)
elif option == "Mejores históricas":
    data = ensure_dataset()
    if len(data):
        render_best_history(data)
elif option == "Exportar análisis":
    data = ensure_dataset()
    if len(data):
        render_export(data)
elif option == "Actualizar datos":
    data = ensure_dataset()
    if len(data):
        render_update(data)
elif option == "Recomendación automática (ML)":
    data = ensure_dataset()
    if len(data):
        render_ml(data)
