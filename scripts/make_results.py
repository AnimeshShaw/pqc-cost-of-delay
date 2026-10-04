"""
Compute every result used in the paper and write it to results/.

    python scripts/make_results.py

Outputs (all deterministic; seeds are fixed in the called modules):
    results/results.json         machine-readable numbers for figures and the paper
    results/scores_<system>.csv  per-asset cost-of-delay table for each system
    results/summary.md           human-readable summary tables

Posited (invented) assets are excluded from every statistic.
"""

from __future__ import annotations

import pathlib as _pl
import sys as _sys
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))

import csv
import json
import time
from pathlib import Path

import numpy as np

from costofdelay.crqc import (MEDIAN_SCENARIOS, gri_2025_optimistic, gri_2025_pessimistic, scenario_grid)
from costofdelay.qars import qars, rank_qars
from costofdelay.register import load_register
from costofdelay.schedule import build_items, optimal_order, siloed_order, smith_order, total_loss
from costofdelay.scoring import kendall_tau, rank_by_cost_of_delay, rank_classical_only, rank_inversions
from costofdelay.stats import (cluster_bootstrap_spearman, flip_effect_to_noise, mc_convergence, oat_tornado,
                               permutation_pvalue_spearman, sobol_indices, tau_distribution, wilson_interval)
from costofdelay.uncertainty import simulate

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
RES.mkdir(exist_ok=True)

SYSTEMS = {
    "mosip": ("MOSIP", "National identity platform"),
    "fineract": ("Apache Fineract", "Core banking"),
    "openmrs": ("OpenMRS", "Medical records"),
    "online_boutique": ("Online Boutique", "Demo web shop (mock data)"),
}
KEY_ASSETS = {"mosip": "M03", "fineract": "B06", "openmrs": "O08", "online_boutique": "A02"}


def observed(system):
    return [a for a in load_register(ROOT / "case_studies" / system / "asset_register.csv")
            if "POSITED" not in "".join(a.tags).upper()]


def main():
    t0 = time.time()
    out = {"systems": {}, "pooled": {}}
    opt, pess = gri_2025_optimistic(), gri_2025_pessimistic()
    pooled_L, pooled_share, pooled_sys = [], [], []

    for key, (title, blurb) in SYSTEMS.items():
        assets = observed(key)
        n = len(assets)
        pairs = n * (n - 1) // 2
        scored = rank_by_cost_of_delay(assets, opt)
        unified = [c.asset_id for c in scored]
        classical = rank_classical_only(assets)
        pos_c = {a: i + 1 for i, a in enumerate(classical)}
        names = {a.asset_id: a.name for a in assets}
        life = {a.asset_id: a.data_lifetime_years for a in assets}
        qr = rank_qars(assets, opt)

        with open(RES / f"scores_{key}.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["rank", "asset_id", "name", "lifetime_years", "classical_usd_per_year",
                        "quantum_usd_per_year", "total_usd_per_year", "quantum_share",
                        "classical_only_rank", "qars_score"])
            for i, c in enumerate(scored, 1):
                a = next(x for x in assets if x.asset_id == c.asset_id)
                w.writerow([i, c.asset_id, names[c.asset_id], life[c.asset_id], f"{c.classical:.2f}",
                            f"{c.quantum:.2f}", f"{c.total:.2f}", f"{c.quantum_share:.4f}",
                            pos_c[c.asset_id], f"{qars(a, opt):.4f}"])

        inv = rank_inversions(unified, classical)
        dom = [c.asset_id for c in scored if c.quantum > c.classical]

        scen = {str(year): [c.asset_id for c in rank_by_cost_of_delay(assets, d)]
                for year, d in zip(MEDIAN_SCENARIOS, scenario_grid())}
        rhos = {f"{r:.2f}": [c.asset_id for c in rank_by_cost_of_delay(assets, opt, discount_rate=r)]
                for r in (0.0, 0.02, 0.05, 0.07, 0.10)}

        mc = simulate(assets, n=4000, seed=11)
        ft = flip_effect_to_noise(assets, n=4000, n_boot=2000)
        tau_d = tau_distribution(assets, n=4000)

        ka = KEY_ASSETS[key]
        kmc = next(a for a in mc["assets"] if a["asset_id"] == ka)
        k_dom = round(kmc["p_quantum_dominant"] * mc["n"])
        lo, hi = wilson_interval(k_dom, mc["n"])

        sched = {}
        for view in ("asset", "leg"):
            items = build_items(assets, opt, view=view)
            sm = total_loss(smith_order(items))
            rec = {"n_items": len(items), "smith": sm}
            if view == "leg":
                rec["siloed_classical_first"] = total_loss(siloed_order(items, "classical"))
                rec["siloed_quantum_first"] = total_loss(siloed_order(items, "quantum"))
            if len(items) <= 18:
                _, ov = optimal_order(items, max_items=18)
                rec["optimal"] = ov
                rec["smith_gap_pct"] = 100 * (sm / ov - 1)
            sched[view] = rec

        leg_items = build_items(assets, opt, view="leg")
        leg_list = [{"item": i.item_id, "leg": i.leg, "asset": i.asset_id, "rate": i.rate0}
                    for i in smith_order(leg_items)]

        key_asset = next(a for a in assets if a.asset_id == ka)
        sob = sobol_indices(key_asset, n_base=4096, n_boot=300)
        sob = {k: (v.tolist() if hasattr(v, "tolist") else v) for k, v in sob.items()}
        torn = oat_tornado(key_asset)
        conv = mc_convergence(assets, ka)

        for c in scored:
            pooled_L.append(life[c.asset_id])
            pooled_share.append(c.quantum_share)
            pooled_sys.append(key)

        out["systems"][key] = dict(
            title=title, blurb=blurb, n_assets=n, n_pairs=pairs,
            median_lifetime=float(np.median([a.data_lifetime_years for a in assets if a.data_lifetime_years > 0.01])),
            unified=unified, classical_only=classical, qars=qr,
            pairs_differing=len(inv), tau_classical=kendall_tau(unified, classical),
            tau_qars=kendall_tau(unified, qr),
            quantum_dominant=dom, n_quantum_dominant=len(dom),
            n_nonzero_quantum=sum(1 for c in scored if c.quantum > 0),
            scenarios=scen, scenario_stable=len({tuple(v) for v in scen.values()}) == 1,
            rho_orders=rhos, rho_stable=len({tuple(v) for v in rhos.values()}) == 1,
            mc=dict(n=mc["n"], k=mc["k"], p_set_changes=mc["p_topk_set_changes"],
                    p_any_dominant=mc["p_any_quantum_dominant"], assets=mc["assets"]),
            key_asset=ka, key_dom_wilson=[lo, hi], key_dom_k=k_dom,
            flip_test=dict(vars(ft)), tau_dist=tau_d,
            schedule=sched, interleaved_items=leg_list,
            sobol={"asset": ka, **sob}, tornado=torn, convergence=conv,
            scores=[dict(id=c.asset_id, name=names[c.asset_id], L=life[c.asset_id], classical=c.classical,
                         quantum=c.quantum, share=c.quantum_share, classical_rank=pos_c[c.asset_id],
                         rank=i + 1) for i, c in enumerate(scored)],
        )
        print(f"  {key:16s} done  ({time.time() - t0:5.1f}s)")

    rho, lo, hi, kg = cluster_bootstrap_spearman(pooled_L, pooled_share, pooled_sys, n_boot=10000)
    pval = permutation_pvalue_spearman(pooled_L, pooled_share, pooled_sys, n_perm=20000)
    out["pooled"] = dict(n_assets=len(pooled_L), spearman=rho, ci_lo=lo, ci_hi=hi, n_clusters=kg,
                         permutation_p_within_system=pval,
                         lifetimes=pooled_L, shares=pooled_share, systems=pooled_sys)
    out["meta"] = dict(crqc=dict(optimistic=dict(alpha=opt.alpha, beta=opt.beta, median=opt.median_years()),
                                 pessimistic=dict(alpha=pess.alpha, beta=pess.beta, median=pess.median_years())))
    (RES / "results.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")

    L = ["# Results summary (generated by scripts/make_results.py)", "",
         "Posited assets excluded. GRI 2025 optimistic scenario unless stated.", "",
         "| System | Assets | Median life (yr) | Pairs differing | Tau vs classical-only | Quantum-led | "
         "Signal/noise (two analysts) | Order stable (CRQC) | Order stable (rho) |",
         "|---|---|---|---|---|---|---|---|---|"]
    for k, v in out["systems"].items():
        f = v["flip_test"]
        L.append(f"| {v['title']} | {v['n_assets']} | {v['median_lifetime']:.0f} | {v['pairs_differing']} of {v['n_pairs']} | "
                 f"{v['tau_classical']:.2f} | {v['n_quantum_dominant']} of {v['n_assets']} | "
                 f"{f['ratio']:.2f} [{f['ratio_lo']:.2f}, {f['ratio_hi']:.2f}] | "
                 f"{'yes' if v['scenario_stable'] else 'no'} | {'yes' if v['rho_stable'] else 'no'} |")
    pl = out["pooled"]
    L += ["", f"Pooled lifetime vs quantum share: Spearman rho = {pl['spearman']:.2f}, cluster-bootstrap 95% CI "
          f"[{pl['ci_lo']:.2f}, {pl['ci_hi']:.2f}] ({pl['n_clusters']} systems, {pl['n_assets']} assets), "
          f"within-system permutation p = {pl['permutation_p_within_system']:.4f}.", "",
          "## Scheduling: committed loss (USD millions), unit item durations", "",
          "| System | Items (leg view) | Unified (Smith) | Siloed, classical first | Siloed, quantum first | "
          "Exact optimum | Smith gap to optimum |", "|---|---|---|---|---|---|---|"]
    for k, v in out["systems"].items():
        s = v["schedule"]["leg"]
        L.append(f"| {v['title']} | {s['n_items']} | {s['smith']/1e6:.2f} | {s['siloed_classical_first']/1e6:.2f} | "
                 f"{s['siloed_quantum_first']/1e6:.2f} | {s.get('optimal', float('nan'))/1e6:.2f} | "
                 f"{s.get('smith_gap_pct', float('nan')):.1f}% |")
    (RES / "summary.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"wrote results/ in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
