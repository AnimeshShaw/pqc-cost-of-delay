"""
REFUTATION TESTS: could the method be trivial?

If ranking by cost of delay turned out to be rank-identical to simply sorting
assets by data lifetime, then the mathematics would contribute nothing beyond
the register's data-lifetime column. These tests try to refute the method's
usefulness against three simple baselines: (i) a lifetime sort, (ii) a
classical-only ranking, (iii) Mosca's binary gate.

They are written as tests rather than notes so that any change to the model
that silently collapses it into one of the baselines is caught.

If one of these fails, do not patch the test: re-examine the model.
"""

import pytest

from costofdelay.crqc import gri_2025_optimistic, gri_2025_pessimistic, scenario_grid
from costofdelay.examples import WORKED_EXAMPLES
from costofdelay.scoring import (
    kendall_tau,
    rank_by_cost_of_delay,
    rank_by_lifetime_only,
    rank_classical_only,
    rank_inversions,
    rank_mosca_gate,
)


def _unified(crqc):
    return [c.asset_id for c in rank_by_cost_of_delay(WORKED_EXAMPLES, crqc)]


class TestNotJustLifetime:
    """The core refutation test."""

    def test_differs_from_lifetime_only_ordering(self):
        unified = _unified(gri_2025_optimistic())
        lifetime = rank_by_lifetime_only(WORKED_EXAMPLES)

        inversions = rank_inversions(unified, lifetime)

        assert unified != lifetime, (
            "REFUTED: cost-of-delay ranking is identical to "
            "sorting by data lifetime. The mathematics adds nothing. "
            "Re-examine the model."
        )
        assert len(inversions) >= 3, (
            f"only {len(inversions)} pairwise disagreements with a plain "
            "lifetime sort. Too few to claim the scoring does real work."
        )

    def test_differs_substantially_not_marginally(self):
        """
        A tau of 0.95 would be a technical pass and a substantive failure.
        Require that the orderings are genuinely different.
        """
        tau = kendall_tau(_unified(gri_2025_optimistic()),
                          rank_by_lifetime_only(WORKED_EXAMPLES))
        assert tau < 0.8, (
            f"Kendall tau vs lifetime-only is {tau:.3f}. The scoring function "
            "is close to a proxy for data lifetime, which is not a defensible "
            "contribution."
        )

    def test_holds_under_every_crqc_scenario(self):
        """
        The refutation must not depend on a convenient CRQC assumption.
        """
        lifetime = rank_by_lifetime_only(WORKED_EXAMPLES)
        scenarios = list(scenario_grid()) + [
            gri_2025_optimistic(), gri_2025_pessimistic()
        ]
        for d in scenarios:
            assert _unified(d) != lifetime, (
                f"REFUTED under scenario '{d.label}': ranking "
                "collapses to a lifetime sort."
            )

    def test_the_specific_counterexamples_exist(self):
        """
        Name the assets that break the lifetime proxy, so the spec can cite
        them concretely rather than appealing to a statistic.

        A06 (30y, PQC-protected) and A07 (20y, air-gapped) hold the two longest
        lifetimes in the set. A lifetime-only heuristic ranks them 1st and 3rd.
        Under cost of delay their quantum leg is exactly zero, so whatever rank
        they hold must be earned entirely by their classical leg.

        Note what this test does NOT assert: that they rank low. A07 carries
        catastrophic value and a real classical hazard, so a high unified rank
        is CORRECT -- that is the point of one register covering both surfaces.
        The claim is that the quantum leg contributes nothing to their position.
        """
        from costofdelay.scoring import cod_quantum, cod_classical

        crqc = gri_2025_optimistic()
        lifetime = rank_by_lifetime_only(WORKED_EXAMPLES)

        assert lifetime[0] == "A06", "A06 has the longest lifetime (30y)"
        assert "A07" in lifetime[:3], "A07 has a 20y lifetime"

        by_id = {a.asset_id: a for a in WORKED_EXAMPLES}
        for aid in ("A06", "A07"):
            asset = by_id[aid]
            assert cod_quantum(asset, crqc) == 0.0, (
                f"{aid} must have a zero quantum leg despite its long lifetime"
            )

        # Their position is driven purely by the classical leg: restricting the
        # set to the zero-quantum assets must give the same order either way.
        zero_q = [a for a in WORKED_EXAMPLES if cod_quantum(a, crqc) == 0.0]
        assert {a.asset_id for a in zero_q} >= {"A03", "A06", "A07"}
        assert [c.asset_id for c in rank_by_cost_of_delay(zero_q, crqc)] == \
            rank_classical_only(zero_q), (
                "for zero-quantum assets the unified ranking must reduce "
                "exactly to the classical ranking"
            )


class TestHowMuchUnificationChanges:
    """
    FINDING, recorded rather than optimised away (2026-10-02).

    On the placeholder asset set, the quantum leg materially changes the cost
    of delay for individual assets (A01 46% quantum share, A04 98%) but flips
    only ONE of 21 pairwise priority decisions against classical-only practice.

    Why: the value bands are log-spaced 10x apart, so a single band difference
    in asset value (10x) swamps almost any quantum contribution, which in these
    examples peaks at roughly 1x the classical leg. Band granularity is
    therefore a design parameter that directly controls how often unification
    changes decisions -- see methodology/STATISTICS.md.

    This is the central risk to the contribution. These tests PIN the current
    number so a regression is visible; they deliberately do not demand a high
    count, because demanding one would be an invitation to tune the example
    assets until the desired conclusion appeared. The honest resolution is real data:
    real elicited data on a real system.
    """

    def test_inversion_count_against_classical_is_pinned(self):
        unified = _unified(gri_2025_optimistic())
        classical = rank_classical_only(WORKED_EXAMPLES)
        inversions = rank_inversions(unified, classical)

        n_pairs = len(WORKED_EXAMPLES) * (len(WORKED_EXAMPLES) - 1) // 2
        assert n_pairs == 21

        assert len(inversions) == 1, (
            f"placeholder inversion count changed from 1 to {len(inversions)}. "
            "If the example assets were edited, confirm the change was for a "
            "modelling reason and not to inflate this number, then update "
            "the paper's evaluation section and this test together."
        )
        assert inversions == [("A04", "A05")]

    def test_quantum_leg_is_material_per_asset_even_when_rank_is_stable(self):
        """
        The distinction that keeps the contribution alive: the quantum leg can
        dominate an asset's cost of delay (so it changes the stated magnitude
        and the roadmap justification) even where it does not reorder the list.
        """
        from costofdelay.scoring import cost_of_delay

        crqc = gri_2025_optimistic()
        by_id = {a.asset_id: a for a in WORKED_EXAMPLES}

        a01 = cost_of_delay(by_id["A01"], crqc)
        assert 0.3 < a01.quantum_share < 0.6, (
            f"A01 quantum share {a01.quantum_share:.2f} outside expected band"
        )

        a04 = cost_of_delay(by_id["A04"], crqc)
        assert a04.quantum_share > 0.9, (
            f"A04 quantum share {a04.quantum_share:.2f}; this is the asset "
            "where classical-only practice is most wrong"
        )


class TestNotJustClassical:
    """Secondary: the quantum leg must change something, or why unify."""

    def test_differs_from_classical_only(self):
        unified = _unified(gri_2025_optimistic())
        classical = rank_classical_only(WORKED_EXAMPLES)
        assert unified != classical, (
            "unified ranking equals classical-only ranking: the quantum leg "
            "changes no decisions and the unification claim is empty"
        )
        assert len(rank_inversions(unified, classical)) >= 1


class TestNotJustMosca:
    """
    Tertiary: Mosca's gate must be insufficient, or the contribution is
    already in the 2018 literature.
    """

    def test_mosca_gate_cannot_order_within_its_set(self):
        """
        The gate's defining limitation: it partitions assets into act-now and
        later, but gives no ordering inside the act-now set. Demonstrate that
        more than one asset fails the inequality, so the gate leaves a real
        decision unmade.
        """
        crqc = gri_2025_optimistic()
        z = crqc.median_years()
        failing = [a for a in WORKED_EXAMPLES if a.fails_mosca(z)]
        assert len(failing) >= 3, (
            f"only {len(failing)} assets fail Mosca's inequality; need several "
            "to demonstrate that the gate leaves the ordering problem open"
        )

    def test_differs_from_mosca_ordering(self):
        unified = _unified(gri_2025_optimistic())
        mosca = rank_mosca_gate(WORKED_EXAMPLES, gri_2025_optimistic())
        assert unified != mosca, (
            "unified ranking equals the Mosca-gate ordering: the contribution "
            "is already taught by Mosca 2018"
        )
