"""
The two candidate commensuration formulations, implemented side by side so the
numbers can decide between them.

Formulation A -- COST OF DELAY (recommended)
    Both surfaces expressed as a rate in USD/year: how much does deferring this
    work by one year cost? No normalisation constant, no horizon weight, no
    discount factor.

        CoD_classical(a) = lambda_a * V_a
        CoD_quantum(a)   = r_a * h_a * integral_0^L f_Q(tau) * exp(-lambda_a*tau) d tau

    The classical leg is annualised loss expectancy -- deliberately identical to
    FAIR/ALE, claiming no novelty where none exists.

    The quantum leg is the derivative of IRREVERSIBLY COMMITTED loss with
    respect to deferral time. Data harvested now is decrypted when a CRQC
    arrives, and causes *marginal* loss only if (a) the CRQC arrives while the
    data still has value, and (b) the classical threat has not already disclosed
    it. Term (b) is the competing-risks coupling exp(-lambda*tau), and it is the
    element that makes this a method rather than arithmetic: a high classical
    hazard DISCOUNTS the same asset's quantum cost, because the data will
    probably leak in plaintext first. The legs interact; they do not sum
    independently.

Formulation B -- EXPECTED LOSS ON A WEIGHTED COMMON SCALE (the original plan)
    Implemented to be refuted, and to document that the obvious
    alternative was evaluated.

        EL_c = P_exploit_per_year * Impact * horizon_weight
        EL_q = F_Q(L) * Impact_retroactive

    `horizon_weight` has no derivation. It exists solely to make a per-year rate
    comparable with a cumulative probability. `rank_flip_horizon_weights` below
    demonstrates by construction that the ranking is a function of this free
    constant -- which is the "is it just a weighted sum?" objection landing.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from costofdelay.crqc import CRQCDistribution
from costofdelay.model import Asset

# --------------------------------------------------------------------------
# Numerical integration
# --------------------------------------------------------------------------

def _simpson(f, a: float, b: float, n: int = 2000) -> float:
    """
    Composite Simpson's rule. n must be even; it is forced even if not.
    Used rather than a library so the reference implementation stays
    dependency-free and auditable.
    """
    if b <= a:
        return 0.0
    if n % 2:
        n += 1
    h = (b - a) / n
    total = f(a) + f(b)
    for i in range(1, n):
        total += (4.0 if i % 2 else 2.0) * f(a + i * h)
    return total * h / 3.0


# --------------------------------------------------------------------------
# Formulation A: cost of delay
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class CostOfDelay:
    """Cost-of-delay decomposition for one asset, all terms in USD/year."""

    asset_id: str
    classical: float
    quantum: float
    quantum_uncoupled: float
    """Quantum leg WITHOUT the competing-risks correction, for comparison."""
    crqc_label: str
    flow_defaulted: bool

    @property
    def total(self) -> float:
        return self.classical + self.quantum

    @property
    def quantum_share(self) -> float:
        return 0.0 if self.total == 0.0 else self.quantum / self.total

    @property
    def coupling_discount(self) -> float:
        """
        How much the competing-risks correction reduced the quantum leg.
        0.0 means no discount; 0.6 means the quantum cost was cut by 60%
        because the asset is likely to be breached classically first.
        """
        if self.quantum_uncoupled == 0.0:
            return 0.0
        return 1.0 - (self.quantum / self.quantum_uncoupled)


def cod_classical(asset: Asset) -> float:
    """lambda * V. Annualised loss expectancy. USD/year."""
    return asset.likelihood.per_year * asset.value.usd


def quantum_rate(
    flow: float,
    exposure: float,
    lifetime: float,
    hazard: float,
    crqc: CRQCDistribution,
    discount_rate: float = 0.0,
    competing_risks: bool = True,
) -> float:
    """
    Continuous-parameter form of the quantum cost-of-delay rate (USD/year).

        r * h * integral_0^L f_Q(t) * exp(-(lambda + rho) * t) dt

    This is the single place the integral is evaluated; `cod_quantum` (which
    works on an `Asset`) and every theorem test call it. Inputs are plain
    floats so properties can be checked on arbitrary, not only banded, values.

    Numerics: the Weibull density behaves like t**(beta-1) at the origin, which
    is non-smooth for 1 < beta < 2 and makes Simpson on the raw integrand
    accurate only to ~1e-5. Integrating by parts is exact because f dt = dF:

        int_0^L e^{-k t} dF  =  e^{-k L} F(L)  +  k * int_0^L F(t) e^{-k t} dt ,   k = lambda + rho

    and has a smoother integrand (~t**beta). Verified against scipy.quad and a
    Monte Carlo simulation of the two competing clocks (costofdelay/validation.py).
    """
    if discount_rate < 0.0:
        raise ValueError(f"discount_rate must be >= 0, got {discount_rate}")
    scale = flow * exposure
    if scale == 0.0 or lifetime <= 0.0:
        return 0.0
    kappa = discount_rate + (hazard if competing_risks else 0.0)
    if kappa == 0.0:
        return scale * crqc.cdf(lifetime)
    tail = math.exp(-kappa * lifetime) * crqc.cdf(lifetime)
    body = kappa * _simpson(lambda t: crqc.cdf(t) * math.exp(-kappa * t), 0.0, lifetime, n=4000)
    return scale * (tail + body)


def cod_quantum(
    asset: Asset,
    crqc: CRQCDistribution,
    competing_risks: bool = True,
    discount_rate: float = 0.0,
) -> float:
    """
    Rate at which deferring migration commits irreversible HNDL loss. USD/year.

    The quantum term is gated to exactly zero unless the protection class is
    quantum-vulnerable, the exposure is non-zero and the lifetime is positive
    (see `Asset.quantum_applicable`).

    DISCOUNTING IS A VALUE JUDGEMENT, NOT A DETAIL. rho defaults to 0.0, a
    stated position (interception harm is locked in at harvest time, so
    discounting it as a far-future event understates it), not the absence of a
    choice. See methodology/FORMAL_METHOD.md and Baradziej (2026); the sweep
    over rho is reported by the evaluation scripts.

    Discounting at rate rho is algebraically identical to adding rho to the
    classical hazard in the survival term (Proposition 7).
    """
    if not asset.quantum_applicable:
        if discount_rate < 0.0:
            raise ValueError(f"discount_rate must be >= 0, got {discount_rate}")
        return 0.0
    return quantum_rate(
        flow=asset.flow_rate,
        exposure=asset.harvest_exposure.fraction,
        lifetime=asset.data_lifetime_years,
        hazard=asset.likelihood.per_year,
        crqc=crqc,
        discount_rate=discount_rate,
        competing_risks=competing_risks,
    )


def cost_of_delay(
    asset: Asset,
    crqc: CRQCDistribution,
    competing_risks: bool = True,
    discount_rate: float = 0.0,
) -> CostOfDelay:
    return CostOfDelay(
        asset_id=asset.asset_id,
        classical=cod_classical(asset),
        quantum=cod_quantum(asset, crqc, competing_risks=competing_risks,
                            discount_rate=discount_rate),
        quantum_uncoupled=cod_quantum(asset, crqc, competing_risks=False,
                                      discount_rate=discount_rate),
        crqc_label=crqc.label,
        flow_defaulted=asset.flow_rate_is_defaulted,
    )


def rank_by_cost_of_delay(
    assets: list[Asset],
    crqc: CRQCDistribution,
    competing_risks: bool = True,
    discount_rate: float = 0.0,
) -> list[CostOfDelay]:
    """Highest cost of delay first."""
    scored = [cost_of_delay(a, crqc, competing_risks, discount_rate) for a in assets]
    return sorted(scored, key=lambda c: c.total, reverse=True)


# --------------------------------------------------------------------------
# Formulation B: expected loss on a weighted common scale
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class ExpectedLoss:
    asset_id: str
    el_classical: float
    el_quantum: float
    horizon_weight: float

    @property
    def combined(self) -> float:
        return self.el_classical + self.el_quantum


def expected_loss(
    asset: Asset,
    crqc: CRQCDistribution,
    horizon_weight: float = 1.0,
) -> ExpectedLoss:
    """
    The Master Execution Plan v3 Step 2 formulation.

    `horizon_weight` is the undefined free parameter. Its only function is to
    convert a per-year rate into something addable to a cumulative probability.
    """
    el_c = asset.likelihood.per_year * asset.value.usd * horizon_weight

    el_q = 0.0
    if asset.quantum_applicable:
        el_q = crqc.cdf(asset.data_lifetime_years) * asset.value.usd

    return ExpectedLoss(
        asset_id=asset.asset_id,
        el_classical=el_c,
        el_quantum=el_q,
        horizon_weight=horizon_weight,
    )


def rank_by_expected_loss(
    assets: list[Asset],
    crqc: CRQCDistribution,
    horizon_weight: float = 1.0,
) -> list[ExpectedLoss]:
    scored = [expected_loss(a, crqc, horizon_weight) for a in assets]
    return sorted(scored, key=lambda e: e.combined, reverse=True)


def rank_flip_horizon_weights(
    assets: list[Asset],
    crqc: CRQCDistribution,
    weights=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 25.0),
) -> dict[float, list[str]]:
    """
    Formulation B's ranking at a range of horizon weights.

    If the orderings differ across weights, the ranking is a function of an
    undefined constant. This is the evidence against Formulation B, generated
    by code rather than asserted.
    """
    return {
        w: [e.asset_id for e in rank_by_expected_loss(assets, crqc, w)]
        for w in weights
    }


# --------------------------------------------------------------------------
# Baselines, for the "does unified change decisions?" comparison
# --------------------------------------------------------------------------

def rank_classical_only(assets: list[Asset]) -> list[str]:
    """What a STRIDE/FAIR practice produces today. Quantum invisible."""
    return [
        a.asset_id
        for a in sorted(assets, key=lambda a: cod_classical(a), reverse=True)
    ]


def rank_by_lifetime_only(assets: list[Asset]) -> list[str]:
    """
    Sort by data lifetime descending.

    This is the refutation baseline: if the cost-of-delay ranking were
    rank-identical to this, the mathematics would contribute nothing beyond
    the register's data-lifetime column. See tests/test_refutation.py.
    """
    return [
        a.asset_id
        for a in sorted(assets, key=lambda a: a.data_lifetime_years, reverse=True)
    ]


def rank_mosca_gate(assets: list[Asset], crqc: CRQCDistribution) -> list[str]:
    """
    Mosca's binary gate: assets failing L + M > Z first, in arbitrary order
    within each group (we use lifetime as the tiebreak, which is the most
    charitable reading available).

    The point of this baseline is that the gate produces a SET, not an order.
    It tells you whether to act; it cannot tell you which asset first. That is
    the gap the cost-of-delay ordering fills.
    """
    z = crqc.median_years()
    failing = [a for a in assets if a.fails_mosca(z)]
    passing = [a for a in assets if not a.fails_mosca(z)]
    key = lambda a: a.data_lifetime_years
    return [a.asset_id for a in sorted(failing, key=key, reverse=True)] + [
        a.asset_id for a in sorted(passing, key=key, reverse=True)
    ]


# --------------------------------------------------------------------------
# Rank comparison
# --------------------------------------------------------------------------

def kendall_tau(a: list[str], b: list[str]) -> float:
    """
    Kendall's tau-a between two orderings of the same items.
    +1 identical, -1 reversed, 0 unrelated. Pure Python, no scipy.
    """
    if sorted(a) != sorted(b):
        raise ValueError("orderings must contain the same items")
    n = len(a)
    if n < 2:
        return 1.0
    pos_b = {item: i for i, item in enumerate(b)}
    concordant = discordant = 0
    for i in range(n):
        for j in range(i + 1, n):
            sign_a = 1  # a[i] precedes a[j] by construction
            sign_b = 1 if pos_b[a[i]] < pos_b[a[j]] else -1
            if sign_a == sign_b:
                concordant += 1
            else:
                discordant += 1
    return (concordant - discordant) / (0.5 * n * (n - 1))


def rank_inversions(reference: list[str], candidate: list[str]) -> list[tuple[str, str]]:
    """
    Pairs whose relative order differs between two rankings. These are the
    decisions the method actually changes -- the decisions the method actually changes.
    """
    pos_ref = {item: i for i, item in enumerate(reference)}
    pos_cand = {item: i for i, item in enumerate(candidate)}
    out = []
    items = list(reference)
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            x, y = items[i], items[j]
            if (pos_ref[x] < pos_ref[y]) != (pos_cand[x] < pos_cand[y]):
                out.append((x, y))
    return out
