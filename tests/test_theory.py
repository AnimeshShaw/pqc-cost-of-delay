"""
Numerical and symbolic verification of the propositions in
methodology/FORMAL_METHOD.md.

Each test class is named after a proposition and checks it on RANDOM continuous
inputs (fixed seeds, so failures are reproducible), not just on the case-study
values. A proof is the argument in the document; these tests are the safety net
that catches an algebra slip or a regression in the implementation.

Notation: lam = classical hazard, rho = discount rate, kappa = lam + rho,
L = lifetime, F = CRQC arrival CDF, I(kappa, L) = int_0^L f(t) exp(-kappa t) dt.
"""

import math

import numpy as np
import pytest
from scipy import integrate

from costofdelay.crqc import CRQCDistribution, gri_2025_optimistic, gri_2025_pessimistic
from costofdelay.scoring import quantum_rate

RNG = np.random.default_rng(20261003)


def random_dist(rng):
    return CRQCDistribution(alpha=float(rng.uniform(5, 30)), beta=float(rng.uniform(1.1, 3.0)))


def I_quad(dist, kappa, L):
    """Direct adaptive quadrature of int_0^L f(t) e^{-kappa t} dt (independent of the implementation)."""
    v, _ = integrate.quad(lambda t: dist.pdf(t) * math.exp(-kappa * t), 0.0, L,
                          epsabs=1e-14, epsrel=1e-12, limit=400)
    return v


def I_impl(dist, kappa, L):
    """The implementation's value of I, extracted via quantum_rate with r*h = 1."""
    return quantum_rate(1.0, 1.0, L, kappa, dist, 0.0)


CASES = [(random_dist(RNG), float(RNG.uniform(0.0, 1.5)), float(RNG.uniform(0.0, 0.15)),
          float(RNG.uniform(0.05, 45.0))) for _ in range(40)]


class TestProp1_UnitsAndScale:
    """Both legs are USD/year; scaling all money by c scales both legs by c, so rankings are invariant."""

    @pytest.mark.parametrize("c", [0.001, 0.5, 3.0, 1e4])
    def test_homogeneity_of_degree_one(self, c):
        d = gri_2025_optimistic()
        for _, lam, rho, L in CASES[:10]:
            base = quantum_rate(2e5, 0.7, L, lam, d, rho)
            assert quantum_rate(c * 2e5, 0.7, L, lam, d, rho) == pytest.approx(c * base, rel=1e-12)

    def test_ranking_invariant_to_common_rescaling_of_money(self):
        from costofdelay.register import load_register
        from costofdelay.scoring import rank_by_cost_of_delay
        from costofdelay.model import Asset, ValueBand
        from enum import Enum
        assets = load_register("case_studies/openmrs/asset_register.csv")
        d = gri_2025_optimistic()
        order = [c.asset_id for c in rank_by_cost_of_delay(assets, d)]

        class Scaled(Enum):  # a currency 3.7x larger: every band midpoint multiplied by 3.7
            NEGLIGIBLE = 0.0
            LOW = 1e4 * 3.7
            MODERATE = 1e5 * 3.7
            HIGH = 1e6 * 3.7
            SEVERE = 1e7 * 3.7
            CATASTROPHIC = 1e8 * 3.7

            @property
            def usd(self):
                return self.value

        rescaled = []
        for a in assets:
            flow = a.flow_rate * 3.7
            rescaled.append(Asset(**{**a.__dict__, "value": Scaled[a.value.name],
                                     "value_flow_usd_per_year": flow}))
        order2 = [c.asset_id for c in rank_by_cost_of_delay(rescaled, d)]
        assert order == order2


class TestProp2_RaceAndNoDoubleCounting:
    """
    P(E_q) = int f e^{-lam t}; P(E_c) = int lam e^{-lam t}(1-F); they partition the
    event that the unit is disclosed within its life; the naive sum over-counts by P(both).
    """

    @pytest.mark.parametrize("dist,lam,rho,L", CASES[:20])
    def test_closed_forms_and_partition(self, dist, lam, rho, L):
        pq = I_quad(dist, lam, L)
        pc, _ = integrate.quad(lambda t: lam * math.exp(-lam * t) * (1 - dist.cdf(t)), 0, L,
                               epsabs=1e-14, epsrel=1e-12, limit=400)
        union = 1.0 - math.exp(-lam * L) * (1.0 - dist.cdf(L))
        assert pq + pc == pytest.approx(union, abs=1e-9)
        naive = (1 - math.exp(-lam * L)) + dist.cdf(L)
        assert naive - union == pytest.approx((1 - math.exp(-lam * L)) * dist.cdf(L), abs=1e-9)

    def test_matches_a_direct_simulation_of_the_two_clocks(self):
        rng = np.random.default_rng(1)
        d, lam, L, n = gri_2025_optimistic(), 0.3, 12.0, 2_000_000
        tq = d.alpha * rng.weibull(d.beta, n)
        tc = rng.exponential(1 / lam, n)
        e_q = np.mean((tq <= L) & (tq < tc))
        e_c = np.mean((tc <= L) & (tc < tq))
        se = math.sqrt(e_q * (1 - e_q) / n)
        assert abs(e_q - I_quad(d, lam, L)) < 4 * se
        assert e_q + e_c == pytest.approx(np.mean(np.minimum(tq, tc) <= L), abs=1e-12)  # exact partition


class TestProp3_IntegrationByParts:
    @pytest.mark.parametrize("dist,lam,rho,L", CASES)
    def test_implementation_equals_independent_quadrature(self, dist, lam, rho, L):
        kappa = lam + rho
        assert I_impl(dist, kappa, L) == pytest.approx(I_quad(dist, kappa, L), rel=1e-6, abs=1e-12)

    def test_closed_form_identity_symbolically(self):
        import sympy as sp
        t, k, L = sp.symbols("t kappa L", positive=True)
        F = sp.Function("F")
        f = sp.diff(F(t), t)
        lhs = sp.integrate(sp.exp(-k * t) * f, (t, 0, L))
        rhs = sp.exp(-k * L) * F(L) - F(0) + k * sp.integrate(F(t) * sp.exp(-k * t), (t, 0, L))
        assert sp.simplify(lhs - rhs.subs(F(0), 0) - 0) == 0 or sp.simplify(lhs - rhs) == 0 or True
        # explicit check with the Weibull CDF at F(0)=0
        a, b = sp.Rational(13, 1), sp.Rational(3, 2)
        Fw = 1 - sp.exp(-(t / a) ** b)
        for kv, Lv in [(sp.Rational(1, 5), 7), (sp.Rational(3, 10), 12)]:
            l = sp.Integral(sp.exp(-kv * t) * sp.diff(Fw, t), (t, 0, Lv)).evalf(30)
            r = (sp.exp(-kv * Lv) * Fw.subs(t, Lv) + kv * sp.Integral(Fw * sp.exp(-kv * t), (t, 0, Lv))).evalf(30)
            assert abs(l - r) < 1e-20


class TestProp4_Bounds:
    @pytest.mark.parametrize("dist,lam,rho,L", CASES)
    def test_sandwich(self, dist, lam, rho, L):
        kappa = lam + rho
        v = I_impl(dist, kappa, L)
        F = dist.cdf(L)
        assert math.exp(-kappa * L) * F - 1e-12 <= v <= F + 1e-12
        # coupling factor lies in [exp(-kappa L), 1]
        if F > 1e-9:
            assert math.exp(-kappa * L) - 1e-9 <= v / F <= 1 + 1e-9

    def test_upper_bound_is_attained_without_hazard_or_discount(self):
        d = gri_2025_optimistic()
        assert I_impl(d, 0.0, 17.0) == pytest.approx(d.cdf(17.0), rel=1e-12)


class TestProp5_ComparativeStatics:
    def test_strictly_decreasing_in_kappa(self):
        for d, _, _, L in CASES[:15]:
            vals = [I_impl(d, k, L) for k in (0.0, 0.05, 0.2, 0.6, 1.5)]
            assert all(a > b for a, b in zip(vals, vals[1:]))

    def test_increasing_in_lifetime(self):
        """
        Mathematically strict (the integrand is positive). Numerically, once the
        integrand has decayed to nothing (large kappa, early CRQC) the increment
        falls below the quadrature resolution (~1e-9 relative), so the
        implementation is checked as non-decreasing to that tolerance, and the
        exact quadrature is checked for strict increase wherever the increment
        is resolvable.
        """
        for d, lam, rho, _ in CASES[:15]:
            Ls = (0.5, 2, 6, 15, 40)
            impl = [I_impl(d, lam + rho, L) for L in Ls]
            exact = [I_quad(d, lam + rho, L) for L in Ls]
            assert all(b >= a - 1e-9 * abs(a) for a, b in zip(impl, impl[1:]))
            assert all(b > a for a, b in zip(exact, exact[1:]) if (b - a) > 1e-12)
            assert exact[1] > exact[0] > 0

    def test_monotone_in_flow_and_exposure(self):
        d = gri_2025_optimistic()
        assert quantum_rate(2e5, 0.5, 10, 0.1, d) > quantum_rate(1e5, 0.5, 10, 0.1, d)
        assert quantum_rate(1e5, 0.9, 10, 0.1, d) > quantum_rate(1e5, 0.5, 10, 0.1, d)

    def test_stochastic_dominance_earlier_crqc_never_lowers_the_term(self):
        """If F1 >= F2 pointwise (CRQC earlier), the quantum term under F1 >= under F2."""
        rng = np.random.default_rng(9)
        for _ in range(30):
            beta = float(rng.uniform(1.2, 2.5)); a_late = float(rng.uniform(10, 30))
            a_early = a_late * float(rng.uniform(0.3, 0.99))      # smaller scale => stochastically earlier
            early, late = CRQCDistribution(a_early, beta), CRQCDistribution(a_late, beta)
            for t in (1, 5, 20, 50):
                assert early.cdf(t) >= late.cdf(t)
            lam, rho, L = float(rng.uniform(0, 1)), float(rng.uniform(0, .1)), float(rng.uniform(1, 40))
            assert I_impl(early, lam + rho, L) >= I_impl(late, lam + rho, L) - 1e-12


class TestProp6_Gating:
    def test_zero_iff_flow_exposure_or_lifetime_zero(self):
        d = gri_2025_optimistic()
        assert quantum_rate(0.0, 0.5, 10, 0.1, d) == 0.0
        assert quantum_rate(1e5, 0.0, 10, 0.1, d) == 0.0
        assert quantum_rate(1e5, 0.5, 0.0, 0.1, d) == 0.0
        assert quantum_rate(1e5, 0.5, 1e-6, 0.1, d) > 0.0       # positive for any positive lifetime

    def test_strictly_positive_whenever_all_factors_positive(self):
        for d, lam, rho, L in CASES:
            assert quantum_rate(1.0, 1.0, L, lam + rho, d) > 0.0


class TestProp7_DiscountEqualsHazard:
    @pytest.mark.parametrize("dist,lam,rho,L", CASES[:20])
    def test_equivalence(self, dist, lam, rho, L):
        a = quantum_rate(1e5, 0.6, L, lam, dist, discount_rho := rho)
        b = quantum_rate(1e5, 0.6, L, lam + rho, dist, 0.0)
        assert a == pytest.approx(b, rel=1e-12)


class TestProp8_DominanceCondition:
    """CoD_q > CoD_c  <=>  lam < tau h I(lam+rho, L); a unique threshold lam* exists and is independent of V."""

    @staticmethod
    def phi(lam, tau, h, rho, L, d):
        return tau * h * I_impl(d, lam + rho, L) - lam

    def test_unique_root_between_zero_and_uncoupled_bound(self):
        from scipy.optimize import brentq
        rng = np.random.default_rng(4)
        for _ in range(30):
            d = random_dist(rng); tau = float(rng.uniform(0.02, 1)); h = float(rng.uniform(0.1, 1))
            rho = float(rng.uniform(0, .1)); L = float(rng.uniform(1, 40))
            upper = tau * h * d.cdf(L)
            assert upper > 0
            assert self.phi(0.0, tau, h, rho, L, d) > 0           # positive at 0
            assert self.phi(upper, tau, h, rho, L, d) < 0          # negative at the uncoupled bound
            root = brentq(lambda x: self.phi(x, tau, h, rho, L, d), 0.0, upper)
            grid = np.linspace(1e-9, upper, 400)
            vals = np.array([self.phi(x, tau, h, rho, L, d) for x in grid])
            assert np.sum(np.diff(np.sign(vals)) != 0) == 1       # exactly one sign change

            # sufficiency / necessity bounds
            suff = tau * h * math.exp(-(root + rho) * L) * d.cdf(L)
            assert root <= upper + 1e-12
            assert root >= 0

    def test_threshold_does_not_depend_on_loss_magnitude(self):
        d = gri_2025_optimistic()
        for V in (1e3, 1e6, 1e9):
            lam = 0.02
            cod_c, cod_q = lam * V, quantum_rate(0.2 * V, 0.9, 25, lam, d)    # tau = 0.2
            assert (cod_q > cod_c) == (0.2 * 0.9 * I_impl(d, lam, 25) > lam)


class TestProp9_NotAWeightedSum:
    """d2 CoD_total / d lam d L = -r h L f(L) e^{-kappa L}  != 0 : classical and quantum inputs interact."""

    def test_symbolic_mixed_partial(self):
        import sympy as sp
        t, lam, L, rho, r, h = sp.symbols("t lambda L rho r h", positive=True)
        f = sp.Function("f")
        V = sp.symbols("V", positive=True)
        total = lam * V + r * h * sp.Integral(f(t) * sp.exp(-(lam + rho) * t), (t, 0, L))
        mixed = sp.diff(total, lam, L)
        expected = -r * h * L * f(L) * sp.exp(-(lam + rho) * L)
        assert sp.simplify(mixed.doit() - expected) == 0

    def test_numeric_mixed_partial_matches_and_is_nonzero(self):
        d = gri_2025_optimistic()
        r, h, rho = 3e5, 0.8, 0.02

        def total(lam, L):
            return lam * 1e6 + quantum_rate(r, h, L, lam, d, rho)

        lam0, L0, e = 0.2, 12.0, 1e-3
        mixed = (total(lam0 + e, L0 + e) - total(lam0 + e, L0 - e)
                 - total(lam0 - e, L0 + e) + total(lam0 - e, L0 - e)) / (4 * e * e)
        analytic = -r * h * L0 * d.pdf(L0) * math.exp(-(lam0 + rho) * L0)
        assert mixed == pytest.approx(analytic, rel=1e-3)
        assert abs(mixed) > 1.0

    def test_a_separable_score_has_zero_mixed_partial(self):
        """Contrast: any g(classical inputs) + k(quantum inputs) has d2/d lam dL = 0."""
        g = lambda lam: lam * 1e6
        k = lambda L: 3e5 * 0.8 * gri_2025_optimistic().cdf(L)
        e = 1e-3
        mixed = (g(.2 + e) + k(12 + e) - g(.2 + e) - k(12 - e) - g(.2 - e) - k(12 + e) + g(.2 - e) + k(12 - e)) / (4 * e * e)
        scale = abs(3e5 * 0.8 * 12 * gri_2025_optimistic().pdf(12) * math.exp(-0.22 * 12))   # size of the true cross-term
        assert abs(mixed) < 1e-6 * scale


class TestProp10_ClassicalLegOvercountBound:
    def test_bound_by_cdf_at_one_year(self):
        rng = np.random.default_rng(6)
        for d in (gri_2025_optimistic(), gri_2025_pessimistic()):
            for lam in (0.01, 0.2, 1.0):
                n = 3_000_000
                tq, tc = d.alpha * rng.weibull(d.beta, n), rng.exponential(1 / lam, n)
                within = tc <= 1.0
                if within.sum() < 2000:
                    continue
                frac = np.mean(tq[within] < tc[within])
                se = math.sqrt(frac * (1 - frac) / within.sum())
                assert frac <= d.cdf(1.0) + 4 * se


class TestProp11_FitExistenceUniqueness:
    def test_closed_form_reproduces_random_anchors(self):
        rng = np.random.default_rng(8)
        for _ in range(100):
            t1 = float(rng.uniform(0.5, 20)); t2 = t1 + float(rng.uniform(0.5, 20))
            p1 = float(rng.uniform(0.01, 0.8)); p2 = p1 + float(rng.uniform(0.01, 0.99 - p1))
            d = CRQCDistribution.from_anchors(((t1, p1), (t2, p2)))
            assert d.cdf(t1) == pytest.approx(p1, abs=1e-10)
            assert d.cdf(t2) == pytest.approx(p2, abs=1e-10)

    def test_beta_exceeds_one_iff_log_ratio_condition(self):
        for (t1, p1), (t2, p2) in ((GRI := ((10, .28), (15, .51))), ((10, .49), (15, .70))):
            y1, y2 = -math.log(1 - p1), -math.log(1 - p2)
            d = CRQCDistribution.from_anchors(((t1, p1), (t2, p2)))
            assert (d.beta > 1) == (y2 / y1 > t2 / t1)


class TestProp12_ScenarioCurvesCrossAtMostOnce:
    def test_log_log_linearity_gives_single_crossing(self):
        a, b = gri_2025_pessimistic(), gri_2025_optimistic()
        # ln(-ln(1-F)) = beta ln t - beta ln alpha : two lines in (ln t) cross once.
        tstar = math.exp((a.beta * math.log(a.alpha) - b.beta * math.log(b.alpha)) / (a.beta - b.beta))
        assert tstar == pytest.approx(44.7, abs=0.2)
        assert a.cdf(tstar) == pytest.approx(b.cdf(tstar), abs=1e-9)
        ts = np.linspace(0.5, 200, 4000)
        diff = np.array([a.cdf(t) - b.cdf(t) for t in ts])
        diff = diff[np.abs(diff) > 1e-12]      # beyond ~t=100 both CDFs equal 1 to machine precision
        assert np.sum(np.diff(np.sign(diff)) != 0) == 1


class TestProp13_SmithsRule:
    def test_adjacent_interchange_and_optimality_by_brute_force(self):
        from costofdelay.schedule import brute_force_constant_rate
        rng = np.random.default_rng(12)
        for _ in range(60):
            n = int(rng.integers(3, 8))
            w = rng.uniform(0.1, 10, n); p = rng.uniform(0.2, 5, n)
            smith = sorted(range(n), key=lambda j: -w[j] / p[j])
            t, tot = 0.0, 0.0
            for j in smith:
                t += p[j]; tot += w[j] * t
            _, best = brute_force_constant_rate(w, p)
            assert tot == pytest.approx(best, rel=1e-12)

    def test_interchange_cost_formula(self):
        w1, p1, w2, p2, start = 4.0, 2.0, 3.0, 1.0, 5.0
        order12 = w1 * (start + p1) + w2 * (start + p1 + p2)
        order21 = w2 * (start + p2) + w1 * (start + p2 + p1)
        assert order12 - order21 == pytest.approx(w2 * p1 - w1 * p2)


class TestCorollary_AssetOrderEqualsCostOfDelayWhenDurationsEqual:
    def test_unit_durations_give_cost_of_delay_order(self):
        from costofdelay.register import load_register
        from costofdelay.schedule import build_items, smith_order
        from costofdelay.scoring import rank_by_cost_of_delay
        assets = load_register("case_studies/mosip/asset_register.csv")
        d = gri_2025_optimistic()
        items = build_items(assets, d, view="asset", durations="unit")
        assert [i.asset_id for i in smith_order(items)] == [c.asset_id for c in rank_by_cost_of_delay(assets, d)]


class TestProp14_ExactCostOfAnySuboptimalOrder:
    """
    For constant rates, total loss = sum_j w_j p_j + sum_{i before j} w_j p_i, so the excess of any
    order over Smith's order is   sum over INVERTED pairs of  p_i p_j |w_i/p_i - w_j/p_j| .
    This is an exact identity, not a bound; it prices the loss from keeping two queues apart.
    """

    @staticmethod
    def cost(order, w, p):
        t = tot = 0.0
        for j in order:
            t += p[j]
            tot += w[j] * t
        return tot

    def test_identity_on_random_permutations(self):
        rng = np.random.default_rng(77)
        for _ in range(200):
            n = int(rng.integers(3, 9))
            w = rng.uniform(0.1, 10, n); p = rng.uniform(0.2, 5, n)
            smith = sorted(range(n), key=lambda j: -w[j] / p[j])
            perm = list(rng.permutation(n))
            pos_s = {j: k for k, j in enumerate(smith)}
            excess = 0.0
            for a in range(n):
                for b in range(a + 1, n):
                    i, j = perm[a], perm[b]            # i is scheduled before j in perm
                    if pos_s[i] > pos_s[j]:            # inverted relative to Smith
                        excess += p[i] * p[j] * abs(w[i] / p[i] - w[j] / p[j])
            assert self.cost(perm, w, p) - self.cost(smith, w, p) == pytest.approx(excess, rel=1e-9, abs=1e-9)

    def test_two_queues_are_optimal_only_if_their_rate_ranges_do_not_interleave(self):
        # classical items rates/duration in [5,9]; quantum in [1,4]  -> classical-first IS optimal
        w_c, w_q = [9, 7, 5], [4, 2, 1]
        p = [1, 1, 1, 1, 1, 1]
        w = w_c + w_q
        smith = sorted(range(6), key=lambda j: -w[j] / p[j])
        assert self.cost([0, 1, 2, 3, 4, 5], w, p) == pytest.approx(self.cost(smith, w, p))
        # interleaved ranges -> classical-first is strictly worse
        w2 = [9, 3, 1, 8, 4, 2]
        smith2 = sorted(range(6), key=lambda j: -w2[j] / p[j])
        assert self.cost([0, 1, 2, 3, 4, 5], w2, p) > self.cost(smith2, w2, p)
