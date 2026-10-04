window.COD_PRESETS = [
 {
  "key": "mosip",
  "title": "MOSIP",
  "blurb": "National identity platform. Biometrics must stay secret for a lifetime.",
  "assets": [
   {
    "id": "M01",
    "name": "Resident biometric templates (fingerprint; iris; face) in the ID Repository",
    "value": "SEVERE",
    "likelihood": "RARE",
    "lifetime": 50.0,
    "protection": "RSA_2048",
    "harvest": "PARTIAL",
    "turnover": 0.05,
    "note": "Biometric traits are permanent so confidentiality must outlast the resident (capped at 50y; the CRQC model is extrapolated). Repository sits inside the national data centre; hardened so classical hazard is the lowest band. At-rest encryption documented [VERIFY]. Transit protection assumed RSA-based [VERIFY]."
   },
   {
    "id": "M02",
    "name": "Resident demographic data and UIN mapping",
    "value": "SEVERE",
    "likelihood": "UNLIKELY",
    "lifetime": 50.0,
    "protection": "RSA_2048",
    "harvest": "PARTIAL",
    "turnover": 0.05,
    "note": "Identity attributes are lifelong. UINs are hashed and encrypted at rest per the docs [VERIFY]."
   },
   {
    "id": "M03",
    "name": "Registration packets sent from enrolment centres to the server",
    "value": "HIGH",
    "likelihood": "RARE",
    "lifetime": 50.0,
    "protection": "RSA_2048",
    "harvest": "HIGH",
    "turnover": 1.0,
    "note": "Offline-first client uploads encrypted packets (demographics + biometrics) over the network from remote centres. Packet encryption assumed RSA-2048 key wrapping [VERIFY]. FLOW ASSET: V is one year of packets, turnover 1. Consistency rule: V_flow ~ turnover_store x V_store = 0.05 x $10M = $0.5M, rounded up to the HIGH band ($1M)."
   },
   {
    "id": "M04",
    "name": "Authentication and e-KYC exchanges with partner organisations (banks; telcos)",
    "value": "HIGH",
    "likelihood": "POSSIBLE",
    "lifetime": 30.0,
    "protection": "ECDH_P256",
    "harvest": "HIGH",
    "turnover": 1.0,
    "note": "Partners subscribe to policies; TLS plus application-layer encryption with signed partner certificates per the docs [VERIFY]. e-KYC responses carry lifelong demographic attributes."
   },
   {
    "id": "M05",
    "name": "Operator and partner session tokens and one-time codes",
    "value": "LOW",
    "likelihood": "LIKELY",
    "lifetime": 0.0001,
    "protection": "ECDH_P256",
    "harvest": "FULL",
    "turnover": "",
    "note": "Minutes-to-hours lifetime. Control case: the quantum leg must vanish."
   },
   {
    "id": "M06",
    "name": "Authentication and registration audit logs (contain identifiers)",
    "value": "MODERATE",
    "likelihood": "RARE",
    "lifetime": 10.0,
    "protection": "ECDH_P256",
    "harvest": "LOW",
    "turnover": 0.2,
    "note": "Regulatory audit retention [VERIFY duration]."
   },
   {
    "id": "M07",
    "name": "Disaster-recovery copies of the ID Repository",
    "value": "SEVERE",
    "likelihood": "RARE",
    "lifetime": 50.0,
    "protection": "ECDH_P256",
    "harvest": "PARTIAL",
    "turnover": 0.05,
    "note": "Copies replicated to a secondary site over partly exposed paths; same lifetime as the primary."
   },
   {
    "id": "M08",
    "name": "Internal service-to-service traffic inside the national data centre",
    "value": "HIGH",
    "likelihood": "UNLIKELY",
    "lifetime": 30.0,
    "protection": "ECDH_P256",
    "harvest": "LOW",
    "turnover": 1.0,
    "note": "MOSIP is deployed inside the country's data centres with no biometric data leaving national borders per the docs [VERIFY]; collection would require an insider or in-network position. FLOW ASSET: V is one year of internal traffic (turnover 1), consistent with the repository-stock rule (about 5% of the $10M stock per year, rounded to the HIGH band)."
   },
   {
    "id": "M09",
    "name": "Published schemas; UI labels and configuration",
    "value": "NEGLIGIBLE",
    "likelihood": "POSSIBLE",
    "lifetime": 0.0,
    "protection": "ECDH_P256",
    "harvest": "FULL",
    "turnover": "",
    "note": "Control case: both legs must vanish."
   }
  ]
 },
 {
  "key": "fineract",
  "title": "Apache Fineract",
  "blurb": "Core banking. Records are kept for roughly 5 to 15 years.",
  "assets": [
   {
    "id": "B01",
    "name": "Customer KYC identity records (ID document copies; name; address; date of birth)",
    "value": "SEVERE",
    "likelihood": "UNLIKELY",
    "lifetime": 15.0,
    "protection": "ECDH_P256",
    "harvest": "HIGH",
    "turnover": 0.1,
    "note": "FATF R.11: CDD records kept at least 5 years after the relationship ends; assume a ~10-year relationship so ~15y total. Mobile and web clients reach the API over HTTPS."
   },
   {
    "id": "B02",
    "name": "Account ledger and transaction history",
    "value": "SEVERE",
    "likelihood": "POSSIBLE",
    "lifetime": 10.0,
    "protection": "ECDH_P256",
    "harvest": "HIGH",
    "turnover": 0.1,
    "note": "Transaction records kept at least 5 years under FATF R.11; many jurisdictions require 7-10 [VERIFY]."
   },
   {
    "id": "B03",
    "name": "Loan applications and credit-check results",
    "value": "HIGH",
    "likelihood": "UNLIKELY",
    "lifetime": 7.0,
    "protection": "ECDH_P256",
    "harvest": "HIGH",
    "turnover": 0.2,
    "note": "Retention tied to loan term plus regulatory period."
   },
   {
    "id": "B04",
    "name": "API sessions and OAuth2 access tokens",
    "value": "LOW",
    "likelihood": "LIKELY",
    "lifetime": 0.0001,
    "protection": "ECDH_P256",
    "harvest": "FULL",
    "turnover": "",
    "note": "Hours of lifetime. Control case: the quantum leg must vanish."
   },
   {
    "id": "B05",
    "name": "Payment and mobile-money messages exchanged with partner systems",
    "value": "HIGH",
    "likelihood": "POSSIBLE",
    "lifetime": 10.0,
    "protection": "ECDH_P256",
    "harvest": "HIGH",
    "turnover": 1.0,
    "note": "Every message is new each year; crosses the internet to partners."
   },
   {
    "id": "B06",
    "name": "Off-site PostgreSQL backups",
    "value": "SEVERE",
    "likelihood": "RARE",
    "lifetime": 10.0,
    "protection": "ECDH_P256",
    "harvest": "PARTIAL",
    "turnover": 0.1,
    "note": "Same retention as the ledger; replicated over partly exposed paths; rarely attacked directly."
   },
   {
    "id": "B07",
    "name": "Application-to-database link",
    "value": "SEVERE",
    "likelihood": "UNLIKELY",
    "lifetime": 10.0,
    "protection": "NONE",
    "harvest": "LOW",
    "turnover": 0.1,
    "note": "Assumed unencrypted unless configured [VERIFY]. No quantum-vulnerable key exchange to attack."
   },
   {
    "id": "B08",
    "name": "Audit trail of staff actions (contains customer identifiers)",
    "value": "MODERATE",
    "likelihood": "RARE",
    "lifetime": 7.0,
    "protection": "ECDH_P256",
    "harvest": "LOW",
    "turnover": 0.2,
    "note": "Regulatory audit retention [VERIFY duration]. Internal network."
   },
   {
    "id": "B09",
    "name": "Reference data (currencies; offices; product codes)",
    "value": "NEGLIGIBLE",
    "likelihood": "POSSIBLE",
    "lifetime": 0.0,
    "protection": "ECDH_P256",
    "harvest": "FULL",
    "turnover": "",
    "note": "Control case: both legs must vanish."
   }
  ]
 },
 {
  "key": "openmrs",
  "title": "OpenMRS",
  "blurb": "Medical records. Children's records are kept until adulthood and beyond.",
  "assets": [
   {
    "id": "O01",
    "name": "Pediatric clinical records (encounters and observations of minors)",
    "value": "SEVERE",
    "likelihood": "UNLIKELY",
    "lifetime": 30.0,
    "protection": "ECDH_P256",
    "harvest": "HIGH",
    "turnover": 0.08,
    "note": "State rules retain minors' records to age of majority plus limitation period; one cited state keeps them until age 30 [VERIFY]. Clinics reach the server over the public internet via HTTPS."
   },
   {
    "id": "O02",
    "name": "Adult clinical records (encounters orders and observations)",
    "value": "SEVERE",
    "likelihood": "UNLIKELY",
    "lifetime": 10.0,
    "protection": "ECDH_P256",
    "harvest": "HIGH",
    "turnover": 0.1,
    "note": "Adult clinical retention typically 5-10 years after last service [VERIFY]."
   },
   {
    "id": "O03",
    "name": "Highly sensitive categories (HIV status; mental health; genetic)",
    "value": "SEVERE",
    "likelihood": "UNLIKELY",
    "lifetime": 30.0,
    "protection": "ECDH_P256",
    "harvest": "HIGH",
    "turnover": 0.05,
    "note": "Confidentiality is effectively lifelong; capped at 30y because the CRQC model is extrapolated beyond that."
   },
   {
    "id": "O04",
    "name": "Patient identifiers and demographics",
    "value": "HIGH",
    "likelihood": "POSSIBLE",
    "lifetime": 30.0,
    "protection": "ECDH_P256",
    "harvest": "HIGH",
    "turnover": 0.1,
    "note": "Identity persists for the patient's lifetime; frequently scraped or enumerated."
   },
   {
    "id": "O05",
    "name": "User credentials and session tokens",
    "value": "LOW",
    "likelihood": "LIKELY",
    "lifetime": 0.0001,
    "protection": "ECDH_P256",
    "harvest": "FULL",
    "turnover": "",
    "note": "Session lifetime in hours. Control case: the quantum leg must vanish."
   },
   {
    "id": "O06",
    "name": "Lab and referral results exchanged with external systems (HL7/FHIR)",
    "value": "HIGH",
    "likelihood": "POSSIBLE",
    "lifetime": 10.0,
    "protection": "ECDH_P256",
    "harvest": "HIGH",
    "turnover": 1.0,
    "note": "New results arrive continuously; every record crosses an organisational boundary."
   },
   {
    "id": "O07",
    "name": "Concept dictionary and metadata (published terminology)",
    "value": "NEGLIGIBLE",
    "likelihood": "POSSIBLE",
    "lifetime": 0.0,
    "protection": "ECDH_P256",
    "harvest": "FULL",
    "turnover": "",
    "note": "Control case: both legs must vanish."
   },
   {
    "id": "O08",
    "name": "Off-site backups and replicas of the clinical database",
    "value": "SEVERE",
    "likelihood": "RARE",
    "lifetime": 30.0,
    "protection": "ECDH_P256",
    "harvest": "PARTIAL",
    "turnover": 0.1,
    "note": "Long-retention copies replicated over partly exposed paths; rarely attacked directly."
   },
   {
    "id": "O09",
    "name": "Application to database link inside the data centre",
    "value": "SEVERE",
    "likelihood": "UNLIKELY",
    "lifetime": 10.0,
    "protection": "NONE",
    "harvest": "LOW",
    "turnover": 0.1,
    "note": "MySQL connections are unencrypted unless configured [VERIFY]. No quantum-vulnerable key exchange to attack."
   },
   {
    "id": "O10",
    "name": "Facility-to-facility patient data transfer",
    "value": "HIGH",
    "likelihood": "POSSIBLE",
    "lifetime": 10.0,
    "protection": "ECDH_P256",
    "harvest": "HIGH",
    "turnover": 0.2,
    "note": "Documented as TLS with mutual certificate authentication between clinics [VERIFY]; crosses the internet."
   }
  ]
 },
 {
  "key": "online_boutique",
  "title": "Online Boutique",
  "blurb": "Google's demo web shop. Short-lived data; a test of the procedure only.",
  "assets": [
   {
    "id": "A01",
    "name": "Cardholder PAN + expiry in transit to PSP",
    "value": "HIGH",
    "likelihood": "POSSIBLE",
    "lifetime": 4.0,
    "protection": "ECDH_P256",
    "harvest": "HIGH",
    "turnover": "",
    "note": "PAN validity ~3-5y (card expiry/reissue). CVV excluded: seconds. Leaves cluster to the PSP over the internet."
   },
   {
    "id": "A02",
    "name": "Customer PII on orders (name; address; email)",
    "value": "HIGH",
    "likelihood": "POSSIBLE",
    "lifetime": 10.0,
    "protection": "ECDH_P256",
    "harvest": "HIGH",
    "turnover": "",
    "note": "Retention-driven (tax/consumer-law ~7-10y). Browser to ingress crosses the public internet."
   },
   {
    "id": "A03",
    "name": "Session IDs and cart contents",
    "value": "LOW",
    "likelihood": "LIKELY",
    "lifetime": 0.0001,
    "protection": "ECDH_P256",
    "harvest": "FULL",
    "turnover": "",
    "note": "Expire in minutes-hours (~1h = 0.0001y). Control case: quantum leg must vanish."
   },
   {
    "id": "A04",
    "name": "Product catalogue",
    "value": "NEGLIGIBLE",
    "likelihood": "POSSIBLE",
    "lifetime": 0.0,
    "protection": "ECDH_P256",
    "harvest": "FULL",
    "turnover": "",
    "note": "Control case: both legs must vanish."
   },
   {
    "id": "A05",
    "name": "Cart store contents at rest (Redis)",
    "value": "LOW",
    "likelihood": "POSSIBLE",
    "lifetime": 0.02,
    "protection": "NONE",
    "harvest": "LOW",
    "turnover": "",
    "note": "Days of retention. Redis in-cluster. Plaintext by default so no quantum-vulnerable KEX; classical sniffing dominates."
   },
   {
    "id": "A06",
    "name": "Service-to-service mTLS identities (mesh certs)",
    "value": "MODERATE",
    "likelihood": "UNLIKELY",
    "lifetime": 0.25,
    "protection": "ECDH_P256",
    "harvest": "LOW",
    "turnover": "",
    "note": "Rotated ~quarterly (assumed). East-west only; collection needs in-cluster or node position."
   },
   {
    "id": "A07",
    "name": "Order-confirmation emails (PII + order contents) to SMTP",
    "value": "MODERATE",
    "likelihood": "POSSIBLE",
    "lifetime": 7.0,
    "protection": "ECDH_P256",
    "harvest": "HIGH",
    "turnover": "",
    "note": "Mailbox retention outlives the order. Crosses to an external mail relay."
   }
  ]
 }
];
