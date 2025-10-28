"""ML ligero: Beta-Binomial, EWMA y Thompson Sampling."""
from __future__ import annotations
from typing import Dict, List, Tuple
from collections import defaultdict
import numpy as np
import pandas as pd
from config import DATA_DIR
from utils import parse_numbers, save_json, load_json

PROBS_FILE = DATA_DIR / "probabilidades.json"

def _counts_from_df(df: pd.DataFrame) -> Dict[int, int]:
    cnt = defaultdict(int)
    for _, r in df.iterrows():
        for n in parse_numbers(r['numeros']):
            cnt[int(n)] += 1
    return dict(cnt)

def _counts_ewma(df: pd.DataFrame, halflife_draws: int = 50) -> Dict[int, float]:
    if len(df) == 0:
        return {i: 0.0 for i in range(1, 46)}
    gamma = 0.5 ** (1.0 / max(1, halflife_draws))
    w = 1.0
    cnt = {i: 0.0 for i in range(1, 46)}
    total_weight = 0.0
    for _, r in df.iloc[::-1].iterrows():
        nums = set(parse_numbers(r['numeros']))
        for i in range(1, 46):
            if i in nums:
                cnt[i] += w
        total_weight += w
        w *= gamma
    cnt['__total_weight__'] = total_weight
    return cnt

def beta_binomial_posteriors(df: pd.DataFrame, prior_strength: float = 30.0, p0: float = 6.0/45.0):
    s = _counts_from_df(df)
    D = float(len(df))
    a0 = prior_strength * p0
    b0 = prior_strength * (1.0 - p0)
    posts = {}
    for i in range(1, 46):
        successes = float(s.get(i, 0))
        failures = max(0.0, D - successes)
        alpha = a0 + successes
        beta  = b0 + failures
        posts[i] = {"alpha": alpha, "beta": beta, "p": alpha/(alpha+beta)}
    return posts

def beta_binomial_posteriors_ewma(df: pd.DataFrame, halflife_draws: int = 50, prior_strength: float = 15.0, p0: float = 6.0/45.0):
    ew = _counts_ewma(df, halflife_draws=halflife_draws)
    total_w = float(ew.get('__total_weight__', 0.0))
    a0 = prior_strength * p0
    b0 = prior_strength * (1.0 - p0)
    posts = {}
    for i in range(1, 46):
        successes = float(ew.get(i, 0.0))
        failures = max(0.0, total_w - successes)
        alpha = a0 + successes
        beta  = b0 + failures
        posts[i] = {"alpha": alpha, "beta": beta, "p": alpha/(alpha+beta)}
    return posts

def blend_probabilities(global_posts, recent_posts, w_recent: float = 0.30):
    w_recent = max(0.0, min(1.0, w_recent))
    out = {}
    for i in range(1, 46):
        pg = float(global_posts[i]["p"])
        pr = float(recent_posts[i]["p"])
        out[i] = (1.0 - w_recent) * pg + w_recent * pr
    return out

def save_probabilities(probs_global, probs_recent, probs_blend):
    data = {"global": probs_global, "recent": probs_recent, "blend": probs_blend}
    save_json(PROBS_FILE, data)

def load_probabilities():
    return load_json(PROBS_FILE, default=None)

def thompson_sampling_combination(posts, k: int = 6):
    draws = []
    for i in range(1, 46):
        a = float(posts[i]['alpha']); b = float(posts[i]['beta'])
        a = max(a, 1e-3); b = max(b, 1e-3)
        theta = np.random.beta(a, b)
        draws.append((i, float(theta)))
    draws.sort(key=lambda x: x[1], reverse=True)
    return sorted([i for (i, t) in draws[:k]])

def thompson_sampling_pool(posts, n_combos: int = 10, k: int = 6):
    combos = []
    seen = set()
    tries = 0
    while len(combos) < n_combos and tries < n_combos * 200:
        c = tuple(thompson_sampling_combination(posts, k=k))
        if c not in seen:
            combos.append(list(c))
            seen.add(c)
        tries += 1
    return combos
