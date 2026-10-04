// Verifies the JavaScript port against golden values computed by the Python reference.
//   node app/test.js
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const S = require("./costofdelay.js");
const golden = JSON.parse(fs.readFileSync(path.join(__dirname, "golden.json"), "utf8"));
const ctx = { window: {} };
vm.runInNewContext(fs.readFileSync(path.join(__dirname, "data.js"), "utf8"), ctx);
const presets = Object.fromEntries(ctx.window.COD_PRESETS.map(p => [p.key, p]));

let pass = 0, fail = 0;
function check(name, ok, detail) { if (ok) pass++; else { fail++; console.log("FAIL", name, detail || ""); } }
function close(a, b, rel, abs) { return Math.abs(a - b) <= Math.max(abs || 1e-6, rel * Math.abs(b)); }

// 1. CRQC arrival law
for (const [name, d] of Object.entries(golden.dists)) {
  const js = S.fitWeibull(S.ANCHORS[name]);
  check(`alpha ${name}`, close(js.alpha, d.alpha, 1e-12), js.alpha + " vs " + d.alpha);
  check(`beta ${name}`, close(js.beta, d.beta, 1e-12));
  check(`median ${name}`, close(js.median(), d.median, 1e-12));
  for (const [t, v] of Object.entries(d.cdf)) check(`cdf ${name} ${t}`, close(js.cdf(+t), v, 1e-12));
  for (const [t, v] of Object.entries(d.pdf)) check(`pdf ${name} ${t}`, close(js.pdf(+t), v, 1e-12));
}
const beta = S.fitWeibull(S.ANCHORS.optimistic).beta;
for (const g of golden.grid) {
  const d = S.distWithMedianYear(g.median_year, S.BASE_YEAR, beta);
  check(`grid ${g.median_year}`, close(d.alpha, g.alpha, 1e-12));
}

// 2. Scores and orderings on all four registers
for (const c of golden.cases) {
  const dist = S.fitWeibull(S.ANCHORS[c.scenario]);
  const res = S.rank(presets[c.system].assets, dist, c.rho);
  const order = res.unified.map(x => x.id);
  check(`order ${c.system}/${c.scenario}/${c.rho}`, JSON.stringify(order) === JSON.stringify(c.order), order.join(">") + " vs " + c.order.join(">"));
  for (const s of res.unified) {
    const g = c.values[s.id];
    check(`classical ${c.system}/${s.id}`, close(s.classical, g.classical, 1e-9));
    check(`quantum ${c.system}/${c.scenario}/${c.rho}/${s.id}`, close(s.quantum, g.quantum, 1e-7, 1e-6), s.quantum + " vs " + g.quantum);
    check(`uncoupled ${c.system}/${s.id}`, close(s.quantumUncoupled, g.quantum_uncoupled, 1e-7, 1e-6));
  }
}

// 3. The race for one unit of data, and the dominance threshold
for (const r of golden.races) {
  const d = S.fitWeibull(S.ANCHORS[r.scenario]);
  const got = S.race(d, r.lam, r.L, 0);
  check(`race counted ${r.scenario}/${r.lam}/${r.L}`, close(got.counted, r.counted, 1e-7, 1e-12), got.counted + " vs " + r.counted);
  check(`race naive ${r.scenario}/${r.L}`, close(got.naive, r.naive, 1e-12));
  check(`race classical-first ${r.scenario}/${r.lam}/${r.L}`, close(got.classicalFirst, r.classical_first, 1e-6, 1e-12));
  check(`race union ${r.scenario}/${r.lam}/${r.L}`, close(got.union, r.union, 1e-12));
  check(`race partition ${r.scenario}/${r.lam}/${r.L}`, close(got.counted + got.classicalFirst, got.union, 1e-6, 1e-10));
}
for (const s of golden.lambda_star) {
  const d = S.fitWeibull(S.ANCHORS[s.scenario]);
  const v = S.lambdaStar(s.tau, s.h, s.L, s.rho, d);
  check(`lambda* ${s.scenario}/${s.tau}/${s.h}/${s.L}/${s.rho}`, close(v, s.value, 1e-5, 1e-9), v + " vs " + s.value);
}

// 4. Properties
const a = { id: "x", name: "x", value: "HIGH", likelihood: "POSSIBLE", lifetime: 15, protection: "RSA_2048", harvest: "HIGH", turnover: "1" };
const opt = S.fitWeibull(S.ANCHORS.optimistic);
check("coupling lowers quantum", S.codQuantum(a, opt, 0, true) < S.codQuantum(a, opt, 0, false));
check("pqc gate", S.codQuantum({ ...a, protection: "ML_KEM_768" }, opt, 0, true) === 0);
check("harvest none gate", S.codQuantum({ ...a, harvest: "NONE" }, opt, 0, true) === 0);
check("zero lifetime gate", S.codQuantum({ ...a, lifetime: 0 }, opt, 0, true) === 0);
check("discount lowers", S.codQuantum(a, opt, 0.07, true) < S.codQuantum(a, opt, 0, true));
check("kendall identical", S.kendallTau(["a", "b", "c"], ["a", "b", "c"]) === 1);
check("kendall reversed", S.kendallTau(["a", "b", "c"], ["c", "b", "a"]) === -1);
check("lambda* null when quantum cannot matter", S.lambdaStar(0.1, 0, 10, 0, opt) === null);

// 5. Monte Carlo sanity: reproducible and valid
const r1 = S.simulate(presets.openmrs.assets, 600, 5), r2 = S.simulate(presets.openmrs.assets, 600, 5);
check("mc reproducible", JSON.stringify(r1) === JSON.stringify(r2));
const backups = r1.assets.find(x => x.id === "O08");
check("mc backups mostly quantum-led", backups.pDominant > 0.6, backups.pDominant);
check("mc gated assets never quantum-led", r1.assets.find(x => x.id === "O07").pDominant === 0);

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
