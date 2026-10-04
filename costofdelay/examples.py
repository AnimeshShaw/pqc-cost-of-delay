"""
Synthetic worked examples used by the unit tests and the illustrative report.

They are modelled loosely on a retail web shop and on assets that retail demos
lack but regulated organisations hold (a long-retention archive, a short-lived
credential). They are NOT case-study data: every value is invented to exercise
a specific behaviour, and none is evidence about any real system. The real
case-study registers are in case_studies/.

Cases covered:
  A01  high value, moderate hazard, 10y lifetime   -> both legs material
  A02  short lifetime (minutes)                    -> quantum leg must vanish
  A03  no confidentiality value                    -> both legs must vanish
  A04  low hazard, 25y lifetime, exposed           -> quantum leg dominates
  A05  high hazard, short lifetime                 -> classical leg dominates
  A06  long lifetime but already PQC-protected     -> quantum leg must vanish
  A07  long lifetime but no harvest exposure       -> quantum leg must vanish
"""

from __future__ import annotations

from costofdelay.model import (
    Asset,
    HarvestBand,
    LikelihoodBand,
    ProtectionClass,
    ValueBand,
)

A01_PAYMENT = Asset(
    asset_id="A01",
    name="Payment and cardholder data store",
    value=ValueBand.SEVERE,
    likelihood=LikelihoodBand.POSSIBLE,
    data_lifetime_years=10.0,
    protection=ProtectionClass.RSA_2048,
    harvest_exposure=HarvestBand.HIGH,
    value_flow_usd_per_year=10_000_000.0,
    migration_time_years=2.0,
    notes="PCI retention plus ongoing customer relationship. TLS to payment "
          "provider uses RSA-2048 key exchange.",
    tags=("checkoutservice", "paymentservice"),
)

A02_SESSION_TOKENS = Asset(
    asset_id="A02",
    name="Session tokens / cart session IDs",
    value=ValueBand.LOW,
    likelihood=LikelihoodBand.LIKELY,
    data_lifetime_years=5.0 / (365.0 * 24.0 * 60.0),  # 5 minutes
    protection=ProtectionClass.ECDH_P256,
    harvest_exposure=HarvestBand.FULL,
    value_flow_usd_per_year=10_000.0,
    notes="Expire in minutes. The canonical case where a naive lifetime-based "
          "quantum flag produces a false positive and ours must not.",
    tags=("frontend", "cartservice"),
)

A03_CATALOGUE = Asset(
    asset_id="A03",
    name="Product catalogue",
    value=ValueBand.NEGLIGIBLE,
    likelihood=LikelihoodBand.POSSIBLE,
    data_lifetime_years=0.0,
    protection=ProtectionClass.ECDH_P256,
    harvest_exposure=HarvestBand.FULL,
    notes="Public data. No confidentiality requirement at all. Integrity and "
          "availability matter but are out of scope for this scoring function.",
    tags=("productcatalogservice",),
)

A04_KYC_ARCHIVE = Asset(
    asset_id="A04",
    name="Long-retention customer identity archive",
    value=ValueBand.HIGH,
    likelihood=LikelihoodBand.RARE,
    data_lifetime_years=25.0,
    protection=ProtectionClass.RSA_4096,
    harvest_exposure=HarvestBand.PARTIAL,
    value_flow_usd_per_year=1_000_000.0,
    migration_time_years=3.0,
    notes="THE DISAGREEMENT CASE. Well segmented and rarely attacked, so a "
          "classical-only practice ranks it near the bottom. 25-year retention "
          "over partially exposed paths under RSA means its HNDL cost of delay "
          "dominates its classical cost by orders of magnitude.",
    tags=("archive", "regulatory-retention"),
)

A05_INTERNAL_CREDS = Asset(
    asset_id="A05",
    name="Internal service-to-service credentials",
    value=ValueBand.MODERATE,
    likelihood=LikelihoodBand.FREQUENT,
    data_lifetime_years=0.25,  # rotated quarterly
    protection=ProtectionClass.ECDH_P256,
    harvest_exposure=HarvestBand.LOW,
    value_flow_usd_per_year=100_000.0,
    notes="Frequently targeted, rotated quarterly. Classical leg dominates and "
          "should. Pairs with A04 to produce a rank inversion against the "
          "classical-only baseline.",
    tags=("mtls", "service-mesh"),
)

A06_PQC_ARCHIVE = Asset(
    asset_id="A06",
    name="Clinical records archive (already migrated to ML-KEM)",
    value=ValueBand.SEVERE,
    likelihood=LikelihoodBand.UNLIKELY,
    data_lifetime_years=30.0,
    protection=ProtectionClass.ML_KEM_768,
    harvest_exposure=HarvestBand.HIGH,
    value_flow_usd_per_year=10_000_000.0,
    notes="Controls the protection-class gate: 30-year lifetime and heavy "
          "exposure, but the key exchange is already quantum-safe, so the "
          "quantum leg must be exactly zero. A lifetime-only heuristic would "
          "rank this first and be wrong.",
    tags=("archive", "pqc-migrated"),
)

A07_AIRGAPPED = Asset(
    asset_id="A07",
    name="Air-gapped signing key material",
    value=ValueBand.CATASTROPHIC,
    likelihood=LikelihoodBand.RARE,
    data_lifetime_years=20.0,
    protection=ProtectionClass.RSA_4096,
    harvest_exposure=HarvestBand.NONE,
    value_flow_usd_per_year=100_000_000.0,
    notes="Controls the harvest-exposure gate: enormous value and vulnerable "
          "crypto, but nothing ever crosses a collectable channel, so there is "
          "no HNDL cost of delay. Distinguishes real exposure from theoretical.",
    tags=("hsm", "code-signing"),
)


WORKED_EXAMPLES: list[Asset] = [
    A01_PAYMENT,
    A02_SESSION_TOKENS,
    A03_CATALOGUE,
    A04_KYC_ARCHIVE,
    A05_INTERNAL_CREDS,
    A06_PQC_ARCHIVE,
    A07_AIRGAPPED,
]

# The four assets the SPEC walks through in full arithmetic detail.
SPEC_WALKTHROUGH: list[Asset] = [A01_PAYMENT, A02_SESSION_TOKENS, A03_CATALOGUE, A04_KYC_ARCHIVE]
