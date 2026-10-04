# Cost of Delay for Post-Quantum Migration

**[Live explorer](https://animeshshaw.github.io/pqc-cost-of-delay/)** · reference implementation, proofs, case studies and statistics for a research paper.

Classical hacking risk and *harvest-now-decrypt-later* (HNDL) quantum risk, expressed in one unit — **US dollars of loss per year of delay** — so a single ordered list can answer *"should we close this classical finding, or migrate that asset's cryptography first?"*

> **Status: research prototype.** All case-study inputs are *assumptions derived from public documentation*; no organisation supplied data, and the method has not been validated against real incidents or migrations. See [Caveats](#caveats).

## What this is

Attackers can copy encrypted data today and decrypt it once a large quantum computer exists. How much that matters depends on how long the data must stay secret, whether it can be recorded, and whether an ordinary attacker would have taken it first. Existing post-quantum risk scores are dimensionless and quantum-only, so they cannot be compared with classical risk, which is measured in dollars.

This repository computes, for each asset, the **cost of waiting one more year** from each threat, in dollars, and couples them so the same loss is not counted twice. It contains:

* a small Python library (`costofdelay/`) with the model, the arrival-time law for a quantum computer, uncertainty propagation, sensitivity analysis and a scheduling check;
* proofs of the model's properties, each backed by an automated test;
* four public case studies (national ID, banking, medical records, demo shop) with a written reason for every input value;
* an interactive explorer (`app/`) that runs in a browser and explains every input.

## At a glance

| | |
|---|---|
| **Idea** | Classical term = annualised loss $\lambda V$. Quantum term = $r\,h\int_0^L f_Q(t)\,e^{-(\lambda+\rho)t}\,dt$, the rate at which deferring migration commits irreversible loss. Both in USD/year; a competing-risks factor stops the same loss being counted twice. |
| **Proved** | Units, no double counting, bounds, comparative statics, a closed-form dominance threshold, non-separability, and optimality of the ordering under Smith's rule ([`methodology/FORMAL_METHOD.md`](methodology/FORMAL_METHOD.md)). |
| **Verified** | 256 automated tests; Monte Carlo and quadrature cross-checks; a second (JavaScript) implementation matching 577 values. |
| **Evaluated on** | MOSIP (national ID), Apache Fineract (banking), OpenMRS (medical records), Online Boutique (demo shop, procedure test only). |
| **Headline results** | The quantum term changes *magnitudes* and a few *specific assets* decisively, but moves the whole list less than input noise does for three of the four systems. The quantum-arrival date explains only 3–17% of the uncertainty; loss and turnover explain 73–91% ([`methodology/STATISTICS.md`](methodology/STATISTICS.md)). |

## Reproduce everything

Requires Python ≥ 3.10. Node ≥ 18 is optional (it runs the check on the explorer's maths).

```bash
git clone https://github.com/AnimeshShaw/pqc-cost-of-delay && cd pqc-cost-of-delay
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/reproduce.py
```

`reproduce.py` runs, in order: the test suite → numerical validation → the statistical analysis (`results/`) → the figures (`paper/figures/`, created if missing) → the parameter tables → the explorer's data and its cross-language check. It takes roughly 2–4 minutes and is deterministic (every random procedure has a fixed seed). Afterwards `git diff --stat results/` should show **no change**, or differences only in the last printed digit if your NumPy/SciPy versions differ. Exact tested versions are in `requirements-lock.txt`.

To explore interactively, use the [live explorer](https://animeshshaw.github.io/pqc-cost-of-delay/) or open `app/index.html` locally. It needs no server, and the page's code makes no network requests and sends your inputs nowhere (GitHub, as host, logs ordinary page visits).

To score your own register:

```bash
python -m costofdelay.register path/to/asset_register.csv
```

The CSV format is described in [`methodology/PARAMETERS.md`](methodology/PARAMETERS.md) and exemplified in `case_studies/`.

## Repository layout

| Path | Contents |
|---|---|
| `costofdelay/` | The Python package: CRQC arrival law, asset model, scoring, a comparator for the published QARS score, uncertainty and statistics, scheduling. The scoring core uses only the standard library. |
| `tests/` | Unit tests, property tests of every proposition, refutation baselines |
| `methodology/` | Proofs; parameter definitions and anchors; statistical analysis |
| `case_studies/` | The four asset registers (CSV), one per system |
| `scripts/` | Reproduction, results, figures and tables |
| `results/` | Generated numbers (JSON, CSV, Markdown) |
| `app/` | Interactive explorer (HTML/JavaScript) with a Python-parity test |

## Caveats

1. **Inputs are assumed, not measured.** Every asset value was derived from public documentation (IBM 2025 breach costs; Ponemon/IBM 2018; FATF Rec. 11; retention rules; system design documents) and drafted with LLM assistance. Two analysts could differ. The uncertainty analysis re-draws every input within stated ranges and reports which conclusions survive.
2. **The weakest inputs are annual turnover and recordable share.** No published source gives them for these systems.
3. **The arrival law is an interpolation of two published points** (Global Risk Institute 2025: 28–49% within 10 years, 51–70% within 15) and is extrapolated beyond 15 years, where most long-lived assets sit.
4. **Confidentiality only.** Integrity and availability are out of scope.
5. **Classical and quantum disclosure are assumed independent** with a constant classical hazard.
6. **Online Boutique is a mock system**; it tests the procedure, not real data.
7. **Optimality is model-internal.** Ranking by cost of delay minimises accrued loss *under the model's own loss definition*; that is not evidence about real organisations.
8. **Prior art is close.** Per-asset quantum scoring, the protection-class and exposure gates, and ranking were published before this work (Grigaliūnas & Brūzgienė 2025 and 2026; US 12,519,809). The contribution is the common currency unit with a competing-risks coupling, its proofs, and its evaluation.

## Future research

* Elicit parameters from practitioners on real registers and measure inter-rater agreement.
* Replace the single recordable share with a per-adversary exposure (a wide-area observer sees internet traffic; an insider sees east–west traffic).
* Estimate turnover and recordable share from data (cryptographic bills of materials, traffic inventories).
* Relax independence and the constant classical hazard; add a correlated-adversary model.
* Outcome validation against any available incident or migration-effort data.
* Extend to integrity and availability.

## Collaboration

If your organisation would like to test the method on a real register, or use the code or paper as a starting point, you are welcome to get in touch: **animesh15b@iimk.edu.in**. Contributions are described in [`CONTRIBUTING.md`](CONTRIBUTING.md).

## AI usage

A large language model (Anthropic's Claude, via Claude Code) was used substantially to draft code, tests, figures, case-study registers and text, and in literature search, under the author's direction. It is not an author. The author is responsible for the content. Every reference with a DOI or arXiv identifier was checked against its registry by script; the mathematics is covered by proof *and* by independent tests; errors made along the way (for example two wrong DOIs and an overstated asset value) were caught by those checks and corrected.

## Licence and citation

Apache License 2.0 (`LICENSE`). Cite via [`CITATION.cff`](CITATION.cff).
