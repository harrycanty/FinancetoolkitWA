# core_dcf.py
import numpy as np


# Discounts an array of cashflows
def discount(values: np.ndarray, r: np.ndarray) -> np.ndarray:
    t = values.shape[1]
    disc = (1 + r[:, None]) ** np.arange(1, t + 1)[None, :]
    return values / disc

# Runs MC sim for 5 years
def run_dcf_vectorized(
    last_fcf_bil: float,
    n: int,
    wacc_mean: float, wacc_std: float,
    tg_mean: float, tg_std: float,
    growth_mean: float, growth_std: float,
    seed: int | None = None,
) -> dict:
    if seed is not None:
        np.random.seed(seed)

    # Simulate WACC, tg and yearly growth rate
    w = np.clip(np.random.normal(wacc_mean, wacc_std, size=n), 0.01, 0.25)
    tg = np.clip(np.random.normal(tg_mean, tg_std, size=n), 0.0, 0.10)
    g = np.clip(np.random.normal(growth_mean, growth_std, size=(n, 5)), -0.9, 0.5)

    # Project 5 years of growth
    fcf = np.empty((n, 5), dtype=float)
    fcf[:, 0] = last_fcf_bil * (1 + g[:, 0])
    for t in range(1, 5):
        fcf[:, t] = fcf[:, t - 1] * (1 + g[:, t])

    # TV (only valid if WACC is greater than tg)
    valid = w > tg
    tv = np.where(valid, fcf[:, -1] * (1 + tg) / (w - tg), np.nan)

    # Discount cash flows and tg
    d_fcf = discount(fcf, w)
    d_tv = tv / ((1 + w) ** 5)

    # EV = PV of fcf and pv of tv
    ev = np.nansum(d_fcf, axis=1) + d_tv
    return {"fcf": fcf, "disc_fcf": d_fcf, "tv_disc": d_tv, "ev": ev, "w": w, "tg": tg}