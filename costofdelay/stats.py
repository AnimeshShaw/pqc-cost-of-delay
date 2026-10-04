"""
Statistical tools used in the evaluation.

Everything here answers a specific question a sceptical reader would ask:

  wilson_interval        How sure are we of a proportion estimated from N draws?
  bootstrap_ci           How much does a statistic move if the sample were different?
  cluster_bootstrap_*    Same, when observations come in groups (assets within systems)
  flip_effect_to_noise   Does the quantum term reorder the list MORE than input
                         noise alone would?  (a signal-to-noise test)
  sobol_indices          Which uncertain input drives the answer?  (variance-based
                         global sensitivity analysis, Saltelli/Jansen estimators)
  oat_tornado            One-at-a-time sensitivity, the simple version of the above
  mc_convergence         Has the Monte Carlo run long enough?

Conventions: every random routine takes an explicit `seed` and is reproducible.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np
from scipy import stats as sps
from scipy.stats import qmc

from costofdelay.crqc import CRQCDistribution, gri_2025_optimistic, gri_2025_pessimistic
from costofdelay.model import Asset
from costofdelay.population import quantum_leg


# ---------------------------------------------------------------------------
# Proportions and bootstrap
# ---------------------------------------------------------------------------

def wilson_interval(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    """
    Wilson score interval for a binomial proportion (Wilson, 1927).
    Better than the textbook +/- z*sqrt(p(1-p)/n) near 0 and 1, which is exactly
    where our probabilities live.
    """
    if n <= 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def bootstrap_ci(values: Sequence[float], stat: Callable[[np.ndarray], float] = np.mean,
                 n_boot: int = 10000, alpha: float = 0.05, seed: int = 1) -> tuple[float, float, float]:
    """Percentile bootstrap (Efron, 1979). Returns (estimate, lo, hi)."""
    x = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), size=(n_boot, len(x)))
    boots = np.array([stat(x[i]) for i in idx])
    return float(stat(x)), float(np.percentile(boots, 100 * alpha / 2)), float(np.percentile(boots, 100 * (1 - alpha / 2)))


def cluster_bootstrap_spearman(x: Sequence[float], y: Sequence[float], groups: Sequence[str],
                               n_boot: int = 10000, alpha: float = 0.05, seed: int = 2):
    """
    Spearman rank correlation with a CLUSTER bootstrap: whole groups (systems) are
    resampled, so the interval respects that assets within one system are not
    independent observations. Returns (rho, lo, hi, n_effective_groups).
    """
    x, y, g = np.asarray(x, float), np.asarray(y, float), np.asarray(groups)
    labels = sorted(set(g))
    members = {k: np.where(g == k)[0] for k in labels}
    rho0 = sps.spearmanr(x, y).statistic
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_boot):
        pick = rng.choice(labels, size=len(labels), replace=True)
        idx = np.concatenate([members[k] for k in pick])
        if len(set(x[idx])) < 2 or len(set(y[idx])) < 2:
            continue
        vals.append(sps.spearmanr(x[idx], y[idx]).statistic)
    vals = np.array(vals)
    return float(rho0), float(np.percentile(vals, 100 * alpha / 2)), float(np.percentile(vals, 100 * (1 - alpha / 2))), len(labels)


def permutation_pvalue_spearman(x: Sequence[float], y: Sequence[float], groups: Sequence[str],
                                n_perm: int = 20000, seed: int = 3) -> float:
    """
    Two-sided permutation p-value for Spearman's rho, permuting y WITHIN each
    system so between-system differences cannot masquerade as the effect.
    """
    x, y, g = np.asarray(x, float), np.asarray(y, float), np.asarray(groups)
    obs = abs(sps.spearmanr(x, y).statistic)
    rng = np.random.default_rng(seed)
    labels = sorted(set(g))
    members = [np.where(g == k)[0] for k in labels]
    hits = 0
    for _ in range(n_perm):
        yp = y.copy()
        for idx in members:
            yp[idx] = rng.permutation(y[idx])
        if abs(sps.spearmanr(x, yp).statistic) >= obs - 1e-12:
            hits += 1
    return (hits + 1) / (n_perm + 1)


# ---------------------------------------------------------------------------
# Shared stochastic input model (same ranges as uncertainty.py)
# ---------------------------------------------------------------------------

DEFAULT_SPREADS = dict(value_decades=0.5, lam_factor=2.0, life_factor=1.5,
                       harvest_abs=0.1, tau_factor=3.0, rho_max=0.07)


def _base_arrays(assets: Sequence[Asset]):
    V0 = np.array([a.value.usd for a in assets])
    lam0 = np.array([a.likelihood.per_year for a in assets])
    L0 = np.array([a.data_lifetime_years for a in assets])
    h0 = np.array([a.harvest_exposure.fraction for a in assets])
    vuln = np.array([a.protection.quantum_vulnerable for a in assets])
    tau0 = np.array([a.flow_rate / a.value.usd if a.value.usd > 0 else 0.0 for a in assets])
    return V0, lam0, L0, h0, vuln, tau0


def _ranks_desc(x: np.ndarray) -> np.ndarray:
    order = np.argsort(-x, axis=1, kind="stable")
    r = np.empty_like(order)
    np.put_along_axis(r, order, np.arange(1, x.shape[1] + 1)[None, :].repeat(x.shape[0], 0), axis=1)
    return r


def _discordant_pairs(r1: np.ndarray, r2: np.ndarray) -> np.ndarray:
    """Number of discordant pairs between two rank matrices (draws x assets)."""
    m = r1.shape[1]
    iu = np.triu_indices(m, 1)
    d1 = np.sign(r1[:, :, None] - r1[:, None, :])[:, iu[0], iu[1]]
    d2 = np.sign(r2[:, :, None] - r2[:, None, :])[:, iu[0], iu[1]]
    return (d1 != d2).sum(axis=1)


def _draw(rng, base, n: int, s: dict, crqc_mode: str = "mix"):
    """Draw n perturbed registers. Returns V, lam, L, h, tau, rho, use_opt."""
    V0, lam0, L0, h0, vuln, tau0 = base
    m = len(V0)
    lf = lambda f, size: np.exp(rng.uniform(-math.log(f), math.log(f), size))
    V = np.where(V0 > 0, V0 * 10 ** rng.uniform(-s["value_decades"], s["value_decades"], (n, m)), 0.0)
    lam = np.minimum(1.0, lam0 * lf(s["lam_factor"], (n, m)))
    L = np.where(L0 > 0, L0 * lf(s["life_factor"], (n, m)), 0.0)
    h = np.where(h0 > 0, np.clip(h0 + rng.uniform(-s["harvest_abs"], s["harvest_abs"], (n, m)), 0, 1), 0.0)
    tau = tau0 * lf(s["tau_factor"], (n, m))
    rho = rng.uniform(0.0, s["rho_max"], n)
    use_opt = rng.random(n) < 0.5
    return V, lam, L, h, tau, rho, use_opt


def _quantum_matrix(base, V, lam, L, h, tau, rho, use_opt):
    _, _, L0, h0, vuln, _ = base
    n, m = V.shape
    q = np.zeros((n, m))
    for opt, crqc in ((True, gri_2025_optimistic()), (False, gri_2025_pessimistic())):
        rows = np.where(use_opt == opt)[0]
        if rows.size == 0:
            continue
        for j in range(m):
            if not (vuln[j] and h0[j] > 0 and L0[j] > 0):
                continue
            q[rows, j] = quantum_leg(crqc, L[rows, j], lam[rows, j] + rho[rows],
                                     tau[rows, j] * V[rows, j] * h[rows, j])
    return q


# ---------------------------------------------------------------------------
# Signal-to-noise test for rank flips
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FlipTest:
    n_pairs: int
    signal_mean: float       # pairs reordered by ADDING the quantum term (same draw)
    noise_pair_mean: float   # pairs reordered between two independent analysts' classical rankings
    noise_base_mean: float   # pairs reordered between the central classical ranking and one analyst's
    ratio: float             # signal / noise_pair   (inter-analyst noise)
    ratio_lo: float
    ratio_hi: float
    ratio_base: float        # signal / noise_base   (analyst vs central estimate)
    ratio_base_lo: float
    ratio_base_hi: float


def flip_effect_to_noise(assets: Sequence[Asset], n: int = 4000, seed: int = 21,
                         spreads: dict | None = None, n_boot: int = 2000) -> FlipTest:
    """
    Question: when the quantum term reorders the priority list, is that a bigger
    change than the list would undergo from input uncertainty alone?

      signal_i = pairs whose order differs between the classical-only and the
                 combined ranking, computed on the SAME perturbed register i.
      noise_pair_i = pairs whose order differs between the classical-only rankings
                 of two INDEPENDENT perturbed registers (two analysts, i and i').
      noise_base_i = pairs whose order differs between the classical-only ranking
                 of the central (unperturbed) register and that of perturbed register i.

    A ratio mean(signal)/mean(noise) above 1 means the quantum term moves the list
    more than input uncertainty does; below 1, uncertainty moves it more. Bootstrap
    percentile intervals over draws are reported for both ratios.
    """
    s = {**DEFAULT_SPREADS, **(spreads or {})}
    rng = np.random.default_rng(seed)
    base = _base_arrays(assets)
    V, lam, L, h, tau, rho, use_opt = _draw(rng, base, n, s)
    V2, lam2, *_ = _draw(rng, base, n, s)
    q = _quantum_matrix(base, V, lam, L, h, tau, rho, use_opt)
    classical, classical2 = lam * V, lam2 * V2
    r_c, r_u, r_c2 = _ranks_desc(classical), _ranks_desc(classical + q), _ranks_desc(classical2)
    V0, lam0 = base[0], base[1]
    r_base = _ranks_desc((lam0 * V0)[None, :].repeat(n, 0))
    signal = _discordant_pairs(r_c, r_u).astype(float)
    noise_pair = _discordant_pairs(r_c, r_c2).astype(float)
    noise_base = _discordant_pairs(r_base, r_c).astype(float)
    m = len(assets)
    boot = np.random.default_rng(seed + 1)
    idx = boot.integers(0, n, size=(n_boot, n))
    sig_b = signal[idx].mean(axis=1)
    ratios = sig_b / np.maximum(noise_pair[idx].mean(axis=1), 1e-12)
    ratios_b = sig_b / np.maximum(noise_base[idx].mean(axis=1), 1e-12)
    return FlipTest(m * (m - 1) // 2, float(signal.mean()), float(noise_pair.mean()), float(noise_base.mean()),
                    float(signal.mean() / max(noise_pair.mean(), 1e-12)),
                    float(np.percentile(ratios, 2.5)), float(np.percentile(ratios, 97.5)),
                    float(signal.mean() / max(noise_base.mean(), 1e-12)),
                    float(np.percentile(ratios_b, 2.5)), float(np.percentile(ratios_b, 97.5)))


def tau_distribution(assets: Sequence[Asset], n: int = 4000, seed: int = 41,
                     spreads: dict | None = None) -> dict:
    """
    Distribution, over perturbed registers, of Kendall's tau between the
    classical-only and the combined ranking (1 = identical order).
    tau = 1 - 2 D / P  with D discordant pairs and P all pairs.
    """
    s = {**DEFAULT_SPREADS, **(spreads or {})}
    rng = np.random.default_rng(seed)
    base = _base_arrays(assets)
    V, lam, L, h, tau, rho, use_opt = _draw(rng, base, n, s)
    q = _quantum_matrix(base, V, lam, L, h, tau, rho, use_opt)
    m = len(assets)
    P = m * (m - 1) / 2
    D = _discordant_pairs(_ranks_desc(lam * V), _ranks_desc(lam * V + q))
    t = 1.0 - 2.0 * D / P
    return dict(median=float(np.median(t)), lo=float(np.percentile(t, 5)), hi=float(np.percentile(t, 95)),
                mean=float(t.mean()), p_identical=float((D == 0).mean()))


# ---------------------------------------------------------------------------
# Global sensitivity analysis (Sobol indices)
# ---------------------------------------------------------------------------

INPUT_NAMES = ["loss V", "hazard lambda", "lifetime L", "recordable share h",
               "turnover tau", "discount rho", "CRQC median year"]


def _sobol_model(asset: Asset, X: np.ndarray, s: dict) -> np.ndarray:
    """
    Output Y = log10 of the asset's quantum cost of delay, as a function of 7
    inputs mapped from the unit hypercube X in [0,1]^7. CRQC arrival is
    parameterised by its median year (2031-2046) with the optimistic-fit shape.
    """
    V0, lam0, L0, h0 = asset.value.usd, asset.likelihood.per_year, asset.data_lifetime_years, asset.harvest_exposure.fraction
    tau0 = asset.flow_rate / V0 if V0 > 0 else 0.0
    n = X.shape[0]
    V = V0 * 10 ** ((2 * X[:, 0] - 1) * s["value_decades"])
    lam = np.minimum(1.0, lam0 * np.exp((2 * X[:, 1] - 1) * math.log(s["lam_factor"])))
    L = L0 * np.exp((2 * X[:, 2] - 1) * math.log(s["life_factor"]))
    h = np.clip(h0 + (2 * X[:, 3] - 1) * s["harvest_abs"], 0, 1) if h0 > 0 else np.zeros(n)
    tau = tau0 * np.exp((2 * X[:, 4] - 1) * math.log(s["tau_factor"]))
    rho = X[:, 5] * s["rho_max"]
    median_year = 2031 + 15 * X[:, 6]
    beta = gri_2025_optimistic().beta
    out = np.zeros(n)
    if not asset.quantum_applicable:
        return out
    # evaluate row-by-row groups of identical CRQC would be slow; vectorise over a CRQC per row
    alpha = (median_year - 2026) / (math.log(2.0) ** (1.0 / beta))
    kappa = lam + rho
    grid = np.linspace(0.0, 1.0, 601)[None, :] * L[:, None]
    F = 1.0 - np.exp(-((np.maximum(grid, 0) / alpha[:, None]) ** beta))
    vals = F * np.exp(-kappa[:, None] * grid)
    w = np.ones(601); w[1:-1:2] = 4.0; w[2:-1:2] = 2.0
    simpson = (L / 600.0 / 3.0) * (vals * w[None, :]).sum(axis=1)
    FL = 1.0 - np.exp(-((L / alpha) ** beta))
    q = (tau * V * h) * (np.exp(-kappa * L) * FL + kappa * simpson)
    return np.log10(np.maximum(q, 1e-12))


def sobol_indices(asset: Asset, n_base: int = 4096, seed: int = 5, spreads: dict | None = None,
                  n_boot: int = 300):
    """
    First-order (S_i) and total-order (ST_i) Sobol indices of the log quantum
    cost of delay with respect to the seven uncertain inputs, using Saltelli's
    (2010) sampling design and Jansen's (1999) estimators on a scrambled Sobol'
    sequence. Bootstrap percentile intervals for each index.

    S_i  : share of output variance explained by input i alone.
    ST_i : share explained by input i including all its interactions.
    ST_i - S_i  is the part due to interactions.
    """
    s = {**DEFAULT_SPREADS, **(spreads or {})}
    d = len(INPUT_NAMES)
    sob = qmc.Sobol(d=2 * d, scramble=True, seed=seed)
    AB = sob.random(n_base)
    A, B = AB[:, :d], AB[:, d:]
    fA, fB = _sobol_model(asset, A, s), _sobol_model(asset, B, s)
    fAB = []
    for i in range(d):
        ABi = A.copy(); ABi[:, i] = B[:, i]
        fAB.append(_sobol_model(asset, ABi, s))
    fAB = np.array(fAB)                                 # (d, n)

    def estimate(idx):
        a, b, ab = fA[idx], fB[idx], fAB[:, idx]
        var = np.var(np.concatenate([a, b]), ddof=1)
        if var < 1e-15:
            return np.zeros(d), np.zeros(d)
        S = 1.0 - np.mean((b[None, :] - ab) ** 2, axis=1) / (2 * var)      # Jansen first-order
        ST = np.mean((a[None, :] - ab) ** 2, axis=1) / (2 * var)           # Jansen total
        return S, ST

    S, ST = estimate(np.arange(n_base))
    rng = np.random.default_rng(seed + 7)
    bs, bt = [], []
    for _ in range(n_boot):
        S_b, ST_b = estimate(rng.integers(0, n_base, n_base))
        bs.append(S_b); bt.append(ST_b)
    bs, bt = np.array(bs), np.array(bt)
    return dict(names=INPUT_NAMES, S=S, ST=ST,
                S_lo=np.percentile(bs, 2.5, axis=0), S_hi=np.percentile(bs, 97.5, axis=0),
                ST_lo=np.percentile(bt, 2.5, axis=0), ST_hi=np.percentile(bt, 97.5, axis=0),
                var=float(np.var(np.concatenate([fA, fB]), ddof=1)))


def oat_tornado(asset: Asset, spreads: dict | None = None) -> list[dict]:
    """
    One-at-a-time sensitivity: move each input to the low and high end of its
    range with all others at their central value; report log10 quantum cost of
    delay. The swing (high - low) ranks inputs by simple influence.
    """
    s = {**DEFAULT_SPREADS, **(spreads or {})}
    mid = np.full((1, 7), 0.5)
    base = float(_sobol_model(asset, mid, s)[0])
    rows = []
    for i, name in enumerate(INPUT_NAMES):
        lo_x, hi_x = mid.copy(), mid.copy()
        lo_x[0, i], hi_x[0, i] = 0.0, 1.0
        lo, hi = float(_sobol_model(asset, lo_x, s)[0]), float(_sobol_model(asset, hi_x, s)[0])
        rows.append(dict(name=name, low=lo, high=hi, swing=abs(hi - lo), base=base))
    return sorted(rows, key=lambda r: -r["swing"])


# ---------------------------------------------------------------------------
# Monte Carlo convergence
# ---------------------------------------------------------------------------

def mc_convergence(assets: Sequence[Asset], asset_id: str, sizes: Sequence[int] = (250, 500, 1000, 2000, 4000, 8000, 16000),
                   seed: int = 31, spreads: dict | None = None):
    """
    How the estimate of P(asset is quantum-dominant) and its Wilson interval
    behave as the number of Monte Carlo draws grows. Returns a list of dicts.
    """
    s = {**DEFAULT_SPREADS, **(spreads or {})}
    j = [a.asset_id for a in assets].index(asset_id)
    rng = np.random.default_rng(seed)
    base = _base_arrays(assets)
    nmax = max(sizes)
    V, lam, L, h, tau, rho, use_opt = _draw(rng, base, nmax, s)
    q = _quantum_matrix(base, V, lam, L, h, tau, rho, use_opt)
    dom = (q[:, j] > (lam * V)[:, j])
    out = []
    for n in sizes:
        k = int(dom[:n].sum())
        lo, hi = wilson_interval(k, n)
        out.append(dict(n=n, p=k / n, lo=lo, hi=hi, half_width=(hi - lo) / 2))
    return out
