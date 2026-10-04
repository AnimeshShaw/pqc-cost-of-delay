"""Tests for the register loader and the quantum-dominant-class measurement."""

import csv
from pathlib import Path

import pytest

from costofdelay.register import RegisterError, load_register, summarise
from costofdelay.crqc import gri_2025_optimistic

HEADER = ["asset_id", "name", "services", "value_band", "likelihood_band",
          "data_lifetime_years", "protection_class", "harvest_band",
          "turnover_per_year", "migration_time_years", "evidence_for_zeroing",
          "rationale", "provenance"]


def _write(tmp_path: Path, rows: list[dict]) -> Path:
    p = tmp_path / "reg.csv"
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=HEADER)
        w.writeheader()
        for r in rows:
            base = dict(asset_id="A1", name="n", services="s", value_band="HIGH",
                        likelihood_band="POSSIBLE", data_lifetime_years="10",
                        protection_class="RSA_2048", harvest_band="HIGH",
                        turnover_per_year="", migration_time_years="1",
                        evidence_for_zeroing="", rationale="", provenance="TEST")
            base.update(r)
            w.writerow(base)
    return p


class TestAntiGaming:
    """Failure mode 3: an owner must not avoid a migration by typing a zero."""

    def test_harvest_none_requires_evidence(self, tmp_path):
        p = _write(tmp_path, [dict(harvest_band="NONE")])
        with pytest.raises(RegisterError, match="REQUIRES evidence"):
            load_register(p)

    def test_zero_lifetime_requires_evidence(self, tmp_path):
        p = _write(tmp_path, [dict(data_lifetime_years="0")])
        with pytest.raises(RegisterError, match="REQUIRES evidence"):
            load_register(p)

    def test_evidence_unlocks_the_zero(self, tmp_path):
        p = _write(tmp_path, [dict(harvest_band="NONE",
                                   evidence_for_zeroing="HSM never leaves the vault; audit ref 123")])
        assert load_register(p)[0].harvest_exposure.fraction == 0.0

    def test_whitespace_only_evidence_is_not_evidence(self, tmp_path):
        p = _write(tmp_path, [dict(harvest_band="NONE", evidence_for_zeroing="   ")])
        with pytest.raises(RegisterError):
            load_register(p)


class TestValidation:
    def test_bad_band_names_the_row_and_valid_values(self, tmp_path):
        p = _write(tmp_path, [dict(value_band="HUGE")])
        with pytest.raises(RegisterError, match=r"row 2.*value_band.*valid:"):
            load_register(p)

    def test_negative_lifetime_rejected(self, tmp_path):
        p = _write(tmp_path, [dict(data_lifetime_years="-1")])
        with pytest.raises(RegisterError):
            load_register(p)

    def test_duplicate_ids_rejected(self, tmp_path):
        p = _write(tmp_path, [dict(asset_id="A1"), dict(asset_id="A1")])
        with pytest.raises(RegisterError, match="duplicate"):
            load_register(p)

    def test_case_insensitive_bands(self, tmp_path):
        p = _write(tmp_path, [dict(value_band="high", protection_class="rsa_2048")])
        assert load_register(p)[0].value.name == "HIGH"


class TestTurnover:
    """r = tau * V replaces eliciting r independently."""

    def test_turnover_sets_flow_from_value(self, tmp_path):
        p = _write(tmp_path, [dict(value_band="HIGH", turnover_per_year="0.5")])
        a = load_register(p)[0]
        assert a.value_flow_usd_per_year == pytest.approx(0.5 * 1_000_000.0)
        assert not a.flow_rate_is_defaulted

    def test_absent_turnover_is_reported_as_defaulted(self, tmp_path):
        p = _write(tmp_path, [dict()])
        assert load_register(p)[0].flow_rate_is_defaulted

    def test_halving_turnover_halves_the_quantum_leg(self, tmp_path):
        from costofdelay.scoring import cod_quantum
        hi = load_register(_write(tmp_path, [dict(turnover_per_year="1.0")]))[0]
        lo = load_register(_write(tmp_path, [dict(turnover_per_year="0.5")]))[0]
        c = gri_2025_optimistic()
        assert cod_quantum(lo, c) == pytest.approx(0.5 * cod_quantum(hi, c))


class TestKillCriterionMeasurement:
    def test_class_counts_assets_where_quantum_exceeds_classical(self, tmp_path):
        rows = [
            dict(asset_id="Q", likelihood_band="RARE", data_lifetime_years="25",
                 harvest_band="FULL", value_band="HIGH"),         # quiet, long-lived
            dict(asset_id="C", likelihood_band="FREQUENT", data_lifetime_years="0.01",
                 harvest_band="LOW", value_band="HIGH"),          # noisy, short-lived
        ]
        res = summarise(load_register(_write(tmp_path, rows)))
        r = res[gri_2025_optimistic().label]
        assert r["quantum_dominant"] == ["Q"]
        assert r["quantum_dominant_share"] == pytest.approx(0.5)

    def test_every_shipped_register_loads_and_has_valid_provenance(self):
        root = Path(__file__).resolve().parents[1] / "case_studies"
        allowed = {"ASSUMED_FROM_PUBLIC_DOCS", "POSITED", "OBSERVED"}
        for system in ("mosip", "fineract", "openmrs", "online_boutique"):
            assets = load_register(root / system / "asset_register.csv")
            assert len(assets) >= 7, system
            for a in assets:
                assert set(a.tags) <= allowed, (system, a.asset_id, a.tags)

    def test_the_posited_asset_is_the_only_quantum_dominant_one_in_the_demo(self):
        """
        The demo shop contains no long-retention asset; one was posited to
        exercise the case. The quantum-dominant class in the demo is therefore
        entirely an artefact of that invented asset, and the paper excludes
        posited assets from every table.
        """
        root = Path(__file__).resolve().parents[1] / "case_studies"
        assets = load_register(root / "online_boutique" / "asset_register.csv")
        r = summarise(assets)[gri_2025_optimistic().label]
        assert r["quantum_dominant"] == ["A08"]
        posited = {a.asset_id for a in assets if "POSITED" in "".join(a.tags)}
        assert posited == {"A08"}

    def test_real_systems_have_no_posited_assets(self):
        root = Path(__file__).resolve().parents[1] / "case_studies"
        for system in ("mosip", "fineract", "openmrs"):
            for a in load_register(root / system / "asset_register.csv"):
                assert "POSITED" not in "".join(a.tags), (system, a.asset_id)
