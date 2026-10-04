"""
Load, validate and score an asset register (CSV) with the reference implementation.

    python -m costofdelay.register case_studies/mosip/asset_register.csv

The register is read, validated, scored under both GRI scenarios, and compared
with a classical-only ranking. Among the outputs is the size of the
quantum-dominant class, the quantity the paper's conclusions depend on.

Rules enforced in code (each addresses a failure mode in methodology/FORMAL_METHOD.md):

  * Any value that ZEROES the quantum leg -- harvest_band NONE, or
    data_lifetime_years == 0 -- must carry text in `evidence_for_zeroing`.
    An asset owner must not be able to avoid a migration simply by typing a
    zero.
  * Bands must be valid names; lifetimes non-negative.
  * `turnover_per_year` (tau = new records per year / records at risk), if
    present, sets r = tau * V. This replaces eliciting r independently, which
    invites inconsistency with V. If absent, r defaults to V and the default is
    REPORTED, never silent.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from costofdelay.crqc import gri_2025_optimistic, gri_2025_pessimistic
from costofdelay.model import (Asset, HarvestBand, LikelihoodBand, ProtectionClass,
                   ValueBand)
from costofdelay.scoring import (cost_of_delay, kendall_tau, rank_by_cost_of_delay,
                     rank_classical_only, rank_inversions)

HARVEST_ZERO = {HarvestBand.NONE}


class RegisterError(ValueError):
    """The register violates a validation rule. Message names row and field."""


def _enum(cls, name: str, row: int, field: str):
    try:
        return cls[name.strip().upper()]
    except KeyError:
        valid = ", ".join(m.name for m in cls)
        raise RegisterError(f"row {row}: {field}={name!r} invalid; valid: {valid}")


def load_register(path: str | Path) -> list[Asset]:
    assets: list[Asset] = []
    with open(path, newline="", encoding="utf-8") as fh:
        for i, rec in enumerate(csv.DictReader(fh), start=2):
            aid = rec["asset_id"].strip()
            if not aid:
                raise RegisterError(f"row {i}: asset_id empty")

            value = _enum(ValueBand, rec["value_band"], i, "value_band")
            lik = _enum(LikelihoodBand, rec["likelihood_band"], i, "likelihood_band")
            prot = _enum(ProtectionClass, rec["protection_class"], i, "protection_class")
            harv = _enum(HarvestBand, rec["harvest_band"], i, "harvest_band")

            try:
                life = float(rec["data_lifetime_years"])
                mig = float(rec["migration_time_years"] or 1.0)
            except ValueError as e:
                raise RegisterError(f"row {i} ({aid}): non-numeric lifetime/migration: {e}")
            if life < 0 or mig < 0:
                raise RegisterError(f"row {i} ({aid}): lifetime and migration must be >= 0")

            evidence = (rec.get("evidence_for_zeroing") or "").strip()
            zeroes = (harv in HARVEST_ZERO) or life == 0.0
            if zeroes and not evidence:
                raise RegisterError(
                    f"row {i} ({aid}): harvest_band=NONE or data_lifetime_years=0 "
                    "zeroes the quantum leg and REQUIRES evidence_for_zeroing "
                    "(SPEC failure mode 3: an assertion must not be enough)"
                )

            tau_txt = (rec.get("turnover_per_year") or "").strip()
            flow = None
            if tau_txt:
                try:
                    tau = float(tau_txt)
                except ValueError:
                    raise RegisterError(f"row {i} ({aid}): turnover_per_year not numeric")
                if tau < 0:
                    raise RegisterError(f"row {i} ({aid}): turnover_per_year must be >= 0")
                flow = tau * value.usd

            assets.append(Asset(
                asset_id=aid, name=rec["name"].strip(), value=value,
                likelihood=lik, data_lifetime_years=life, protection=prot,
                harvest_exposure=harv, value_flow_usd_per_year=flow,
                migration_time_years=mig, notes=rec.get("rationale", ""),
                tags=(rec.get("provenance", "").strip(),),
            ))
    ids = [a.asset_id for a in assets]
    if len(set(ids)) != len(ids):
        raise RegisterError("duplicate asset_id values")
    return assets


def usd(x: float) -> str:
    if x == 0:
        return "0"
    if x >= 1e6:
        return f"{x/1e6:,.2f}M"
    if x >= 1e3:
        return f"{x/1e3:,.1f}k"
    return f"{x:,.2f}"


def summarise(assets: list[Asset]) -> dict:
    """Return the numbers a report needs; also used by the tests."""
    out = {}
    for crqc in (gri_2025_optimistic(), gri_2025_pessimistic()):
        scored = {c.asset_id: c for c in rank_by_cost_of_delay(assets, crqc)}
        unified = list(scored)  # insertion order == ranked order
        classical = rank_classical_only(assets)
        n = len(assets)
        dom = [a.asset_id for a in assets if scored[a.asset_id].quantum > scored[a.asset_id].classical]
        k = max(1, round(0.1 * n))
        top_u, top_c = set(unified[:k]), set(classical[:k])
        out[crqc.label] = dict(
            scored=scored, unified=unified, classical=classical,
            quantum_dominant=dom,
            quantum_dominant_share=len(dom) / n if n else 0.0,
            nonzero_quantum=[a.asset_id for a in assets if scored[a.asset_id].quantum > 0],
            inversions=rank_inversions(unified, classical),
            tau=kendall_tau(unified, classical) if n > 1 else 1.0,
            top_displaced=1.0 - len(top_u & top_c) / k,
        )
    return out


def main(path: str) -> int:
    assets = load_register(path)
    res = summarise(assets)
    defaulted = [a.asset_id for a in assets
                 if a.flow_rate_is_defaulted and a.quantum_applicable]
    print(f"Register: {path}   ({len(assets)} assets)")
    if defaulted:
        print(f"WARNING r defaulted to V (no turnover given) for: {defaulted}")
        print("        State this assumption in any report.")
    print()
    for label, r in res.items():
        print("=" * 78)
        print(label)
        print("=" * 78)
        print(f"{'id':<5}{'asset':<46}{'classical':>11}{'quantum':>11}{'q share':>9}")
        print("-" * 82)
        for aid in r["unified"]:
            c = r["scored"][aid]
            name = next(a.name for a in assets if a.asset_id == aid)
            print(f"{aid:<5}{name[:45]:<46}{usd(c.classical):>11}{usd(c.quantum):>11}"
                  f"{c.quantum_share:>8.0%}")
        print()
        print(f"  unified  : {' > '.join(r['unified'])}")
        print(f"  classical: {' > '.join(r['classical'])}")
        print(f"  pairs flipped vs classical-only: {len(r['inversions'])}   "
              f"tau {r['tau']:.3f}   top-decile displaced {r['top_displaced']:.0%}")
        print(f"  assets with any quantum leg     : {len(r['nonzero_quantum'])}/{len(assets)}")
        print(f"  QUANTUM-DOMINANT CLASS          : {len(r['quantum_dominant'])}/{len(assets)}"
              f" = {r['quantum_dominant_share']:.0%}   {r['quantum_dominant']}")
        print()
    opt = res[gri_2025_optimistic().label]
    posited = {a.asset_id for a in assets if "POSITED" in "".join(a.tags).upper()}
    real = [a for a in assets if a.asset_id not in posited]
    dom_real = [i for i in opt["quantum_dominant"] if i not in posited]
    share_all = opt["quantum_dominant_share"]
    share_real = len(dom_real) / len(real) if real else 0.0

    print("QUANTUM-DOMINANT CLASS: assets whose quantum cost of delay exceeds their classical one.")
    print("If it is empty (or very small) on a register, the quantum term changes magnitudes")
    print("but not what is funded first.")
    print(f"   all assets            : {len(opt['quantum_dominant'])}/{len(assets)} = {share_all:.0%}")
    if posited:
        print(f"   EXCLUDING POSITED {sorted(posited)}: {len(dom_real)}/{len(real)} = {share_real:.0%}")
        print("   POSITED assets are inventions, not observations; they are excluded from the")
        print("   share used to judge whether this class exists in practice.")
    verdict = "empty or negligible (<5%)" if share_real < 0.05 else "present"
    print(f"   class size (observed assets only): {verdict}")
    print()
    print("Provenance of this register:",
          sorted({t for a in assets for t in a.tags}))
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
