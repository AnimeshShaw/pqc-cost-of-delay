"""
QARS comparator -- the closest published prior art, implemented from its
equations so the two can be run side by side on the same assets.

Source: Grigaliunas S., Bruzgiene R. "Towards a Unified Quantum Risk
Assessment", Electronics 2025, 14(17), 3338. Published 22 Aug 2025, CC BY.
DOI 10.3390/electronics14173338.
[VERIFIED against the full text, read directly, 2026-10-02: equations (2)-(8),
section 3.3 weights, section 5 discussion p.14.]

THIS IS MY READING OF THE PAPER, not the authors' code. Where the paper leaves a
parameter open I state the choice here:

  - f_time:   the paper offers a logistic with steepness alpha (unspecified) or
              "a simpler linear surrogate min(1, r)". Default here is the
              linear surrogate, the paper's own stated low-uncertainty option.
  - g(D):     the paper gives only g(Low)=0.25 and g(Critical)=1 as an example.
              We interpolate linearly across our value bands.
  - f_sens, f_expos: identity (paper: "typically identity").
  - weights:  equal, 1/3 each (the paper's baseline, section 3.3 stage 1).
  - Z:        a single point estimate (the paper's Z). We use the CRQC median.

What QARS is, structurally (and what ours is not)
-------------------------------------------------
QARS(a) = w_T*T(a) + w_S*S(a) + w_E*E(a), a dimensionless weighted sum on [0,1]
whose three terms are a normalised ratio, an ordinal label and a harvestability
score. It has NO currency unit, NO classical-risk leg, and its own discussion
(p.14) writes it as "proportional to w_T P(CRQC arrives) + w_E P(data exposure)
+ w_S Impact" -- a sum of two probabilities and an impact. It states the aim
that QARS "supplies likelihood/impact numbers that can be embedded in FAIR or
NIST 800-30 registers, ensuring quantum risk is evaluated alongside classical
threats rather than siloed", but gives no method for doing so.

Prior art relevant to our own design -- PROTECTION-CLASS GATE (v(a), eq 6) and
HARVEST-EXPOSURE FACTOR (q(a), eq 7) and their product E = v*q (eq 8) are
QARS's. Our gates for A06/A07 are therefore NOT novel and must be credited.
"""

from __future__ import annotations

import math

from costofdelay.crqc import CRQCDistribution
from costofdelay.model import Asset, ValueBand

# Sensitivity mapping g: value band -> [0,1]. The paper fixes only the two
# endpoints of a four-label scale; this is a linear interpolation of ours.
SENSITIVITY = {
    ValueBand.NEGLIGIBLE: 0.0,
    ValueBand.LOW: 0.25,
    ValueBand.MODERATE: 0.50,
    ValueBand.HIGH: 0.75,
    ValueBand.SEVERE: 1.00,
    ValueBand.CATASTROPHIC: 1.00,
}


def timeline_T(asset: Asset, z_years: float, mode: str = "linear",
               alpha: float = 4.0) -> float:
    """Eq (3)-(4). r = (X+Y)/Z, then a monotone map to [0,1]."""
    r = (asset.data_lifetime_years + asset.migration_time_years) / z_years
    if mode == "linear":
        return min(1.0, r)
    if mode == "logistic":
        return 1.0 / (1.0 + math.exp(-alpha * (r - 1.0)))
    raise ValueError(f"unknown mode {mode!r}")


def exposure_E(asset: Asset) -> float:
    """Eq (6)-(8). E = v(a) * q(a); v=1 iff the primitive is quantum-breakable."""
    v = 1.0 if asset.protection.quantum_vulnerable else 0.0
    return v * asset.harvest_exposure.fraction


def qars(asset: Asset, crqc: CRQCDistribution, weights=(1 / 3, 1 / 3, 1 / 3),
         mode: str = "linear", alpha: float = 4.0) -> float:
    """Eq (2). Weighted sum on [0,1]."""
    wT, wS, wE = weights
    if abs(wT + wS + wE - 1.0) > 1e-9:
        raise ValueError("weights must sum to 1")
    return (wT * timeline_T(asset, crqc.median_years(), mode, alpha)
            + wS * SENSITIVITY[asset.value]
            + wE * exposure_E(asset))


def rank_qars(assets: list[Asset], crqc: CRQCDistribution, **kw) -> list[str]:
    return [a.asset_id for a in
            sorted(assets, key=lambda a: qars(a, crqc, **kw), reverse=True)]
