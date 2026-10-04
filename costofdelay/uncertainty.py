"""
Which conclusions survive when the inputs are uncertain?

Every input in a register is an ordinal band, not a measurement. Instead of
trusting one point estimate, we re-draw every asset's inputs many times within
stated ranges and ask how often each conclusion still holds:

  * how often is each asset in the funded top-k?
  * what range of ranks can it take (5th-95th percentile)?
  * how often is it quantum-dominant (quantum cost of delay > classical)?
  * how often does the unified order differ from the classical-only order?

Spreads (all [ASSUMED], stated so they can be argued with):

  value V      : log-uniform within +/- half a band (a band is 10x wide)
  hazard lam   : multiplied by a log-uniform factor in [1/2, 2], capped at 1
  lifetime L   : multiplied by a log-uniform factor in [1/1.5, 1.5]
  harvest h    : +/- 0.1, clipped to [0,1] (an evidenced zero stays zero)
  turnover tau : multiplied by a log-uniform factor in [1/3, 3]  (weakest input)
  CRQC         : GRI pessimistic or optimistic with equal probability
  discount rho : uniform on [0, 0.07]

Gated terms stay gated: a non-vulnerable protection class, h = 0 or L = 0 keeps
the quantum leg at exactly zero in every draw.
"""

from __future__ import annotations

import math

import numpy as np

from costofdelay.crqc import gri_2025_optimistic, gri_2025_pessimistic
from costofdelay.model import Asset
from costofdelay.population import quantum_leg

SPREADS = dict(value_decades=0.5, lam_factor=2.0, life_factor=1.5,
               harvest_abs=0.1, tau_factor=3.0, rho_max=0.07)


def _logu(rng, factor: float, size) -> np.ndarray:
    """Multiplicative factor, log-uniform in [1/factor, factor]."""
    return np.exp(rng.uniform(-math.log(factor), math.log(factor), size))


def simulate(assets: list[Asset], n: int = 4000, seed: int = 11,
             spreads: dict | None = None, top_frac: float = 0.25):
    s = {**SPREADS, **(spreads or {})}
    rng = np.random.default_rng(seed)
    m = len(assets)

    V0 = np.array([a.value.usd for a in assets])
    lam0 = np.array([a.likelihood.per_year for a in assets])
    L0 = np.array([a.data_lifetime_years for a in assets])
    h0 = np.array([a.harvest_exposure.fraction for a in assets])
    vuln = np.array([a.protection.quantum_vulnerable for a in assets])
    tau0 = np.array([a.flow_rate / a.value.usd if a.value.usd > 0 else 0.0
                     for a in assets])

    V = V0 * 10 ** rng.uniform(-s["value_decades"], s["value_decades"], (n, m))
    V = np.where(V0 > 0, V, 0.0)                               # NEGLIGIBLE stays 0
    lam = np.minimum(1.0, lam0 * _logu(rng, s["lam_factor"], (n, m)))
    L = np.where(L0 > 0, L0 * _logu(rng, s["life_factor"], (n, m)), 0.0)
    h = np.where(h0 > 0, np.clip(h0 + rng.uniform(-s["harvest_abs"], s["harvest_abs"], (n, m)), 0, 1), 0.0)
    tau = tau0 * _logu(rng, s["tau_factor"], (n, m))
    rho = rng.uniform(0.0, s["rho_max"], n)
    use_opt = rng.random(n) < 0.5

    classical = lam * V
    quantum = np.zeros((n, m))
    for opt, crqc in ((True, gri_2025_optimistic()), (False, gri_2025_pessimistic())):
        rows = np.where(use_opt == opt)[0]
        for j in range(m):
            if not (vuln[j] and h0[j] > 0 and L0[j] > 0):
                continue
            scale = tau[rows, j] * V[rows, j] * h[rows, j]
            # discounting at rho is algebraically adding rho to the hazard
            quantum[rows, j] = quantum_leg(crqc, L[rows, j], lam[rows, j] + rho[rows],
                                           scale)
    total = classical + quantum

    # ranks, 1 = highest priority (stable on ties)
    def ranks(x):
        order = np.argsort(-x, axis=1, kind="stable")
        r = np.empty_like(order)
        np.put_along_axis(r, order, np.arange(1, m + 1)[None, :].repeat(n, 0), axis=1)
        return r

    rk_u, rk_c = ranks(total), ranks(classical)
    k = max(1, round(top_frac * m))
    top_u, top_c = rk_u <= k, rk_c <= k

    out = []
    for j, a in enumerate(assets):
        out.append(dict(
            asset_id=a.asset_id, name=a.name,
            p_top_unified=float(top_u[:, j].mean()),
            p_top_classical=float(top_c[:, j].mean()),
            rank_median=float(np.median(rk_u[:, j])),
            rank_lo=float(np.percentile(rk_u[:, j], 5)),
            rank_hi=float(np.percentile(rk_u[:, j], 95)),
            p_quantum_dominant=float((quantum[:, j] > classical[:, j]).mean()),
            p_moves_up_2=float(((rk_c[:, j] - rk_u[:, j]) >= 2).mean()),
        ))
    # how often does the funded top-k SET change because of the quantum term?
    set_changed = float((top_u != top_c).any(axis=1).mean())
    dom_any = float(((quantum > classical).any(axis=1)).mean())
    return dict(assets=out, k=k, p_topk_set_changes=set_changed,
                p_any_quantum_dominant=dom_any, n=n)


def report(name: str, assets: list[Asset], **kw) -> str:
    r = simulate(assets, **kw)
    lines = [f"### {name}\n",
             f"{r['n']} draws; top-k = {r['k']} of {len(assets)}.\n",
             "| Asset | P(in top-k), unified | P(in top-k), classical-only | Rank (median, 5-95%) | P(quantum-dominant) | P(moves up 2+) |",
             "|---|---|---|---|---|---|"]
    for a in sorted(r["assets"], key=lambda x: x["rank_median"]):
        lines.append(f"| {a['asset_id']} {a['name'][:42]} | {a['p_top_unified']:.0%} | "
                     f"{a['p_top_classical']:.0%} | {a['rank_median']:.0f} "
                     f"({a['rank_lo']:.0f}-{a['rank_hi']:.0f}) | {a['p_quantum_dominant']:.0%} | "
                     f"{a['p_moves_up_2']:.0%} |")
    lines.append(f"\n- Probability the funded top-{r['k']} set differs from classical-only: **{r['p_topk_set_changes']:.0%}**")
    lines.append(f"- Probability at least one asset is quantum-dominant: **{r['p_any_quantum_dominant']:.0%}**\n")
    return "\n".join(lines)
