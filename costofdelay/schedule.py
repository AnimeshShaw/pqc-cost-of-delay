"""
Why rank by cost of delay? Because it is the order that minimises accrued loss.

A security team has a backlog of work items and one team to execute them. Item
j needs p_j years of work and, until it is finished, costs w_j USD per year.
Finishing order determines total loss: an item finished late has bled for longer.

Smith's rule (Smith, 1956) says the order that minimises  sum_j w_j * C_j
(C_j = completion time of item j) is non-increasing  w_j / p_j.  When all items
take equal time this is simply "highest cost of delay first" -- the ranking this
library produces. Proposition 8 in methodology/FORMAL_METHOD.md proves it by an
adjacent-interchange argument; tests/test_theory.py checks it by brute force.

This module has two jobs:

  1. Build the backlog from a register. Two views are supported:
       * "asset"  : one item per asset ("harden this asset": both legs removed)
       * "leg"    : two items per asset, a classical fix and a PQC migration,
                    each carrying only its own leg. This is the literal answer
                    to "should I fix the hacking risk on A or upgrade the locks
                    on B?" -- both kinds of work sit on one list.
  2. Evaluate any ordering, with the quantum leg accruing at its exact
     time-varying rate (it rises as a quantum computer becomes more likely),
     and find the true optimum by dynamic programming over subsets, so the
     first-order Smith ordering can be compared with the exact optimum.

Time-varying quantum accrual
----------------------------
Traffic sent at calendar time s (years from now) is lost to a quantum attacker
if a quantum computer exists by s (it then decrypts live) or arrives within the
data's remaining life, and the classical hazard has not already disclosed it:

    g(s) / (r h)  =  F(s)  +  int_s^{s+L} f(t) exp(-kappa (t - s)) dt
                  =  exp(-kappa L) F(s + L)  +  kappa * int_s^{s+L} F(t) exp(-kappa (t - s)) dt

with kappa = lambda + rho. At s = 0 this is the cost-of-delay rate. The loss
committed by finishing the migration at time C is  int_0^C g(s) ds.

numpy is used here (and only in analysis modules); the core scoring in
scoring.py is dependency-free.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Callable, Sequence

import numpy as np

from costofdelay.crqc import CRQCDistribution
from costofdelay.model import Asset
from costofdelay.scoring import cod_classical, cod_quantum


# ---------------------------------------------------------------------------
# Work items
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class WorkItem:
    item_id: str
    asset_id: str
    leg: str                      # "classical" | "quantum" | "asset"
    duration: float               # p_j, years of team time
    rate0: float                  # w_j at s = 0, USD/year (the cost of delay)
    cumulative: Callable[[float], float]  # L_j(C): loss committed if finished at time C

    @property
    def smith_key(self) -> float:
        return self.rate0 / self.duration


def _gauss_cumulative(f_vals: np.ndarray, grid: np.ndarray) -> Callable[[float], float]:
    """Cumulative trapezoid integral of tabulated values, as an interpolating function."""
    cum = np.concatenate([[0.0], np.cumsum(0.5 * (f_vals[1:] + f_vals[:-1]) * np.diff(grid))])
    return lambda c: float(np.interp(c, grid, cum))


def quantum_accrual_rate(asset: Asset, crqc: CRQCDistribution, s: np.ndarray,
                         rho: float = 0.0, n_inner: int = 600) -> np.ndarray:
    """g(s): USD/year of quantum loss committed by exposure at calendar time s."""
    if not asset.quantum_applicable:
        return np.zeros_like(s, dtype=float)
    L = asset.data_lifetime_years
    kappa = asset.likelihood.per_year + rho
    scale = asset.flow_rate * asset.harvest_exposure.fraction

    def F(t):
        t = np.maximum(t, 0.0)
        return 1.0 - np.exp(-((t / crqc.alpha) ** crqc.beta))

    # inner integral over u in [0, L]: F(s+u) * exp(-kappa*u), Simpson, vectorised over s
    u = np.linspace(0.0, L, n_inner + 1)
    w = np.ones(n_inner + 1); w[1:-1:2] = 4.0; w[2:-1:2] = 2.0
    h = L / n_inner
    inner = (F(s[:, None] + u[None, :]) * np.exp(-kappa * u)[None, :] * w[None, :]).sum(axis=1) * h / 3.0
    return scale * (np.exp(-kappa * L) * F(s + L) + kappa * inner)


def build_items(assets: Sequence[Asset], crqc: CRQCDistribution, *, view: str = "leg",
                durations: str = "unit", rho: float = 0.0, horizon: float = 40.0,
                n_grid: int = 801) -> list[WorkItem]:
    """
    Build the backlog.

    view      "leg" (classical and quantum items separately) or "asset" (one combined item)
    durations "unit"      every item takes 1 year of team time
              "migration" the quantum/asset item takes the register's migration time;
                          classical items take 1 year (an assumption; the register
                          holds no classical remediation times)
    """
    grid = np.linspace(0.0, horizon, n_grid)
    items: list[WorkItem] = []
    for a in assets:
        p_m = a.migration_time_years if durations == "migration" else 1.0
        w_c = cod_classical(a)
        w_q = cod_quantum(a, crqc, discount_rate=rho)
        if view == "asset":
            g = quantum_accrual_rate(a, crqc, grid, rho)
            cum_q = _gauss_cumulative(g, grid)
            items.append(WorkItem(f"{a.asset_id}", a.asset_id, "asset", p_m, w_c + w_q,
                                  (lambda C, w=w_c, cq=cum_q: w * C + cq(C))))
        else:
            if w_c > 0:
                items.append(WorkItem(f"{a.asset_id}-C", a.asset_id, "classical", 1.0, w_c,
                                      (lambda C, w=w_c: w * C)))
            if w_q > 0:
                g = quantum_accrual_rate(a, crqc, grid, rho)
                items.append(WorkItem(f"{a.asset_id}-Q", a.asset_id, "quantum", p_m, w_q,
                                      _gauss_cumulative(g, grid)))
    return items


# ---------------------------------------------------------------------------
# Orderings and evaluation
# ---------------------------------------------------------------------------

def total_loss(order: Sequence[WorkItem]) -> float:
    """Sum of committed loss when items are executed back-to-back in this order."""
    t, total = 0.0, 0.0
    for it in order:
        t += it.duration
        total += it.cumulative(t)
    return total


def smith_order(items: Sequence[WorkItem]) -> list[WorkItem]:
    """Non-increasing rate0 / duration. Ties broken by item id for determinism."""
    return sorted(items, key=lambda it: (-it.smith_key, it.item_id))


def siloed_order(items: Sequence[WorkItem], first: str = "classical") -> list[WorkItem]:
    """
    Two separate backlogs, each ranked by its own cost of delay, one finished
    before the other starts. This is what a team does when classical findings
    and PQC migration live in different processes.
    """
    other = "quantum" if first == "classical" else "classical"
    a = smith_order([i for i in items if i.leg == first])
    b = smith_order([i for i in items if i.leg == other])
    return a + b


def optimal_order(items: Sequence[WorkItem], max_items: int = 16) -> tuple[list[WorkItem], float]:
    """
    Exact minimiser of total committed loss by dynamic programming over subsets:

        f(S) = min_{j in S}  f(S \\ {j}) + L_j( P(S) ),    P(S) = sum of durations in S

    Valid for time-varying loss functions L_j (Smith's rule is exact only for
    constant rates). Exponential in the number of items; capped at `max_items`.
    """
    n = len(items)
    if n > max_items:
        raise ValueError(f"{n} items exceeds the DP cap of {max_items}")
    if n == 0:
        return [], 0.0
    p = np.array([it.duration for it in items])
    size = 1 << n
    P = np.zeros(size)
    for mask in range(1, size):
        low = (mask & -mask).bit_length() - 1
        P[mask] = P[mask & (mask - 1)] + p[low]
    f = np.full(size, np.inf); f[0] = 0.0
    choice = np.zeros(size, dtype=np.int64)
    for mask in range(1, size):
        t = P[mask]
        best, bj = np.inf, -1
        m = mask
        while m:
            j = (m & -m).bit_length() - 1
            m &= m - 1
            v = f[mask ^ (1 << j)] + items[j].cumulative(t)
            if v < best:
                best, bj = v, j
        f[mask], choice[mask] = best, bj
    order, mask = [], size - 1
    while mask:
        j = int(choice[mask]); order.append(items[j]); mask ^= 1 << j
    order.reverse()
    return order, float(f[size - 1])


def brute_force_constant_rate(w: Sequence[float], p: Sequence[float]) -> tuple[tuple[int, ...], float]:
    """Exhaustive minimiser of sum w_j C_j (constant rates). Used to verify Smith's rule."""
    best, best_perm = np.inf, ()
    for perm in itertools.permutations(range(len(w))):
        t, tot = 0.0, 0.0
        for j in perm:
            t += p[j]; tot += w[j] * t
        if tot < best - 1e-12:
            best, best_perm = tot, perm
    return best_perm, float(best)
