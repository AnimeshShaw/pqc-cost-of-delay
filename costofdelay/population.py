"""
Population-level study: how often does adding the quantum term change a decision?

A handful of hand-picked assets prove little either way. This module draws many
synthetic registers from stated (assumed) distributions and measures, as
distributions:

  * the fraction of pairwise priority decisions the quantum term flips
  * the fraction of the classical top decile it displaces
    (the planning-relevant quantity: what lands in the funded top of the list)

and shows how both depend on (a) the spacing of the value bands and (b) the
weakest input, the value-flow rate r.

Every population parameter below is an assumption. The point is not the
absolute numbers but their sensitivity to the two design choices.

Vectorised with numpy for speed. numpy is used here only; the reference
implementation in scoring.py stays dependency-free, and tests/test_validation.py
checks that this vectorised version agrees with it.
"""

from __future__ import annotations

import math

import numpy as np

from costofdelay.crqc import CRQCDistribution, gri_2025_optimistic

LIKELIHOODS = np.array([0.01, 0.05, 0.20, 0.50, 1.00])


def _cdf(crqc: CRQCDistribution, t: np.ndarray) -> np.ndarray:
    t = np.maximum(t, 0.0)
    return 1.0 - np.exp(-((t / crqc.alpha) ** crqc.beta))


def quantum_leg(crqc, L, lam, scale, n: int = 800) -> np.ndarray:
    """
    Vectorised cod_quantum (integration-by-parts form). One row per asset.
    L, lam, scale are 1-D arrays of equal length.
    """
    kappa = lam
    grid = np.linspace(0.0, 1.0, n + 1)[None, :] * L[:, None]  # (assets, n+1)
    vals = _cdf(crqc, grid) * np.exp(-kappa[:, None] * grid)
    h = (L / n)[:, None]
    w = np.ones(n + 1)
    w[1:-1:2] = 4.0
    w[2:-1:2] = 2.0
    simpson = (h[:, 0] / 3.0) * (vals * w[None, :]).sum(axis=1)
    return scale * (np.exp(-kappa * L) * _cdf(crqc, L) + kappa * simpson)


def draw_register(rng, n_assets: int, n_value_levels: int, flow_mode: str,
                  p_vulnerable: float = 0.7):
    """
    One synthetic register. [ASSUMED] distributions:
      value      : log-uniform over a fixed 4-decade range 1e4..1e8, snapped to
                   n_value_levels equally log-spaced bands (this is the knob:
                   5 levels = 10x spacing, 9 = 3.16x, 17 = 1.78x)
      likelihood : uniform over the five bands
      lifetime   : log-uniform 0.01..30 years
      vulnerable : Bernoulli(p_vulnerable)
      harvest    : uniform over {0, .1, .5, .9, 1.0}
      flow r     : 'V' -> r = V ; 'V_over_L' -> r = V / max(L, 1)
    """
    levels = np.logspace(4, 8, n_value_levels)
    V = levels[rng.integers(0, n_value_levels, n_assets)]
    lam = LIKELIHOODS[rng.integers(0, 5, n_assets)]
    L = np.exp(rng.uniform(math.log(0.01), math.log(30.0), n_assets))
    vuln = rng.random(n_assets) < p_vulnerable
    h = np.array([0.0, 0.1, 0.5, 0.9, 1.0])[rng.integers(0, 5, n_assets)]

    r = V.copy() if flow_mode == "V" else V / np.maximum(L, 1.0)
    scale = r * h * vuln
    return V, lam, L, scale


def metrics(V, lam, L, scale, crqc, top_frac: float = 0.10):
    cl = lam * V
    q = quantum_leg(crqc, L, lam, scale)
    total = cl + q

    n = len(V)
    # rank positions (0 = highest priority)
    order_c = np.argsort(-cl, kind="stable")
    order_u = np.argsort(-total, kind="stable")
    pos_c = np.empty(n, int); pos_c[order_c] = np.arange(n)
    pos_u = np.empty(n, int); pos_u[order_u] = np.arange(n)

    # fraction of discordant pairs, via sign matrices (n is small enough)
    dc = np.sign(pos_c[:, None] - pos_c[None, :])
    du = np.sign(pos_u[:, None] - pos_u[None, :])
    iu = np.triu_indices(n, 1)
    discordant = float((dc[iu] != du[iu]).mean())

    k = max(1, int(round(top_frac * n)))
    top_c = set(order_c[:k].tolist())
    top_u = set(order_u[:k].tolist())
    displaced = 1.0 - len(top_c & top_u) / k

    share = q / np.where(total > 0, total, np.nan)
    return discordant, displaced, float(np.nanmedian(share[q > 0])) if (q > 0).any() else 0.0


def study(n_registers: int = 300, n_assets: int = 60, seed: int = 7):
    crqc = gri_2025_optimistic()
    out = {}
    for flow_mode in ("V", "V_over_L"):
        for n_levels in (5, 9, 17):
            rng = np.random.default_rng(seed)
            disc, disp, share = [], [], []
            for _ in range(n_registers):
                reg = draw_register(rng, n_assets, n_levels, flow_mode)
                d, p, s = metrics(*reg, crqc)
                disc.append(d); disp.append(p); share.append(s)
            out[(flow_mode, n_levels)] = (
                np.array(disc), np.array(disp), np.array(share))
    return out


def run() -> None:
    print("=" * 88)
    print("POPULATION STUDY: how often does unification change the decision?")
    print("=" * 88)
    print("300 synthetic registers x 60 assets. All population parameters [ASSUMED].")
    print("CRQC scenario: GRI 2025 optimistic. Classical-only practice is the baseline.")
    print()
    res = study()
    print(f"{'flow r':<10}{'value bands':<22}{'pairs flipped':>20}"
          f"{'top-10% displaced':>22}{'median q-share':>16}")
    print("-" * 90)
    for (flow, k), (d, p, s) in res.items():
        spacing = {5: "5  (10x spacing)", 9: "9  (3.2x)", 17: "17 (1.8x)"}[k]
        print(f"{flow:<10}{spacing:<22}"
              f"{d.mean():>10.1%} [{np.percentile(d,5):.1%},{np.percentile(d,95):.1%}]"
              f"{p.mean():>12.1%} [{np.percentile(p,5):.0%},{np.percentile(p,95):.0%}]"
              f"{np.mean(s):>14.1%}")
    print()
    print("Brackets are the 5th-95th percentile across registers.")
    print()
    print("READ THIS CAREFULLY. The two columns answer different questions:")
    print("  pairs flipped      -> how much the whole ORDER changes")
    print("  top-10% displaced  -> how much the FUNDED TOP OF THE ROADMAP changes")


if __name__ == "__main__":
    run()
