"""
Generate every figure used in the paper and the repository documentation.

    python scripts/make_figures.py            # reads results/results.json (run make_results.py first)

Writes vector PDF and 300-dpi PNG to paper/figures/ (created if missing).  Colour-blind-safe palette
(Okabe & Ito, 2008): blue = classical, vermillion = quantum.
"""

from __future__ import annotations

import pathlib as _pl
import sys as _sys
_sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[1]))

import json
import math
from pathlib import Path

import matplotlib as mpl
import numpy as np

mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from scipy import integrate
from scipy.optimize import brentq

from costofdelay.crqc import (MEDIAN_SCENARIOS, CRQCDistribution, gri_2025_optimistic, gri_2025_pessimistic,
                              scenario_grid, GRI_2025_OPTIMISTIC, GRI_2025_PESSIMISTIC)
from costofdelay.register import load_register
from costofdelay.scoring import cost_of_delay, quantum_rate, rank_by_cost_of_delay

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / "paper" / "figures"   # generated output; the paper/ folder is not part of the public repository
FIG.mkdir(exist_ok=True)
R = json.loads((ROOT / "results" / "results.json").read_text(encoding="utf-8"))

# Okabe-Ito
BLUE, ORANGE, GREEN, SKY, PURPLE, YELLOW, GREY, INK = (
    "#0072B2", "#D55E00", "#009E73", "#56B4E9", "#CC79A7", "#E69F00", "#8A8A8A", "#222222")
SYS_COL = {"mosip": BLUE, "fineract": GREEN, "openmrs": ORANGE, "online_boutique": PURPLE}
SYS_NAME = {k: v["title"] for k, v in R["systems"].items()}

mpl.rcParams.update({
    "font.family": "serif", "font.serif": ["Times New Roman", "DejaVu Serif"], "mathtext.fontset": "stix",
    "font.size": 9, "axes.titlesize": 9.5, "axes.labelsize": 9, "legend.fontsize": 8, "xtick.labelsize": 8,
    "ytick.labelsize": 8, "axes.spines.top": False, "axes.spines.right": False, "axes.linewidth": 0.7,
    "xtick.major.width": 0.7, "ytick.major.width": 0.7, "lines.linewidth": 1.5, "figure.dpi": 120,
    "savefig.bbox": "tight", "savefig.pad_inches": 0.04, "pdf.fonttype": 42, "axes.grid": False,
})


def save(fig, name):
    fig.savefig(FIG / f"{name}.pdf")
    fig.savefig(FIG / f"{name}.png", dpi=300)
    plt.close(fig)
    print("  wrote", name)


def panel_label(ax, s, dx=-0.12, dy=1.04):
    ax.text(dx, dy, s, transform=ax.transAxes, fontsize=11, fontweight="bold", va="bottom", ha="left")


def usd_fmt(x):
    if x >= 1e6:
        return f"${x/1e6:g}M"
    if x >= 1e3:
        return f"${x/1e3:g}k"
    return f"${x:g}"


OPT, PESS = gri_2025_optimistic(), gri_2025_pessimistic()


# ---------------------------------------------------------------------------
def fig_overview():
    fig, ax = plt.subplots(figsize=(7.4, 3.7))
    ax.set_xlim(0, 100); ax.set_ylim(0, 58); ax.axis("off")

    def box(x, y, w, h, title, body, fc="#F4F4F2", ec=INK, size=7.4):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.25,rounding_size=1.2", fc=fc, ec=ec, lw=0.9))
        ax.text(x + w / 2, y + h - 1.6, title, ha="center", va="top", fontsize=8.6, fontweight="bold", color=INK)
        ax.text(x + w / 2, y + h - 6.2, body, ha="center", va="top", fontsize=size, color=INK, linespacing=1.45)

    def arrow(x1, y1, x2, y2, c=INK):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=9, lw=0.9, color=c))

    box(0.5, 12, 22, 44, "1  Asset register",
        "for each asset:\nloss  $V$\nhazard  $\\lambda$ (per year)\nlifetime  $L$ (years)\nlock (protection class)\nrecordable share  $h$\nturnover  $\\tau$")
    box(29, 37, 25, 19, "2a  Classical leg",
        "$\\mathrm{CoD}_c=\\lambda V$\n(annualised loss)\nUSD per year", fc="#E8F1F8", ec=BLUE)
    box(29, 8, 25, 22, "2b  Quantum leg",
        "$r\\,h\\int_0^{L} f_Q(t)\\,e^{-(\\lambda+\\rho)t}\\,dt$\nwith $r=\\tau V$\nzero if the lock is quantum-safe,\n$h=0$ or $L=0$\nUSD per year",
        fc="#FBEBDD", ec=ORANGE, size=7.2)
    ax.add_patch(FancyBboxPatch((23, 0.2), 37, 4.6, boxstyle="round,pad=0.2,rounding_size=1", fc="#FFFFFF", ec=GREY, lw=0.8, ls="--"))
    ax.text(41.5, 2.5, "CRQC arrival $F_Q(t)$: Weibull fitted to GRI 2025", ha="center", va="center", fontsize=6.9)
    box(60, 12, 19, 44, "3  One unit",
        "classical and quantum\nboth in USD per year\nof waiting\n\nno weights\nno conversion constant\n\ntwo clocks race:\na quantum loss counts\nonly if the hacker has\nnot already struck", size=7.2)
    box(84.5, 12, 15, 44, "4  Outputs",
        "one ranked list\n\nitem-level backlog\n\nscenario and\ndiscount sweeps\n\nuncertainty\nbands")
    arrow(23.2, 48, 28.4, 48, BLUE); arrow(23.2, 28, 28.4, 21, ORANGE)
    arrow(54.6, 48, 59.4, 44, BLUE); arrow(54.6, 20, 59.4, 28, ORANGE)
    arrow(79.6, 34, 83.9, 34)
    arrow(41.5, 5.1, 41.5, 7.6, GREY)
    save(fig, "fig01_overview")


# ---------------------------------------------------------------------------
def fig_crqc():
    fig, ax = plt.subplots(figsize=(5.6, 3.3))
    t = np.linspace(0, 50, 500)
    ax.axvspan(15, 50, color="#EDEDED", lw=0)
    ax.text(32.5, 0.03, "extrapolation: no published anchor", ha="center", va="bottom", fontsize=8, color="#555")
    ax.plot(t, [OPT.cdf(x) for x in t], color=ORANGE, label=f"optimistic fit (median {OPT.median_years():.1f} y)")
    ax.plot(t, [PESS.cdf(x) for x in t], color=BLUE, label=f"pessimistic fit (median {PESS.median_years():.1f} y)")
    for (tt, p) in GRI_2025_OPTIMISTIC:
        ax.plot([tt], [p], "o", color=ORANGE, ms=5.5, mfc="white", mew=1.4)
    for (tt, p) in GRI_2025_PESSIMISTIC:
        ax.plot([tt], [p], "o", color=BLUE, ms=5.5, mfc="white", mew=1.4)
    ax.annotate("published range\n28-49% at 10 y", xy=(10, 0.49), xytext=(2.0, 0.66), fontsize=7.5, arrowprops=dict(arrowstyle="-", lw=0.6, color=GREY))
    ax.annotate("51-70% at 15 y", xy=(15, 0.70), xytext=(17.5, 0.80), fontsize=7.5, arrowprops=dict(arrowstyle="-", lw=0.6, color=GREY))
    ax.set_xlabel("Years from 2026"); ax.set_ylabel("Probability a CRQC exists, $F_Q(t)$")
    ax.set_xlim(0, 50); ax.set_ylim(0, 1.02)
    top = ax.secondary_xaxis("top", functions=(lambda x: x + 2026, lambda x: x - 2026)); top.set_xlabel("Calendar year")
    top.spines["top"].set_visible(True)
    ax.legend(loc="center right", bbox_to_anchor=(1.0, 0.36), frameon=False)
    save(fig, "fig02_crqc_distribution")


# ---------------------------------------------------------------------------
def fig_race():
    fig, axs = plt.subplots(1, 3, figsize=(7.4, 2.7), sharey=True)
    t = np.linspace(0, 30, 600)
    f = np.array([OPT.pdf(x) for x in t])
    L = 25.0
    for ax, lam, lab in zip(axs, (0.0, 0.05, 0.5), ("no classical hazard", r"quiet asset, $\lambda=0.05$", r"noisy asset, $\lambda=0.5$")):
        ax.fill_between(t, 0, f, where=t <= L, color="#DADADA", lw=0, label="CRQC arrives (density)")
        surv = np.exp(-lam * t)
        ax.fill_between(t, 0, f * surv, where=t <= L, color=ORANGE, alpha=0.85, lw=0, label="...and hacker has not struck")
        ax.axvline(L, color=INK, lw=0.7, ls=":")
        pq = integrate.quad(lambda x: OPT.pdf(x) * math.exp(-lam * x), 0, L)[0]
        ax.set_title(lab, fontsize=8.6)
        ax.text(0.97, 0.93, f"counted: {pq/OPT.cdf(L):.0%}\nof the naive amount", transform=ax.transAxes, ha="right", va="top", fontsize=7.8)
        ax.set_xlabel("Years from now")
    axs[0].set_ylabel("density")
    axs[0].legend(loc="upper left", fontsize=6.8, frameon=False, bbox_to_anchor=(0.0, 0.75))
    axs[0].text(L + 0.4, axs[0].get_ylim()[1] * 0.05, "data stops\nbeing secret", fontsize=6.5, rotation=90, va="bottom")
    save(fig, "fig03_competing_risks")


# ---------------------------------------------------------------------------
def fig_coupling():
    fig, axs = plt.subplots(1, 2, figsize=(7.4, 2.9))
    lam = np.logspace(-2.3, 0.1, 120)
    ax = axs[0]
    for L, c in zip((5, 10, 20, 30, 50), (SKY, BLUE, GREEN, ORANGE, PURPLE)):
        ratio = [quantum_rate(1, 1, L, x, OPT) / OPT.cdf(L) for x in lam]
        ax.plot(lam, ratio, color=c, label=f"$L={L}$ y")
    ax.set_xscale("log"); ax.set_ylim(0, 1.03)
    ax.set_xlabel(r"classical hazard $\lambda$ (per year)"); ax.set_ylabel("coupled / uncoupled quantum term")
    ax.legend(frameon=False, ncol=2, fontsize=7.4); panel_label(ax, "A")
    ax = axs[1]
    V, tau, h, L = 1e7, 0.10, 0.5, 30.0
    cl = lam * V
    qc = np.array([quantum_rate(tau * V, h, L, x, OPT) for x in lam])
    qu = np.array([quantum_rate(tau * V, h, L, x, OPT, competing_risks=False) for x in lam])
    ax.plot(lam, cl, color=BLUE, label="classical  $\\lambda V$")
    ax.plot(lam, qc, color=ORANGE, label="quantum, coupled")
    ax.plot(lam, qu, color=ORANGE, ls="--", lw=1.0, label="quantum, uncoupled")
    lam_star = brentq(lambda x: quantum_rate(tau * V, h, L, x, OPT) - x * V, 1e-4, 1.0)
    ax.axvline(lam_star, color=INK, lw=0.7, ls=":")
    ax.text(lam_star * 1.08, 4.5e6, f"$\\lambda^*={lam_star:.3f}$", fontsize=8, va="bottom")
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_ylim(1e3, 2e7)
    ax.set_xlabel(r"classical hazard $\lambda$ (per year)"); ax.set_ylabel("USD per year of delay")
    ax.legend(frameon=False, fontsize=7.4, loc="lower right"); panel_label(ax, "B")
    ax.set_title(r"$V=\$10$M, $\tau=0.1$, $h=0.5$, $L=30$ y", fontsize=8, pad=3)
    save(fig, "fig04_coupling_and_dominance_threshold")


# ---------------------------------------------------------------------------
def short(name, n=34):
    return name if len(name) <= n else name[: n - 1].rstrip() + "…"


def fig_bars():
    fig, axs = plt.subplots(2, 2, figsize=(7.6, 6.6))
    order = ["mosip", "fineract", "openmrs", "online_boutique"]
    floor, span = 3.0, 4.6                      # axis shows $1k .. $40M
    f = lambda v: 0.0 if v < 10 ** floor else min(math.log10(v) - floor, span)
    for ax, k, lab in zip(axs.ravel(), order, "ABCD"):
        s = R["systems"][k]["scores"]
        y = np.arange(len(s))[::-1]
        for yi, row in zip(y, s):
            ax.barh(yi, -f(row["classical"]), color=BLUE, height=0.62)
            ax.barh(yi, f(row["quantum"]), color=ORANGE, height=0.62)
            move = row["classical_rank"] - row["rank"]
            tag = f"▲{move}" if move > 0 else (f"▼{-move}" if move < 0 else "")
            if tag:
                ax.text(span + 0.15, yi, tag, va="center", ha="left", fontsize=7.2, color=(ORANGE if move > 0 else BLUE))
        ax.set_yticks(y); ax.set_yticklabels([f"{r['id']}  {short(r['name'], 34)}" for r in s], fontsize=6.9)
        pos = [-4, -3, -2, -1, 0, 1, 2, 3, 4]
        tick_labels = ["10M", "1M", "100k", "10k", "0", "10k", "100k", "1M", "10M"]
        ax.set_xticks(pos); ax.set_xticklabels(tick_labels, fontsize=6.4)
        ax.set_xlim(-span - 0.1, span + 1.1); ax.axvline(0, color=INK, lw=0.6)
        ax.set_title(f"{R['systems'][k]['title']}", fontsize=9, loc="left"); panel_label(ax, lab, dx=-0.02, dy=1.07)
        ax.spines["left"].set_visible(False); ax.tick_params(axis="y", length=0)
    fig.legend(handles=[Line2D([0], [0], color=BLUE, lw=6), Line2D([0], [0], color=ORANGE, lw=6)],
               labels=["classical cost of delay (left)", "quantum cost of delay (right)"], loc="lower center", ncol=2, frameon=False)
    fig.text(0.5, 0.045, "USD per year of delay (log scale; 0 = below $1k).  ▲/▼ = places gained/lost versus a classical-only list.",
             ha="center", fontsize=7.6)
    fig.tight_layout(rect=(0, 0.07, 1, 1), h_pad=1.6, w_pad=1.2)
    save(fig, "fig05_cost_of_delay_by_system")


def fig_slope():
    fig, axs = plt.subplots(1, 4, figsize=(7.6, 3.4))
    for ax, k in zip(axs, ("mosip", "fineract", "openmrs", "online_boutique")):
        s = R["systems"][k]["scores"]; n = len(s)
        for row in s:
            a, b = row["classical_rank"], row["rank"]
            c = ORANGE if a > b else (BLUE if a < b else "#B8B8B8")
            ax.plot([0, 1], [-a, -b], color=c, lw=2.0 if a != b else 1.0, alpha=0.95)
            ax.text(-0.06, -a, row["id"], ha="right", va="center", fontsize=6.8)
            ax.text(1.06, -b, row["id"], ha="left", va="center", fontsize=6.8)
        ax.set_xlim(-0.55, 1.55); ax.set_ylim(-n - 0.6, -0.4); ax.axis("off")
        ax.text(0, -0.1, "classical\nonly", ha="center", va="bottom", fontsize=7.2)
        ax.text(1, -0.1, "combined", ha="center", va="bottom", fontsize=7.2)
        ax.set_title(R["systems"][k]["title"], fontsize=8.6, pad=34)
    fig.legend(handles=[Line2D([0], [0], color=ORANGE, lw=2), Line2D([0], [0], color=BLUE, lw=2), Line2D([0], [0], color="#B8B8B8", lw=1)],
               labels=["moves up", "moves down", "unchanged"], loc="lower center", ncol=3, frameon=False)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    save(fig, "fig06_rank_shift")


# ---------------------------------------------------------------------------
def fig_dominance_map():
    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    Ls = np.logspace(-1.2, 1.78, 120)

    def lam_star(L, th):
        g = lambda x: th * OPT_I(x, L) - x
        return brentq(g, 1e-7, th * OPT.cdf(L)) if th * OPT.cdf(L) > 1e-7 else np.nan

    OPT_I = lambda lam, L: quantum_rate(1.0, 1.0, L, lam, OPT)
    for th, ls, lab in ((1.0, "-", r"$\tau h=1$"), (0.3, "--", r"$\tau h=0.3$"), (0.05, ":", r"$\tau h=0.05$")):
        y = np.array([lam_star(L, th) for L in Ls])
        ax.plot(Ls, y, color=ORANGE, ls=ls, lw=1.5, label=lab)
    y1 = np.array([lam_star(L, 1.0) for L in Ls])
    ax.fill_between(Ls, 1e-3, y1, color=ORANGE, alpha=0.10, lw=0)
    ax.text(2.4, 0.0019, "quantum term dominates\nbelow the curve", fontsize=7.6, color=ORANGE, va="bottom")
    markers = {"mosip": "o", "fineract": "s", "openmrs": "^", "online_boutique": "D"}
    for k in R["systems"]:
        assets = [a for a in load_register(ROOT / "case_studies" / k / "asset_register.csv") if "POSITED" not in "".join(a.tags)]
        sc = {r["id"]: r for r in R["systems"][k]["scores"]}
        for a in assets:
            if a.data_lifetime_years <= 0.01:
                continue
            dom = sc[a.asset_id]["quantum"] > sc[a.asset_id]["classical"]
            ax.scatter(a.data_lifetime_years, a.likelihood.per_year, marker=markers[k], s=34,
                       facecolor=SYS_COL[k] if dom else "white", edgecolor=SYS_COL[k], lw=1.2, zorder=3)
    ax.set_xscale("log"); ax.set_yscale("log"); ax.set_ylim(1.2e-3, 1.6); ax.set_xlim(0.06, 70)
    ax.set_xlabel("required confidentiality lifetime $L$ (years)"); ax.set_ylabel(r"classical hazard $\lambda$ (per year)")
    h1 = [Line2D([0], [0], marker=markers[k], color="w", mfc=SYS_COL[k], mec=SYS_COL[k], ms=6, label=SYS_NAME[k]) for k in R["systems"]]
    h2 = [Line2D([0], [0], marker="o", color="w", mfc="w", mec=INK, ms=6, label="classical-led"),
          Line2D([0], [0], marker="o", color="w", mfc=INK, mec=INK, ms=6, label="quantum-led")]
    l1 = ax.legend(handles=h1, loc="upper right", frameon=False, fontsize=7.2); ax.add_artist(l1)
    l2 = ax.legend(handles=h2, loc="lower right", frameon=False, fontsize=7.2); ax.add_artist(l2)
    ax.legend(loc="upper left", frameon=False, fontsize=7.4, title="dominance boundary", title_fontsize=7.4)
    save(fig, "fig07_dominance_map")


# ---------------------------------------------------------------------------
def fig_sensitivity():
    assets = {a.asset_id: a for a in load_register(ROOT / "case_studies" / "openmrs" / "asset_register.csv")}
    fig, axs = plt.subplots(1, 2, figsize=(7.4, 3.0))
    years = np.arange(2028, 2051)
    beta = OPT.beta
    ax = axs[0]
    show = [("O01", BLUE, "-"), ("O09", GREEN, "-"), ("O08", ORANGE, "-"), ("O06", PURPLE, "-"), ("O10", GREY, "--")]
    for aid, c, ls in show:
        a = assets[aid]
        vals = [cost_of_delay(a, CRQCDistribution.from_median(int(y), beta)).total for y in years]
        ax.plot(years, np.array(vals) / 1e3, color=c, ls=ls, label=f"{aid}")
    ax.set_xlabel("median CRQC arrival year"); ax.set_ylabel("cost of delay (k$ per year)")
    ax.legend(frameon=False, ncol=3, fontsize=7.4, loc="upper right"); panel_label(ax, "A")
    for y in MEDIAN_SCENARIOS:
        ax.axvline(y, color="#CCC", lw=0.6, zorder=0)
    ax = axs[1]
    rhos = np.linspace(0, 0.10, 41)
    for aid, c, ls in show:
        a = assets[aid]
        vals = [cost_of_delay(a, OPT, discount_rate=r).total for r in rhos]
        ax.plot(rhos * 100, np.array(vals) / 1e3, color=c, ls=ls, label=aid)
    ax.set_xlabel("discount rate $\\rho$ (%)"); ax.set_ylabel("cost of delay (k$ per year)"); panel_label(ax, "B")
    fig.suptitle("OpenMRS: where the ordering changes", fontsize=9.2, y=1.0)
    fig.tight_layout()
    save(fig, "fig08_scenario_and_discount_sensitivity")


def fig_uncertainty():
    fig, axs = plt.subplots(2, 2, figsize=(7.6, 6.4))
    for ax, k, lab in zip(axs.ravel(), ("mosip", "fineract", "openmrs", "online_boutique"), "ABCD"):
        mc = R["systems"][k]["mc"]["assets"]
        rows = sorted(mc, key=lambda a: a["rank_median"])
        cl = {r["id"]: r["classical_rank"] for r in R["systems"][k]["scores"]}
        for i, a in enumerate(rows):
            y = len(rows) - i
            ax.plot([a["rank_lo"], a["rank_hi"]], [y, y], color=ORANGE, lw=2.2, solid_capstyle="round", alpha=0.85)
            ax.plot(a["rank_median"], y, "o", color=INK, ms=3.6, zorder=3)
            ax.plot(cl[a["asset_id"]], y, "D", mfc="white", mec=BLUE, ms=4.6, mew=1.2, zorder=4)
        ax.set_yticks([len(rows) - i for i in range(len(rows))]); ax.set_yticklabels([a["asset_id"] for a in rows], fontsize=7.4)
        ax.set_xlim(0.3, len(rows) + 0.7); ax.set_xticks(range(1, len(rows) + 1))
        ax.set_xlabel("rank (1 = most urgent)"); ax.set_title(R["systems"][k]["title"], fontsize=9, loc="left"); panel_label(ax, lab, dx=-0.13)
        ax.grid(axis="x", color="#E6E6E6", lw=0.5); ax.set_axisbelow(True)
    fig.legend(handles=[Line2D([0], [0], color=ORANGE, lw=3), Line2D([0], [0], marker="o", color="w", mfc=INK, mec=INK, ms=5),
                        Line2D([0], [0], marker="D", color="w", mfc="white", mec=BLUE, ms=6)],
               labels=["5-95% range of combined rank across 4,000 perturbed registers", "median", "classical-only rank (central estimate)"],
               loc="lower center", ncol=1, frameon=False, fontsize=7.6)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    save(fig, "fig09_rank_uncertainty")


def fig_sobol():
    fig, axs = plt.subplots(1, 4, figsize=(7.8, 3.0), sharey=True)
    for ax, k in zip(axs, ("mosip", "fineract", "openmrs", "online_boutique")):
        so = R["systems"][k]["sobol"]; names = [n.replace("recordable share h", "recordable h").replace("CRQC median year", "CRQC year") for n in so["names"]]
        y = np.arange(len(names))[::-1]
        ST, S = np.array(so["ST"]), np.array(so["S"])
        err = np.array([ST - np.array(so["ST_lo"]), np.array(so["ST_hi"]) - ST])
        ax.barh(y, ST, color="#E8C4A8", height=0.62, xerr=err, error_kw=dict(lw=0.7, capsize=1.5, ecolor=GREY))
        ax.barh(y, S, color=ORANGE, height=0.34)
        ax.set_yticks(y); ax.set_yticklabels(names, fontsize=7.4)
        ax.set_xlim(0, 0.62); ax.set_xlabel("share of variance")
        ax.set_title(f"{R['systems'][k]['title']}\n(asset {so['asset']})", fontsize=7.8)
    fig.legend(handles=[plt.Rectangle((0, 0), 1, 1, color="#E8C4A8"), plt.Rectangle((0, 0), 1, 1, color=ORANGE)],
               labels=["total-order index $S_T$ (95% bootstrap interval)", "first-order index $S_1$"],
               loc="lower center", ncol=2, frameon=False, fontsize=7.6)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    save(fig, "fig10_sobol_indices")


# ---------------------------------------------------------------------------
def fig_validation():
    from costofdelay.validation import mc_quantum_leg
    from costofdelay.scoring import _simpson
    fig, axs = plt.subplots(1, 2, figsize=(7.4, 3.1))
    ax = axs[0]
    pts = []
    for k in R["systems"]:
        for a in load_register(ROOT / "case_studies" / k / "asset_register.csv"):
            if "POSITED" in "".join(a.tags).upper() or not a.quantum_applicable or a.data_lifetime_years < 0.5:
                continue
            for crqc, mk in ((OPT, "o"), (PESS, "s")):
                an = cost_of_delay(a, crqc).quantum
                mc, se = mc_quantum_leg(a, crqc, n=400_000, seed=5)
                pts.append((an, mc, se, k, mk))
    for an, mc, se, k, mk in pts:
        ax.errorbar(an, mc, yerr=3 * se, fmt=mk, color=SYS_COL[k], ms=3.4, lw=0.6, alpha=0.85)
    lim = [min(p[0] for p in pts) * 0.7, max(p[0] for p in pts) * 1.4]
    ax.plot(lim, lim, color=INK, lw=0.8, ls="--"); ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlim(lim); ax.set_ylim(lim)
    ax.set_xlabel("closed form (USD/year)"); ax.set_ylabel("Monte Carlo of the two clocks (USD/year)")
    ax.text(0.04, 0.95, f"{len(pts)} asset × scenario cases\nbars = ±3 s.e.", transform=ax.transAxes, va="top", fontsize=7.6)
    panel_label(ax, "A")
    ax = axs[1]
    d, lam, L = OPT, 0.2, 10.0
    ref = integrate.quad(lambda t: d.pdf(t) * math.exp(-lam * t), 0, L, epsabs=1e-14, epsrel=1e-13, limit=500)[0]
    ns = [50, 100, 200, 400, 800, 1600, 3200, 6400]
    raw = [abs(_simpson(lambda t: d.pdf(t) * math.exp(-lam * t), 0.0, L, n) - ref) / ref for n in ns]
    byp = [abs(math.exp(-lam * L) * d.cdf(L) + lam * _simpson(lambda t: d.cdf(t) * math.exp(-lam * t), 0.0, L, n) - ref) / ref for n in ns]
    ax.loglog(ns, raw, "o-", color=BLUE, ms=3.5, label="Simpson on $f(t)e^{-\\kappa t}$")
    ax.loglog(ns, byp, "s-", color=ORANGE, ms=3.5, label="by parts (used)")
    sl = lambda y: np.polyfit(np.log(ns[:6]), np.log(y[:6]), 1)[0]
    ax.text(0.04, 0.05, f"slopes: {sl(raw):.1f} vs {sl(byp):.1f}", transform=ax.transAxes, fontsize=7.6)
    ax.set_xlabel("quadrature points"); ax.set_ylabel("relative error"); ax.legend(frameon=False, fontsize=7.4, loc="upper right"); panel_label(ax, "B")
    fig.tight_layout()
    save(fig, "fig11_numerical_validation")


def fig_schedule():
    fig, ax = plt.subplots(figsize=(6.3, 3.1))
    ks = list(R["systems"]); x = np.arange(len(ks)); w = 0.26
    smith = [R["systems"][k]["schedule"]["leg"]["smith"] / R["systems"][k]["schedule"]["leg"]["optimal"] for k in ks]
    cf = [R["systems"][k]["schedule"]["leg"]["siloed_classical_first"] / R["systems"][k]["schedule"]["leg"]["optimal"] for k in ks]
    qf = [R["systems"][k]["schedule"]["leg"]["siloed_quantum_first"] / R["systems"][k]["schedule"]["leg"]["optimal"] for k in ks]
    b1 = ax.bar(x - w, smith, w, color=GREEN, label="one list, by cost of delay")
    b2 = ax.bar(x, cf, w, color=BLUE, label="two queues, classical first")
    b3 = ax.bar(x + w, qf, w, color=ORANGE, label="two queues, quantum first")
    for bars in (b1, b2, b3):
        for b in bars:
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.04, f"{b.get_height():.2f}", ha="center", fontsize=6.8)
    ax.axhline(1.0, color=INK, lw=0.8, ls="--"); ax.text(-0.46, 1.03, "exact optimum = 1", fontsize=7.2, ha="left")
    ax.set_xticks(x); ax.set_xticklabels([SYS_NAME[k] for k in ks], fontsize=8)
    ax.set_ylabel("committed loss ÷ exact optimum"); ax.set_ylim(0.9, 4.6); ax.legend(frameon=False, fontsize=7.4, loc="upper right")
    save(fig, "fig12_scheduling")


def fig_signal_noise():
    fig, ax = plt.subplots(figsize=(5.4, 2.9))
    ks = list(R["systems"]); y = np.arange(len(ks))[::-1]
    for yi, k in zip(y, ks):
        f = R["systems"][k]["flip_test"]
        ax.errorbar(f["ratio"], yi, xerr=[[f["ratio"] - f["ratio_lo"]], [f["ratio_hi"] - f["ratio"]]], fmt="o", color=SYS_COL[k], ms=6, capsize=2.5, lw=1.2)
        ax.text(max(f["ratio"], 1.0) + 0.12, yi, f"{f['signal_mean']:.1f} vs {f['noise_pair_mean']:.1f} pairs", va="center", fontsize=7.2)
    ax.axvline(1.0, color=INK, lw=0.8, ls="--")
    ax.set_yticks(y); ax.set_yticklabels([SYS_NAME[k] for k in ks]); ax.set_xlim(0, 1.9)
    ax.set_xlabel("pairs reordered by the quantum term ÷ pairs reordered by input noise")
    ax.text(1.02, len(ks) - 0.45, "quantum term moves\nthe list MORE than noise →", fontsize=7, va="top")
    ax.text(0.98, len(ks) - 0.45, "← LESS than noise", fontsize=7, va="top", ha="right")
    save(fig, "fig13_signal_to_noise")


def fig_pooled():
    P = R["pooled"]
    fig, ax = plt.subplots(figsize=(5.4, 3.5))
    L = np.array(P["lifetimes"]); sh = np.array(P["shares"]); sy = np.array(P["systems"])
    x = np.where(L <= 0.01, 0.003, L)
    rng = np.random.default_rng(3)
    for k in R["systems"]:
        m = sy == k
        ax.scatter(x[m] * np.exp(rng.normal(0, 0.03, m.sum())), sh[m], s=26, color=SYS_COL[k], label=SYS_NAME[k], alpha=0.9, edgecolor="white", lw=0.5)
    ax.set_xscale("log"); ax.set_xlim(0.0018, 90)
    ax.set_xticks([0.003, 0.1, 1, 10, 50]); ax.set_xticklabels(["≈0", "0.1", "1", "10", "50"])
    ax.set_xlabel("required confidentiality lifetime (years)"); ax.set_ylabel("quantum share of cost of delay")
    ax.text(0.03, 0.96, f"Spearman $\\rho={P['spearman']:.2f}$\n95% CI [{P['ci_lo']:.2f}, {P['ci_hi']:.2f}] (cluster bootstrap, {P['n_clusters']} systems)\n"
            f"within-system permutation $p={P['permutation_p_within_system']:.4f}$", transform=ax.transAxes, va="top", fontsize=7.4)
    ax.legend(frameon=False, fontsize=7.2, loc="center left", bbox_to_anchor=(0.0, 0.62))
    save(fig, "fig14_lifetime_vs_quantum_share")


def fig_convergence():
    fig, ax = plt.subplots(figsize=(4.8, 2.9))
    conv = R["systems"]["openmrs"]["convergence"]
    n = [c["n"] for c in conv]; p = [c["p"] for c in conv]
    ax.fill_between(n, [c["lo"] for c in conv], [c["hi"] for c in conv], color=ORANGE, alpha=0.2, lw=0)
    ax.plot(n, p, "o-", color=ORANGE, ms=3.6)
    ax.set_xscale("log"); ax.set_xlabel("Monte Carlo draws"); ax.set_ylabel("P(O08 is quantum-led)")
    ax.set_ylim(0.75, 1.0); ax.text(0.97, 0.06, "band = 95% Wilson interval", transform=ax.transAxes, ha="right", fontsize=7.4)
    save(fig, "fig15_monte_carlo_convergence")


def main():
    for fn in (fig_overview, fig_crqc, fig_race, fig_coupling, fig_bars, fig_slope, fig_dominance_map,
               fig_sensitivity, fig_uncertainty, fig_sobol, fig_validation, fig_schedule, fig_signal_noise,
               fig_pooled, fig_convergence):
        fn()
    print("done")


if __name__ == "__main__":
    main()
