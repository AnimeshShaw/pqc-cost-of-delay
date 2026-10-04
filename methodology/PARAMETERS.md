# Parameters: definitions, anchors and honest limits

This document explains every number the model uses: what it means, where its value comes from, how well that value is supported, and how much the answer depends on it. Per-asset values are in [`PARAMETERS_BY_ASSET.md`](PARAMETERS_BY_ASSET.md) (generated from the CSV registers that the code reads).

## 0. What "assumed" means here

**No organisation supplied data.** Every asset value in the four case studies is an *assumption derived from public documentation*, labelled `ASSUMED_FROM_PUBLIC_DOCS` in the registers. The case-study registers were drafted with the assistance of a large language model (see *AI usage* in the README); the author is responsible for them and has not validated them against any operator's deployment.

The values are therefore **calibrated assumptions**, not measurements, in this specific sense:

* **Anchored:** the band midpoints and the CRQC curve are tied to a published number (IBM 2025; Ponemon/IBM 2018; Global Risk Institute 2025; FATF Rec. 11).
* **Judged:** which band a given asset falls in is a judgement made from the system's public design documents. Two analysts could differ. The uncertainty analysis (`STATISTICS.md`) re-draws every judged value within a stated range and reports which conclusions survive.

Two structural facts reduce how much the judgements matter:

1. **Proposition 1** (`FORMAL_METHOD.md`): the *ranking* is unchanged by any common rescaling of money, so absolute dollar calibration affects only the stated magnitudes. Only the *relative* values between assets matter for the order.
2. **Proposition 8**: whether the quantum term dominates an asset depends on $\lambda<\lambda^*(\tau,h,L,\rho)$, which does **not** involve the loss value $V$ at all.

## 1. The parameters at a glance

| Symbol | Name | Unit | Source of the *scale* | How the *asset's value* is chosen | Support |
|---|---|---|---|---|---|
| $V$ | Loss if disclosed | USD | IBM 2025 per-record cost | band chosen from the data's sensitivity and volume | band midpoints anchored; per-asset choice judged |
| $\lambda$ | Classical hazard | events / year | Ponemon/IBM 2018 | band chosen from exposure and hardening | anchored to one organisation-level rate; relative multipliers judged |
| $L$ | Confidentiality lifetime | years | retention rules, design facts | cited per asset | strongest input: tied to a rule or design fact where one exists |
| lock | Protection class | category | cryptographic fact | observed from public docs | factual where documented; several assumed `[VERIFY]` |
| $h$ | Recordable share | 0–1 | topology | band chosen from where traffic travels | judged |
| $\tau$ | Annual turnover | per year | none published | judged; consistency rule in §2.6 | **weakest input** |
| $F_Q(t)$ | CRQC arrival law | probability | GRI 2025 survey | fitted to two published points | anchored to 10 y and 15 y only; extrapolated beyond |
| $\rho$ | Discount rate | per year | none (value judgement) | default 0, swept to 10% | explicit value judgement |

## 2. Each parameter

### 2.1 Loss $V$ and the value bands

**Definition.** The loss, in USD, if the asset's data for one retention period (or, for a transit flow, one year of flow; see §2.6) is disclosed.

**Anchor.** IBM's *Cost of a Data Breach Report 2025* (read in full; conducted by the Ponemon Institute): global average breach cost **$4.44M**; financial services **$5.56M**; healthcare **$7.42M**; United States **$10.22M**; India **$2.51M**. Cost per record for customer personal data: **$160**; employee personal data $168; intellectual property $178. The study covered **600 organisations** and breaches of **2,960 to 113,620 records**.

**Bands.** The five bands are 10× apart (log-spaced) because practitioners distinguish "tens of thousands" from "millions" far more reliably than $2.0M from $3.5M.

| Band | USD | ≈ customer records at $160 | Meaning |
|---|---|---|---|
| NEGLIGIBLE | 0 | 0 | public data; no confidentiality requirement (needs written evidence) |
| LOW | 10k | 60 | a handful of accounts; a short-lived credential |
| MODERATE | 100k | 600 | a department's records |
| HIGH | 1M | 6,250 | a mid-sized dataset; **inside IBM's sampled range** |
| SEVERE | 10M | 62,500 | a large customer or patient base; **inside IBM's sampled range** (upper end) |
| CATASTROPHIC | 100M | 625,000 | national scale; **outside IBM's sampled range** |

**Limits, stated plainly.**

* IBM's per-record cost is an *average over breaches of 3k–114k records*. Cost per record **falls** for mega-breaches (Edwards et al. 2016 find breach sizes extremely heavy-tailed; Eling & Wirfs 2019 find severity heavy-tailed). So a national-scale asset valued at 625,000 × $160 would be overstated; we cap the case-study systems at SEVERE even where the real stock is larger.
* The costs include notification, response, lost business and fines; they are *averages across industries and countries*. India's average ($2.51M) is lower than the global figure; we use one scale for all four systems so that the comparison across systems is internally consistent. By Proposition 1, the order within a system is unaffected.

### 2.2 Classical hazard $\lambda$ and the hazard bands

**Definition.** The expected number of times per year that a classical channel (hacking, insider, misconfiguration) discloses **this asset's data**. Confidentiality only; integrity and availability events must not be entered.

**Anchor.** Ponemon/IBM *2018 Cost of a Data Breach*: among 477 companies that had experienced a breach, the likelihood of a *recurring material breach within the next two years* was **27.9%** (as quoted in IBM's published summary; the figure is conditional on the company already having been breached, so it may overstate the rate for organisations in general). Under a constant-rate (Poisson) assumption this is
$$\lambda_{\text{org}}=-\tfrac12\ln(1-0.279)=0.164\ \text{per year},\qquad P(\text{at least one breach in a year})=15.1\%.$$

**Bands.** Each band is expressed as a multiple of this *organisation-level* rate, reflecting how exposed a single data store is relative to the organisation as a whole:

| Band | $\lambda$ per year | × organisation rate | Typical asset |
|---|---|---|---|
| RARE | 0.01 | 0.06 | segmented, hardened, rarely a direct target (e.g. an off-site backup) |
| UNLIKELY | 0.05 | 0.3 | well-defended internal store |
| POSSIBLE | 0.20 | 1.2 | typical business data store |
| LIKELY | 0.50 | 3 | internet-facing store or frequently targeted flow |
| FREQUENT | 1.00 | 6 | credentials and sessions attacked continuously |

**Limits.** The anchor is one survey of one kind of event. The *multipliers* are judgements, not measurements. A heavy-tailed, time-varying reality (Eling, Ibragimov & Ning on the time dynamics of cyber risk) is replaced here by a constant rate. The Sobol analysis (`STATISTICS.md`) shows the *magnitude* of the quantum cost is almost insensitive to $\lambda$ for long-lived assets, but $\lambda$ decides *which* leg dominates (Proposition 8).

### 2.3 Lifetime $L$

**Definition.** How long, in years, the data must stay confidential from the moment it is created or sent.

**How it is chosen.** From a rule or a design fact, cited in each asset's rationale:

| Basis | Lifetime used | Systems |
|---|---|---|
| **FATF Recommendation 11**: customer due diligence and transaction records kept at least **five years** after the business relationship ends | 7–15 y (a ~10-year relationship + the 5-year minimum, or a longer national rule) | Fineract |
| State medical-record retention rules: adults typically 5–10 years from last service; **minors until age of majority plus a limitation period**; one cited state retains to age 30 *(secondary sources; `[VERIFY]`)* | 10 y adult; **30 y** minors and sensitive categories | OpenMRS |
| **Biometric traits are permanent**: confidentiality must outlast the resident | **50 y** (capped; see below) | MOSIP |
| Session lifetime of hours | 0.0001 y (about 1 hour) | all |
| Public data (no confidentiality requirement) | 0, **with written evidence** | catalogues, schemas |

**Cap at 50 years.** Beyond 15 years the CRQC curve is extrapolation (§2.8); beyond 50 it is purely speculative, so long lifetimes are capped.

**Why this is the strongest input.** It is tied to a published rule or an immutable design fact for most assets, and Proposition 8's boundary is monotone in $L$.

### 2.4 Protection class (the "lock")

**Definition.** The cryptography currently protecting the asset's data *in transit* (the channel an adversary can record). It decides whether the quantum term can be non-zero at all.

| Class | Quantum-vulnerable? | Reason |
|---|---|---|
| RSA_2048, RSA_4096 | **yes** | Shor's algorithm breaks RSA key exchange; recorded traffic can be decrypted later |
| ECDH_P256, ECDH_P384 | **yes** | Shor breaks elliptic-curve Diffie–Hellman. *X25519 (the usual TLS 1.3 default) is also quantum-vulnerable and is entered as ECDH.* |
| AES_256_PSK | no | symmetric key shared in advance; Grover's search halves effective strength to 128 bits, which is adequate |
| ML_KEM_768 | no | NIST FIPS 203 post-quantum key encapsulation |
| HYBRID_X25519_MLKEM | no | hybrid; secure if either component holds |
| NONE | no (quantum term) | no encryption; classical sniffing dominates and a quantum computer adds nothing |

**Limit.** Grover's effect on AES-128 is not modelled. Several system-specific locks (e.g. MOSIP's packet encryption) are assumed RSA-based from public descriptions and marked `[VERIFY]`.

### 2.5 Recordable share $h$

**Definition.** The fraction of the asset's data flow that crosses a channel on which a *passive* adversary with storage could record the ciphertext. It is about **observation opportunity**, not storage cost: Blanco-Romero et al. (2026) find retaining intercepted traffic is economically trivial, so what limits harvesting is access to the channel.

| Band | $h$ | Meaning |
|---|---|---|
| NONE | 0 | never leaves a physically controlled boundary. **Requires written evidence** (the code refuses the value otherwise). |
| LOW | 0.1 | private interconnect inside a trusted data centre; collection needs an insider or in-network foothold |
| PARTIAL | 0.5 | mixed internal and external paths (e.g. replication to a second site) |
| HIGH | 0.9 | crosses public networks routinely |
| FULL | 1.0 | all of it is on an internet-facing channel |

**Limit.** A single number per asset hides *who* can observe which channel (a wide-area observer sees internet traffic and not east–west traffic; an insider sees the reverse). Per-adversary exposure is future work.

### 2.6 Annual turnover $\tau$ (the weakest input)

**Definition.** $\tau=$ (new data per year) ÷ (data at risk). It sets the rate at which new value crosses the harvestable channel: $r=\tau V$. A pond refilled once a year has $\tau=1$; an archive growing 5% a year has $\tau=0.05$.

**Consistency rule (added after a self-review).** $V$ and $\tau$ together define $r=\tau V$, so assets that carry the *same data in different forms* must agree. A transit **flow** asset's $V$ is **one year of that flow**; a **store**'s $V$ is the whole stock. Therefore for a flow of the same data, $V_{\text{flow}}\approx\tau_{\text{store}}\times V_{\text{store}}$. Example (MOSIP): the repository holds a $10M stock growing 5% a year, so a year of registration packets is about $0.5M, entered as the HIGH band ($1M) with $\tau=1$. An earlier draft entered the packets at SEVERE ($10M) and overstated their cost of delay about tenfold; that was corrected and every result regenerated. Pre-correction numbers are not used anywhere.

**Default.** If $\tau$ is left blank, $r=V$ (full annual re-exposure) and the scorer **reports** that the default was used.

**Why it is the weakest input.** No published source gives turnover for these systems, and the variance decomposition shows that $\tau$ and $V$ together explain 73–91% of the variance of the quantum term (across the four key assets) (`STATISTICS.md`, Sobol indices). It is the first thing a real organisation would supply.

### 2.7 Migration time $M$

Used only in two places: Mosca's inequality (as a baseline comparison) and the optional "migration" duration variant of the scheduling analysis. Values are judged (1–4 years) from the register. They do not enter the cost-of-delay ranking itself.

### 2.8 CRQC arrival law $F_Q(t)$

**Anchor.** *Quantum Threat Timeline Report 2025*, Mosca & Piani, evolutionQ / Global Risk Institute, published 2026-03-09, 26 experts. Probability of a cryptographically relevant quantum computer within **10 years: 28–49%**; within **15 years: 51–70%**. The low and high ends define two named scenarios (pessimistic; optimistic). The Weibull $(\alpha,\beta)$ is solved in closed form from the two points of each scenario (Proposition 11): optimistic $\alpha=13.18,\ \beta=1.433$ (median 10.2 y); pessimistic $\alpha=17.90,\ \beta=1.912$ (median 14.8 y).

**Limits.**

* The curve is an **interpolation of two points**. Beyond 15 years it is extrapolation, and most long-lived assets sit there.
* The report's statement that 92% of respondents rated 20-year arrival at 50% or above is a *count of respondents*, not an averaged probability, and is deliberately **not** used as an anchor.
* The expert estimate moved by 15 percentage points in one year (Baradziej 2026), so the scenario sweep is part of the result, not decoration.
* *Secondary-source status:* the figures were confirmed from two secondary sources and the GRI landing page; the full PDF was not read.

### 2.9 Discount rate $\rho$

A value judgement, not a measurement. Default 0 (interception harm is locked in at harvest; Baradziej 2026), swept to 10%. Discounting at $\rho$ is algebraically identical to adding $\rho$ to the classical hazard (Proposition 7).

### 2.10 Uncertainty ranges used in the simulations

| Input | Range used | Why |
|---|---|---|
| Loss $V$ | ± half a band (±0.5 decade) | adjacent bands are 10× apart; analysts plausibly differ by one band |
| Hazard $\lambda$ | × or ÷ 2 | the multipliers in §2.2 are judgements; a factor of 2 is a generous within-band spread |
| Lifetime $L$ | × or ÷ 1.5 | retention rules vary by jurisdiction |
| Recordable $h$ | ± 0.1 | one band step |
| Turnover $\tau$ | × or ÷ 3 | the weakest input, so the widest range |
| CRQC | pessimistic or optimistic, equal probability | the two published scenarios |
| Discount $\rho$ | uniform on 0–7% | spans zero to a public-sector benefit–cost rate |

All draws are log-uniform for multiplicative inputs. Gated zeros stay zero in every draw. **These ranges are themselves assumptions**, and the Sobol shares depend on them.

## 3. How to read the results given all this

* **Trust more:** results that hold across the whole uncertainty range (e.g. a quantum term that is zero for assets already on ML-KEM; the ordering of effect size by data lifetime; the finding that the CRQC date explains little of the variance).
* **Trust less:** the exact dollar values; the exact ranks of assets whose rank intervals in Figure 9 (`python scripts/make_figures.py`) are wide.
* **Do not trust:** any statement that a particular real system *has* these exposures. Only an assessment of that system with its own data can say so.

## 4. What an organisation should supply instead

1. Replace $V$ with its own breach-impact estimate for the data in question.
2. Replace $\lambda$ with its own incident history or a threat-model-derived rate.
3. State $L$ from its own regulatory and contractual retention terms.
4. **Observe** the protection class (scan, configuration, certificates); do not assume it.
5. Supply $\tau$ from its own data volumes (records created per year ÷ records held).
6. Document, with evidence, any $h=0$ or $L=0$ claim; the software will not accept it otherwise.

## 5. What would change our minds

* A published dataset linking realised harvest-now-decrypt-later harm to asset attributes, which would let $h$ and $\tau$ be estimated rather than judged.
* A real register in which the quantum-led class is empty: the conclusion for that sector would be that the quantum term changes magnitudes but not what is funded.
* A demonstration that classical disclosure and CRQC arrival are strongly dependent (e.g. through a common state-level adversary), which would require replacing Assumption A3.

## Sources (full bibliography in the accompanying paper)

IBM Security & Ponemon Institute (2025); Ponemon Institute / IBM (2018); Mosca & Piani (2025); FATF (2012, as updated); Edwards, Hofmeyr & Forrest (2016); Eling & Wirfs (2019); Eling, Ibragimov & Ning (2023); Blanco-Romero et al. (2026); Baradziej (2026); NIST FIPS 203; NIST IR 8547 (draft).
