"""
CRQC arrival distribution F_Q(t).

The arrival of a cryptographically relevant quantum computer is modelled as a
Weibull-distributed waiting time, with parameters SOLVED from published expert
anchor points rather than chosen by hand. The anchors are the single source of
truth: change them and the curve regenerates.

Source of anchors
-----------------
Quantum Threat Timeline Report 2025, Dr. Michele Mosca & Dr. Marco Piani,
evolutionQ / Global Risk Institute, published 2026-03-09, 26 experts surveyed.
  - CRQC within 10 years: "quite possible (28-49%)"
  - CRQC within 15 years: "likely (51-70%)"
  [VERIFIED: https://globalriskinstitute.org/publication/quantum-threat-timeline-report-2025b/
   accessed 2026-10-02]

The low end of each range is the report's pessimistic averaged interpretation,
the high end the optimistic one. We expose both as named scenarios rather than
averaging them, because the spread IS the decision-relevant uncertainty.

What is NOT sourced
-------------------
The 2025 report also states that 92% of respondents placed the 20-year
probability at 50% or above. That is a statistic about the distribution of
RESPONDENTS, not an averaged probability, so it is NOT used as an anchor here.
Do not conflate the two. Any F_Q(t) value beyond t=15 is extrapolation from the
fitted curve and must be reported as such.  [VERIFY: obtain averaged 20-year
and 30-year figures from the full report PDF if they exist.]

Why Weibull
-----------
Two free parameters (so it is exactly determined by two anchors), support on
t >= 0, and a monotone hazard - appropriate for a technology-arrival process
where the conditional probability of arrival rises over time. No claim is made
that the true arrival process is Weibull; it is a parameterised interpolation
between published anchors. Alternative families are discussed in methodology/FORMAL_METHOD.md.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# --------------------------------------------------------------------------
# Published anchor points: (years_from_baseline, P(CRQC exists by then))
# --------------------------------------------------------------------------

GRI_2025_BASELINE_YEAR = 2026  # report published 2026-03-09

GRI_2025_PESSIMISTIC = ((10.0, 0.28), (15.0, 0.51))
GRI_2025_OPTIMISTIC = ((10.0, 0.49), (15.0, 0.70))

# Sensitivity scenarios expressed as CRQC *median* arrival years, used for the
# ranking-stability table. These are not GRI figures; they are the scenario
# grid the analysis is stressed against.
MEDIAN_SCENARIOS = (2032, 2035, 2040, 2045)


class AnchorError(ValueError):
    """Raised when anchor points cannot define a valid distribution."""


@dataclass(frozen=True)
class CRQCDistribution:
    """
    Weibull waiting-time distribution for CRQC arrival.

    F(t) = 1 - exp(-(t/alpha)^beta),  t >= 0, in years from now.
    """

    alpha: float  # scale, years
    beta: float  # shape, dimensionless
    label: str = "unnamed"

    # -- core ---------------------------------------------------------------

    def cdf(self, t: float) -> float:
        """P(CRQC arrives within t years). F_Q(t)."""
        if t <= 0.0:
            return 0.0
        return 1.0 - math.exp(-((t / self.alpha) ** self.beta))

    def pdf(self, t: float) -> float:
        """Density f_Q(t)."""
        if t <= 0.0:
            # For beta > 1 the density is 0 at the origin. For beta < 1 it
            # diverges; callers integrating must guard against that.
            return 0.0 if self.beta > 1.0 else float("inf")
        z = (t / self.alpha) ** self.beta
        return (self.beta / self.alpha) * ((t / self.alpha) ** (self.beta - 1.0)) * math.exp(-z)

    def median_years(self) -> float:
        """Years until P(arrival) = 0.5."""
        return self.alpha * (math.log(2.0) ** (1.0 / self.beta))

    def quantile(self, p: float) -> float:
        """Years until P(arrival) = p."""
        if not 0.0 < p < 1.0:
            raise ValueError(f"quantile p must be in (0,1), got {p}")
        return self.alpha * ((-math.log(1.0 - p)) ** (1.0 / self.beta))

    def is_extrapolated(self, t: float, anchors=GRI_2025_OPTIMISTIC) -> bool:
        """True if t lies outside the range covered by the published anchors."""
        horizons = [h for h, _ in anchors]
        return t > max(horizons) or t < min(horizons)

    # -- constructors -------------------------------------------------------

    @classmethod
    def from_anchors(cls, anchors, label: str = "fitted") -> "CRQCDistribution":
        """
        Solve (alpha, beta) exactly from two anchor points.

        Given F(t1)=p1 and F(t2)=p2, let y_i = -ln(1-p_i). Then
            (t1/alpha)^beta = y1 and (t2/alpha)^beta = y2
        so  beta = ln(y2/y1) / ln(t2/t1)  and  alpha = t1 / y1^(1/beta).

        Closed form, no numerical search required.
        """
        if len(anchors) != 2:
            raise AnchorError(f"need exactly 2 anchor points, got {len(anchors)}")

        (t1, p1), (t2, p2) = sorted(anchors, key=lambda a: a[0])

        if not (0.0 < p1 < 1.0 and 0.0 < p2 < 1.0):
            raise AnchorError(f"anchor probabilities must be in (0,1): {p1}, {p2}")
        if t1 <= 0.0 or t2 <= t1:
            raise AnchorError(f"anchor horizons must be positive and distinct: {t1}, {t2}")
        if p2 <= p1:
            raise AnchorError(
                f"probability must increase with horizon: F({t1})={p1}, F({t2})={p2}"
            )

        y1 = -math.log(1.0 - p1)
        y2 = -math.log(1.0 - p2)

        beta = math.log(y2 / y1) / math.log(t2 / t1)
        alpha = t1 / (y1 ** (1.0 / beta))

        return cls(alpha=alpha, beta=beta, label=label)

    @classmethod
    def from_median(cls, median_year: int, beta: float, baseline_year: int = 2026,
                    label: str | None = None) -> "CRQCDistribution":
        """
        Build a distribution with a stated median arrival year, holding shape
        fixed. Used for the sensitivity grid, where we vary *when* rather than
        re-fitting the whole curve.
        """
        years_out = median_year - baseline_year
        if years_out <= 0:
            raise AnchorError(f"median_year {median_year} must be after {baseline_year}")
        alpha = years_out / (math.log(2.0) ** (1.0 / beta))
        return cls(alpha=alpha, beta=beta,
                   label=label or f"median {median_year}")


# --------------------------------------------------------------------------
# The two published scenarios
# --------------------------------------------------------------------------

def gri_2025_pessimistic() -> CRQCDistribution:
    return CRQCDistribution.from_anchors(GRI_2025_PESSIMISTIC, label="GRI 2025 pessimistic")


def gri_2025_optimistic() -> CRQCDistribution:
    return CRQCDistribution.from_anchors(GRI_2025_OPTIMISTIC, label="GRI 2025 optimistic")


def scenario_grid(beta: float | None = None) -> list[CRQCDistribution]:
    """
    The sensitivity grid: CRQC median at 2032 / 2035 / 2040 / 2045, holding the
    shape parameter at the GRI optimistic fit so only timing varies.
    """
    if beta is None:
        beta = gri_2025_optimistic().beta
    return [CRQCDistribution.from_median(y, beta) for y in MEDIAN_SCENARIOS]
