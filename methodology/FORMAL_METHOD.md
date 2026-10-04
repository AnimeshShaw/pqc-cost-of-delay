# Formal method: definitions, propositions and proofs

This document states the model precisely, proves its properties, and says which automated test checks each proof. A proof is the argument given here; the tests in `tests/test_theory.py` are an independent safety net that checks every proposition on random continuous inputs and, where possible, symbolically (SymPy). Neither replaces the other.

**What is and is not new.** The classical leg is annualised loss expectancy. The quantum leg builds on Mosca's inequality (2018), on per-asset quantum scoring (Grigaliūnas & Brūzgienė 2025), on the observation that deferral under interception leaks the payoff (Baradziej 2026), and on cost of delay (Reinertsen 2009). The propositions below are standard probability and scheduling arguments applied to this setting. The contribution is the construction (a common unit, a competing-risks coupling, a dominance condition, a scheduling justification) and its verification, not new mathematics. The accompanying paper gives the positioning against prior work.

Notation. $\lambda$ classical hazard (per year); $\rho \ge 0$ discount rate; $\kappa=\lambda+\rho$; $L$ confidentiality lifetime (years); $F$ CDF of the CRQC arrival time $T_q$ with density $f$; $h\in[0,1]$ recordable share; $V$ loss (USD); $\tau$ turnover (per year); $r=\tau V$ (USD per year).

---

## 1. Model

**A1 (arrival of a CRQC).** $T_q$ has a continuous distribution on $(0,\infty)$ with $F(0)=0$ and $F(t)>0$ for every $t>0$. We use a Weibull law, $F(t)=1-\exp\{-(t/\alpha)^{\beta}\}$.

**A2 (classical disclosure).** For data created at time 0, the time $T_c$ at which a classical channel discloses it is exponential with rate $\lambda$ (a constant hazard).

**A3 (independence).** $T_c$ and $T_q$ are independent.

**A4 (sensitivity window).** Data created at time 0 is sensitive during $[0,L]$ and worthless afterwards. Disclosure by any channel at time $t\le L$ loses its full value.

**A5 (harvestability).** A fraction $h$ of the asset's value flow crosses a channel a passive adversary can record; new value flows in at rate $r$ per year. Value that cannot be recorded is not exposed to quantum loss.

**Definition 1 (cost of delay).**
$$\mathrm{CoD}_c=\lambda V,\qquad \mathrm{CoD}_q = r\,h\,I(\kappa,L),\qquad I(\kappa,L)=\int_0^{L} f(t)\,e^{-\kappa t}\,dt,\qquad \mathrm{CoD}=\mathrm{CoD}_c+\mathrm{CoD}_q .$$
The quantum term is set to exactly zero when the key exchange is already quantum-safe, when $h=0$, or when $L=0$ (the *gates*).

*Interpretation.* $I(\lambda,L)$ is the probability that a CRQC exists within the data's life **and** the classical hazard has not already disclosed it (Prop. 2). $r\,h\,I$ is the rate at which each further year of delay adds irreversible quantum loss. The discount $\rho$ shrinks a loss realised at decryption time.

**Remark (what is deliberately not claimed).** A2 and A3 are modelling assumptions. A nation-state with both classical and quantum capability would violate independence. The constant hazard is a simplification. See §6 and `methodology/STATISTICS.md`.

---

## 2. Propositions

### Proposition 1 (units, homogeneity, scale invariance of the ranking)

Both legs are in USD per year. If all losses are rescaled by $c>0$ ($V\mapsto cV$) with turnovers $\tau$ fixed, then $\mathrm{CoD}_c$, $\mathrm{CoD}_q$ and $\mathrm{CoD}$ are all multiplied by $c$. Hence **the ranking of assets is invariant to a common rescaling of money** (currency, inflation, a uniformly too-high or too-low calibration of the value bands).

*Proof.* $\mathrm{CoD}_c=\lambda V$ and $\mathrm{CoD}_q=\tau V h I$ are each linear in $V$ and $I,h,\tau,\lambda$ do not involve money. Multiplying all $V$ by $c$ multiplies every $\mathrm{CoD}$ by $c$; a common positive factor does not change an ordering. $\square$

*Consequence.* Only *relative* values across assets matter for the order; the absolute dollar calibration (IBM's $4.44M, etc.) matters only for the stated magnitudes. Test: `TestProp1_UnitsAndScale`.

### Proposition 2 (the race; no double counting)

For a unit created at time 0 let $E_q=\{T_q\le L,\ T_q<T_c\}$ (a quantum loss) and $E_c=\{T_c\le L,\ T_c<T_q\}$ (a classical loss that beat the quantum computer). Then:

1. $P(E_q)=\displaystyle\int_0^{L} f(t)e^{-\lambda t}\,dt = I(\lambda,L)$;
2. $P(E_c)=\displaystyle\int_0^{L}\lambda e^{-\lambda t}\bigl(1-F(t)\bigr)\,dt$;
3. $E_c\cap E_q=\varnothing$ and $E_c\cup E_q=\{\min(T_c,T_q)\le L\}$, so
$$P(E_c)+P(E_q)=1-e^{-\lambda L}\bigl(1-F(L)\bigr);$$
4. the naive sum $P(T_c\le L)+P(T_q\le L)$ over-counts the union by exactly $P(T_c\le L)\,P(T_q\le L)=(1-e^{-\lambda L})F(L)$.

*Proof.* (1) By independence, $P(T_q\in dt,\ T_c>t)=f(t)e^{-\lambda t}dt$; integrate over $[0,L]$. (2) Likewise $P(T_c\in dt,\ T_q>t)=\lambda e^{-\lambda t}(1-F(t))dt$. (3) The events differ in which clock rings first (ties have probability 0), so they are disjoint; their union is "some clock rings by $L$", whose complement is $\{T_c>L,T_q>L\}$ with probability $e^{-\lambda L}(1-F(L))$. (4) Inclusion–exclusion: $P(A\cup B)=P(A)+P(B)-P(A\cap B)$ with $A=\{T_c\le L\}$, $B=\{T_q\le L\}$ independent. $\square$

*Consequence.* Assigning each loss to the channel that discloses first removes double counting *by construction*. Test: `TestProp2_RaceAndNoDoubleCounting` (closed forms, partition identity, and a 2-million-draw simulation).

### Proposition 3 (integration by parts; the numerical form)

For $\kappa\ge 0$,
$$I(\kappa,L)=e^{-\kappa L}F(L)+\kappa\int_0^{L}F(t)e^{-\kappa t}\,dt .$$

*Proof.* Since $f\,dt=dF$ and $F(0)=0$, Stieltjes integration by parts gives $\int_0^{L}e^{-\kappa t}dF=[e^{-\kappa t}F(t)]_0^{L}+\kappa\int_0^{L}F(t)e^{-\kappa t}dt$. $\square$

*Why it matters.* For $1<\beta<2$ the Weibull density behaves like $t^{\beta-1}$ at the origin, which is not smooth, so Simpson's rule on $f e^{-\kappa t}$ is only $O(h^{\approx1.4})$ accurate (measured). The right-hand side has a smoother integrand ($F\sim t^{\beta}$) and is measured at $O(h^{\approx2.4})$ (Figure 11 (`python scripts/make_figures.py`)). Tests: `TestProp3_IntegrationByParts` (40 random cases against adaptive quadrature; a symbolic check).

### Proposition 4 (bounds; the coupling factor)

$$e^{-\kappa L}F(L)\ \le\ I(\kappa,L)\ \le\ F(L).$$
Hence the *coupling factor* $c=I(\kappa,L)/F(L)$ lies in $[e^{-\kappa L},1]$, and the coupled quantum term never exceeds the uncoupled one $r\,h\,F(L)$; equality holds iff $\kappa=0$.

*Proof.* On $[0,L]$, $e^{-\kappa L}\le e^{-\kappa t}\le1$; multiply by $f\ge0$ and integrate. $\square$ Test: `TestProp4_Bounds`.

### Proposition 5 (comparative statics)

1. $\partial I/\partial\kappa=-\int_0^{L}t f(t)e^{-\kappa t}dt<0$: a higher classical hazard **or** a higher discount rate strictly lowers the quantum term.
2. $\partial I/\partial L=f(L)e^{-\kappa L}>0$ wherever $f(L)>0$: a longer confidentiality requirement raises it.
3. **Stochastic dominance.** If $F_1(t)\ge F_2(t)$ for all $t$ (the CRQC arrives earlier under 1), then $I_1(\kappa,L)\ge I_2(\kappa,L)$.
4. $\mathrm{CoD}_q$ is linear and increasing in $r$ and in $h$.

*Proof.* (1)–(2): differentiate under the integral (Leibniz). (3): in the form of Proposition 3 each of the two terms is a non-decreasing function of $F$ pointwise, because $e^{-\kappa L}\ge0$, $\kappa\ge0$ and $e^{-\kappa t}>0$. (4) is immediate from Definition 1. $\square$

*Consequence.* Waiting for a *later* CRQC lowers the quantum term monotonically, so the sweep over CRQC scenarios (Figure 8 (`python scripts/make_figures.py`)) is well-ordered, and an asset's quantum term cannot rise when its classical hazard rises. Tests: `TestProp5_ComparativeStatics` (including stochastic dominance on 30 random Weibull pairs). *(The strictness of (2) is mathematical; numerically it is resolved only to about $10^{-9}$ relative, see the test's docstring.)*

### Proposition 6 (gating)

$\mathrm{CoD}_q=0$ if and only if $r\,h\,L=0$ or the key exchange is quantum-safe. In particular, a minutes-long lifetime gives a quantum term that is positive but negligible, with no special-case rule.

*Proof.* Under A1, $F(t)>0$ for $t>0$, so $I(\kappa,L)>0$ for every $L>0$, finite $\kappa$. The protection-class gate is a definition. $\square$ Test: `TestProp6_Gating`.

### Proposition 7 (discounting equals extra hazard)

$\mathrm{CoD}_q(\lambda,\rho)=\mathrm{CoD}_q(\lambda+\rho,0)$.

*Proof.* The integrand depends on $(\lambda,\rho)$ only through $\kappa=\lambda+\rho$. $\square$ Test: `TestProp7_DiscountEqualsHazard`.

*Remark.* Whether to discount a harm that is *locked in at interception* but *realised at decryption* is a value judgement (Baradziej 2026). We default to $\rho=0$ and always report the sweep.

### Proposition 8 (dominance threshold)

Let $V,\tau,h,L>0$ and $\rho\ge0$, and define $\Phi(\lambda)=\tau h\,I(\lambda+\rho,L)-\lambda$. Then:

1. $\mathrm{CoD}_q>\mathrm{CoD}_c\iff\Phi(\lambda)>0$. The condition does **not** depend on $V$.
2. There is a unique $\lambda^*\in\bigl(0,\ \tau h F(L)\bigr)$ with $\Phi(\lambda^*)=0$, and the quantum term dominates exactly when $\lambda<\lambda^*$.
3. *Necessary:* $\lambda<\tau h F(L)$. *Sufficient:* $\lambda<\tau h\,e^{-(\lambda+\rho)L}F(L)$.

*Proof.* (1) $\mathrm{CoD}_q=\tau V h I$ and $\mathrm{CoD}_c=\lambda V$; divide by $V>0$. (2) $\Phi$ is continuous. $\Phi(0)=\tau h\,I(\rho,L)>0$. By Prop. 4, $\Phi(\tau hF(L))\le \tau h F(L)-\tau hF(L)=0$, with strict inequality because $I<F$ for $\kappa>0$. By Prop. 5, $\Phi'(\lambda)=\tau h\,\partial_\kappa I-1<0$, so $\Phi$ is strictly decreasing and has exactly one root in the interval. (3) The upper bound $I\le F$ gives necessity; the lower bound $I\ge e^{-\kappa L}F$ gives sufficiency (with $\kappa=\lambda+\rho$). $\square$

*Consequence.* The quantum-led class is **{low classical hazard, long lifetime, quantum-vulnerable, harvestable, high turnover}**, and its boundary $\lambda^*$ is a single number per asset (Figure 7 (`python scripts/make_figures.py`), `fig04`). Test: `TestProp8_DominanceCondition` (30 random cases: sign change count, root bracket, independence from $V$).

### Proposition 9 (not a weighted sum)

Suppose total cost had the form $A(V,\lambda)+B(L,h,r,F,\rho)$ (a classical score plus a quantum score, each depending only on its own inputs). Then $\partial^2\mathrm{CoD}/\partial\lambda\,\partial L\equiv0$. But
$$\frac{\partial^{2}\,\mathrm{CoD}}{\partial\lambda\,\partial L}=-\,r\,h\,L\,f(L)\,e^{-\kappa L}\ <0\quad\text{whenever } r\,h\,L\,f(L)>0 .$$
Therefore $\mathrm{CoD}$ is **not** separable into a classical and a quantum score. In particular it is not of the form $w_1S_c+w_2S_q$ with $S_c$ a function of the classical inputs only and $S_q$ a function of the quantum inputs only, for any weights $w_1,w_2$. (The proposition says nothing about composites that first transform the sum nonlinearly.)

*Proof.* $\partial_\lambda\mathrm{CoD}=V-r h\int_0^{L}t f(t)e^{-\kappa t}dt$ and $\partial_L$ of this is $-r h\,L f(L)e^{-\kappa L}$ (Leibniz). If $\mathrm{CoD}=A(V,\lambda)+B(L,\dots)$ then $\partial_\lambda\partial_L\mathrm{CoD}=\partial_\lambda\partial_L A+\partial_\lambda\partial_L B=0+0$ since $A$ does not depend on $L$ and $B$ does not depend on $\lambda$. Contradiction. $\square$

*Consequence and scope.* This shows the coupling is real and that the construction is outside the class of additive composites. It does **not** show the composite is better; and a competing-risks term is textbook (Prentice et al. 1978), so the claim concerns the *application*. The QARS score has no classical-hazard input at all, so its mixed partial with respect to $\lambda$ is trivially zero. Test: `TestProp9_NotAWeightedSum` (SymPy derivation, finite-difference check, and a separable contrast).

### Proposition 10 (the classical leg is not materially double counted)

The classical leg $\lambda V$ is the standard annualised loss and ignores that a classical disclosure in year one might have been pre-empted by a quantum computer. The fraction of first-year classical disclosures pre-empted is at most $F(1)$:
$$P(T_q<T_c\mid T_c\le 1)\ \le\ F(1).$$
With the fitted GRI scenarios, $F(1)=0.0245$ (optimistic) and $0.0040$ (pessimistic): at most 2.5% and 0.4% of the classical leg.

*Proof.* $\{T_q<T_c\le1\}\subseteq\{T_q\le1\}$, and by independence $P(T_q\le1\mid T_c\le1)=F(1)$. $\square$ Test: `TestProp10_ClassicalLegOvercountBound`.

### Proposition 11 (fitting the arrival law: existence, uniqueness, closed form)

For anchors $(t_1,p_1),(t_2,p_2)$ with $0<t_1<t_2$ and $0<p_1<p_2<1$, there is exactly one Weibull $(\alpha,\beta)$, $\alpha,\beta>0$, with $F(t_i)=p_i$, namely
$$\beta=\frac{\ln(y_2/y_1)}{\ln(t_2/t_1)},\qquad \alpha=\frac{t_1}{y_1^{1/\beta}},\qquad y_i=-\ln(1-p_i).$$
Moreover $\beta>1$ (hazard rising over time, and $f(0)=0$) iff $y_2/y_1>t_2/t_1$. The GRI 2025 anchors give $\beta=1.43$ (28–49%/51–70% upper ends, "optimistic") and $\beta=1.91$ ("pessimistic").

*Proof.* $F(t)=1-e^{-(t/\alpha)^{\beta}}$ implies $\ln y(t)=\beta\ln t-\beta\ln\alpha$ where $y=-\ln(1-F)$: a straight line in $(\ln t,\ln y)$. Two distinct points ($y_2>y_1$, $t_2>t_1$) determine one line with slope $\beta>0$. $\square$ Test: `TestProp11_FitExistenceUniqueness` (100 random anchor pairs).

### Proposition 12 (two fitted scenarios cross at most once)

Two Weibull CDFs with different $(\alpha,\beta)$ cross at most once for $t>0$, at $t^*=\exp\!\bigl\{(\beta_1\ln\alpha_1-\beta_2\ln\alpha_2)/(\beta_1-\beta_2)\bigr\}$. For the two GRI fits, $t^*\approx44.7$ years, where both CDFs are $\approx0.997$ (differing by $<4\times10^{-4}$); the pessimistic curve is the lower for all $t<t^*$.

*Proof.* In $(\ln t,\ln y)$ coordinates each CDF is a straight line (Prop. 11); distinct lines meet at most once. $\square$ Test: `TestProp12_ScenarioCurvesCrossAtMostOnce`. *Effect:* none for any realistic lifetime; stated so a reader does not discover it.

### Proposition 13 (Smith's rule: why rank by cost of delay)

A single team executes items $j=1,\dots,n$ back-to-back. Item $j$ takes $p_j>0$ years and, until finished, costs a constant $w_j\ge0$ USD per year. The order minimising total loss $\sum_j w_jC_j$ ($C_j$ = completion time) is non-increasing $w_j/p_j$ (Smith, 1956). With equal durations this is "highest cost of delay first".

*Proof (adjacent interchange).* Total loss is $\sum_j w_jp_j+\sum_{i\prec j}w_jp_i$ (item $i$ scheduled before $j$). For a pair of adjacent items $i,j$ starting at time $s$, scheduling $i$ first costs $w_i(s+p_i)+w_j(s+p_i+p_j)$ and $j$ first costs $w_j(s+p_j)+w_i(s+p_j+p_i)$; the difference is $w_jp_i-w_ip_j$. So swapping to put the larger $w/p$ first never increases loss. Any permutation can be sorted into non-increasing $w/p$ by adjacent swaps, each non-increasing in cost; hence the sorted order is optimal. $\square$ Test: `TestProp13_SmithsRule` (60 random instances against exhaustive search).

### Proposition 14 (the exact price of a sub-optimal order; why one list)

Let $\rho_j=w_j/p_j$. For any order $\pi$, its total loss exceeds Smith's by exactly
$$\sum_{\text{pairs }(i\prec j\text{ in }\pi,\ \text{inverted relative to Smith})}p_i\,p_j\,|\rho_i-\rho_j| .$$
Consequently, if the work is split into two queues finished one after the other (e.g. all classical fixes, then all PQC migrations), that split is optimal **if and only if** the two queues' $\rho$-ranges do not interleave; otherwise it is strictly worse by the sum above over every cross-queue inverted pair.

*Proof.* From $\sum_{i\prec j}w_jp_i$: for each unordered pair the contribution is $w_jp_i$ if $i$ precedes $j$ and $w_ip_j$ otherwise; the difference between the two orders is $p_ip_j(\rho_j-\rho_i)$, and summing over pairs inverted relative to Smith gives the formula. $\square$ Test: `TestProp14_ExactCostOfAnySuboptimalOrder` (200 random permutations; the two-queue iff statement).

*Scope.* Proposition 13–14 assume constant loss rates. The quantum rate actually rises with calendar time (a CRQC becomes more likely), so Smith's order is a first-order rule; `costofdelay/schedule.py` evaluates the exact time-varying accrual and finds the true optimum by dynamic programming. On the four case studies Smith's order is within 3–10% of that optimum (`results/summary.md`).

---

## 3. What the propositions establish, and what they do not

| Claim | Established by | Not established |
|---|---|---|
| Both legs share a unit; ranking is invariant to a common money rescaling | Prop. 1 | Absolute dollar accuracy |
| No double counting between classical and quantum disclosure | Prop. 2, 10 | That the independence assumption (A3) holds in practice |
| The quantum term falls as hazard or discounting rises, and as the CRQC is later | Prop. 5 | That the hazard is constant |
| Which assets the quantum term can dominate, and where the boundary is | Prop. 8 | That such assets are common in real registers (empirical) |
| The construction is not a weighted sum | Prop. 9 | That it is more accurate than one |
| Ranking by cost of delay minimises accrued loss (to first order) | Prop. 13–14 | That accrued loss is the right objective for a real organisation |
| The fitted arrival law matches the published anchors | Prop. 11 | That a Weibull is the right shape beyond the anchors |

## 4. Verification layers

1. **Proof** (this document).
2. **Symbolic** checks of the derivative and integration-by-parts identities (SymPy).
3. **Property tests** of every proposition on random continuous inputs (`tests/test_theory.py`).
4. **Independent numerics:** adaptive quadrature (`scipy.integrate.quad`) and a Monte Carlo simulation of the two clocks (`costofdelay/validation.py`; Figure 11 (`python scripts/make_figures.py`)).
5. **Second implementation:** a JavaScript port, used by the web application, reproduces 577 Python values (`app/test.js`).
6. **Refutation baselines:** the ranking is tested against a data-lifetime sort, a classical-only ranking and Mosca's binary gate (`tests/test_refutation.py`).
7. **Known artefacts** are documented, not hidden (Prop. 12; the quadrature's non-smooth origin).

## 5. Limitations of the model

1. Constant classical hazard and independence of the two clocks (A2, A3).
2. Confidentiality only; integrity and availability are out of scope and must not be entered as $\lambda$.
3. The Weibull arrival law is an interpolation of two published points and is extrapolated beyond 15 years, where most long-lived assets sit.
4. Symmetric-key weakening by Grover's algorithm is not modelled (adequate for AES-256, not for AES-128).
5. The turnover $\tau$ and recordable share $h$ are the weakest inputs; no elicitation protocol has been validated.
6. Smith's rule is exact only for constant rates and a single team.

## References

Mosca (2018); Gordon & Loeb (2002); Smith (1956); Prentice et al. (1978); Reinertsen (2009); Grigaliūnas & Brūzgienė (2025); Baradziej (2026). Full entries are in the accompanying paper's bibliography.
