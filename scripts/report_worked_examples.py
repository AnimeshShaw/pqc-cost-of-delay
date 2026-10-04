"""
Generates the numbers used in the illustrative worked examples.

Run:  python scripts/report_worked_examples.py

No figure in the methodology notes is hand-computed. If a number in them disagrees with
this output, the spec is wrong.
"""

from __future__ import annotations

import pathlib as _pl
import sys as _sys
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))

import sys

from costofdelay.crqc import (
    GRI_2025_OPTIMISTIC,
    GRI_2025_PESSIMISTIC,
    MEDIAN_SCENARIOS,
    gri_2025_optimistic,
    gri_2025_pessimistic,
    scenario_grid,
)
from costofdelay.examples import WORKED_EXAMPLES
from costofdelay.model import Asset
from costofdelay.scoring import (
    cost_of_delay,
    kendall_tau,
    rank_by_cost_of_delay,
    rank_by_lifetime_only,
    rank_classical_only,
    rank_flip_horizon_weights,
    rank_inversions,
    rank_mosca_gate,
)


def usd(x: float) -> str:
    if x == 0:
        return "0"
    if abs(x) >= 1_000_000:
        return f"{x/1_000_000:,.2f}M"
    if abs(x) >= 1_000:
        return f"{x/1_000:,.1f}k"
    return f"{x:,.2f}"


def section(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def report_distribution() -> None:
    section("1. CRQC ARRIVAL DISTRIBUTION  F_Q(t)")
    print()
    print("Anchors from Quantum Threat Timeline Report 2025 (Mosca & Piani,")
    print("evolutionQ / Global Risk Institute, 2026-03-09, 26 experts):")
    print(f"  pessimistic: {GRI_2025_PESSIMISTIC}")
    print(f"  optimistic:  {GRI_2025_OPTIMISTIC}")
    print()
    print("Weibull parameters solved in closed form from those anchors:")
    print()
    print(f"{'scenario':<26} {'alpha':>9} {'beta':>8} {'median':>9}")
    print("-" * 56)
    for d in (gri_2025_pessimistic(), gri_2025_optimistic()):
        print(f"{d.label:<26} {d.alpha:>9.4f} {d.beta:>8.4f} "
              f"{d.median_years():>8.1f}y")
    print()
    print("F_Q(t) at the horizons that matter:")
    print()
    horizons = [0.00001, 0.25, 1, 5, 10, 15, 20, 25, 30]
    hdr = "".join(f"{h:>9}" if h >= 1 else f"{h:>9.2g}" for h in horizons)
    print(f"{'scenario':<26}{hdr}")
    print("-" * (26 + 9 * len(horizons)))
    for d in (gri_2025_pessimistic(), gri_2025_optimistic()):
        row = "".join(f"{d.cdf(h):>9.4f}" for h in horizons)
        print(f"{d.label:<26}{row}")
    print()
    print("  t=10 and t=15 reproduce the published anchors exactly (that is the")
    print("  fit). Values beyond t=15 are EXTRAPOLATION from the fitted curve,")
    print("  not published figures. Report them as such.")


def report_worked_examples(assets: list[Asset]) -> None:
    section("2. WORKED EXAMPLES -- COST OF DELAY (USD/year)")
    crqc = gri_2025_optimistic()
    print()
    print(f"CRQC scenario: {crqc.label}  (median {crqc.median_years():.1f}y)")
    print()
    print(f"{'id':<5}{'asset':<42}{'L (yr)':>9}{'classical':>12}"
          f"{'quantum':>12}{'total':>12}{'q share':>9}")
    print("-" * 101)
    for a in assets:
        c = cost_of_delay(a, crqc)
        L = f"{a.data_lifetime_years:.4g}"
        print(f"{a.asset_id:<5}{a.name[:41]:<42}{L:>9}"
              f"{usd(c.classical):>12}{usd(c.quantum):>12}"
              f"{usd(c.total):>12}{c.quantum_share:>8.1%}")

    print()
    print("Competing-risks coupling -- how much the classical hazard discounts")
    print("the same asset's quantum cost:")
    print()
    print(f"{'id':<5}{'q uncoupled':>14}{'q coupled':>14}{'discount':>11}")
    print("-" * 44)
    for a in assets:
        c = cost_of_delay(a, crqc)
        if c.quantum_uncoupled == 0.0:
            continue
        print(f"{a.asset_id:<5}{usd(c.quantum_uncoupled):>14}"
              f"{usd(c.quantum):>14}{c.coupling_discount:>10.1%}")
    print()
    print("  This is the interaction term. A02/A05 are discounted hardest")
    print("  because they are frequently attacked -- their data will probably")
    print("  leak in plaintext before any CRQC exists. The legs are not")
    print("  independent and do not sum like a weighted score.")

    defaulted = [a.asset_id for a in assets if a.flow_rate_is_defaulted]
    if defaulted:
        print()
        print(f"  WARNING: r defaulted to V for {defaulted} -- state explicitly.")


def report_rankings(assets: list[Asset]) -> None:
    section("3. DOES IT CHANGE DECISIONS? RANKING COMPARISON")
    crqc = gri_2025_optimistic()

    unified = [c.asset_id for c in rank_by_cost_of_delay(assets, crqc)]
    classical = rank_classical_only(assets)
    lifetime = rank_by_lifetime_only(assets)
    mosca = rank_mosca_gate(assets, crqc)

    print()
    print(f"{'rank':<6}{'unified CoD':<14}{'classical only':<16}"
          f"{'lifetime only':<16}{'Mosca gate':<14}")
    print("-" * 66)
    for i in range(len(assets)):
        print(f"{i+1:<6}{unified[i]:<14}{classical[i]:<16}"
              f"{lifetime[i]:<16}{mosca[i]:<14}")

    print()
    print(f"{'comparison':<40}{'Kendall tau':>13}{'inversions':>12}")
    print("-" * 65)
    for name, other in (
        ("unified vs classical-only", classical),
        ("unified vs lifetime-only (KILL TEST)", lifetime),
        ("unified vs Mosca gate", mosca),
    ):
        tau = kendall_tau(unified, other)
        inv = rank_inversions(unified, other)
        print(f"{name:<40}{tau:>13.3f}{len(inv):>12}")

    print()
    print("Decisions the unified ranking changes vs classical-only practice")
    print("(pairs whose relative priority flips -- paper section 6 material):")
    print()
    for x, y in rank_inversions(unified, classical):
        print(f"  {x} now ranks above {y}")

    print()
    print("REFUTATION TEST: if unified CoD were rank-identical to")
    print("sorting by data lifetime alone, the mathematics would contribute")
    print("nothing beyond the register design.")
    tau_life = kendall_tau(unified, lifetime)
    inv_life = rank_inversions(unified, lifetime)
    print(f"  Kendall tau vs lifetime-only: {tau_life:.3f}")
    print(f"  Discordant pairs: {len(inv_life)}")
    verdict = "NOT FIRED -- the math earns its place" if inv_life else \
              "*** FIRED -- STOP. The math adds nothing. ***"
    print(f"  Verdict: {verdict}")


def report_sensitivity(assets: list[Asset]) -> None:
    section("4. SENSITIVITY -- RANKING STABILITY ACROSS CRQC SCENARIOS")
    print()
    print("Shape parameter held at the GRI optimistic fit; only the median")
    print("arrival year varies. This is the robustness result that replaces")
    print("any claim of calibrated point scores.")
    print()

    grid = scenario_grid()
    rankings = {}
    print(f"{'CRQC median':<14}{'ranking (highest cost of delay first)':<48}")
    print("-" * 62)
    for year, d in zip(MEDIAN_SCENARIOS, grid):
        order = [c.asset_id for c in rank_by_cost_of_delay(assets, d)]
        rankings[year] = order
        print(f"{year:<14}{' > '.join(order):<48}")

    base = rankings[MEDIAN_SCENARIOS[0]]
    print()
    print(f"{'vs ' + str(MEDIAN_SCENARIOS[0]):<16}{'Kendall tau':>13}{'inversions':>12}")
    print("-" * 41)
    for year in MEDIAN_SCENARIOS[1:]:
        tau = kendall_tau(base, rankings[year])
        inv = rank_inversions(base, rankings[year])
        print(f"{year:<16}{tau:>13.3f}{len(inv):>12}")

    all_same = all(rankings[y] == base for y in MEDIAN_SCENARIOS)
    print()
    if all_same:
        print("  Ordering is INVARIANT across all four CRQC scenarios. The")
        print("  decision does not depend on resolving the CRQC date -- which")
        print("  is the strongest possible answer to the calibration objection.")
    else:
        print("  Ordering SHIFTS between scenarios. The crossover boundaries")
        print("  are the decision-relevant uncertainties and must be reported")
        print("  explicitly in the paper rather than hidden behind a point score.")

    print()
    print("Per-asset quantum cost of delay by scenario (USD/year):")
    print()
    hdr = "".join(f"{y:>12}" for y in MEDIAN_SCENARIOS)
    print(f"{'id':<5}{hdr}")
    print("-" * (5 + 12 * len(MEDIAN_SCENARIOS)))
    for a in assets:
        row = "".join(usd(cost_of_delay(a, d).quantum).rjust(12) for d in grid)
        print(f"{a.asset_id:<5}{row}")


def report_formulation_b(assets: list[Asset]) -> None:
    section("5. FORMULATION B REFUTED -- THE RANKING IS A FREE PARAMETER")
    crqc = gri_2025_optimistic()
    print()
    print("Master Execution Plan v3 Step 2: EL_c = P * Impact * horizon_weight,")
    print("EL_q = F_Q(L) * Impact, ranked on the sum. `horizon_weight` has no")
    print("derivation. Its ranking at a range of values:")
    print()
    flips = rank_flip_horizon_weights(assets, crqc)
    print(f"{'horizon_weight':<17}{'ranking':<48}")
    print("-" * 65)
    for w, order in flips.items():
        print(f"{w:<17}{' > '.join(order):<48}")

    distinct = {tuple(o) for o in flips.values()}
    print()
    print(f"  Distinct orderings produced: {len(distinct)} across "
          f"{len(flips)} weight values.")
    if len(distinct) > 1:
        print("  The priority order is a function of an undefined constant.")
        print("  An examiner reads this as 'applies a weight to combine two")
        print("  known scores'. A reviewer reads it as a tuned knob. Both are")
        print("  correct. REJECT Formulation B.")
    else:
        print("  Ordering happened to be stable on THIS asset set. That is not")
        print("  a defence -- the parameter remains underived. Re-run on the")
        print("  real assets before concluding anything.")

    print()
    print("Formulation A needs no such parameter: both legs are rates in")
    print("USD/year, so they are comparable without conversion, and the")
    print("discount factor is 1 on both legs at t=0.")


def report_qars(assets: list[Asset]) -> None:
    from costofdelay.qars import qars, rank_qars
    section("6. CLOSEST PRIOR ART: QARS (Grigaliunas & Bruzgiene, Electronics 2025)")
    crqc = gri_2025_optimistic()
    print()
    print("QARS(a) = wT*T + wS*S + wE*E, equal weights, linear f_time, Z = CRQC median.")
    print("My reading of the published equations (2)-(8); see qars.py for choices.")
    print()
    print(f"{'id':<5}{'QARS':>8}{'band':>10}{'CoD classical':>16}{'CoD quantum':>14}")
    print("-" * 53)
    for a in assets:
        c = cost_of_delay(a, crqc)
        q = qars(a, crqc)
        band = "critical" if q > 0.85 else "high" if q > 0.60 else "medium" if q >= 0.30 else "low"
        print(f"{a.asset_id:<5}{q:>8.3f}{band:>10}{usd(c.classical):>16}{usd(c.quantum):>14}")
    unified = [c.asset_id for c in rank_by_cost_of_delay(assets, crqc)]
    qr = rank_qars(assets, crqc)
    print()
    print(f"  QARS rank        : {' > '.join(qr)}")
    print(f"  cost-of-delay    : {' > '.join(unified)}")
    print(f"  Kendall tau      : {kendall_tau(unified, qr):.3f}   "
          f"discordant pairs: {len(rank_inversions(unified, qr))}")
    print()
    print("  A06 is ALREADY on ML-KEM yet scores 0.667 ('high'): QARS's PQC gate")
    print("  zeroes only the exposure term; timeline and sensitivity stay saturated.")
    print("  A05 (frequently attacked) ranks LAST: QARS has no classical-hazard input.")
    print("  Credit: QARS's v(a)/q(a) gates (eq 6-8) are the origin of ours.")


def report_discount(assets: list[Asset]) -> None:
    section("7. DISCOUNT RATE -- A VALUE JUDGEMENT, SWEPT NOT HIDDEN")
    crqc = gri_2025_optimistic()
    print()
    print("rho=0 is a STATED POSITION (interception harm is locked in at harvest),")
    print("not the absence of a choice. Baradziej 2026 shows the rate flips")
    print("expected-value conclusions on its own. Discounting rho is algebraically")
    print("identical to adding rho to the classical hazard in the survival term.")
    print()
    print(f"{'rho':<8}{'A01 quantum':>14}{'A04 quantum':>14}   ordering")
    print("-" * 78)
    for rho in (0.0, 0.02, 0.05, 0.07, 0.10):
        r = rank_by_cost_of_delay(assets, crqc, discount_rate=rho)
        d = {x.asset_id: x for x in r}
        print(f"{rho:<8.2f}{usd(d['A01'].quantum):>14}{usd(d['A04'].quantum):>14}   "
              f"{' > '.join(x.asset_id for x in r)}")


def report_population() -> None:
    import costofdelay.population as population
    population.run()


def main() -> None:
    assets = WORKED_EXAMPLES
    print()
    print("Cost-of-delay scoring -- reference implementation output")
    print("Generated by scripts/report_worked_examples.py.")
    print()
    print("ALL ASSET FIGURES BELOW ARE SYNTHETIC. They illustrate behaviour only;")
    print("no result below is evidence about any real system.")

    report_distribution()
    report_worked_examples(assets)
    report_rankings(assets)
    report_sensitivity(assets)
    report_formulation_b(assets)
    report_qars(assets)
    report_discount(assets)
    report_population()

    print()
    print("=" * 78)
    print("end")
    print("=" * 78)


if __name__ == "__main__":
    main()
