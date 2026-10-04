/*
 * Explanations shown in the margin of the explorer. One entry per input.
 * Each entry says: what it is, how to choose a value, why it matters, where its scale comes from,
 * and the commonest mistake. `options` explains every allowed choice.
 * Sources: methodology/PARAMETERS.md.
 */
window.COD_HELP = {
  system: {
    title: "Which system to explore",
    what: "Four open-source or public systems whose designs are documented. Each is a short list of kinds of data (assets) with the values the study assumed for them.",
    how: [
      "Start with MOSIP or OpenMRS: their data must stay secret for decades, so the quantum term matters.",
      "Compare with Online Boutique: its data is short-lived, so the quantum term barely matters. That contrast is the point."
    ],
    why: "The study's finding is conditional: the quantum term matters when data lives long, and not otherwise.",
    source: "Registers in case_studies/. Every value is an assumption drawn from public documents; no organisation supplied data.",
    mistake: "Reading these as facts about a real deployment. They are illustrations. Edit any value in the table below, or add your own assets."
  },

  scenario: {
    title: "When a quantum computer might arrive",
    what: "A cryptographically relevant quantum computer (CRQC) is one strong enough to break the locks that protect most internet traffic today. Nobody knows the date, so the explorer uses the experts' own spread of opinion.",
    how: [
      "Compare both published views rather than picking one.",
      "Choose a year only to test a specific belief; the explorer keeps the same curve shape and moves its middle."
    ],
    options: [
      { label: "Soon-ish", say: "The experts' faster reading: 49% chance within 10 years, 70% within 15. Middle of the curve about 2036." },
      { label: "Later", say: "The experts' slower reading: 28% chance within 10 years, 51% within 15. Middle of the curve about 2041." },
      { label: "Pick a year", say: "Moves the middle of the curve to the year you choose. The shape stays that of the faster view." }
    ],
    why: "The date changes the size of the quantum cost, but for data that must stay secret 30 years or more it matters little, because by then arrival is almost certain. Across the four systems it explained only 3 to 17% of the uncertainty in the quantum cost.",
    source: "Global Risk Institute, Quantum Threat Timeline Report 2025 (Mosca and Piani; 26 experts). A smooth curve is fitted through the two published points and extended beyond 15 years, where it is extrapolation.",
    mistake: "Treating either curve as a forecast. Look instead at where the ranking changes between them."
  },

  rho: {
    title: "How much to shrink far-future losses",
    what: "A loss that appears 30 years from now can be counted in full or shrunk, the way money in the future is worth less to you today. This is a value judgement, not a measurement.",
    how: [
      "Leave it at 0% unless you have a reason. The harm is done when the data is copied, even though it shows up later, so shrinking it understates it.",
      "Slide it up to see whether your conclusions survive a different view."
    ],
    options: [
      { label: "0%", say: "Count harm in full. The study's default." },
      { label: "2 to 3%", say: "A low rate used in some public-sector appraisals." },
      { label: "7%", say: "A US federal benefit-cost rate discussed in the post-quantum timing literature." },
      { label: "10%", say: "A high commercial rate. Future harm counts for little." }
    ],
    why: "Every quantum cost falls as this rises, and the order can change. In OpenMRS the backups fall below the database link at about 0.7%.",
    source: "Baradziej (2026) shows the discount rate alone can reverse a timing conclusion. Shrinking at this rate is mathematically the same as raising the hacker's yearly rate.",
    mistake: "Using your company's cost of capital. That fits money you could invest, not harm done to other people's privacy."
  },

  lifetime: {
    title: "Years the data must stay secret",
    what: "Counted from the moment the data is sent or created. After this, exposure no longer hurts.",
    how: [
      "Use a rule or a physical fact, not a feeling: a legal retention period, a contract term, or something permanent such as a fingerprint.",
      "Typical values: an hour for a session (0.0001 years); 5 to 10 years for financial records; 30 years for children's medical records; 50 years for biometrics (capped, because beyond that the curve is pure extrapolation).",
      "Use 0 only for data that is genuinely public."
    ],
    why: "The chance that a quantum computer exists within the lifetime grows with it. Under a year the quantum cost is almost zero; beyond 30 years it levels off because arrival is nearly certain. This is the study's strongest input: it is tied to a rule or a fact.",
    source: "FATF Recommendation 11 (records kept at least five years after a relationship ends); state medical-record rules; the permanence of biometric traits.",
    mistake: "Entering how long you store the data rather than how long it must stay secret. Or entering 0 for 'we do not care' without proof."
  },

  likelihood: {
    title: "How often ordinary hacking exposes this data",
    what: "The average number of times per year that hackers, insiders or mistakes expose this particular data. Secrecy only.",
    how: [
      "Think of one data store, not the whole company. A hardened, rarely targeted store sits low; an internet-facing store or a credential sits high.",
      "A useful anchor: a published study found a 27.9% chance that a company already breached is breached again within two years, about 0.16 per year for a whole organisation."
    ],
    options: [
      { label: "Rare, 0.01", say: "About once in a hundred years. Segmented, hardened, rarely a direct target, such as an off-site backup." },
      { label: "Unlikely, 0.05", say: "About once in twenty years. A well-defended internal store." },
      { label: "Possible, 0.20", say: "About once in five years. A typical business data store." },
      { label: "Likely, 0.50", say: "About once in two years. Internet-facing, or often targeted." },
      { label: "Frequent, 1.00", say: "About once a year. Credentials and sessions that are attacked all the time." }
    ],
    why: "It does two things. It sets the classical cost (this rate times the loss). And it lowers the quantum cost, because data likely to be stolen in plain form first leaves nothing for a quantum computer to add. Quiet assets are where the quantum term matters.",
    source: "Ponemon Institute and IBM, 2018 Cost of Data Breach Study (477 companies that had already been breached, so it may overstate the rate for others). The multipliers per band are judgement.",
    mistake: "Entering incidents that lock or alter data without stealing it, such as ransomware that only encrypts. This tool scores secrecy only."
  },

  value: {
    title: "Loss if this data is exposed",
    what: "The damage, in dollars, if one retention period of this data is exposed once. For data that only ever travels, use one year of it.",
    how: [
      "Estimate how many people's records are involved and multiply by about $160, IBM's 2025 average cost per customer record. Round to the nearest band.",
      "Large breaches cost less per record, so do not scale linearly to millions. The study caps its systems at the severe band.",
      "A year of traffic is only the new part of a stored dataset. If the store is worth $10M and grows 5% a year, a year of its traffic is worth about $0.5M."
    ],
    options: [
      { label: "Negligible, $0", say: "Public data with no secrecy requirement." },
      { label: "Low, $10k", say: "About 60 records. A handful of accounts; a short-lived credential." },
      { label: "Moderate, $100k", say: "About 600 records. One department's data." },
      { label: "High, $1M", say: "About 6,250 records. A mid-sized dataset." },
      { label: "Severe, $10M", say: "About 62,500 records. A large customer or patient base." },
      { label: "Catastrophic, $100M", say: "About 625,000 records. National scale. Beyond the range IBM sampled, so treat with caution." }
    ],
    why: "Only the relative values between assets change the ranking. Multiplying every loss by the same factor changes the dollars on the screen but not the order.",
    source: "IBM and Ponemon Institute, Cost of a Data Breach Report 2025: global average $4.44M; healthcare $7.42M; financial services $5.56M; about $160 per customer record; 600 organisations, breaches of 2,960 to 113,620 records.",
    mistake: "Giving a stored dataset and a year of its traffic the same value. That counts the same data twice."
  },

  protection: {
    title: "The lock protecting the data in transit",
    what: "The cryptography that sets up the secret key for the connection an adversary could record. It decides whether a quantum computer could ever unlock the recording.",
    how: [
      "Observe it: scan the service, read the TLS settings, or ask the platform team. Do not guess.",
      "The weak link is the key exchange, not the cipher. AES-256 is strong, but if the key that feeds it was agreed with RSA or elliptic curves, a recorded session can still be opened later."
    ],
    options: [
      { label: "RSA 2048", say: "Breakable by a quantum computer. Older TLS and VPN setups." },
      { label: "RSA 4096", say: "Breakable by a quantum computer. A longer key does not help against Shor's algorithm." },
      { label: "Elliptic curve P-256", say: "Breakable by a quantum computer. The common modern default; X25519 belongs here too." },
      { label: "Elliptic curve P-384", say: "Breakable by a quantum computer." },
      { label: "AES-256, shared key", say: "Not breakable in practice. A quantum computer only halves its strength to 128 bits. Applies when the key is agreed in advance, not negotiated over the network." },
      { label: "ML-KEM-768", say: "The new NIST post-quantum standard (FIPS 203). Not breakable by a quantum computer." },
      { label: "Hybrid X25519 + ML-KEM", say: "Both locks together. Safe if either one holds." },
      { label: "None", say: "No encryption. A quantum computer adds nothing, because anyone could already read it. Fix that first." }
    ],
    why: "If the lock cannot be broken by a quantum computer, the quantum cost is exactly zero. This is one of the three gates that switch the quantum term off.",
    source: "NIST FIPS 203 and the published behaviour of Shor's and Grover's algorithms. The gate on protection class was described earlier by Grigaliunas and Bruzgiene (2025).",
    mistake: "Entering AES-256 for a connection whose key exchange is RSA or elliptic-curve."
  },

  harvest: {
    title: "Share of the traffic someone could record",
    what: "The fraction of this data's traffic that a patient observer with plenty of disk space could copy while it travels. It is about opportunity to watch, not about the cost of storing.",
    how: [
      "Follow the data. Which networks does it cross? Who could sit on them: an internet observer, a rogue insider, someone who has broken into the data centre?",
      "Inside a trusted data centre is not zero. An intruder or insider can still record it, which is why the lowest non-zero value is 0.1."
    ],
    options: [
      { label: "None, 0", say: "Never leaves a physically controlled room. Needs written evidence; the Python tool refuses it without." },
      { label: "Low, 0.1", say: "A private link inside a trusted data centre. Recording needs an insider or a foothold." },
      { label: "Partial, 0.5", say: "A mix of internal and external paths, such as replication to a second site." },
      { label: "High, 0.9", say: "Crosses public networks as a matter of routine." },
      { label: "Full, 1.0", say: "All of it travels over an internet-facing channel." }
    ],
    why: "Copying is cheap, so the limit is access, not storage. If nothing can be recorded, the quantum cost vanishes. This is the second gate.",
    source: "Blanco-Romero and colleagues (2026) show that retaining intercepted traffic is economically trivial, so access to the channel is what limits harvesting.",
    mistake: "Treating the whole data centre as unobservable, or treating every internal link as fully exposed."
  },

  turnover: {
    title: "How much of the data is new each year",
    what: "New data per year divided by data at risk. A pond refilled once a year is 1. An archive that grows 5% a year is 0.05. A stream of fresh messages is 1.",
    how: [
      "Records created per year divided by records held.",
      "Leave it blank if you do not know. The explorer then assumes all the value is new every year, and flags that it did so.",
      "Keep it consistent with the loss. For a stream, enter the loss of one year of that stream, and turnover 1."
    ],
    why: "The quantum cost is proportional to it: new data is what an adversary can still start recording today. With loss, it explains 73 to 91% of the uncertainty in the quantum cost. It is the study's weakest input, because nobody publishes it.",
    source: "None published for these systems. It is the first thing a real organisation would supply from its own data volumes.",
    mistake: "Giving a stream the full value of the store behind it. Entering a flow at stock scale overstated one asset about tenfold in an early draft of this study."
  }
};
