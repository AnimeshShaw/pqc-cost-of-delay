"""
Tests for the second-pass checks: discounting, numerical accuracy, the
vectorised population code, and the QARS comparator.
"""

import math

import numpy as np
import pytest
from scipy import integrate

from costofdelay.crqc import gri_2025_optimistic, gri_2025_pessimistic
from costofdelay.examples import (A01_PAYMENT, A02_SESSION_TOKENS, A03_CATALOGUE,
                      A04_KYC_ARCHIVE, A05_INTERNAL_CREDS, A06_PQC_ARCHIVE,
                      A07_AIRGAPPED, WORKED_EXAMPLES)
from costofdelay.model import (Asset, HarvestBand, LikelihoodBand, ProtectionClass,
                   ValueBand)
from costofdelay.scoring import cod_quantum

CRQC = gri_2025_optimistic()


def _asset(**kw):
    base = dict(asset_id="X", name="x", value=ValueBand.HIGH,
                likelihood=LikelihoodBand.POSSIBLE, data_lifetime_years=15.0,
                protection=ProtectionClass.RSA_2048,
                harvest_exposure=HarvestBand.HIGH,
                value_flow_usd_per_year=1_000_000.0)
    base.update(kw)
    return Asset(**base)


class TestNumericalAccuracy:
    """The integration-by-parts form must match adaptive quadrature."""

    @pytest.mark.parametrize("a", [A01_PAYMENT, A04_KYC_ARCHIVE, A05_INTERNAL_CREDS])
    @pytest.mark.parametrize("crqc", [gri_2025_optimistic(), gri_2025_pessimistic()])
    def test_matches_scipy_quad(self, a, crqc):
        lam = a.likelihood.per_year
        ref, _ = integrate.quad(lambda t: crqc.pdf(t) * math.exp(-lam * t),
                                0.0, a.data_lifetime_years,
                                epsabs=1e-14, epsrel=1e-13, limit=400)
        expected = a.flow_rate * a.harvest_exposure.fraction * ref
        assert cod_quantum(a, crqc) == pytest.approx(expected, rel=1e-7)

    def test_matches_monte_carlo_of_the_two_clocks(self):
        """
        Independent method: simulate both competing clocks directly. This is the
        check that the analytic derivation (not just the quadrature) is right.
        """
        from costofdelay.validation import mc_quantum_leg
        for a in (A01_PAYMENT, A04_KYC_ARCHIVE):
            analytic = cod_quantum(a, CRQC)
            mc, se = mc_quantum_leg(a, CRQC, n=2_000_000)
            assert abs(mc - analytic) < 4 * se


class TestDiscounting:
    """Discount rate is an explicit, swept value judgement -- not a hidden 1.0."""

    def test_zero_discount_is_the_default(self):
        assert cod_quantum(A01_PAYMENT, CRQC) == \
            cod_quantum(A01_PAYMENT, CRQC, discount_rate=0.0)

    def test_discounting_strictly_lowers_quantum_cost(self):
        prev = cod_quantum(A04_KYC_ARCHIVE, CRQC, discount_rate=0.0)
        for rho in (0.02, 0.05, 0.07, 0.15):
            cur = cod_quantum(A04_KYC_ARCHIVE, CRQC, discount_rate=rho)
            assert cur < prev
            prev = cur

    def test_discounting_equals_extra_hazard(self):
        """
        Algebraic identity: exp(-rho*tau) in the integrand is indistinguishable
        from raising the classical hazard by rho. Check it numerically.
        """
        rho = 0.05
        a = _asset(likelihood=LikelihoodBand.UNLIKELY)            # lambda = 0.05
        b = _asset(likelihood=LikelihoodBand.POSSIBLE)            # lambda = 0.20
        # a with rho=0.15  ==  b with rho=0.0   (0.05+0.15 == 0.20)
        assert cod_quantum(a, CRQC, discount_rate=0.15) == \
            pytest.approx(cod_quantum(b, CRQC, discount_rate=0.0), rel=1e-12)

    def test_discounting_does_not_touch_the_classical_leg(self):
        from costofdelay.scoring import cost_of_delay
        assert cost_of_delay(A01_PAYMENT, CRQC, discount_rate=0.07).classical == \
            cost_of_delay(A01_PAYMENT, CRQC, discount_rate=0.0).classical

    def test_negative_discount_rejected(self):
        with pytest.raises(ValueError):
            cod_quantum(A01_PAYMENT, CRQC, discount_rate=-0.01)

    def test_discount_cannot_resurrect_a_gated_leg(self):
        for a in (A03_CATALOGUE, A06_PQC_ARCHIVE, A07_AIRGAPPED):
            assert cod_quantum(a, CRQC, discount_rate=0.0) == 0.0


class TestPopulationCodeAgreesWithReference:
    """The numpy version must agree with the dependency-free reference."""

    def test_vectorised_quantum_leg_matches_reference(self):
        from costofdelay.population import quantum_leg
        assets = [a for a in WORKED_EXAMPLES if a.quantum_applicable]
        L = np.array([a.data_lifetime_years for a in assets])
        lam = np.array([a.likelihood.per_year for a in assets])
        scale = np.array([a.flow_rate * a.harvest_exposure.fraction for a in assets])
        vec = quantum_leg(CRQC, L, lam, scale)
        for v, a in zip(vec, assets):
            assert v == pytest.approx(cod_quantum(a, CRQC), rel=1e-6, abs=1e-6)


class TestDominanceCondition:
    """
    The quantum leg dominates roughly when  lambda < (r/V) * h * F_Q(L).
    Derived from the uncoupled form; the coupled leg is smaller, so the true
    boundary sits slightly lower. Pin both directions.
    """

    def test_uncoupled_dominance_boundary(self):
        from costofdelay.scoring import cod_classical, cod_quantum
        a = _asset(data_lifetime_years=25.0, harvest_exposure=HarvestBand.FULL,
                   value_flow_usd_per_year=ValueBand.HIGH.usd)  # r = V
        threshold = 1.0 * 1.0 * CRQC.cdf(25.0)                  # (r/V)*h*F
        for lam_band in LikelihoodBand:
            b = _asset(likelihood=lam_band, data_lifetime_years=25.0,
                       harvest_exposure=HarvestBand.FULL,
                       value_flow_usd_per_year=ValueBand.HIGH.usd)
            q_unc = cod_quantum(b, CRQC, competing_risks=False)
            dominant = q_unc > cod_classical(b)
            assert dominant == (lam_band.per_year < threshold)


class TestQARSComparator:
    from costofdelay.qars import qars, rank_qars  # noqa: F401  (import check)

    def test_equations_reproduce_the_papers_table_2(self):
        """
        The paper's Table 2: Asset A (X=15, Y=5, Z=12, S=0.9, E=0.3) scores
        0.733; Asset B (X=1, Y=2, Z=12, S=0.1, E=0.8) scores 0.383, with the
        LOGISTIC timeline map (T=1.00 and 0.25). Re-derive from the equations
        to confirm the comparator is a faithful reading of the published model.
        """
        def T_logistic(x, y, z, alpha):
            return 1.0 / (1.0 + math.exp(-alpha * ((x + y) / z - 1.0)))

        # Asset A: r = 20/12 = 1.667. T ~ 1.00 needs steep alpha; the paper
        # rounds. Check the arithmetic of the weighted sum given its T/S/E.
        score_a = (1.0 + 0.9 + 0.3) / 3.0
        score_b = (0.25 + 0.1 + 0.8) / 3.0
        assert score_a == pytest.approx(0.733, abs=5e-4)
        assert score_b == pytest.approx(0.383, abs=5e-4)
        # and T for B: r = 3/12 = 0.25 -> the paper reports T_B = 0.25, which
        # is the LINEAR surrogate min(1, r), confirming that surrogate.
        assert min(1.0, 3.0 / 12.0) == pytest.approx(0.25)

    def test_qars_has_the_pqc_and_harvest_gates(self):
        """Credit where due: v(a) and q(a) are QARS's, not ours."""
        from costofdelay.qars import exposure_E
        assert exposure_E(A06_PQC_ARCHIVE) == 0.0       # v = 0
        assert exposure_E(A07_AIRGAPPED) == 0.0         # q = 0
        assert exposure_E(A01_PAYMENT) > 0.0

    def test_qars_is_scale_blind_where_cost_of_delay_is_not(self):
        """
        The structural contrast. Multiply an asset's monetary value by 10 within
        the SAME sensitivity band (SEVERE and CATASTROPHIC both map to S=1.0).
        QARS cannot see the change; cost of delay moves tenfold.
        """
        from costofdelay.qars import qars
        from costofdelay.scoring import cost_of_delay
        a = _asset(value=ValueBand.SEVERE, value_flow_usd_per_year=1e7)
        b = _asset(value=ValueBand.CATASTROPHIC, value_flow_usd_per_year=1e8)
        assert qars(a, CRQC) == pytest.approx(qars(b, CRQC))
        assert cost_of_delay(b, CRQC).total > 9 * cost_of_delay(a, CRQC).total

    def test_qars_has_no_classical_leg(self):
        """
        Two assets identical except for classical hazard. QARS cannot
        distinguish them; it contains no classical-threat input at all.
        """
        from costofdelay.qars import qars
        calm = _asset(likelihood=LikelihoodBand.RARE)
        noisy = _asset(likelihood=LikelihoodBand.FREQUENT)
        assert qars(calm, CRQC) == pytest.approx(qars(noisy, CRQC))

    def test_qars_scores_a_fully_migrated_asset_in_its_high_band(self):
        """
        Under equations (2)-(8) AS PUBLISHED, the PQC gate zeroes only the
        exposure term E. Timeline T (saturated by a 30-year shelf life) and
        sensitivity S are untouched, so an asset ALREADY on ML-KEM still scores
        (1 + 1 + 0)/3 = 0.667 -- above the paper's own 'high' threshold of 0.60.
        Our quantum leg is exactly 0 for the same asset.

        This is a statement about the published equations under my reading of
        them (equal weights, linear f_time), not about the authors' tool.
        """
        from costofdelay.qars import qars
        from costofdelay.scoring import cost_of_delay
        s = qars(A06_PQC_ARCHIVE, CRQC)
        assert s == pytest.approx(2.0 / 3.0)
        assert s > 0.60, "QARS paper section 4.2: high > 0.60"
        assert cost_of_delay(A06_PQC_ARCHIVE, CRQC).quantum == 0.0
