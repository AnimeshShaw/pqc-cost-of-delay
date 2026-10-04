"""
Independent validation of the scoring function.

Two checks that do not trust scoring.py's own arithmetic:

  1. MONTE CARLO of the competing-risks quantum leg.
     Simulate the two competing clocks directly (classical first-disclosure time
     ~ Exponential(lambda); CRQC arrival ~ fitted Weibull) and measure how often
     the CRQC wins inside the data lifetime. That frequency, times r*h, must
     equal the closed-form integral in scoring.cod_quantum. Different code path,
     different method; agreement is real evidence, disagreement means a bug.

  2. QUADRATURE cross-check against scipy.integrate.quad, to confirm the
     hand-rolled Simpson rule is not hiding an error near the origin.

numpy/scipy are used ONLY here, never in the reference implementation, so the
reference stays dependency-free and auditable.
"""

from __future__ import annotations

import math

import numpy as np
from scipy import integrate

from costofdelay.crqc import gri_2025_optimistic, gri_2025_pessimistic
from costofdelay.examples import WORKED_EXAMPLES
from costofdelay.model import Asset
from costofdelay.scoring import cod_quantum

RNG_SEED = 20261002


def mc_quantum_leg(asset: Asset, crqc, n: int = 4_000_000, seed: int = RNG_SEED):
    """
    Monte Carlo estimate of cod_quantum by direct simulation of both clocks.

    Returns (estimate, standard_error), both in USD/year.

    Marginal loss of the data harvested at t=0 is realised iff
        the CRQC arrives within the data lifetime   (tau_q <= L)   AND
        the classical threat has not already disclosed it  (tau_q < tau_c).
    """
    if not asset.quantum_applicable:
        return 0.0, 0.0

    rng = np.random.default_rng(seed)
    L = asset.data_lifetime_years
    lam = asset.likelihood.per_year

    # Weibull(alpha, beta): numpy's weibull() is the unit-scale form.
    tau_q = crqc.alpha * rng.weibull(crqc.beta, size=n)
    tau_c = rng.exponential(1.0 / lam, size=n)

    hit = (tau_q <= L) & (tau_q < tau_c)
    p = hit.mean()
    se_p = math.sqrt(p * (1.0 - p) / n)

    scale = asset.flow_rate * asset.harvest_exposure.fraction
    return scale * p, scale * se_p


def quad_quantum_leg(asset: Asset, crqc) -> float:
    """scipy adaptive quadrature of the same integral."""
    if not asset.quantum_applicable:
        return 0.0
    lam = asset.likelihood.per_year
    val, _err = integrate.quad(
        lambda t: crqc.pdf(t) * math.exp(-lam * t),
        0.0, asset.data_lifetime_years, epsabs=1e-13, epsrel=1e-12, limit=200,
    )
    return asset.flow_rate * asset.harvest_exposure.fraction * val


def run() -> bool:
    ok = True
    print("=" * 78)
    print("VALIDATION 1: closed-form competing-risks integral vs Monte Carlo")
    print("=" * 78)
    print("4,000,000 simulated (CRQC, classical-breach) clock pairs per asset.")
    print()
    print(f"{'scenario':<22}{'id':<5}{'analytic':>13}{'monte carlo':>14}"
          f"{'std err':>11}{'z-score':>9}{'verdict':>10}")
    print("-" * 84)

    for crqc in (gri_2025_optimistic(), gri_2025_pessimistic()):
        for a in WORKED_EXAMPLES:
            if not a.quantum_applicable:
                continue
            analytic = cod_quantum(a, crqc)
            mc, se = mc_quantum_leg(a, crqc)
            z = 0.0 if se == 0.0 else (mc - analytic) / se
            good = abs(z) < 4.0
            ok &= good
            print(f"{crqc.label:<22}{a.asset_id:<5}{analytic:>13,.1f}{mc:>14,.1f}"
                  f"{se:>11,.1f}{z:>9.2f}{('OK' if good else 'FAIL'):>10}")

    print()
    print("=" * 78)
    print("VALIDATION 2: Simpson rule vs scipy adaptive quadrature")
    print("=" * 78)
    print()
    print(f"{'scenario':<22}{'id':<5}{'simpson':>16}{'scipy quad':>16}{'rel err':>12}")
    print("-" * 71)
    worst = 0.0
    for crqc in (gri_2025_optimistic(), gri_2025_pessimistic()):
        for a in WORKED_EXAMPLES:
            if not a.quantum_applicable:
                continue
            s = cod_quantum(a, crqc)
            q = quad_quantum_leg(a, crqc)
            rel = abs(s - q) / max(abs(q), 1e-3)  # absolute floor: sub-milli-dollar values are noise
            worst = max(worst, rel)
            print(f"{crqc.label:<22}{a.asset_id:<5}{s:>16,.6f}{q:>16,.6f}{rel:>12.2e}")
    ok &= worst < 1e-7
    print()
    print(f"worst relative error: {worst:.2e}  ->  {'OK' if worst < 1e-7 else 'FAIL'}")
    print()
    print("OVERALL:", "PASS" if ok else "*** FAIL ***")
    return ok


if __name__ == "__main__":
    raise SystemExit(0 if run() else 1)
