"""Visualizaciones básicas: ASCII y PNG/HTML."""
from __future__ import annotations
from typing import Dict
import base64
from io import BytesIO
import matplotlib.pyplot as plt
from utils import ascii_bar

def render_ascii_hist(freq_abs: Dict[int,int]) -> str:
    maxv = max(freq_abs.values()) if freq_abs else 0
    lines = []
    for n, v in sorted(freq_abs.items()):
        lines.append(ascii_bar(f"{n:02d}", v, maxv, width=34))
    return "\n".join(lines)

def plot_freq_png(freq_abs: Dict[int,int]) -> bytes:
    xs = list(sorted(freq_abs.keys()))
    ys = [freq_abs[k] for k in xs]
    fig, ax = plt.subplots(figsize=(10,4))
    ax.bar(xs, ys)
    ax.set_title("Frecuencia absoluta de números (1-45)")
    ax.set_xlabel("Número")
    ax.set_ylabel("Frecuencia")
    buf = BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    return buf.getvalue()

def html_report(stats: Dict) -> str:
    png = plot_freq_png(stats['frecuencias']['freq_abs'])
    b64 = base64.b64encode(png).decode("ascii")
    chi2 = stats['chi_cuadrado']
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8"/>
<title>Reporte Tinka</title>
<style>
body {{ font-family: Arial, Helvetica, sans-serif; margin: 20px; }}
h1, h2 {{ margin: 0.4em 0; }}
pre {{ background: #f6f8fa; padding: 12px; overflow: auto; }}
.small {{ color:#555; font-size: 0.9em; }}
</style>
</head>
<body>
<h1>Reporte de Análisis — Tinka</h1>
<p class="small">Este reporte se genera a partir de los resultados históricos presentes en tu base de datos.</p>

<h2>Frecuencias</h2>
<img src="data:image/png;base64,{b64}" alt="Frecuencias"/>
<pre>{render_ascii_hist(stats['frecuencias']['freq_abs'])}</pre>

<h2>Chi-cuadrado</h2>
<p>Chi2 = {chi2.get('chi2')} &nbsp;&nbsp; p-value = {chi2.get('p_value')}</p>
<p class="small">Si p-value es muy pequeño (&lt; 0.05), indica desviación respecto a uniformidad; recuerda que los sorteos son procesos aleatorios.</p>

<h2>Disclaimer</h2>
<p class="small">Este sistema es informativo y educativo. La lotería es aleatoria. Juega con responsabilidad.</p>
</body>
</html>
"""
    return html
