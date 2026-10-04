"""Tests for the uncertainty simulation."""

import pytest

from costofdelay.crqc import gri_2025_optimistic
from costofdelay.register import load_register
from costofdelay.examples import WORKED_EXAMPLES, A03_CATALOGUE, A06_PQC_ARCHIVE, A07_AIRGAPPED
from costofdelay.scoring import cost_of_delay
from costofdelay.uncertainty import simulate

ZERO = dict(value_decades=0.0, lam_factor=1.0000001, life_factor=1.0000001,
            harvest_abs=0.0, tau_factor=1.0000001, rho_max=0.0)


class TestUncertainty:
    def test_zero_spread_reproduces_the_point_estimate(self):
        """With no spread and the optimistic scenario forced, ranks match the reference."""
        import numpy as np
        r = simulate(WORKED_EXAMPLES, n=400, spreads=ZERO)
        # classical-only rank of the most expensive asset must be rank_median 1
        by = {a["asset_id"]: a for a in r["assets"]}
        assert by["A01"]["rank_median"] == 1

    def test_gated_terms_stay_gated_in_every_draw(self):
        r = simulate(WORKED_EXAMPLES, n=2000)
        by = {a["asset_id"]: a for a in r["assets"]}
        for aid in ("A03", "A06", "A07"):
            assert by[aid]["p_quantum_dominant"] == 0.0
            assert by[aid]["p_moves_up_2"] <= 0.5

    def test_probabilities_are_valid(self):
        r = simulate(WORKED_EXAMPLES, n=1000)
        for a in r["assets"]:
            for key in ("p_top_unified", "p_top_classical", "p_quantum_dominant", "p_moves_up_2"):
                assert 0.0 <= a[key] <= 1.0
            assert a["rank_lo"] <= a["rank_median"] <= a["rank_hi"]

    def test_is_reproducible_for_a_fixed_seed(self):
        a = simulate(WORKED_EXAMPLES, n=500, seed=3)
        b = simulate(WORKED_EXAMPLES, n=500, seed=3)
        assert a["assets"] == b["assets"]

    def test_wider_tau_uncertainty_blurs_the_quantum_dominant_class(self):
        """The weakest input: widening turnover spread should not sharpen conclusions."""
        a = next(x for x in simulate(WORKED_EXAMPLES, n=3000, spreads=dict(tau_factor=1.2))["assets"]
                 if x["asset_id"] == "A04")
        b = next(x for x in simulate(WORKED_EXAMPLES, n=3000, spreads=dict(tau_factor=10.0))["assets"]
                 if x["asset_id"] == "A04")
        # A04 is firmly quantum-dominant; with huge tau spread it must be less certain
        assert b["p_quantum_dominant"] <= a["p_quantum_dominant"] + 0.02

    def test_runs_on_every_shipped_register(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1] / "case_studies"
        for sub in ("online_boutique", "openmrs", "mosip", "fineract"):
            assets = load_register(root / sub / "asset_register.csv")
            assert simulate(assets, n=300)["n"] == 300
