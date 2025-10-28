"""Interfaz de consola (menú) para el sistema Tinka con opción ML."""
from __future__ import annotations
from pathlib import Path
import pandas as pd

from config import DATA_DIR, COMBOS_FILE
from db_connector import get_data, refresh_cache
from analizador import analisis_completo, analisis_frecuencias, analisis_temporal
from generador import (
    estrategia_frecuencia_pura,
    estrategia_equilibrio_hot_cold,
    estrategia_temporal_inteligente,
    estrategia_patrones_detectados,
    estrategia_random_ponderado,
    rankear_combos_ml,
)
from utils import parse_numbers, save_json, load_json
from visualizador import render_ascii_hist, html_report
from ml import (
    beta_binomial_posteriors,
    beta_binomial_posteriors_ewma,
    blend_probabilities,
    save_probabilities,
    thompson_sampling_pool,
)

def pause():
    input("\nPresiona ENTER para continuar...")

def _int_input_default(prompt: str, default: int) -> int:
    s = input(prompt).strip()
    if not s:
        return default
    try:
        v = int(s)
        if v <= 0: return default
        return v
    except Exception:
        return default

def show_dashboard(df: pd.DataFrame):
    stats = analisis_completo(df)
    print("\n=== DASHBOARD RÁPIDO ===\n")
    frec = stats['frecuencias']
    print("Top 15 calientes:", frec['hot_15'])
    print("Top 15 fríos   :", frec['cold_15'])
    print("En racha (ult10):", frec['en_racha_ult10'])
    print("Dormidos (>20)  :", frec['dormidos_mas20'])
    print("\nHistograma (ASCII):\n")
    print(render_ascii_hist(frec['freq_abs']))
    print("\nChi-cuadrado:", stats['chi_cuadrado'])
    out_html = DATA_DIR / "reporte.html"
    out_html.write_text(html_report(stats), encoding="utf-8")
    print(f"\nReporte HTML exportado en: {out_html}")

def analisis_por_numero(df: pd.DataFrame):
    try:
        n = int(input("Número (1-45): ").strip())
    except Exception:
        print("Entrada inválida"); return
    if not (1 <= n <= 45):
        print("Fuera de rango"); return
    frec = analisis_frecuencias(df)
    fa = frec['freq_abs'].get(n, 0)
    fr = frec['freq_rel'].get(n, 0.0)
    ult10 = n in frec['en_racha_ult10']
    dorm = n in frec['dormidos_mas20']
    print(f"\nNúmero {n}: freq_abs={fa}, freq_rel={fr:.4f}, en_racha_ult10={ult10}, dormido>20={dorm}\n")

def _imprimir_combos(combos):
    for i, c in enumerate(combos, 1):
        print(f"{i:02d})", " ".join(f"{x:02d}" for x in c))

def generar_combinaciones(df: pd.DataFrame):
    stats = analisis_completo(df)
    frec = stats['frecuencias']
    cooc = stats['coocurrencias']
    temp = analisis_temporal(df)
    last50 = temp['ventanas']['50']

    print("\nEstrategias:")
    print(" 1) Frecuencia pura")
    print(" 2) Equilibrio caliente-frío")
    print(" 3) Temporal inteligente (últimos 50)")
    print(" 4) Patrones detectados (pares/tríos)")
    print(" 5) Random ponderado")
    op = input("Elige 1-5: ").strip()

    n = _int_input_default("¿Cuántas combinaciones quieres generar? [10 por defecto]: ", 10)

    combos = []
    if op == "1":
        combos = estrategia_frecuencia_pura(frec['freq_abs'], n_combos=n)
        etiqueta = "frecuencia_pura"
    elif op == "2":
        combos = estrategia_equilibrio_hot_cold(frec['freq_abs'], frec['hot_15'], frec['cold_15'], n_combos=n)
        etiqueta = "equilibrio_hot_cold"
    elif op == "3":
        combos = estrategia_temporal_inteligente(last50['freq_abs'], last50['hot_15'], n_combos=n)
        etiqueta = "temporal_inteligente_50"
    elif op == "4":
        combos = estrategia_patrones_detectados(cooc['pairs_top20'], cooc['trios_top20'], n_combos=n)
        etiqueta = "patrones_detectados"
    elif op == "5":
        combos = estrategia_random_ponderado(frec['freq_abs'], n_combos=n)
        etiqueta = "random_ponderado"
    else:
        print("Opción no válida"); return

    if not combos:
        print("\nNo se pudieron generar combinaciones."); return

    print("\n=== Combinaciones sugeridas ===\n")
    _imprimir_combos(combos)

    record = load_json(COMBOS_FILE, default=[])
    record.append({"estrategia": etiqueta, "n": n, "combos": combos})
    save_json(COMBOS_FILE, record)
    print(f"\nGuardado en {COMBOS_FILE}")

def comparar_mi_combinacion(df: pd.DataFrame):
    s = input("Ingresa tus 6 números separados por espacio: ").strip()
    arr = sorted(parse_numbers(s))
    if len(arr) != 6 or min(arr) < 1 or max(arr) > 45 or len(set(arr)) != 6:
        print("Entrada inválida"); return
    stats = analisis_completo(df)
    frec = stats['frecuencias']
    hot = set(frec['hot_15'])
    cold = set(frec['cold_15'])
    score = sum(frec['freq_abs'].get(x,0) for x in arr)
    suma = sum(arr)
    ev = sum(1 for x in arr if x % 2 == 0)
    od = 6 - ev
    in_hot = [x for x in arr if x in hot]
    in_cold = [x for x in arr if x in cold]
    print("\n=== Evaluación ===")
    print("Tu combinación :", " ".join(f"{x:02d}" for x in arr))
    print("Suma           :", suma, "(recomendado 90-180)")
    print("Pares/Impares  :", ev, "/", od)
    print("En HOT         :", in_hot)
    print("En COLD        :", in_cold)
    print("Puntuación (sum freq_abs):", score)

def ver_mejores_historicas(df: pd.DataFrame):
    frec = analisis_frecuencias(df)['freq_abs']
    rows = []
    for _, r in df.iterrows():
        arr = sorted(parse_numbers(r['numeros']))
        s = sum(arr)
        score = sum(frec.get(x,0) for x in arr)
        penal = abs(135 - s)
        rows.append({"id_sorteo": int(r['id_sorteo']), "fecha": str(r['fecha_sorteo']),
                     "combo": " ".join(f"{x:02d}" for x in arr),
                     "suma": s, "score": score - penal})
    top = sorted(rows, key=lambda x: x['score'], reverse=True)[:10]
    print("\n=== Top 10 históricas por score heurístico ===\n")
    for i, row in enumerate(top, 1):
        print(f"{i:02d}) {row['fecha']}  id={row['id_sorteo']}  {row['combo']}  score={row['score']:.2f}")

def exportar_analisis(df: pd.DataFrame):
    html = html_report(analisis_completo(df))
    out = DATA_DIR / "reporte.html"
    out.write_text(html, encoding="utf-8")
    print(f"Reporte exportado en {out}")

def actualizar_cache():
    df = refresh_cache()
    print(f"Cache actualizado. Registros: {len(df)}")

# -- Opción 8: Recomendación automática (ML)
def recomendacion_ml_menu(df: pd.DataFrame):
    print("\nCalculando probabilidades bayesianas (global + reciente)...")
    posts_global = beta_binomial_posteriors(df, prior_strength=30.0, p0=(6.0/45.0))
    posts_recent = beta_binomial_posteriors_ewma(df, halflife_draws=50, prior_strength=15.0, p0=(6.0/45.0))
    probs_blend = blend_probabilities(posts_global, posts_recent, w_recent=0.30)
    save_probabilities(posts_global, posts_recent, probs_blend)

    n = _int_input_default("¿Cuántas recomendaciones quieres? [1 por defecto]: ", 1)

    stats = analisis_completo(df)
    frec = stats['frecuencias']
    cooc = stats['coocurrencias']
    temp = analisis_temporal(df)
    last50 = temp['ventanas']['50']

    pool = []
    N = max(10, n * 12)
    pool += estrategia_equilibrio_hot_cold(frec['freq_abs'], frec['hot_15'], frec['cold_15'], n_combos=N)
    pool += estrategia_temporal_inteligente(last50['freq_abs'], last50['hot_15'], n_combos=N)
    pool += estrategia_random_ponderado(frec['freq_abs'], n_combos=N // 2)
    pool += estrategia_patrones_detectados(cooc['pairs_top20'], cooc['trios_top20'], n_combos=max(5, n*6))

    # Thompson Sampling extra (con posts recientes para mayor reactividad)
    from ml import thompson_sampling_pool
    pool += thompson_sampling_pool(posts_recent, n_combos=max(10, n*10), k=6)

    if not pool:
        print("No se pudieron generar candidatas. Actualiza la base y reintenta."); return

    ranked = rankear_combos_ml(pool, probs_blend)
    topn = ranked[:n]

    print("\n=== Recomendación automática (ML) ===\n")
    for i, (combo, score) in enumerate(topn, 1):
        print(f"{i:02d})", " ".join(f"{x:02d}" for x in combo), f"   score={score:.2f}")

    record = load_json(COMBOS_FILE, default=[])
    record.append({"estrategia": "auto_ml", "n": n,
                   "ranked": [{"combo": c, "score": float(s)} for (c, s) in topn]})
    save_json(COMBOS_FILE, record)
    print(f"\nGuardado en {COMBOS_FILE}")

def main():
    print("""====================================================
   SISTEMA DE ANÁLISIS Y PREDICCIÓN — TINKA
   (Educativo/Estadístico) — by tu asesor
====================================================
AVISO: La lotería es aleatoria. Este sistema NO garantiza aciertos.
Usa la información con responsabilidad.
""" )
    df = get_data(use_cache=True)
    if len(df)==0:
        print("No hay datos en la base. Ejecuta tu scraper primero.")
        return
    while True:
        print("""Menú:
 1) Ver dashboard completo de estadísticas
 2) Análisis específico por número
 3) Generar combinaciones (elegir estrategia y cantidad)
 4) Comparar mi combinación vs estadísticas
 5) Ver mejores combinaciones históricas
 6) Exportar análisis a HTML
 7) Actualizar datos desde BD (refresh cache)
 8) Recomendación automática (ML)
 0) Salir
""" )
        op = input("Elige opción: ").strip()
        if op == "1": show_dashboard(df); pause()
        elif op == "2": analisis_por_numero(df); pause()
        elif op == "3": generar_combinaciones(df); pause()
        elif op == "4": comparar_mi_combinacion(df); pause()
        elif op == "5": ver_mejores_historicas(df); pause()
        elif op == "6": exportar_analisis(df); pause()
        elif op == "7": df = refresh_cache(); print("Datos recargados."); pause()
        elif op == "8": recomendacion_ml_menu(df); pause()
        elif op == "0": print("¡Hasta luego!"); break
        else: print("Opción inválida")

if __name__ == "__main__":
    main()
