"""Tests for costofdelay.stats and costofdelay.schedule."""

import math

import numpy as np
import pytest

from costofdelay.crqc import gri_2025_optimistic
from costofdelay.examples import WORKED_EXAMPLES, A04_KYC_ARCHIVE
from costofdelay.register import load_register
from costofdelay.schedule import (build_items, optimal_order, siloed_order, smith_order,
                                  total_loss, quantum_accrual_rate)
from costofdelay.stats import (bootstrap_ci, cluster_bootstrap_spearman, flip_effect_to_noise,
                               mc_convergence, oat_tornado, permutation_pvalue_spearman,
                               sobol_indices, wilson_interval)


class TestWilson:
    def test_known_value(self):
        lo, hi = wilson_interval(8, 10)
        assert lo == pytest.approx(0.4902, abs=1e-3) and hi == pytest.approx(0.9433, abs=1e-3)

    def test_edge_cases_stay_in_unit_interval(self):
        assert wilson_interval(0, 50)[0] == 0.0
        assert wilson_interval(50, 50)[1] == pytest.approx(1.0, abs=1e-12)
        assert wilson_interval(0, 0) == (0.0, 1.0)

    def test_narrows_with_n(self):
        w = lambda n: np.subtract(*wilson_interval(n // 2, n)[::-1])
        assert w(100) > w(1000) > w(10000)


class TestBootstrap:
    def test_interval_contains_estimate_and_is_reproducible(self):
        x = np.random.default_rng(0).normal(5, 2, 200)
        a = bootstrap_ci(x, n_boot=2000, seed=3)
        assert a[1] <= a[0] <= a[2]
        assert a == bootstrap_ci(x, n_boot=2000, seed=3)
        assert a[1] < 5.0 < a[2] or abs(a[0] - 5) < 0.6

    def test_cluster_bootstrap_detects_a_perfect_monotone_relation(self):
        x = np.tile(np.arange(10.0), 4); y = x ** 2
        g = np.repeat(list("abcd"), 10)
        rho, lo, hi, k = cluster_bootstrap_spearman(x, y, g, n_boot=500)
        assert rho == pytest.approx(1.0) and lo > 0.99 and k == 4

    def test_permutation_pvalue_small_for_signal_large_for_noise(self):
        rng = np.random.default_rng(0)
        x = np.tile(np.arange(12.0), 3); g = np.repeat(list("abc"), 12)
        assert permutation_pvalue_spearman(x, x * 2 + rng.normal(0, .1, 36), g, n_perm=2000) < 0.01
        assert permutation_pvalue_spearman(x, rng.normal(size=36), g, n_perm=2000) > 0.05


class TestFlipTest:
    def test_returns_sane_numbers(self):
        f = flip_effect_to_noise(WORKED_EXAMPLES, n=800, n_boot=200)
        assert f.n_pairs == 21 and f.signal_mean >= 0 and f.noise_pair_mean > 0
        assert f.ratio_lo <= f.ratio <= f.ratio_hi
        assert f.noise_base_mean <= f.noise_pair_mean + 1.0


class TestSobol:
    def test_indices_in_range_and_total_geq_first(self):
        r = sobol_indices(A04_KYC_ARCHIVE, n_base=1024, n_boot=50)
        assert np.all(r["ST"] >= r["S"] - 0.05)
        assert 0.8 < r["S"].sum() <= 1.1          # near-additive model in log space
        # money inputs dominate: loss and turnover enter multiplicatively
        top = [r["names"][i] for i in np.argsort(-r["ST"])[:2]]
        assert set(top) == {"loss V", "turnover tau"}

    def test_gated_asset_has_zero_variance(self):
        from costofdelay.examples import A06_PQC_ARCHIVE
        r = sobol_indices(A06_PQC_ARCHIVE, n_base=256, n_boot=10)
        assert r["var"] == 0.0 and np.all(r["S"] == 0)

    def test_tornado_orders_by_swing(self):
        t = oat_tornado(A04_KYC_ARCHIVE)
        assert all(a["swing"] >= b["swing"] for a, b in zip(t, t[1:]))


class TestConvergence:
    def test_interval_width_shrinks_like_root_n(self):
        rows = mc_convergence(load_register("case_studies/openmrs/asset_register.csv"), "O08")
        hw = [r["half_width"] for r in rows]
        assert hw[0] > hw[-1]
        assert hw[-1] < 0.01
        assert all(r["lo"] <= r["p"] <= r["hi"] for r in rows)


class TestSchedule:
    def setup_method(self):
        self.assets = load_register("case_studies/openmrs/asset_register.csv")
        self.crqc = gri_2025_optimistic()

    def test_accrual_rate_at_zero_equals_cost_of_delay(self):
        from costofdelay.scoring import cod_quantum
        a = A04_KYC_ARCHIVE
        g0 = quantum_accrual_rate(a, self.crqc, np.array([0.0]))[0]
        assert g0 == pytest.approx(cod_quantum(a, self.crqc), rel=1e-6)

    def test_accrual_rate_is_nondecreasing_in_time(self):
        g = quantum_accrual_rate(A04_KYC_ARCHIVE, self.crqc, np.linspace(0, 30, 31))
        assert np.all(np.diff(g) >= -1e-6)

    def test_smith_never_worse_than_siloed_and_close_to_optimal(self):
        items = build_items(self.assets, self.crqc, view="leg")
        s = total_loss(smith_order(items))
        assert s <= total_loss(siloed_order(items, "classical")) + 1e-6
        assert s <= total_loss(siloed_order(items, "quantum")) + 1e-6
        opt, ov = optimal_order(items, max_items=18)
        assert ov <= s + 1e-6                       # optimum cannot be worse
        assert s / ov < 1.12                        # and Smith is within 12% on this register

    def test_optimal_order_matches_total_loss_of_its_own_ordering(self):
        items = build_items(self.assets, self.crqc, view="asset")
        opt, ov = optimal_order(items)
        assert total_loss(opt) == pytest.approx(ov, rel=1e-9)
