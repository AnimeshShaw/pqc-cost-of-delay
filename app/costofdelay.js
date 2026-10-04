/*
 * Cost-of-delay scoring core: a JavaScript port of the Python reference implementation
 * (costofdelay/*.py). No dependencies. Works in the browser (window.CostOfDelay) and in
 * Node (module.exports). app/test.js verifies it against golden values produced by Python.
 */
(function (root) {
  "use strict";

  // ---------- ordinal bands with fixed midpoints (see methodology/PARAMETERS.md) ----------
  var BANDS = {
    value: { NEGLIGIBLE: 0, LOW: 1e4, MODERATE: 1e5, HIGH: 1e6, SEVERE: 1e7, CATASTROPHIC: 1e8 },
    likelihood: { RARE: 0.01, UNLIKELY: 0.05, POSSIBLE: 0.2, LIKELY: 0.5, FREQUENT: 1.0 },
    harvest: { NONE: 0, LOW: 0.1, PARTIAL: 0.5, HIGH: 0.9, FULL: 1.0 },
  };
  // Can a quantum computer break the key exchange of traffic recorded under this lock?
  var PROTECTION = {
    RSA_2048: true, RSA_4096: true, ECDH_P256: true, ECDH_P384: true,
    AES_256_PSK: false, ML_KEM_768: false, HYBRID_X25519_MLKEM: false, NONE: false,
  };

  // Quantum Threat Timeline Report 2025 (Mosca & Piani): by year 10 28-49%, by year 15 51-70%.
  var ANCHORS = {
    pessimistic: [[10, 0.28], [15, 0.51]],
    optimistic: [[10, 0.49], [15, 0.70]],
  };
  var BASE_YEAR = 2026;

  function makeDist(alpha, beta) {
    return {
      alpha: alpha, beta: beta,
      cdf: function (t) { return t <= 0 ? 0 : 1 - Math.exp(-Math.pow(t / alpha, beta)); },
      pdf: function (t) {
        if (t <= 0) return beta > 1 ? 0 : Infinity;
        var z = Math.pow(t / alpha, beta);
        return (beta / alpha) * Math.pow(t / alpha, beta - 1) * Math.exp(-z);
      },
      median: function () { return alpha * Math.pow(Math.LN2, 1 / beta); },
    };
  }

  /** Closed-form Weibull through two anchor points (Proposition 11). */
  function fitWeibull(anchors) {
    var a = anchors.slice().sort(function (x, y) { return x[0] - y[0]; });
    var t1 = a[0][0], p1 = a[0][1], t2 = a[1][0], p2 = a[1][1];
    var y1 = -Math.log(1 - p1), y2 = -Math.log(1 - p2);
    var beta = Math.log(y2 / y1) / Math.log(t2 / t1);
    return makeDist(t1 / Math.pow(y1, 1 / beta), beta);
  }

  /** Same shape as a reference fit, but a chosen median arrival year. */
  function distWithMedianYear(year, baselineYear, beta) {
    var alpha = (year - baselineYear) / Math.pow(Math.LN2, 1 / beta);
    return makeDist(alpha, beta);
  }

  // ---------- numerics ----------
  function simpson(f, a, b, n) {
    if (b <= a) return 0;
    if (n % 2) n += 1;
    var h = (b - a) / n, s = f(a) + f(b);
    for (var i = 1; i < n; i++) s += (i % 2 ? 4 : 2) * f(a + i * h);
    return s * h / 3;
  }

  /**
   * I(kappa, L) = integral_0^L f(t) exp(-kappa t) dt, evaluated exactly by parts (Proposition 3):
   *   exp(-kappa L) F(L) + kappa * integral_0^L F(t) exp(-kappa t) dt
   */
  function integralI(dist, kappa, L, n) {
    if (L <= 0) return 0;
    if (kappa === 0) return dist.cdf(L);
    var tail = Math.exp(-kappa * L) * dist.cdf(L);
    var body = kappa * simpson(function (t) { return dist.cdf(t) * Math.exp(-kappa * t); }, 0, L, n || 4000);
    return tail + body;
  }

  /** Quantum cost of delay for plain numbers (USD per year). */
  function quantumRate(flow, h, L, lam, dist, rho, competing, n) {
    var scale = flow * h;
    if (scale === 0 || L <= 0) return 0;
    var kappa = (rho || 0) + (competing === false ? 0 : lam);
    return scale * integralI(dist, kappa, L, n);
  }

  /** The unique hazard below which the quantum term dominates (Proposition 8). null if none. */
  function lambdaStar(tau, h, L, rho, dist) {
    var upper = tau * h * dist.cdf(L);
    if (!(upper > 1e-12) || L <= 0) return null;
    var phi = function (x) { return tau * h * integralI(dist, x + (rho || 0), L, 1500) - x; };
    var lo = 0, hi = upper;
    for (var i = 0; i < 60; i++) { var mid = (lo + hi) / 2; if (phi(mid) > 0) lo = mid; else hi = mid; }
    return (lo + hi) / 2;
  }

  // ---------- register scoring ----------
  function assetNumbers(a) {
    return {
      V: BANDS.value[a.value], lam: BANDS.likelihood[a.likelihood], h: BANDS.harvest[a.harvest],
      L: Number(a.lifetime),
      tau: (a.turnover === "" || a.turnover == null) ? null : Number(a.turnover),
      vulnerable: !!PROTECTION[a.protection],
    };
  }
  function codClassical(a) { var n = assetNumbers(a); return n.lam * n.V; }
  function codQuantum(a, dist, rho, competing) {
    var n = assetNumbers(a);
    if (!(n.vulnerable && n.h > 0 && n.L > 0)) return 0;
    var r = (n.tau == null ? 1 : n.tau) * n.V;
    return quantumRate(r, n.h, n.L, n.lam, dist, rho, competing);
  }
  function scoreAsset(a, dist, rho) {
    var c = codClassical(a), q = codQuantum(a, dist, rho, true), qu = codQuantum(a, dist, rho, false);
    return { id: a.id, name: a.name, classical: c, quantum: q, quantumUncoupled: qu, total: c + q,
             quantumShare: (c + q) > 0 ? q / (c + q) : 0, dominant: q > c,
             turnoverDefaulted: assetNumbers(a).tau == null && q > 0 };
  }
  function rank(assets, dist, rho) {
    var scored = assets.map(function (a) { return scoreAsset(a, dist, rho); });
    var byUnified = scored.slice().sort(function (x, y) { return y.total - x.total; });
    var byClassical = scored.slice().sort(function (x, y) { return y.classical - x.classical; });
    var posC = {}; byClassical.forEach(function (s, i) { posC[s.id] = i + 1; });
    byUnified.forEach(function (s, i) { s.rank = i + 1; s.classicalRank = posC[s.id]; s.move = posC[s.id] - (i + 1); });
    return { unified: byUnified, classicalOrder: byClassical };
  }
  function kendallTau(a, b) {
    var pos = {}; b.forEach(function (x, i) { pos[x] = i; });
    var n = a.length, c = 0, d = 0;
    for (var i = 0; i < n; i++) for (var j = i + 1; j < n; j++) { if (pos[a[i]] < pos[a[j]]) c++; else d++; }
    return n < 2 ? 1 : (c - d) / (0.5 * n * (n - 1));
  }

  // ---------- the race for one unit of data (Proposition 2) ----------
  function race(dist, lam, L, rho) {
    var kappa = (rho || 0) + lam;
    var naive = dist.cdf(L);
    var counted = integralI(dist, kappa, L);
    var classicalFirst = lam > 0
      ? simpson(function (t) { return lam * Math.exp(-lam * t) * (1 - dist.cdf(t)); }, 0, L, 3000) : 0;
    var union = 1 - Math.exp(-lam * L) * (1 - dist.cdf(L));
    return { naive: naive, counted: counted, fraction: naive > 0 ? counted / naive : 0,
             classicalFirst: classicalFirst, union: union, overcount: (1 - Math.exp(-lam * L)) * naive };
  }

  // ---------- uncertainty: Monte Carlo over input ranges ----------
  function mulberry32(seed) {
    return function () {
      seed |= 0; seed = (seed + 0x6D2B79F5) | 0;
      var t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function logU(rnd, f) { return Math.exp((rnd() * 2 - 1) * Math.log(f)); }
  var DEFAULT_SPREADS = { valueDecades: 0.5, lamFactor: 2, lifeFactor: 1.5, harvestAbs: 0.1, tauFactor: 3, rhoMax: 0.07 };

  function simulate(assets, n, seed, spreads, topFrac) {
    var s = Object.assign({}, DEFAULT_SPREADS, spreads || {});
    var rnd = mulberry32(seed || 11), m = assets.length;
    var pess = fitWeibull(ANCHORS.pessimistic), opt = fitWeibull(ANCHORS.optimistic);
    var k = Math.max(1, Math.round((topFrac || 0.25) * m));
    var acc = assets.map(function () { return { topU: 0, topC: 0, dom: 0, up2: 0, ranks: [] }; });
    var setChanged = 0, anyDom = 0;
    for (var it = 0; it < n; it++) {
      var dist = rnd() < 0.5 ? opt : pess, rho = rnd() * s.rhoMax;
      var rows = assets.map(function (a) {
        var nn = assetNumbers(a);
        var V = nn.V > 0 ? nn.V * Math.pow(10, (rnd() * 2 - 1) * s.valueDecades) : 0;
        var lam = Math.min(1, nn.lam * logU(rnd, s.lamFactor));
        var L = nn.L > 0 ? nn.L * logU(rnd, s.lifeFactor) : 0;
        var h = nn.h > 0 ? Math.min(1, Math.max(0, nn.h + (rnd() * 2 - 1) * s.harvestAbs)) : 0;
        var tau = (nn.tau == null ? 1 : nn.tau) * logU(rnd, s.tauFactor);
        var cl = lam * V, q = 0;
        if (nn.vulnerable && h > 0 && L > 0 && V > 0) {
          var kap = lam + rho, scale = tau * V * h;
          var tail = Math.exp(-kap * L) * dist.cdf(L);
          var body = kap * simpson(function (t) { return dist.cdf(t) * Math.exp(-kap * t); }, 0, L, 300);
          q = scale * (tail + body);
        }
        return { c: cl, q: q, t: cl + q };
      });
      var oU = rows.map(function (_, i) { return i; }).sort(function (x, y) { return rows[y].t - rows[x].t; });
      var oC = rows.map(function (_, i) { return i; }).sort(function (x, y) { return rows[y].c - rows[x].c; });
      var rU = new Array(m), rC = new Array(m);
      oU.forEach(function (idx, pos) { rU[idx] = pos + 1; });
      oC.forEach(function (idx, pos) { rC[idx] = pos + 1; });
      var changed = false, any = false;
      for (var j = 0; j < m; j++) {
        var inU = rU[j] <= k, inC = rC[j] <= k;
        if (inU) acc[j].topU++; if (inC) acc[j].topC++; if (inU !== inC) changed = true;
        if (rows[j].q > rows[j].c) { acc[j].dom++; any = true; }
        if (rC[j] - rU[j] >= 2) acc[j].up2++;
        acc[j].ranks.push(rU[j]);
      }
      if (changed) setChanged++; if (any) anyDom++;
    }
    function pct(arr, p) { var a = arr.slice().sort(function (x, y) { return x - y; }); return a[Math.min(a.length - 1, Math.floor(p * a.length))]; }
    return {
      n: n, k: k, pSetChanges: setChanged / n, pAnyDominant: anyDom / n,
      assets: assets.map(function (a, j) {
        return { id: a.id, name: a.name, pTopUnified: acc[j].topU / n, pTopClassical: acc[j].topC / n,
                 pDominant: acc[j].dom / n, pUp2: acc[j].up2 / n,
                 rankMedian: pct(acc[j].ranks, 0.5), rankLo: pct(acc[j].ranks, 0.05), rankHi: pct(acc[j].ranks, 0.95) };
      }),
    };
  }

  var API = {
    BANDS: BANDS, PROTECTION: PROTECTION, ANCHORS: ANCHORS, BASE_YEAR: BASE_YEAR,
    fitWeibull: fitWeibull, makeDist: makeDist, distWithMedianYear: distWithMedianYear,
    simpson: simpson, integralI: integralI, quantumRate: quantumRate, lambdaStar: lambdaStar,
    codClassical: codClassical, codQuantum: codQuantum, scoreAsset: scoreAsset,
    rank: rank, kendallTau: kendallTau, race: race, simulate: simulate,
  };
  if (typeof module !== "undefined" && module.exports) module.exports = API; else root.CostOfDelay = API;
})(typeof window !== "undefined" ? window : this);
