"""Lógica de análisis estadístico para Tinka/Boliyapa."""
from __future__ import annotations
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
from itertools import combinations
from collections import Counter
from config import TOTAL_NUMBERS, COMBINATION_SIZE, LAST_N_WINDOWS, SUM_RANGE
from utils import parse_numbers, is_prime

def _explode_numeros(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in df.iterrows():
        nums = parse_numbers(r['numeros'])
        for n in nums:
            rows.append({'id_sorteo': r['id_sorteo'], 'fecha_sorteo': r['fecha_sorteo'], 'numero': n})
    return pd.DataFrame(rows, columns=['id_sorteo','fecha_sorteo','numero'])

def _coocurrencias(df: pd.DataFrame, k: int = 2):
    cnt = Counter()
    for _, r in df.iterrows():
        arr = sorted(parse_numbers(r['numeros']))
        for combo in combinations(arr, k):
            cnt[combo] += 1
    return cnt

def _ultimos(df: pd.DataFrame, n: int):
    return df.tail(n) if len(df) >= n else df.copy()

def analisis_frecuencias(df: pd.DataFrame) -> Dict:
    exploded = _explode_numeros(df)
    freq_abs = Counter(exploded['numero'].tolist())
    for k in range(1, TOTAL_NUMBERS+1):
        freq_abs.setdefault(k, 0)
    total_bolas = len(exploded)
    freq_rel = {k: (v/total_bolas if total_bolas else 0.0) for k, v in freq_abs.items()}
    top = sorted(freq_abs.items(), key=lambda x: (-x[1], x[0]))
    hot = [k for k,_ in top[:15]]
    cold = [k for k,_ in sorted(freq_abs.items(), key=lambda x: (x[1], x[0]))[:15]]
    ult10 = set(_explode_numeros(_ultimos(df, 10))['numero'].tolist())
    # dormidos: no aparecen hace >20 sorteos
    last_seen_idx = {}
    for idx, r in enumerate(df.itertuples(index=False), start=1):
        for n in parse_numbers(r.numeros):
            last_seen_idx[n] = idx
    dormidos = []
    threshold = max(1, len(df) - 20)
    for n in range(1, TOTAL_NUMBERS+1):
        if last_seen_idx.get(n, 0) < threshold:
            dormidos.append(n)
    return {'freq_abs': dict(sorted(freq_abs.items())),
            'freq_rel': dict(sorted(freq_rel.items())),
            'hot_15': hot,
            'cold_15': cold,
            'en_racha_ult10': sorted(ult10),
            'dormidos_mas20': sorted(dormidos)}

def analisis_temporal(df: pd.DataFrame) -> Dict:
    exploded = _explode_numeros(df)
    tmp = exploded.copy()
    tmp['fecha_sorteo'] = pd.to_datetime(tmp['fecha_sorteo'])
    tmp['anio'] = tmp['fecha_sorteo'].dt.year
    tmp['mes'] = tmp['fecha_sorteo'].dt.month
    by_mes = tmp.groupby(['anio','mes','numero']).size().reset_index(name='freq')
    gaps = {}
    for n in range(1, TOTAL_NUMBERS+1):
        apar = tmp.loc[tmp['numero']==n, 'fecha_sorteo'].sort_values().tolist()
        if len(apar) >= 2:
            difs = [(apar[i]-apar[i-1]).days for i in range(1, len(apar))]
            gaps[n] = float(np.mean(difs))
        else:
            gaps[n] = None
    ventanas = {}
    for win in LAST_N_WINDOWS:
        sub = _ultimos(df, win)
        ventanas[str(win)] = analisis_frecuencias(sub)
    return {'por_mes': by_mes.to_dict(orient='records'), 'gaps_prom_dias': gaps, 'ventanas': ventanas}

def analisis_patrones(df: pd.DataFrame) -> Dict:
    even, odd = 0, 0
    ranges = {'1-9':0,'10-18':0,'19-27':0,'28-36':0,'37-45':0}
    suma_vals = []
    consecutivos = 0
    distancias = []
    primos_cnt = 0
    total_combinaciones = 0
    for _, r in df.iterrows():
        arr = sorted(parse_numbers(r['numeros']))
        total_combinaciones += 1
        suma_vals.append(sum(arr))
        for x in arr:
            if x % 2 == 0: even += 1
            else: odd += 1
            if 1 <= x <= 9: ranges['1-9'] += 1
            elif 10 <= x <= 18: ranges['10-18'] += 1
            elif 19 <= x <= 27: ranges['19-27'] += 1
            elif 28 <= x <= 36: ranges['28-36'] += 1
            elif 37 <= x <= 45: ranges['37-45'] += 1
            if is_prime(x): primos_cnt += 1
        consecutivos += sum(1 for a,b in zip(arr, arr[1:]) if b==a+1)
        distancias += [abs(b-a) for a,b in zip(arr, arr[1:])]
    return {'pares': even, 'impares': odd, 'rangos': ranges,
            'suma_min': int(min(suma_vals)) if suma_vals else None,
            'suma_max': int(max(suma_vals)) if suma_vals else None,
            'suma_prom': float(np.mean(suma_vals)) if suma_vals else None,
            'consecutivos_total': int(consecutivos),
            'dist_prom': float(np.mean(distancias)) if distancias else None,
            'primos_total': int(primos_cnt),
            'total_combinaciones': total_combinaciones}

def analisis_coocurrencias(df: pd.DataFrame) -> Dict:
    pairs = _coocurrencias(df, k=2)
    trios = _coocurrencias(df, k=3)
    top_pairs = pairs.most_common(20)
    top_trios = trios.most_common(20)
    return {'pairs_top20': [{'pair': list(k), 'freq': v} for k,v in top_pairs],
            'trios_top20': [{'trio': list(k), 'freq': v} for k,v in top_trios]}

def analisis_boliyapa(df: pd.DataFrame) -> Dict:
    bol = df['boliyapa'].dropna().astype(int).tolist()
    cnt = Counter(bol)
    total = len(bol)
    freq_rel = {k: (v/total if total else 0.0) for k,v in cnt.items()}
    return {'freq_abs': dict(sorted(cnt.items())),
            'freq_rel': dict(sorted(freq_rel.items()))}

def analisis_chicuadrado(df: pd.DataFrame) -> Dict:
    exploded = []
    for _, r in df.iterrows():
        exploded += parse_numbers(r['numeros'])
    from collections import Counter
    cnt = Counter(exploded)
    import numpy as np
    obs = np.array([cnt.get(i, 0) for i in range(1, TOTAL_NUMBERS+1)], dtype=float)
    n = obs.sum()
    if n == 0:
        return {'chi2': None, 'p_value': None, 'expected': None}
    expected = np.ones_like(obs) * (n / TOTAL_NUMBERS)
    chi2 = ((obs - expected)**2 / expected).sum()
    p_value = None
    try:
        from scipy.stats import chi2 as chi2_dist
        dfree = TOTAL_NUMBERS - 1
        p_value = float(1 - chi2_dist.cdf(chi2, dfree))
    except Exception:
        p_value = None
    std_dev = float(np.std(obs))
    return {'chi2': float(chi2), 'p_value': p_value, 'std_freq': std_dev, 'expected_each': float(n / TOTAL_NUMBERS)}

def analisis_completo(df: pd.DataFrame) -> Dict:
    return {'frecuencias': analisis_frecuencias(df),
            'temporal': analisis_temporal(df),
            'patrones': analisis_patrones(df),
            'coocurrencias': analisis_coocurrencias(df),
            'boliyapa': analisis_boliyapa(df),
            'chi_cuadrado': analisis_chicuadrado(df)}
