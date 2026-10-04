"""
Asset model and the ordinal->currency band mappings.

Design decision: everything is denominated in USD,
because a cost-of-delay rate must be currency/time to be actionable. Nobody
can give exact figures for a session token, so values are elicited in ordinal
bands with PUBLISHED midpoints, and the analysis reports rank stability across
band assignments rather than claiming calibrated point scores.

The bands are log-spaced. That is deliberate: security loss magnitudes span
orders of magnitude, and practitioners distinguish "tens of thousands" from
"millions" far more reliably than they distinguish 2.0M from 3.5M.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ValueBand(Enum):
    """Loss in USD if the asset's confidentiality is lost in one event."""

    NEGLIGIBLE = 0.0
    LOW = 10_000.0
    MODERATE = 100_000.0
    HIGH = 1_000_000.0
    SEVERE = 10_000_000.0
    CATASTROPHIC = 100_000_000.0

    @property
    def usd(self) -> float:
        return self.value


class LikelihoodBand(Enum):
    """Classical threat hazard rate, expected events per year (lambda)."""

    RARE = 0.01  # once per century
    UNLIKELY = 0.05  # once per 20 years
    POSSIBLE = 0.20  # once per 5 years
    LIKELY = 0.50  # once per 2 years
    FREQUENT = 1.00  # annually

    @property
    def per_year(self) -> float:
        return self.value


class HarvestBand(Enum):
    """
    Fraction of the asset's traffic exposed to passive collection by an
    adversary capable of storing ciphertext (h). This is the field that
    distinguishes a real HNDL exposure from a theoretical one: data that never
    crosses a collectable channel cannot be harvested.
    """

    NONE = 0.0  # never leaves a physically controlled boundary
    LOW = 0.10  # private interconnect, limited collection opportunity
    PARTIAL = 0.50  # mixed internal/external paths
    HIGH = 0.90  # traverses public networks routinely
    FULL = 1.00  # fully exposed, e.g. internet-facing TLS

    @property
    def fraction(self) -> float:
        return self.value


class ProtectionClass(Enum):
    """
    Cryptographic protection currently in place for the asset's confidentiality
    in transit. Determines whether the quantum leg applies at all.

    quantum_vulnerable: True if a CRQC breaks the confidentiality of data
    already recorded under this protection (i.e. Shor against the key exchange).
    """

    RSA_2048 = ("RSA-2048 key exchange", True)
    RSA_4096 = ("RSA-4096 key exchange", True)
    ECDH_P256 = ("ECDH P-256 key exchange", True)
    ECDH_P384 = ("ECDH P-384 key exchange", True)
    AES_256_PSK = ("AES-256 with pre-shared symmetric key", False)
    ML_KEM_768 = ("ML-KEM-768 (FIPS 203)", False)
    HYBRID_X25519_MLKEM = ("Hybrid X25519 + ML-KEM", False)
    NONE = ("no cryptographic protection", False)

    def __init__(self, description: str, quantum_vulnerable: bool):
        self.description = description
        self.quantum_vulnerable = quantum_vulnerable


@dataclass(frozen=True)
class Asset:
    """
    One row of an asset register, carrying only the fields the scoring
    needs. The two fields no other methodology collects are `data_lifetime_years`
    and `protection`.
    """

    asset_id: str
    name: str

    # -- classical leg inputs ------------------------------------------------
    value: ValueBand
    """Loss if confidentiality is lost in a single event (USD)."""

    likelihood: LikelihoodBand
    """Classical confidentiality-threat hazard rate (events/year)."""

    # -- quantum leg inputs --------------------------------------------------
    data_lifetime_years: float
    """How long the data must remain confidential. L in Mosca's inequality."""

    protection: ProtectionClass
    """Current cryptographic protection class."""

    harvest_exposure: HarvestBand = HarvestBand.HIGH
    """Fraction of traffic exposed to passive collection. h."""

    value_flow_usd_per_year: float | None = None
    """
    Rate at which NEW sensitive value crosses the harvestable channel (USD/year).
    r in the cost-of-delay formulation.

    THIS IS THE WEAKEST INPUT IN THE MODEL. See methodology/PARAMETERS.md. When not
    supplied it defaults to `value.usd`, i.e. the conservative assumption that
    the asset's full value is re-exposed once per year. State the assumption
    explicitly in any assessment; do not let the default pass silently.
    """

    migration_time_years: float = 1.0
    """M in Mosca's inequality. Used for the Mosca gate comparison only."""

    notes: str = ""
    tags: tuple[str, ...] = field(default_factory=tuple)

    # -- derived -------------------------------------------------------------

    @property
    def flow_rate(self) -> float:
        """r, with the documented default applied."""
        if self.value_flow_usd_per_year is not None:
            return self.value_flow_usd_per_year
        return self.value.usd

    @property
    def flow_rate_is_defaulted(self) -> bool:
        """True if r fell back to the V-per-year approximation."""
        return self.value_flow_usd_per_year is None

    @property
    def quantum_applicable(self) -> bool:
        """
        Whether the quantum leg can be non-zero at all. Requires vulnerable
        crypto, some harvest exposure, and a non-zero data lifetime.
        """
        return (
            self.protection.quantum_vulnerable
            and self.harvest_exposure.fraction > 0.0
            and self.data_lifetime_years > 0.0
        )

    def fails_mosca(self, crqc_years_to_arrival: float) -> bool:
        """
        Mosca's inequality: L + M > Z. True means 'act now' under the classic
        binary gate. Retained only to compare the gate against our ordering --
        the cost-of-delay formulation does not use it.
        """
        return self.data_lifetime_years + self.migration_time_years > crqc_years_to_arrival
