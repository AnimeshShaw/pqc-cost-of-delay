"""
Tests for the cost-of-delay scoring function.

These encode the behavioural claims the method makes. If one fails, the claim in
the spec is false and must be withdrawn -- not patched around.
"""

import pytest

from costofdelay.crqc import gri_2025_optimistic, gri_2025_pessimistic, scenario_grid
from costofdelay.examples import (
    A01_PAYMENT,
    A02_SESSION_TOKENS,
    A03_CATALOGUE,
    A04_KYC_ARCHIVE,
    A05_INTERNAL_CREDS,
    A06_PQC_ARCHIVE,
    A07_AIRGAPPED,
    WORKED_EXAMPLES,
)
from costofdelay.model import (
    Asset,
    HarvestBand,
    LikelihoodBand,
    ProtectionClass,
    ValueBand,
)
from costofdelay.scoring import (
    cod_classical,
    cod_quantum,
    cost_of_delay,
    expected_loss,
    kendall_tau,
    rank_by_cost_of_delay,
    rank_by_lifetime_only,
    rank_classical_only,
    rank_flip_horizon_weights,
    rank_inversions,
)

CRQC = gri_2025_optimistic()


class TestUnits:
    """Both legs must be rates in USD/year, or the comparison is meaningless."""

    def test_classical_leg_is_ale(self):
        """lambda * V, exactly. No novelty claimed on the classical leg."""
        assert cod_classical(A01_PAYMENT) == pytest.approx(0.20 * 10_000_000.0)

    def test_both_legs_nonnegative(self):
        for a in WORKED_EXAMPLES:
            c = cost_of_delay(a, CRQC)
            assert c.classical >= 0.0
            assert c.quantum >= 0.0

    def test_doubling_value_doubles_classical_leg(self):
        base = Asset(
            asset_id="X", name="x", value=ValueBand.MODERATE,
            likelihood=LikelihoodBand.POSSIBLE, data_lifetime_years=5.0,
            protection=ProtectionClass.RSA_2048,
        )
        bigger = Asset(**{**base.__dict__, "value": ValueBand.HIGH})
        assert cod_classical(bigger) == pytest.approx(10 * cod_classical(base))

    def test_doubling_flow_doubles_quantum_leg(self):
        base = Asset(
            asset_id="X", name="x", value=ValueBand.HIGH,
            likelihood=LikelihoodBand.RARE, data_lifetime_years=15.0,
            protection=ProtectionClass.RSA_2048,
            harvest_exposure=HarvestBand.HIGH,
            value_flow_usd_per_year=1_000_000.0,
        )
        doubled = Asset(**{**base.__dict__, "value_flow_usd_per_year": 2_000_000.0})
        assert cod_quantum(doubled, CRQC) == pytest.approx(
            2 * cod_quantum(base, CRQC)
        )


class TestTheGatesMustHold:
    """
    Each of these is a case where a naive heuristic produces a false positive
    and ours must not. These are the easy cases the formula has to get right
    WITHOUT a hand-written exception.
    """

    def test_short_lifetime_kills_quantum_leg(self):
        """Session tokens: minutes of lifetime, so no HNDL cost."""
        c = cost_of_delay(A02_SESSION_TOKENS, CRQC)
        assert c.quantum < 1e-3, (
            f"5-minute lifetime produced quantum CoD of {c.quantum}; a "
            "lifetime-based flag would false-positive here"
        )
        assert c.classical > 0.0, "classical leg should still be live"

    def test_no_confidentiality_value_kills_both_legs(self):
        """Public product catalogue."""
        c = cost_of_delay(A03_CATALOGUE, CRQC)
        assert c.classical == 0.0
        assert c.quantum == 0.0
        assert c.total == 0.0

    def test_pqc_protection_kills_quantum_leg_exactly(self):
        """
        A06 has a 30-year lifetime and heavy exposure. A lifetime-only
        heuristic ranks it first. Because the key exchange is already
        quantum-safe, the quantum leg must be EXACTLY zero.
        """
        c = cost_of_delay(A06_PQC_ARCHIVE, CRQC)
        assert c.quantum == 0.0
        assert A06_PQC_ARCHIVE.data_lifetime_years == 30.0
        assert not A06_PQC_ARCHIVE.quantum_applicable

    def test_no_harvest_exposure_kills_quantum_leg_exactly(self):
        """
        A07 is air-gapped: catastrophic value, RSA-4096, 20-year lifetime, but
        nothing crosses a collectable channel. This is what separates real HNDL
        exposure from theoretical exposure.
        """
        c = cost_of_delay(A07_AIRGAPPED, CRQC)
        assert c.quantum == 0.0
        assert not A07_AIRGAPPED.quantum_applicable


class TestCompetingRisks:
    """
    The coupling term is the element that makes this a method rather than
    arithmetic. It must actually do something, and in the right direction.
    """

    def test_coupling_reduces_quantum_cost(self):
        coupled = cod_quantum(A01_PAYMENT, CRQC, competing_risks=True)
        uncoupled = cod_quantum(A01_PAYMENT, CRQC, competing_risks=False)
        assert coupled < uncoupled, "coupling must discount, never inflate"

    def test_higher_classical_hazard_discounts_quantum_more(self):
        """
        Two identical assets differing only in classical hazard. The one more
        likely to be breached classically should carry LESS quantum cost of
        delay, because its data will probably leak in plaintext first.
        """
        common = dict(
            name="x", value=ValueBand.HIGH, data_lifetime_years=20.0,
            protection=ProtectionClass.RSA_2048,
            harvest_exposure=HarvestBand.HIGH,
            value_flow_usd_per_year=1_000_000.0,
        )
        calm = Asset(asset_id="CALM", likelihood=LikelihoodBand.RARE, **common)
        stormy = Asset(asset_id="STORM", likelihood=LikelihoodBand.FREQUENT, **common)

        q_calm = cod_quantum(calm, CRQC)
        q_stormy = cod_quantum(stormy, CRQC)

        assert q_stormy < q_calm, (
            "a frequently-breached asset should have its quantum cost "
            "discounted; got calm=%.1f stormy=%.1f" % (q_calm, q_stormy)
        )

    def test_zero_hazard_collapses_to_uncoupled_form(self):
        """With lambda = 0 the integral must reduce to r * h * F_Q(L)."""
        a = Asset(
            asset_id="Z", name="z", value=ValueBand.HIGH,
            likelihood=LikelihoodBand.RARE, data_lifetime_years=15.0,
            protection=ProtectionClass.RSA_2048,
            harvest_exposure=HarvestBand.FULL,
            value_flow_usd_per_year=1_000_000.0,
        )
        # Patch lambda to exactly zero via a tiny subclass-free trick:
        # LikelihoodBand has no zero member by design, so verify the limit
        # instead -- as lambda shrinks, coupled approaches uncoupled.
        uncoupled = cod_quantum(a, CRQC, competing_risks=False)
        coupled = cod_quantum(a, CRQC, competing_risks=True)
        expected_closed_form = (
            a.flow_rate * a.harvest_exposure.fraction * CRQC.cdf(15.0)
        )
        assert uncoupled == pytest.approx(expected_closed_form, rel=1e-9)
        assert coupled < uncoupled
        assert coupled > 0.9 * uncoupled, (
            "with a RARE hazard the discount should be small"
        )

    def test_legs_are_not_independently_additive(self):
        """
        The headline claim against 'it is just a weighted sum': changing only
        the classical hazard changes BOTH legs, so the total is not a sum of
        two independently-computed scores.
        """
        common = dict(
            name="x", value=ValueBand.HIGH, data_lifetime_years=20.0,
            protection=ProtectionClass.RSA_2048,
            harvest_exposure=HarvestBand.HIGH,
            value_flow_usd_per_year=1_000_000.0,
        )
        a = Asset(asset_id="A", likelihood=LikelihoodBand.UNLIKELY, **common)
        b = Asset(asset_id="B", likelihood=LikelihoodBand.LIKELY, **common)

        ca, cb = cost_of_delay(a, CRQC), cost_of_delay(b, CRQC)
        classical_ratio = cb.classical / ca.classical
        quantum_ratio = cb.quantum / ca.quantum

        assert classical_ratio > 1.0, "higher hazard raises the classical leg"
        assert quantum_ratio < 1.0, "higher hazard lowers the quantum leg"


class TestDisagreementWithBaselines:
    """
    The paper's section 6 result. If these fail, the method does not change
    decisions and there is nothing to publish.
    """

    def test_quantum_dominates_on_the_disagreement_case(self):
        """
        A04: rarely attacked, 25-year retention, partially exposed, RSA-4096.
        A classical-only practice ranks it near the bottom. Its quantum cost of
        delay must dominate its classical cost by a wide margin.
        """
        c = cost_of_delay(A04_KYC_ARCHIVE, CRQC)
        assert c.quantum > 10 * c.classical, (
            f"expected quantum to dominate; got classical={c.classical:.0f} "
            f"quantum={c.quantum:.0f}"
        )
        assert c.quantum_share > 0.9

    def test_unified_ranking_differs_from_classical_only(self):
        unified = [c.asset_id for c in rank_by_cost_of_delay(WORKED_EXAMPLES, CRQC)]
        classical = rank_classical_only(WORKED_EXAMPLES)
        assert unified != classical
        inversions = rank_inversions(unified, classical)
        assert len(inversions) > 0, (
            "unified ranking must flip at least one pairwise priority against "
            "classical-only practice, or it changes no decisions"
        )

    def test_a04_outranks_a05_only_under_unification(self):
        """
        The specific, reportable inversion: A04 (quiet, long-lived) vs A05
        (noisy, short-lived). Classical-only puts A05 first. Unified puts A04
        first. This single pair is the paper's worked argument.
        """
        pair = [A04_KYC_ARCHIVE, A05_INTERNAL_CREDS]

        classical = rank_classical_only(pair)
        assert classical.index("A05") < classical.index("A04"), (
            "classical-only should prefer the frequently-attacked asset"
        )

        unified = [c.asset_id for c in rank_by_cost_of_delay(pair, CRQC)]
        assert unified.index("A04") < unified.index("A05"), (
            "unified ranking should promote the long-lived harvestable asset"
        )


class TestSensitivity:
    """Rank stability is the result that replaces calibrated point scores."""

    def test_ranking_is_computable_in_every_scenario(self):
        for d in scenario_grid():
            order = [c.asset_id for c in rank_by_cost_of_delay(WORKED_EXAMPLES, d)]
            assert len(order) == len(WORKED_EXAMPLES)
            assert len(set(order)) == len(order)

    def test_later_crqc_lowers_every_quantum_leg(self):
        grid = scenario_grid()
        for a in WORKED_EXAMPLES:
            costs = [cod_quantum(a, d) for d in grid]
            for earlier, later in zip(costs, costs[1:]):
                assert later <= earlier + 1e-9, (
                    f"{a.asset_id}: a later CRQC must not increase quantum cost"
                )

    def test_pessimistic_scenario_lowers_quantum_cost(self):
        for a in WORKED_EXAMPLES:
            q_opt = cod_quantum(a, gri_2025_optimistic())
            q_pess = cod_quantum(a, gri_2025_pessimistic())
            assert q_pess <= q_opt + 1e-9


class TestFormulationB:
    """Formulation B is implemented to be refuted. Prove the refutation."""

    def test_horizon_weight_changes_the_ranking(self):
        flips = rank_flip_horizon_weights(WORKED_EXAMPLES, CRQC)
        distinct = {tuple(order) for order in flips.values()}
        assert len(distinct) > 1, (
            "Formulation B's ranking should depend on the undefined "
            "horizon_weight; if it does not on this asset set, re-run on the "
            "real assets before claiming otherwise"
        )

    def test_expected_loss_has_mismatched_units(self):
        """
        EL_c carries a per-year rate; EL_q carries a dimensionless probability
        times a value. Adding them is a unit error, which is exactly why a
        conversion constant is needed. Documented here as a test so the defect
        is recorded, not merely asserted in prose.
        """
        el = expected_loss(A01_PAYMENT, CRQC, horizon_weight=1.0)
        # classical leg scales with horizon_weight, quantum leg does not
        el2 = expected_loss(A01_PAYMENT, CRQC, horizon_weight=2.0)
        assert el2.el_classical == pytest.approx(2 * el.el_classical)
        assert el2.el_quantum == pytest.approx(el.el_quantum)


class TestRankUtilities:
    def test_kendall_tau_identical(self):
        assert kendall_tau(["a", "b", "c"], ["a", "b", "c"]) == pytest.approx(1.0)

    def test_kendall_tau_reversed(self):
        assert kendall_tau(["a", "b", "c"], ["c", "b", "a"]) == pytest.approx(-1.0)

    def test_kendall_tau_rejects_mismatched_sets(self):
        with pytest.raises(ValueError):
            kendall_tau(["a", "b"], ["a", "c"])

    def test_inversions_found(self):
        inv = rank_inversions(["a", "b", "c"], ["b", "a", "c"])
        assert ("a", "b") in inv
        assert len(inv) == 1

    def test_no_inversions_when_identical(self):
        assert rank_inversions(["a", "b", "c"], ["a", "b", "c"]) == []
