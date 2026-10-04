"""
Generate the evaluation tables for the paper, for every case-study register.

    python paper_tables.py > ../paper/tables.md

Every number in paper/paper.md section 5 is copied from this output; none is
typed by hand.
"""

from __future__ import annotations

import pathlib as _pl
import sys as _sys
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))

from pathlib import Path

from costofdelay.crqc import MEDIAN_SCENARIOS, gri_2025_optimistic, gri_2025_pessimistic, scenario_grid
from costofdelay.register import load_register
from costofdelay.qars import qars, rank_qars
from costofdelay.scoring import (cost_of_delay, kendall_tau, rank_by_cost_of_delay,
                     rank_classical_only, rank_inversions)

ROOT = Path(__file__).resolve().parents[1]
SYSTEMS = {
    "MOSIP (open-source national identity platform)": ROOT / "case_studies" / "mosip" / "asset_register.csv",
    "Apache Fineract (open-source core banking)": ROOT / "case_studies" / "fineract" / "asset_register.csv",
    "OpenMRS (open-source medical record system)": ROOT / "case_studies" / "openmrs" / "asset_register.csv",
    "Online Boutique (demo shop; mock data; procedure test only)": ROOT / "case_studies" / "online_boutique" / "asset_register.csv",
}


def usd(x: float) -> str:
    if x == 0:
        return "0"
    if x >= 1e6:
        return f"{x/1e6:.2f}M"
    if x >= 1e3:
        return f"{x/1e3:.1f}k"
    return f"{x:.1f}"


def system_tables(name: str, path: Path) -> None:
    assets = [a for a in load_register(path)]
    observed = [a for a in assets if "POSITED" not in "".join(a.tags).upper()]
    crqc = gri_2025_optimistic()
    n = len(observed)

    print(f"## {name}\n")
    print(f"{len(assets)} assets in register ({len(observed)} observed-category, "
          f"{len(assets)-len(observed)} posited). Tables use observed-category assets only.\n")

    scored = rank_by_cost_of_delay(observed, crqc)
    unified = [c.asset_id for c in scored]
    classical = rank_classical_only(observed)
    pos_c = {a: i + 1 for i, a in enumerate(classical)}
    names = {a.asset_id: a.name for a in observed}
    life = {a.asset_id: a.data_lifetime_years for a in observed}

    print("| Rank | Asset | L (yr) | Classical CoD | Quantum CoD | Quantum share | Classical-only rank |")
    print("|---|---|---|---|---|---|---|")
    for i, c in enumerate(scored, 1):
        print(f"| {i} | {c.asset_id} {names[c.asset_id][:48]} | {life[c.asset_id]:g} | "
              f"{usd(c.classical)} | {usd(c.quantum)} | {c.quantum_share:.0%} | {pos_c[c.asset_id]} |")

    inv = rank_inversions(unified, classical)
    dom = [c.asset_id for c in scored if c.quantum > c.classical]
    pairs = n * (n - 1) // 2
    print()
    print(f"- Pairs whose order differs from classical-only: **{len(inv)} of {pairs}** "
          f"(Kendall tau {kendall_tau(unified, classical):.3f}).")
    print(f"- Quantum-dominant assets (quantum CoD > classical CoD): **{len(dom)} of {n}** "
          f"({', '.join(dom) if dom else 'none'}).")
    print(f"- Assets with a non-zero quantum term: {sum(1 for c in scored if c.quantum > 0)} of {n}.")

    print("\nOrdering across CRQC scenarios (shape fixed, median arrival varies):\n")
    print("| CRQC median | Ordering |")
    print("|---|---|")
    base = None
    for year, d in zip(MEDIAN_SCENARIOS, scenario_grid()):
        order = [c.asset_id for c in rank_by_cost_of_delay(observed, d)]
        base = base or order
        print(f"| {year} | {' > '.join(order)} |")
    stable = all([c.asset_id for c in rank_by_cost_of_delay(observed, d)] == base
                 for d in scenario_grid())
    print(f"\nOrdering invariant across all four scenarios: **{'yes' if stable else 'no'}**.")

    print("\nOrdering across discount rates (optimistic scenario):\n")
    print("| rho | Ordering |")
    print("|---|---|")
    rb = None
    same = True
    for rho in (0.0, 0.02, 0.05, 0.07, 0.10):
        order = [c.asset_id for c in rank_by_cost_of_delay(observed, crqc, discount_rate=rho)]
        rb = rb or order
        same &= order == rb
        print(f"| {rho:.2f} | {' > '.join(order)} |")
    print(f"\nOrdering invariant across discount rates 0-10%: **{'yes' if same else 'no'}**.")

    q = rank_qars(observed, crqc)
    print(f"\nQARS (equal weights, linear timeline term) ordering: {' > '.join(q)}  "
          f"(tau vs cost-of-delay {kendall_tau(unified, q):.3f}).")
    migrated = [a.asset_id for a in observed if not a.protection.quantum_vulnerable
                and a.data_lifetime_years > 5]
    if migrated:
        print(f"Assets not quantum-vulnerable yet long-lived, scored by QARS: "
              + ", ".join(f"{i}={qars(next(a for a in observed if a.asset_id == i), crqc):.2f}"
                          for i in migrated) + ".")
    print()
    from costofdelay.uncertainty import report as unc_report
    print(unc_report(name + " - uncertainty", observed))


def summary_table() -> None:
    import statistics
    from costofdelay.scoring import kendall_tau
    print("## Cross-system summary")
    print()
    print("| System | Assets | Median lifetime of assets with L>0 (yr) | Pairs differing from classical-only | Quantum-dominant | Order stable across CRQC scenarios |")
    print("|---|---|---|---|---|---|")
    crqc = gri_2025_optimistic()
    for name, path in SYSTEMS.items():
        a = [x for x in load_register(path) if "POSITED" not in "".join(x.tags).upper()]
        sc = rank_by_cost_of_delay(a, crqc)
        u = [c.asset_id for c in sc]; cl = rank_classical_only(a)
        n = len(a)
        dom = sum(1 for c in sc if c.quantum > c.classical)
        lives = [x.data_lifetime_years for x in a if x.data_lifetime_years > 0.01]
        base = None; stable = True
        for d in scenario_grid():
            o = [c.asset_id for c in rank_by_cost_of_delay(a, d)]
            base = base or o; stable &= (o == base)
        print(f"| {name.split(' (')[0]} | {n} | {statistics.median(lives):.0f} | "
              f"{len(rank_inversions(u, cl))} of {n*(n-1)//2} | {dom} of {n} | {'yes' if stable else 'no'} |")
    print()


def main() -> None:
    print("# Generated evaluation tables\n")
    print("GRI 2025 optimistic scenario unless stated. All parameters assumed from public "
          "documentation; no practitioner elicitation.\n")
    summary_table()
    for name, path in SYSTEMS.items():
        system_tables(name, path)


if __name__ == "__main__":
    main()
