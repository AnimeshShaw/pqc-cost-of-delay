"""
Generate the web app's data from the same CSV registers the Python code scores, plus golden
values from the Python reference implementation so app/test.js can prove that the JavaScript
port computes the same numbers.

    python scripts/make_app_data.py
"""

from __future__ import annotations

import pathlib as _pl
import sys as _sys
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))

import json
import math
from pathlib import Path

from scipy import integrate
from scipy.optimize import brentq

from costofdelay.crqc import gri_2025_optimistic, gri_2025_pessimistic, scenario_grid
from costofdelay.register import load_register
from costofdelay.scoring import quantum_rate, rank_by_cost_of_delay

ROOT = Path(__file__).resolve().parents[1]
SYSTEMS = [
    ("mosip", "MOSIP", "National identity platform. Biometrics must stay secret for a lifetime."),
    ("fineract", "Apache Fineract", "Core banking. Records are kept for roughly 5 to 15 years."),
    ("openmrs", "OpenMRS", "Medical records. Children's records are kept until adulthood and beyond."),
    ("online_boutique", "Online Boutique", "Google's demo web shop. Short-lived data; a test of the procedure only."),
]


def preset(key, title, blurb):
    assets = load_register(ROOT / "case_studies" / key / "asset_register.csv")
    rows = []
    for a in assets:
        if "POSITED" in "".join(a.tags).upper():
            continue
        rows.append(dict(
            id=a.asset_id, name=a.name, value=a.value.name, likelihood=a.likelihood.name,
            lifetime=a.data_lifetime_years, protection=a.protection.name,
            harvest=a.harvest_exposure.name,
            turnover="" if a.flow_rate_is_defaulted else round(a.flow_rate / a.value.usd, 6),
            note=a.notes))
    return dict(key=key, title=title, blurb=blurb, assets=rows)


def golden():
    cases = []
    for key, _t, _b in SYSTEMS:
        assets = [a for a in load_register(ROOT / "case_studies" / key / "asset_register.csv")
                  if "POSITED" not in "".join(a.tags).upper()]
        for crqc_name, crqc in (("optimistic", gri_2025_optimistic()), ("pessimistic", gri_2025_pessimistic())):
            for rho in (0.0, 0.05):
                scored = rank_by_cost_of_delay(assets, crqc, discount_rate=rho)
                cases.append(dict(
                    system=key, scenario=crqc_name, rho=rho,
                    order=[c.asset_id for c in scored],
                    values={c.asset_id: dict(classical=c.classical, quantum=c.quantum,
                                             quantum_uncoupled=c.quantum_uncoupled) for c in scored}))
    dists = {name: dict(alpha=d.alpha, beta=d.beta, median=d.median_years(),
                        cdf={str(t): d.cdf(t) for t in (1, 5, 10, 15, 25, 30, 50)},
                        pdf={str(t): d.pdf(t) for t in (1, 5, 10, 25)})
             for name, d in (("optimistic", gri_2025_optimistic()), ("pessimistic", gri_2025_pessimistic()))}
    grid = [dict(median_year=y, alpha=d.alpha, beta=d.beta) for y, d in zip((2032, 2035, 2040, 2045), scenario_grid())]

    # race quantities and dominance thresholds
    races, stars = [], []
    for name, d in (("optimistic", gri_2025_optimistic()), ("pessimistic", gri_2025_pessimistic())):
        for lam in (0.01, 0.2, 0.9):
            for L in (3.0, 12.0, 30.0):
                kappa = lam
                counted = integrate.quad(lambda t: d.pdf(t) * math.exp(-kappa * t), 0, L, epsabs=1e-13, epsrel=1e-12, limit=400)[0]
                cf = integrate.quad(lambda t: lam * math.exp(-lam * t) * (1 - d.cdf(t)), 0, L, epsabs=1e-13, epsrel=1e-12, limit=400)[0]
                races.append(dict(scenario=name, lam=lam, L=L, counted=counted, naive=d.cdf(L),
                                  classical_first=cf, union=1 - math.exp(-lam * L) * (1 - d.cdf(L))))
        for tau, h, L, rho in ((0.1, 0.5, 30.0, 0.0), (1.0, 0.9, 10.0, 0.0), (0.05, 0.5, 50.0, 0.05), (0.3, 0.9, 5.0, 0.02)):
            upper = tau * h * d.cdf(L)
            phi = lambda x: tau * h * quantum_rate(1.0, 1.0, L, x, d, rho) - x
            stars.append(dict(scenario=name, tau=tau, h=h, L=L, rho=rho, value=brentq(phi, 0.0, upper, xtol=1e-14)))
    return dict(dists=dists, grid=grid, cases=cases, races=races, lambda_star=stars)


def main():
    presets = [preset(*s) for s in SYSTEMS]
    (ROOT / "app" / "data.js").write_text(
        "window.COD_PRESETS = " + json.dumps(presets, indent=1, ensure_ascii=False) + ";\n", encoding="utf-8")
    (ROOT / "app" / "golden.json").write_text(json.dumps(golden(), indent=1), encoding="utf-8")
    print("wrote app/data.js and app/golden.json")


if __name__ == "__main__":
    main()
