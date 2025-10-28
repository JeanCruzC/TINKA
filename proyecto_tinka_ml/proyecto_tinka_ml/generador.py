"""Generación y evaluación de combinaciones a partir de las estadísticas."""
from __future__ import annotations
from typing import List, Dict, Tuple
import random
import numpy as np

from config import TOTAL_NUMBERS, COMBINATION_SIZE, SUM_RANGE

def _validate_combo(combo: List[int]) -> bool:
    if len(combo) != COMBINATION_SIZE: return False
    if len(set(combo)) != COMBINATION_SIZE: return False
    if not all(1 <= x <= TOTAL_NUMBERS for x in combo): return False
    return True

def _meets_heuristics(combo: List[int]) -> bool:
    s = sum(combo)
    if not (SUM_RANGE[0] <= s <= SUM_RANGE[1]):
        return False
    ev = sum(1 for x in combo if x % 2 == 0)
    od = COMBINATION_SIZE - ev
    if abs(ev - od) > 2:
        return False
    return True

def _weighted_choice(population: List[int], weights: List[float], k: int) -> List[int]:
    arr = np.array(population)
    w = np.array(weights, dtype=float)
    if w.sum() <= 0:
        w = np.ones_like(w) / len(w)
    else:
        w = w / w.sum()
    picks = set()
    for _ in range(2000):
        x = np.random.choice(arr, p=w)
        picks.add(int(x))
        if len(picks) == k:
            break
    if len(picks) < k:
        rest = [p for p in population if p not in picks]
        random.shuffle(rest)
        picks.update(rest[:(k-len(picks))])
    return sorted(picks)

def _rango_bucket(n: int) -> int:
    if   1 <= n <= 9:   return 0
    elif 10 <= n <= 18: return 1
    elif 19 <= n <= 27: return 2
    elif 28 <= n <= 36: return 3
    elif 37 <= n <= 45: return 4
    return 4

def _consecutivos(combo: List[int]) -> int:
    arr = sorted(combo)
    return sum(1 for a, b in zip(arr, arr[1:]) if b == a + 1)

# Estrategias clásicas
def estrategia_frecuencia_pura(freq_abs: Dict[int,int], n_combos: int = 10) -> List[List[int]]:
    top = sorted(freq_abs.items(), key=lambda x: (-x[1], x[0]))
    top_pool = [k for k,_ in top[:min(25, len(top))]]
    combos, tries = [], 0
    while len(combos) < n_combos and tries < 8000:
        c = sorted(random.sample(top_pool, COMBINATION_SIZE))
        if _validate_combo(c) and _meets_heuristics(c) and c not in combos:
            combos.append(c)
        tries += 1
    return combos

def estrategia_equilibrio_hot_cold(freq_abs: Dict[int,int], hot_15: List[int], cold_15: List[int], n_combos: int = 10) -> List[List[int]]:
    combos, tries = [], 0
    pool_cold = cold_15[:]
    pool_hot  = hot_15[:]
    if len(pool_hot) < 3 or len(pool_cold) < 3:
        return estrategia_frecuencia_pura(freq_abs, n_combos)
    while len(combos) < n_combos and tries < 8000:
        c = sorted(random.sample(pool_hot, 3) + random.sample(pool_cold, 3))
        if _validate_combo(c) and _meets_heuristics(c) and c not in combos:
            combos.append(c)
        tries += 1
    return combos

def estrategia_temporal_inteligente(freq_last: Dict[int,int], hot_cycle: List[int], n_combos: int = 10) -> List[List[int]]:
    keys = list(range(1, TOTAL_NUMBERS+1))
    weights = [freq_last.get(k, 0) + (1.5 if k in hot_cycle else 0.0) + 0.01 for k in keys]
    combos, tries = [], 0
    while len(combos) < n_combos and tries < 10000:
        c = _weighted_choice(keys, weights, COMBINATION_SIZE)
        c = sorted(c)
        if _validate_combo(c) and _meets_heuristics(c) and c not in combos:
            combos.append(c)
        tries += 1
    return combos

def estrategia_patrones_detectados(pairs_top: List[Dict], trios_top: List[Dict], n_combos: int = 10) -> List[List[int]]:
    combos, tries = [], 0
    pairs = [tuple(p['pair']) for p in pairs_top]
    trios = [tuple(t['trio']) for t in trios_top]
    while len(combos) < n_combos and tries < 12000:
        base = set()
        if trios and random.random() < 0.6:
            base.update(random.choice(trios))
        guard = 0
        while len(base) < 4 and pairs and guard < 10:
            cand = random.choice(pairs)
            if not (set(cand) & base):
                base.update(cand)
            guard += 1
        rest = [x for x in range(1, TOTAL_NUMBERS+1) if x not in base]
        random.shuffle(rest)
        while len(base) < 6 and rest:
            base.add(rest.pop())
        c = sorted(list(base))[:6]
        if _validate_combo(c) and _meets_heuristics(c) and c not in combos:
            combos.append(c)
        tries += 1
    return combos

def estrategia_random_ponderado(freq_abs: Dict[int,int], n_combos: int = 10) -> List[List[int]]:
    keys = list(range(1, TOTAL_NUMBERS+1))
    raw = [freq_abs.get(k, 0) + 0.01 for k in keys]
    combos, tries = [], 0
    while len(combos) < n_combos and tries < 8000:
        c = _weighted_choice(keys, raw, COMBINATION_SIZE)
        c = sorted(c)
        if _validate_combo(c) and _meets_heuristics(c) and c not in combos:
            combos.append(c)
        tries += 1
    return combos

# Scoring ML
def score_combo_ml(combo: List[int], probs: Dict[int, float]) -> float:
    eps = 1e-9
    ll = sum(np.log(max(probs.get(x, eps), eps)) for x in combo) * 10.0
    suma = sum(combo)
    penalty_sum = abs(135 - suma) * 1.0
    ev = sum(1 for x in combo if x % 2 == 0)
    od = COMBINATION_SIZE - ev
    penalty_parity = abs(ev - od) * 2.0
    consec = _consecutivos(combo)
    penalty_consec = max(0, consec - 1) * 3.0
    buckets = [0,0,0,0,0]
    for x in combo:
        if   1 <= x <= 9:   buckets[0]+=1
        elif 10 <= x <= 18: buckets[1]+=1
        elif 19 <= x <= 27: buckets[2]+=1
        elif 28 <= x <= 36: buckets[3]+=1
        elif 37 <= x <= 45: buckets[4]+=1
    cobertura = sum(1 for b in buckets if b > 0)
    penalty_bucket = 0.0
    if max(buckets) > 3:
        penalty_bucket += (max(buckets) - 3) * 2.0
    if cobertura < 3:
        penalty_bucket += (3 - cobertura) * 2.0
    return float(ll - penalty_sum - penalty_parity - penalty_consec - penalty_bucket)

def rankear_combos_ml(combos: List[List[int]], probs: Dict[int, float]):
    scored = []
    seen = set()
    for c in combos:
        t = tuple(sorted(c))
        if t in seen: 
            continue
        seen.add(t)
        scored.append((list(t), score_combo_ml(list(t), probs)))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored
