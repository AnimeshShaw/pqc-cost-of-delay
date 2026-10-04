# Generated evaluation tables

GRI 2025 optimistic scenario unless stated. All parameters assumed from public documentation; no practitioner elicitation.

## Cross-system summary

| System | Assets | Median lifetime of assets with L>0 (yr) | Pairs differing from classical-only | Quantum-dominant | Order stable across CRQC scenarios |
|---|---|---|---|---|---|
| MOSIP | 9 | 50 | 5 of 36 | 4 of 9 | yes |
| Apache Fineract | 9 | 10 | 0 of 36 | 1 of 9 | yes |
| OpenMRS | 10 | 20 | 6 of 45 | 1 of 10 | no |
| Online Boutique | 7 | 4 | 2 of 21 | 0 of 7 | yes |

## MOSIP (open-source national identity platform)

9 assets in register (9 observed-category, 0 posited). Tables use observed-category assets only.

| Rank | Asset | L (yr) | Classical CoD | Quantum CoD | Quantum share | Classical-only rank |
|---|---|---|---|---|---|---|
| 1 | M03 Registration packets sent from enrolment centres | 50 | 10.0k | 800.7k | 99% | 6 |
| 2 | M02 Resident demographic data and UIN mapping | 50 | 500.0k | 148.4k | 23% | 1 |
| 3 | M04 Authentication and e-KYC exchanges with partner  | 30 | 200.0k | 195.1k | 49% | 2 |
| 4 | M01 Resident biometric templates (fingerprint; iris; | 50 | 100.0k | 222.4k | 69% | 3 |
| 5 | M07 Disaster-recovery copies of the ID Repository | 50 | 100.0k | 222.4k | 69% | 4 |
| 6 | M08 Internal service-to-service traffic inside the n | 30 | 50.0k | 58.7k | 54% | 5 |
| 7 | M05 Operator and partner session tokens and one-time | 0.0001 | 5.0k | 0.0 | 0% | 7 |
| 8 | M06 Authentication and registration audit logs (cont | 10 | 1.0k | 929.0 | 48% | 8 |
| 9 | M09 Published schemas; UI labels and configuration | 0 | 0 | 0 | 0% | 9 |

- Pairs whose order differs from classical-only: **5 of 36** (Kendall tau 0.722).
- Quantum-dominant assets (quantum CoD > classical CoD): **4 of 9** (M03, M01, M07, M08).
- Assets with a non-zero quantum term: 8 of 9.

Ordering across CRQC scenarios (shape fixed, median arrival varies):

| CRQC median | Ordering |
|---|---|
| 2032 | M03 > M02 > M04 > M01 > M07 > M08 > M05 > M06 > M09 |
| 2035 | M03 > M02 > M04 > M01 > M07 > M08 > M05 > M06 > M09 |
| 2040 | M03 > M02 > M04 > M01 > M07 > M08 > M05 > M06 > M09 |
| 2045 | M03 > M02 > M04 > M01 > M07 > M08 > M05 > M06 > M09 |

Ordering invariant across all four scenarios: **yes**.

Ordering across discount rates (optimistic scenario):

| rho | Ordering |
|---|---|
| 0.00 | M03 > M02 > M04 > M01 > M07 > M08 > M05 > M06 > M09 |
| 0.02 | M03 > M02 > M04 > M01 > M07 > M08 > M05 > M06 > M09 |
| 0.05 | M02 > M03 > M04 > M01 > M07 > M08 > M05 > M06 > M09 |
| 0.07 | M02 > M03 > M04 > M01 > M07 > M08 > M05 > M06 > M09 |
| 0.10 | M02 > M03 > M04 > M01 > M07 > M08 > M05 > M06 > M09 |

Ordering invariant across discount rates 0-10%: **no**.

QARS (equal weights, linear timeline term) ordering: M03 > M04 > M01 > M02 > M07 > M08 > M06 > M05 > M09  (tau vs cost-of-delay 0.833).

### MOSIP (open-source national identity platform) - uncertainty

4000 draws; top-k = 2 of 9.

| Asset | P(in top-k), unified | P(in top-k), classical-only | Rank (median, 5-95%) | P(quantum-dominant) | P(moves up 2+) |
|---|---|---|---|---|---|
| M02 Resident demographic data and UIN mapping | 64% | 92% | 2 (1-5) | 3% | 0% |
| M03 Registration packets sent from enrolment c | 55% | 0% | 2 (1-5) | 100% | 91% |
| M04 Authentication and e-KYC exchanges with pa | 35% | 59% | 3 (1-6) | 32% | 2% |
| M01 Resident biometric templates (fingerprint; | 22% | 22% | 4 (1-6) | 65% | 6% |
| M07 Disaster-recovery copies of the ID Reposit | 22% | 22% | 4 (1-6) | 65% | 5% |
| M08 Internal service-to-service traffic inside | 1% | 5% | 6 (3-6) | 33% | 1% |
| M05 Operator and partner session tokens and on | 0% | 0% | 7 (7-8) | 0% | 0% |
| M06 Authentication and registration audit logs | 0% | 0% | 8 (7-8) | 25% | 0% |
| M09 Published schemas; UI labels and configura | 0% | 0% | 9 (9-9) | 0% | 0% |

- Probability the funded top-2 set differs from classical-only: **71%**
- Probability at least one asset is quantum-dominant: **100%**

## Apache Fineract (open-source core banking)

9 assets in register (9 observed-category, 0 posited). Tables use observed-category assets only.

| Rank | Asset | L (yr) | Classical CoD | Quantum CoD | Quantum share | Classical-only rank |
|---|---|---|---|---|---|---|
| 1 | B02 Account ledger and transaction history | 10 | 2.00M | 173.4k | 8% | 1 |
| 2 | B01 Customer KYC identity records (ID document copie | 15 | 500.0k | 442.3k | 47% | 2 |
| 3 | B07 Application-to-database link | 10 | 500.0k | 0 | 0% | 3 |
| 4 | B05 Payment and mobile-money messages exchanged with | 10 | 200.0k | 173.4k | 46% | 4 |
| 5 | B06 Off-site PostgreSQL backups | 10 | 100.0k | 232.3k | 70% | 5 |
| 6 | B03 Loan applications and credit-check results | 7 | 50.0k | 49.4k | 50% | 6 |
| 7 | B04 API sessions and OAuth2 access tokens | 0.0001 | 5.0k | 0.0 | 0% | 7 |
| 8 | B08 Audit trail of staff actions (contains customer  | 7 | 1.0k | 639.2 | 39% | 8 |
| 9 | B09 Reference data (currencies; offices; product cod | 0 | 0 | 0 | 0% | 9 |

- Pairs whose order differs from classical-only: **0 of 36** (Kendall tau 1.000).
- Quantum-dominant assets (quantum CoD > classical CoD): **1 of 9** (B06).
- Assets with a non-zero quantum term: 7 of 9.

Ordering across CRQC scenarios (shape fixed, median arrival varies):

| CRQC median | Ordering |
|---|---|
| 2032 | B02 > B01 > B07 > B05 > B06 > B03 > B04 > B08 > B09 |
| 2035 | B02 > B01 > B07 > B05 > B06 > B03 > B04 > B08 > B09 |
| 2040 | B02 > B01 > B07 > B05 > B06 > B03 > B04 > B08 > B09 |
| 2045 | B02 > B01 > B07 > B05 > B06 > B03 > B04 > B08 > B09 |

Ordering invariant across all four scenarios: **yes**.

Ordering across discount rates (optimistic scenario):

| rho | Ordering |
|---|---|
| 0.00 | B02 > B01 > B07 > B05 > B06 > B03 > B04 > B08 > B09 |
| 0.02 | B02 > B01 > B07 > B05 > B06 > B03 > B04 > B08 > B09 |
| 0.05 | B02 > B01 > B07 > B05 > B06 > B03 > B04 > B08 > B09 |
| 0.07 | B02 > B01 > B07 > B05 > B06 > B03 > B04 > B08 > B09 |
| 0.10 | B02 > B01 > B07 > B05 > B06 > B03 > B04 > B08 > B09 |

Ordering invariant across discount rates 0-10%: **yes**.

QARS (equal weights, linear timeline term) ordering: B01 > B02 > B05 > B03 > B06 > B07 > B08 > B04 > B09  (tau vs cost-of-delay 0.667).
Assets not quantum-vulnerable yet long-lived, scored by QARS: B07=0.67.

### Apache Fineract (open-source core banking) - uncertainty

4000 draws; top-k = 2 of 9.

| Asset | P(in top-k), unified | P(in top-k), classical-only | Rank (median, 5-95%) | P(quantum-dominant) | P(moves up 2+) |
|---|---|---|---|---|---|
| B02 Account ledger and transaction history | 93% | 95% | 1 (1-3) | 0% | 0% |
| B01 Customer KYC identity records (ID document | 57% | 47% | 2 (1-5) | 26% | 4% |
| B07 Application-to-database link | 29% | 46% | 3 (1-5) | 0% | 0% |
| B05 Payment and mobile-money messages exchange | 13% | 10% | 4 (2-6) | 25% | 4% |
| B06 Off-site PostgreSQL backups | 8% | 2% | 4 (2-6) | 64% | 14% |
| B03 Loan applications and credit-check results | 0% | 0% | 6 (4-6) | 28% | 1% |
| B04 API sessions and OAuth2 access tokens | 0% | 0% | 7 (7-8) | 0% | 0% |
| B08 Audit trail of staff actions (contains cus | 0% | 0% | 8 (7-8) | 15% | 0% |
| B09 Reference data (currencies; offices; produ | 0% | 0% | 9 (9-9) | 0% | 0% |

- Probability the funded top-2 set differs from classical-only: **26%**
- Probability at least one asset is quantum-dominant: **83%**

## OpenMRS (open-source medical record system)

10 assets in register (10 observed-category, 0 posited). Tables use observed-category assets only.

| Rank | Asset | L (yr) | Classical CoD | Quantum CoD | Quantum share | Classical-only rank |
|---|---|---|---|---|---|---|
| 1 | O01 Pediatric clinical records (encounters and obser | 30 | 500.0k | 422.7k | 46% | 1 |
| 2 | O02 Adult clinical records (encounters orders and ob | 10 | 500.0k | 340.1k | 40% | 2 |
| 3 | O03 Highly sensitive categories (HIV status; mental  | 30 | 500.0k | 264.2k | 35% | 3 |
| 4 | O08 Off-site backups and replicas of the clinical da | 30 | 100.0k | 431.6k | 81% | 8 |
| 5 | O09 Application to database link inside the data cen | 10 | 500.0k | 0 | 0% | 4 |
| 6 | O06 Lab and referral results exchanged with external | 10 | 200.0k | 173.4k | 46% | 6 |
| 7 | O10 Facility-to-facility patient data transfer | 10 | 200.0k | 34.7k | 15% | 7 |
| 8 | O04 Patient identifiers and demographics | 30 | 200.0k | 19.5k | 9% | 5 |
| 9 | O05 User credentials and session tokens | 0.0001 | 5.0k | 0.0 | 0% | 9 |
| 10 | O07 Concept dictionary and metadata (published termi | 0 | 0 | 0 | 0% | 10 |

- Pairs whose order differs from classical-only: **6 of 45** (Kendall tau 0.733).
- Quantum-dominant assets (quantum CoD > classical CoD): **1 of 10** (O08).
- Assets with a non-zero quantum term: 8 of 10.

Ordering across CRQC scenarios (shape fixed, median arrival varies):

| CRQC median | Ordering |
|---|---|
| 2032 | O02 > O01 > O03 > O08 > O09 > O06 > O10 > O04 > O05 > O07 |
| 2035 | O01 > O02 > O03 > O08 > O09 > O06 > O10 > O04 > O05 > O07 |
| 2040 | O01 > O02 > O03 > O09 > O08 > O06 > O10 > O04 > O05 > O07 |
| 2045 | O01 > O03 > O02 > O09 > O08 > O06 > O10 > O04 > O05 > O07 |

Ordering invariant across all four scenarios: **no**.

Ordering across discount rates (optimistic scenario):

| rho | Ordering |
|---|---|
| 0.00 | O01 > O02 > O03 > O08 > O09 > O06 > O10 > O04 > O05 > O07 |
| 0.02 | O01 > O02 > O03 > O09 > O08 > O06 > O10 > O04 > O05 > O07 |
| 0.05 | O01 > O02 > O03 > O09 > O08 > O06 > O10 > O04 > O05 > O07 |
| 0.07 | O01 > O02 > O03 > O09 > O06 > O08 > O10 > O04 > O05 > O07 |
| 0.10 | O02 > O01 > O03 > O09 > O06 > O08 > O10 > O04 > O05 > O07 |

Ordering invariant across discount rates 0-10%: **no**.

QARS (equal weights, linear timeline term) ordering: O01 > O02 > O03 > O04 > O06 > O10 > O08 > O09 > O05 > O07  (tau vs cost-of-delay 0.644).
Assets not quantum-vulnerable yet long-lived, scored by QARS: O09=0.67.

### OpenMRS (open-source medical record system) - uncertainty

4000 draws; top-k = 2 of 10.

| Asset | P(in top-k), unified | P(in top-k), classical-only | Rank (median, 5-95%) | P(quantum-dominant) | P(moves up 2+) |
|---|---|---|---|---|---|
| O01 Pediatric clinical records (encounters and | 50% | 44% | 3 (1-6) | 24% | 12% |
| O02 Adult clinical records (encounters orders  | 44% | 42% | 3 (1-7) | 18% | 8% |
| O03 Highly sensitive categories (HIV status; m | 43% | 44% | 3 (1-7) | 12% | 6% |
| O09 Application to database link inside the da | 26% | 43% | 4 (1-8) | 0% | 0% |
| O06 Lab and referral results exchanged with ex | 11% | 9% | 5 (2-8) | 27% | 12% |
| O08 Off-site backups and replicas of the clini | 19% | 1% | 5 (1-8) | 87% | 56% |
| O04 Patient identifiers and demographics | 4% | 9% | 7 (3-8) | 0% | 0% |
| O10 Facility-to-facility patient data transfer | 4% | 8% | 7 (3-8) | 0% | 0% |
| O05 User credentials and session tokens | 0% | 0% | 9 (9-9) | 0% | 0% |
| O07 Concept dictionary and metadata (published | 0% | 0% | 10 (10-10) | 0% | 0% |

- Probability the funded top-2 set differs from classical-only: **45%**
- Probability at least one asset is quantum-dominant: **94%**

## Online Boutique (demo shop; mock data; procedure test only)

8 assets in register (7 observed-category, 1 posited). Tables use observed-category assets only.

| Rank | Asset | L (yr) | Classical CoD | Quantum CoD | Quantum share | Classical-only rank |
|---|---|---|---|---|---|---|
| 1 | A02 Customer PII on orders (name; address; email) | 10 | 200.0k | 173.4k | 46% | 2 |
| 2 | A01 Cardholder PAN + expiry in transit to PSP | 4 | 200.0k | 96.3k | 32% | 1 |
| 3 | A07 Order-confirmation emails (PII + order contents) | 7 | 20.0k | 14.7k | 42% | 3 |
| 4 | A06 Service-to-service mTLS identities (mesh certs) | 0.25 | 5.0k | 33.7 | 1% | 5 |
| 5 | A03 Session IDs and cart contents | 0.0001 | 5.0k | 0.0 | 0% | 4 |
| 6 | A05 Cart store contents at rest (Redis) | 0.02 | 2.0k | 0 | 0% | 6 |
| 7 | A04 Product catalogue | 0 | 0 | 0 | 0% | 7 |

- Pairs whose order differs from classical-only: **2 of 21** (Kendall tau 0.810).
- Quantum-dominant assets (quantum CoD > classical CoD): **0 of 7** (none).
- Assets with a non-zero quantum term: 5 of 7.

Ordering across CRQC scenarios (shape fixed, median arrival varies):

| CRQC median | Ordering |
|---|---|
| 2032 | A02 > A01 > A07 > A06 > A03 > A05 > A04 |
| 2035 | A02 > A01 > A07 > A06 > A03 > A05 > A04 |
| 2040 | A02 > A01 > A07 > A06 > A03 > A05 > A04 |
| 2045 | A02 > A01 > A07 > A06 > A03 > A05 > A04 |

Ordering invariant across all four scenarios: **yes**.

Ordering across discount rates (optimistic scenario):

| rho | Ordering |
|---|---|
| 0.00 | A02 > A01 > A07 > A06 > A03 > A05 > A04 |
| 0.02 | A02 > A01 > A07 > A06 > A03 > A05 > A04 |
| 0.05 | A02 > A01 > A07 > A06 > A03 > A05 > A04 |
| 0.07 | A02 > A01 > A07 > A06 > A03 > A05 > A04 |
| 0.10 | A02 > A01 > A07 > A06 > A03 > A05 > A04 |

Ordering invariant across discount rates 0-10%: **yes**.

QARS (equal weights, linear timeline term) ordering: A02 > A01 > A07 > A03 > A04 > A06 > A05  (tau vs cost-of-delay 0.714).

### Online Boutique (demo shop; mock data; procedure test only) - uncertainty

4000 draws; top-k = 2 of 7.

| Asset | P(in top-k), unified | P(in top-k), classical-only | Rank (median, 5-95%) | P(quantum-dominant) | P(moves up 2+) |
|---|---|---|---|---|---|
| A02 Customer PII on orders (name; address; ema | 99% | 99% | 1 (1-2) | 26% | 0% |
| A01 Cardholder PAN + expiry in transit to PSP | 99% | 99% | 2 (1-2) | 9% | 0% |
| A07 Order-confirmation emails (PII + order con | 2% | 3% | 3 (3-4) | 19% | 2% |
| A03 Session IDs and cart contents | 0% | 0% | 5 (4-6) | 0% | 0% |
| A06 Service-to-service mTLS identities (mesh c | 0% | 0% | 5 (4-6) | 0% | 0% |
| A05 Cart store contents at rest (Redis) | 0% | 0% | 6 (4-6) | 0% | 0% |
| A04 Product catalogue | 0% | 0% | 7 (7-7) | 0% | 0% |

- Probability the funded top-2 set differs from classical-only: **2%**
- Probability at least one asset is quantum-dominant: **43%**

