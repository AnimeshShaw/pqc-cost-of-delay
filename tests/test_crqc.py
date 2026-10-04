"""Tests for the CRQC arrival distribution."""

import math

import pytest

from costofdelay.crqc import (
    GRI_2025_OPTIMISTIC,
    GRI_2025_PESSIMISTIC,
    MEDIAN_SCENARIOS,
    AnchorError,
    CRQCDistribution,
    gri_2025_optimistic,
    gri_2025_pessimistic,
    scenario_grid,
)


class TestAnchorFit:
    """The fit must reproduce the published figures exactly."""

    @pytest.mark.parametrize("anchors", [GRI_2025_PESSIMISTIC, GRI_2025_OPTIMISTIC])
    def test_reproduces_published_anchors(self, anchors):
        d = CRQCDistribution.from_anchors(anchors)
        for horizon, published in anchors:
            assert d.cdf(horizon) == pytest.approx(published, abs=1e-9), (
                f"fitted F_Q({horizon})={d.cdf(horizon):.6f} does not match "
                f"published {published}"
            )

    def test_pessimistic_is_below_optimistic_in_the_decision_range(self):
        """
        Over any plausible data lifetime (0-40y) the pessimistic scenario must
        assign lower probability than the optimistic one. See
        test_known_crossover_artifact below for what happens past that.
        """
        pess, opt = gri_2025_pessimistic(), gri_2025_optimistic()
        for t in [1, 5, 10, 15, 20, 25, 30, 40]:
            assert pess.cdf(t) < opt.cdf(t), f"scenarios cross at t={t}"

    def test_known_crossover_artifact(self):
        """
        DOCUMENTED MODEL ARTIFACT, not a bug.

        Fitting two independent Weibulls to two anchor pairs yields different
        shape parameters (beta 1.91 pessimistic vs 1.43 optimistic). The
        steeper curve eventually overtakes the shallower one, so the two
        scenarios cross at roughly t=45y, where both CDFs are ~0.997.

        This is immaterial: no asset in any register has a 45-year
        confidentiality requirement, and at the crossover the two scenarios
        differ by less than 0.0004. But it must be stated in the spec rather
        than discovered by a reviewer, and it is a reason to prefer a shared
        shape parameter if the model is ever extended past 40 years.
        """
        pess, opt = gri_2025_pessimistic(), gri_2025_optimistic()

        lo, hi = 15.0, 200.0
        for _ in range(200):
            mid = (lo + hi) / 2.0
            if pess.cdf(mid) < opt.cdf(mid):
                lo = mid
            else:
                hi = mid

        assert 40.0 < lo < 50.0, f"crossover moved to t={lo:.1f}y; re-check the spec"
        assert pess.cdf(lo) > 0.99, "crossover occurs deep in the saturated tail"
        assert abs(pess.cdf(lo) - opt.cdf(lo)) < 1e-3

    def test_shape_parameters_are_plausible(self):
        """
        beta > 1 means a rising hazard -- the conditional probability of CRQC
        arrival increases over time. That is the expected shape for a
        technology-arrival process, and it also guarantees f(0)=0 so the
        competing-risks integral is well behaved at the origin.
        """
        for d in (gri_2025_pessimistic(), gri_2025_optimistic()):
            assert d.beta > 1.0, f"{d.label} has beta={d.beta} <= 1"
            assert 5.0 < d.alpha < 40.0, f"{d.label} has implausible alpha={d.alpha}"


class TestCDFProperties:
    def test_cdf_is_a_cdf(self):
        d = gri_2025_optimistic()
        assert d.cdf(0.0) == 0.0
        assert d.cdf(-1.0) == 0.0
        prev = 0.0
        for t in [0.1, 1, 5, 10, 20, 50, 100, 500]:
            v = d.cdf(t)
            assert 0.0 <= v <= 1.0
            assert v >= prev, f"not monotone at t={t}"
            prev = v
        assert d.cdf(1000.0) == pytest.approx(1.0, abs=1e-6)

    def test_pdf_integrates_to_cdf(self):
        """Sanity check that pdf and cdf are consistent."""
        from costofdelay.scoring import _simpson

        d = gri_2025_optimistic()
        for upper in [5.0, 10.0, 25.0]:
            integral = _simpson(d.pdf, 0.0, upper, n=4000)
            assert integral == pytest.approx(d.cdf(upper), rel=1e-4)

    def test_pdf_vanishes_at_origin(self):
        """Required for the competing-risks integral to be well behaved."""
        for d in (gri_2025_pessimistic(), gri_2025_optimistic()):
            assert d.pdf(0.0) == 0.0

    def test_quantile_inverts_cdf(self):
        d = gri_2025_optimistic()
        for p in [0.05, 0.25, 0.5, 0.75, 0.95]:
            assert d.cdf(d.quantile(p)) == pytest.approx(p, abs=1e-9)

    def test_median_consistent_with_quantile(self):
        d = gri_2025_pessimistic()
        assert d.median_years() == pytest.approx(d.quantile(0.5), abs=1e-9)


class TestShortLifetimes:
    """The session-token case: minutes of lifetime must give ~zero probability."""

    def test_minutes_of_lifetime_is_negligible(self):
        five_minutes = 5.0 / (365.0 * 24.0 * 60.0)
        for d in (gri_2025_pessimistic(), gri_2025_optimistic()):
            assert d.cdf(five_minutes) < 1e-7, (
                f"{d.label} assigns {d.cdf(five_minutes):.3e} to a 5-minute "
                "lifetime; the formula must make short-lived data vanish "
                "without a special-case rule"
            )


class TestScenarioGrid:
    def test_grid_medians_match_requested_years(self):
        for year, d in zip(MEDIAN_SCENARIOS, scenario_grid()):
            years_out = year - 2026
            assert d.median_years() == pytest.approx(years_out, abs=1e-6)

    def test_later_medians_give_lower_probabilities(self):
        grid = scenario_grid()
        for earlier, later in zip(grid, grid[1:]):
            assert earlier.cdf(10.0) > later.cdf(10.0)


class TestAnchorValidation:
    def test_rejects_wrong_anchor_count(self):
        with pytest.raises(AnchorError, match="exactly 2"):
            CRQCDistribution.from_anchors(((10.0, 0.3),))

    def test_rejects_non_monotone_anchors(self):
        with pytest.raises(AnchorError, match="must increase"):
            CRQCDistribution.from_anchors(((10.0, 0.5), (15.0, 0.4)))

    def test_rejects_degenerate_probabilities(self):
        with pytest.raises(AnchorError):
            CRQCDistribution.from_anchors(((10.0, 0.0), (15.0, 0.5)))
        with pytest.raises(AnchorError):
            CRQCDistribution.from_anchors(((10.0, 0.5), (15.0, 1.0)))

    def test_rejects_bad_horizons(self):
        with pytest.raises(AnchorError):
            CRQCDistribution.from_anchors(((0.0, 0.3), (15.0, 0.5)))

    def test_extrapolation_is_flagged(self):
        d = gri_2025_optimistic()
        assert not d.is_extrapolated(12.0)
        assert d.is_extrapolated(25.0), (
            "values beyond the published anchors must be reported as "
            "extrapolation, not as GRI figures"
        )
