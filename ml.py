"""Failure-risk model: one tool the harness calls. Trains in ~1s on synthetic data."""
from functools import cache

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from data import FEATURES


def label(df):
    out = np.full(len(df), "none", dtype=object)
    out[(df.load_pct > 100) & (df.spindle_rpm > 15000)] = "overload"
    out[(df.yarn_tension_cn < 15) | (df.yarn_tension_cn > 35)] = "tension_fault"
    out[(df.motor_temp_c > 85) | ((df.motor_temp_c > 78) & (df.load_pct > 95))] = "motor_overheat"
    out[(df.vibration_mm_s > 7) | ((df.vibration_mm_s > 5) & (df.hours_since_service > 900))] = "bearing_wear"
    return out


@cache
def model():
    # ponytail: synthetic data, rules define labels; swap in real mill logs when available
    rng = np.random.default_rng(0)
    n = 6000
    df = pd.DataFrame({
        "spindle_rpm": rng.uniform(8000, 18000, n),
        "vibration_mm_s": rng.gamma(4, 1.1, n),
        "motor_temp_c": rng.normal(65, 12, n),
        "yarn_tension_cn": rng.normal(25, 6, n),
        "load_pct": rng.normal(75, 15, n),
        "hours_since_service": rng.uniform(0, 1500, n),
    })
    y = label(df)
    noisy = df + rng.normal(0, 0.03, df.shape) * df.std().values  # sensor noise on what the model sees
    return RandomForestClassifier(200, random_state=0).fit(noisy[FEATURES], y)


def risk(readings):
    """-> (failure risk 0..1, most likely fault)."""
    m = model()
    p = pd.Series(m.predict_proba(pd.DataFrame([readings])[FEATURES])[0], index=m.classes_)
    return float(1 - p.get("none", 0)), p.drop("none").idxmax()
