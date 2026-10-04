# Contributing

Thank you for your interest. This is research code; correctness and honesty matter more than features.

## Ways to contribute

1. **A real register.** The most valuable contribution. Provide an asset register (CSV, format below) from a real or realistic system, ideally with the sources of each value. Anonymise anything sensitive. This replaces assumed inputs and tests the central empirical question.
2. **Bug reports and counter-examples.** If a proposition fails, a test is wrong, or a result does not reproduce, open an issue with the command and output.
3. **Review of the mathematics, statistics or references.** Disagreement with a proof, an assumption or a citation is welcome and will be recorded in the issue tracker and answered in the paper's next revision.
4. **New case studies** from public systems, with a rationale for every value.

## Development

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest -q                                   # all tests must pass
node app/test.js                                      # JS port must match Python
python scripts/reproduce.py                           # regenerates results (and the paper's figures into `paper/figures/`)
```

* Keep the scoring core (`costofdelay/scoring.py`, `crqc.py`, `model.py`) free of third-party dependencies.
* Every change to a formula needs a test, and a change to behaviour needs the matching proposition in `methodology/FORMAL_METHOD.md` updated.
* After changing any register or model code, run `python scripts/reproduce.py` and commit the regenerated `results/` together with the change. Never edit a generated number by hand.
* Do not tune inputs to improve a result. If a result is unexpected, report it.

## Register format

A CSV with the columns `asset_id, name, services, value_band, likelihood_band, data_lifetime_years, protection_class, harvest_band, turnover_per_year, migration_time_years, evidence_for_zeroing, rationale, provenance`. Allowed band names and their meanings are in `methodology/PARAMETERS.md`. A recordable share of `NONE` or a lifetime of `0` must carry text in `evidence_for_zeroing`; the loader refuses the row otherwise. `provenance` must be one of `OBSERVED`, `ASSUMED_FROM_PUBLIC_DOCS` or `POSITED`.

## Style

Python 3.10+, type hints where they clarify, plain-English docstrings that state the *why*. Comments explain assumptions and limits, not what the code does.

## Conduct

Be courteous and assume good faith. Critique ideas, not people.

## Licence of contributions

By contributing you agree that your contribution is licensed under the Apache License 2.0, as in `LICENSE`.
