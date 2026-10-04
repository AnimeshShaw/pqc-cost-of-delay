(function () {
  "use strict";
  var C = window.CostOfDelay, PRESETS = window.COD_PRESETS, HELP = window.COD_HELP;
  var OPT = C.fitWeibull(C.ANCHORS.optimistic), PESS = C.fitWeibull(C.ANCHORS.pessimistic);
  var BASE_YEAR = C.BASE_YEAR;

  var state = {
    system: PRESETS[0].key, assets: [], scen: "optimistic", year: 2036, rho: 0,
    open: null, mc: null,
    race: { L: 12, lam: 0.05, scen: "optimistic" },
  };

  // ---------- helpers ----------
  function $(id) { return document.getElementById(id); }
  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function money(x) {
    if (x === 0) return "$0";
    if (x >= 1e6) return "$" + trim(x / 1e6, x >= 1e7 ? 1 : 2) + "M";
    if (x >= 1e3) return "$" + trim(x / 1e3, x >= 1e5 ? 0 : 1) + "k";
    return "$" + (x < 10 ? x.toFixed(2) : Math.round(x));
  }
  function trim(v, d) { return String(parseFloat(v.toFixed(d))); }
  function pct(x, d) { return (x * 100).toFixed(d == null ? 0 : d) + "%"; }
  function fmtYears(L) { return L >= 10 ? trim(L, 0) : L >= 1 ? trim(L, 1) : L >= 0.01 ? trim(L, 2) : trim(L, 4); }
  function fmtRate(x) { return x >= 0.1 ? trim(x, 2) : x >= 0.01 ? trim(x, 3) : trim(x, 4); }
  function dist(scen, year) {
    if (scen === "optimistic") return OPT;
    if (scen === "pessimistic") return PESS;
    return C.distWithMedianYear(year, BASE_YEAR, OPT.beta);
  }
  function currentDist() { return dist(state.scen, state.year); }
  function medianYear(d) { return Math.round(BASE_YEAR + d.median()); }
  function svgEl(w, h, inner, extra) {
    return '<svg viewBox="0 0 ' + w + ' ' + h + '" ' + (extra || "") + ">" + inner + "</svg>";
  }

  // ---------- margin notes ----------
  var FIELD_OPTIONS = {
    value: ["NEGLIGIBLE", "LOW", "MODERATE", "HIGH", "SEVERE", "CATASTROPHIC"],
    likelihood: ["RARE", "UNLIKELY", "POSSIBLE", "LIKELY", "FREQUENT"],
    harvest: ["NONE", "LOW", "PARTIAL", "HIGH", "FULL"],
    protection: ["RSA_2048", "RSA_4096", "ECDH_P256", "ECDH_P384", "AES_256_PSK", "ML_KEM_768", "HYBRID_X25519_MLKEM", "NONE"],
  };
  function helpHTML(key, currentIdx) {
    var h = HELP[key]; if (!h) return "";
    var out = "<h3>" + esc(h.title) + "</h3><p>" + esc(h.what) + "</p>";
    out += "<h4>How to choose</h4><ul>" + h.how.map(function (t) { return "<li>" + esc(t) + "</li>"; }).join("") + "</ul>";
    if (h.options) {
      out += "<h4>Your options</h4><dl>" + h.options.map(function (o, i) {
        return '<dt' + (i === currentIdx ? ' class="current"' : "") + ">" + esc(o.label) + "</dt><dd>" + esc(o.say) + "</dd>";
      }).join("") + "</dl>";
    }
    out += "<h4>Why it matters</h4><p>" + esc(h.why) + "</p>";
    out += '<h4>Where the scale comes from</h4><p class="src">' + esc(h.source) + "</p>";
    out += '<h4>Common mistake</h4><p class="mistake">' + esc(h.mistake) + "</p>";
    return out;
  }
  function showHelp(key, el) {
    var idx = -1;
    if (el && FIELD_OPTIONS[key] && el.value != null) idx = FIELD_OPTIONS[key].indexOf(el.value);
    if (key === "scenario") idx = ({ optimistic: 0, pessimistic: 1, custom: 2 })[state.scen];
    if (key === "rho") { var r = state.rho; idx = r === 0 ? 0 : (r >= 2 && r <= 3) ? 1 : r === 7 ? 2 : r === 10 ? 3 : -1; }
    $("glossBody").innerHTML = helpHTML(key, idx);
  }
  function idleHelp() {
    $("glossBody").innerHTML = '<h3>Margin notes</h3><p class="idle">Move the pointer over, or select, any slider, button or field. This margin explains what it means, how to choose a value, and why it matters.</p><p class="idle">Every input here is a rough judgement. The numbers behind the scales are sourced in the parameter notes.</p>';
  }
  function bindHelp() {
    document.addEventListener("focusin", function (e) { var t = e.target.closest("[data-help]"); if (t) showHelp(t.getAttribute("data-help"), e.target); });
    document.addEventListener("mouseover", function (e) { var t = e.target.closest("[data-help]"); if (t && !t.contains(document.activeElement)) showHelp(t.getAttribute("data-help"), e.target); });
    idleHelp();
  }
  function inlineHelp(key) {
    return '<details class="inlinehelp"><summary>What does this mean?</summary><div class="box">' + helpHTML(key, -1) + "</div></details>";
  }
  function addInlineHelp() {
    Array.prototype.forEach.call(document.querySelectorAll(".control[data-help], #systemList"), function (el) {
      var key = el.getAttribute("data-help");
      var holder = el.id === "systemList" ? el.parentNode : el;
      var tpl = document.createElement("div"); tpl.innerHTML = inlineHelp(key);
      if (el.id === "systemList") holder.insertBefore(tpl.firstChild, el.nextSibling); else holder.appendChild(tpl.firstChild);
    });
    var wrap = document.createElement("div");
    wrap.innerHTML = ["value", "likelihood", "lifetime", "protection", "harvest", "turnover"].map(function (k) {
      return '<details class="inlinehelp"><summary>About “' + esc(HELP[k].title) + '”</summary><div class="box">' + helpHTML(k, -1) + "</div></details>";
    }).join("");
    var host = $("assets").querySelector(".tablewrap");
    host.parentNode.insertBefore(wrap, host);
  }

  // ---------- the race (hero figure) ----------
  function sliderL(v) { return 0.2 * Math.pow(60 / 0.2, v / 100); }
  function sliderLam(v) { return 0.005 * Math.pow(1 / 0.005, v / 100); }
  function invL(L) { return 100 * Math.log(L / 0.2) / Math.log(60 / 0.2); }
  function invLam(x) { return 100 * Math.log(x / 0.005) / Math.log(1 / 0.005); }

  function renderRace() {
    var L = state.race.L, lam = state.race.lam, d = dist(state.race.scen);
    var W = 760, H = 330, ml = 48, mr = 14, mt = 22, mb = 70, pw = W - ml - mr, ph = H - mt - mb;
    var T = 50, N = 250, maxF = 0, i, t;
    for (i = 1; i <= N; i++) maxF = Math.max(maxF, d.pdf(T * i / N));
    maxF *= 1.12;
    var X = function (tt) { return ml + pw * tt / T; };
    var Y = function (v) { return mt + ph * (1 - v / maxF); };
    var line = "", all = "M" + X(0) + "," + Y(0);
    for (i = 1; i <= N; i++) { t = T * i / N; all += " L" + X(t).toFixed(1) + "," + Y(d.pdf(t)).toFixed(1); }
    var Lc = Math.min(L, T);
    var gray = "M" + X(0) + "," + Y(0), orange = "M" + X(0) + "," + Y(0);
    var M = Math.max(2, Math.round(N * Lc / T));
    for (i = 1; i <= M; i++) {
      t = Lc * i / M; var f = d.pdf(t);
      gray += " L" + X(t).toFixed(1) + "," + Y(f).toFixed(1);
      orange += " L" + X(t).toFixed(1) + "," + Y(f * Math.exp(-lam * t)).toFixed(1);
    }
    gray += " L" + X(Lc).toFixed(1) + "," + Y(0) + " Z";
    // orange region: between the survival-weighted curve and zero
    orange += " L" + X(Lc).toFixed(1) + "," + Y(0) + " Z";

    var axis = '<line x1="' + ml + '" y1="' + Y(0) + '" x2="' + (W - mr) + '" y2="' + Y(0) + '" stroke="var(--ink)" stroke-width="1"/>';
    for (t = 0; t <= T; t += 10) {
      axis += '<line x1="' + X(t) + '" y1="' + Y(0) + '" x2="' + X(t) + '" y2="' + (Y(0) + 5) + '" stroke="var(--ink)"/>' +
        '<text x="' + X(t) + '" y="' + (Y(0) + 20) + '" text-anchor="middle" font-size="14" fill="var(--ink)">' + t + "</text>" +
        '<text x="' + X(t) + '" y="' + (Y(0) + 37) + '" text-anchor="middle" font-size="12.5" fill="var(--muted)">' + (BASE_YEAR + t) + "</text>";
    }
    axis += '<text x="' + (ml + pw / 2) + '" y="' + (Y(0) + 54) + '" text-anchor="middle" font-size="13" fill="var(--muted)">years from now (calendar year in grey)</text>';
    axis += '<text transform="translate(14,' + (mt + ph / 2) + ') rotate(-90)" text-anchor="middle" font-size="13" fill="var(--muted)">chance of arrival in each year</text>';

    var defs = '<defs><pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" stroke="var(--rule)" stroke-width="2"/></pattern></defs>';
    var after = L < T ? '<rect x="' + X(L) + '" y="' + mt + '" width="' + (X(T) - X(L)) + '" height="' + ph + '" fill="url(#hatch)"/>' : "";
    var body = defs + after +
      '<path d="' + gray + '" fill="var(--rule)" opacity="0.9"/>' +
      '<path d="' + orange + '" fill="var(--quantum-fill)" opacity="0.92"/>' +
      '<path d="' + all + '" fill="none" stroke="var(--muted)" stroke-width="1.4"/>' +
      '<line x1="' + X(Lc) + '" y1="' + mt + '" x2="' + X(Lc) + '" y2="' + Y(0) + '" stroke="var(--ink)" stroke-width="1.6" stroke-dasharray="5 4"/>' +
      '<text x="' + Math.min(X(Lc) + 6, W - 150) + '" y="' + (mt + 10) + '" font-size="14" fill="var(--ink)">data stops mattering: year ' + fmtYears(L) + "</text>" +
      axis;
    $("raceSvg").innerHTML = '<title id="raceTitle">The race between a quantum computer and a hacker</title><desc id="raceDesc">Grey: chance a quantum computer arrives in each year. Orange: the part of that chance in which a hacker has not already taken the data, up to the year the data stops mattering.</desc>' + body;

    var r = C.race(d, lam, L, 0);
    var dd = d, Vx = 1e7, tau = 0.1, h = 0.5;
    var classical = lam * Vx, quantum = C.quantumRate(tau * Vx, h, L, lam, dd, 0, true);
    var star = C.lambdaStar(tau, h, L, 0, dd);
    var bigger = quantum > classical ? "quantum" : "classical";
    var html = "<p>A quantum computer exists within " + fmtYears(L) + " years with probability <strong>" + pct(r.naive, 1) + "</strong> (grey area).</p>" +
      "<p>It arrives <em>before</em> a hacker has taken the data with probability <strong>" + pct(r.counted, 1) + "</strong> (orange area), which is <strong>" + pct(r.fraction, 0) + "</strong> of the grey. In the rest, the data was already gone, so a quantum computer adds nothing.</p>" +
      "<p>Take a store worth $10M, where a tenth of the content is new each year and half of the traffic can be recorded. Waiting one more year costs <span class=\"c-classical\">" + money(classical) + "</span> from hackers and <span class=\"c-quantum\">" + money(quantum) + "</span> from the quantum threat, so the " + bigger + " term is larger." +
      (star == null ? "" : " The quantum term wins whenever the hacker rate is below <strong>" + fmtRate(star) + "</strong> a year; yours is " + fmtRate(lam) + ".") + "</p>";
    $("raceReadout").innerHTML = html;
    $("raceCaption").textContent = "Grey: the chance, year by year, that a quantum computer arrives. Orange: the part in which a hacker has not already taken the data. Hatched: after the data stops mattering.";
    $("raceLout").textContent = fmtYears(L) + " years";
    $("raceLamOut").textContent = fmtRate(lam) + " a year, about once in " + trim(1 / lam, lam > 0.3 ? 1 : 0) + " years";
  }

  function segmented(host, items, current, onPick) {
    host.innerHTML = items.map(function (it) {
      return '<button type="button" role="radio" aria-checked="' + (it.key === current) + '" data-key="' + it.key + '">' + esc(it.label) + "</button>";
    }).join("");
    Array.prototype.forEach.call(host.querySelectorAll("button"), function (b) {
      b.onclick = function () { onPick(b.getAttribute("data-key")); };
      b.onkeydown = function (e) {
        var btns = Array.prototype.slice.call(host.querySelectorAll("button")), i = btns.indexOf(b);
        if (e.key === "ArrowRight" || e.key === "ArrowDown") { e.preventDefault(); btns[(i + 1) % btns.length].click(); btns[(i + 1) % btns.length].focus(); }
        if (e.key === "ArrowLeft" || e.key === "ArrowUp") { e.preventDefault(); btns[(i - 1 + btns.length) % btns.length].click(); btns[(i - 1 + btns.length) % btns.length].focus(); }
      };
    });
  }

  // ---------- systems ----------
  function renderSystems() {
    $("systemList").innerHTML = PRESETS.map(function (p) {
      return '<button type="button" role="radio" aria-checked="' + (state.system === p.key) + '" data-key="' + p.key + '"><span class="name">' + esc(p.title) + '</span><span class="blurb">' + esc(p.blurb) + "</span></button>";
    }).join("");
    Array.prototype.forEach.call($("systemList").querySelectorAll("button"), function (b) {
      b.onclick = function () { loadSystem(b.getAttribute("data-key")); };
    });
  }
  function loadSystem(key) {
    var p = PRESETS.filter(function (x) { return x.key === key; })[0];
    state.system = key; state.assets = JSON.parse(JSON.stringify(p.assets)); state.open = null; state.mc = null;
    renderSystems(); renderEditor(); renderAll();
  }

  // ---------- assumptions ----------
  function renderAssumptions() {
    segmented($("scen"), [{ key: "optimistic", label: "Soon-ish" }, { key: "pessimistic", label: "Later" }, { key: "custom", label: "Pick a year" }], state.scen, function (k) {
      state.scen = k; state.mc = null; renderAssumptions(); renderAll();
    });
    $("yearBox").hidden = state.scen !== "custom";
    var d = currentDist();
    $("scenHint").textContent = "Middle of the curve: about " + medianYear(d) + ". Chance within 10 years: " + pct(d.cdf(10)) + "; within 15 years: " + pct(d.cdf(15)) + ".";
    $("rhoOut").textContent = state.rho + "%" + (state.rho === 0 ? " (count harm in full)" : "");
  }

  // ---------- the ranking ----------
  var FLOOR = 3, SPAN = 4.6, HALF = 138;
  function barW(v) { return v < Math.pow(10, FLOOR) ? 0 : Math.max(0, Math.min(Math.log(v) / Math.LN10 - FLOOR, SPAN)) / SPAN * HALF; }
  function barSvg(c, q) {
    var cx = 150, wc = barW(c), wq = barW(q);
    return '<svg viewBox="0 0 300 24" role="img" aria-label="classical ' + money(c) + ', quantum ' + money(q) + '" preserveAspectRatio="none">' +
      '<rect x="' + (cx - wc) + '" y="3" width="' + wc + '" height="18" fill="var(--classical)"/>' +
      '<rect x="' + cx + '" y="3" width="' + wq + '" height="18" fill="var(--quantum-fill)"/>' +
      '<line x1="' + cx + '" y1="0" x2="' + cx + '" y2="24" stroke="var(--ink)" stroke-width="1"/></svg>';
  }
  function derivation(s) {
    var a = state.assets.filter(function (x) { return x.id === s.id; })[0];
    var B = C.BANDS, V = B.value[a.value], lam = B.likelihood[a.likelihood], h = B.harvest[a.harvest], L = Number(a.lifetime);
    var tau = (a.turnover === "" || a.turnover == null) ? null : Number(a.turnover), d = currentDist(), F = d.cdf(L), vuln = C.PROTECTION[a.protection];
    var out = "<p><strong>" + esc(s.name) + "</strong></p><ol>";
    out += "<li><strong>Hackers today.</strong> A single exposure costs about " + money(V) + " and happens about " + fmtRate(lam) + " times a year, so waiting a year costs " + fmtRate(lam) + " × " + money(V) + " = <span class=\"c-classical\">" + money(s.classical) + "</span>.</li>";
    if (!vuln) out += "<li><strong>Quantum later.</strong> The lock (" + esc(a.protection.replace(/_/g, " ").toLowerCase()) + ") cannot be broken by a quantum computer, so this term is <span class=\"c-quantum\">$0</span>.</li>";
    else if (h === 0) out += "<li><strong>Quantum later.</strong> Nothing can be recorded in transit, so there is nothing to unlock later. This term is <span class=\"c-quantum\">$0</span>.</li>";
    else if (L <= 0) out += "<li><strong>Quantum later.</strong> The data does not have to stay secret, so unlocking it later hurts nothing. This term is <span class=\"c-quantum\">$0</span>.</li>";
    else {
      var r = (tau == null ? 1 : tau) * V;
      out += "<li><strong>How long it must stay secret.</strong> " + fmtYears(L) + " years. The chance a quantum computer exists within that time is " + pct(F, 1) + ".</li>";
      out += "<li><strong>New data each year.</strong> " + (tau == null ? "No turnover was given, so all the value is assumed to be new every year (turnover 1)." : pct(tau, 0) + " of it is new each year.") + " That is about " + money(r) + " of fresh value a year.</li>";
      out += "<li><strong>What can be recorded.</strong> About " + pct(h, 0) + " of the traffic, so " + money(r * h) + " a year is exposed.</li>";
      out += "<li><strong>Not counting data a hacker takes first.</strong> Counting the quantum chance alone would give " + money(s.quantumUncoupled) + " a year. Removing the cases where a hacker got there first leaves <span class=\"c-quantum\">" + money(s.quantum) + "</span>.</li>";
    }
    out += "<li><strong>Total.</strong> " + money(s.classical) + " + " + money(s.quantum) + " = " + money(s.total) + " a year. A hacker-only list puts this asset " + ordinal(s.classicalRank) + "; this list puts it " + ordinal(s.rank) + ".</li></ol>";
    if (s.turnoverDefaulted) out += "<p class=\"hint\">Turnover was left blank, so the default of 1 was used. Enter a value in the table below for a better estimate.</p>";
    if (a.note) out += "<p class=\"hint\">Why the study assumed this: " + esc(a.note) + "</p>";
    return out;
  }
  function ordinal(n) { return "#" + n; }
  function renderLedger() {
    var res = C.rank(state.assets, currentDist(), state.rho / 100);
    var n = res.unified.length, flips = 0, pos = {};
    res.classicalOrder.forEach(function (s, i) { pos[s.id] = i; });
    for (var i = 0; i < n; i++) for (var j = i + 1; j < n; j++) if (pos[res.unified[i].id] > pos[res.unified[j].id]) flips++;
    var dom = res.unified.filter(function (s) { return s.dominant; });
    $("summary").innerHTML = n === 0 ? "Add an asset to begin." :
      "<strong>" + flips + " of " + (n * (n - 1) / 2) + "</strong> pairs of assets are ordered differently than on a hacker-only list, and <strong>" + dom.length + " of " + n + "</strong> are quantum-led (their quantum cost is the larger half)" +
      (dom.length ? ": " + dom.map(function (s) { return esc(s.id); }).join(", ") : "") + ".";
    var max = 0;
    $("ledgerBody").innerHTML = res.unified.map(function (s) {
      var open = state.open === s.id;
      var mv = s.move > 0 ? '<span class="moveup">up ' + s.move + "</span>" : s.move < 0 ? '<span class="movedown">down ' + (-s.move) + "</span>" : '<span class="same">same place</span>';
      var row = '<tr class="' + (open ? "open" : "") + '"><td class="num">' + s.rank + '</td><td class="name"><button type="button" data-id="' + esc(s.id) + '" aria-expanded="' + open + '">' + esc(s.name) + "</button>" + (s.dominant ? '<span class="tag">quantum-led</span>' : "") + "</td>" +
        '<td class="barcell">' + barSvg(s.classical, s.quantum) + '<div class="nums"><span>' + (s.classical >= 1e3 ? money(s.classical) : "under $1k") + "</span><span>" + (s.quantum >= 1e3 ? money(s.quantum) : "under $1k") + "</span></div></td>" +
        '<td class="num"><strong>' + money(s.total) + "</strong></td><td class=\"num\">" + mv + "</td></tr>";
      if (open) row += '<tr class="derive"><td></td><td colspan="4">' + derivation(s) + "</td></tr>";
      return row;
    }).join("");
    Array.prototype.forEach.call($("ledgerBody").querySelectorAll("button[data-id]"), function (b) {
      b.onclick = function () { var id = b.getAttribute("data-id"); state.open = state.open === id ? null : id; renderLedger(); var nb = $("ledgerBody").querySelector('button[data-id="' + id + '"]'); if (nb) nb.focus(); };
    });
  }

  // ---------- sensitivity ----------
  function orderRow(order, base) {
    return order.map(function (id, k) { return base && base[k] !== id ? '<span class="diff">' + esc(id) + "</span>" : esc(id); }).join(" ");
  }
  function renderSensitivity() {
    if (!state.assets.length) { $("sensYears").innerHTML = ""; $("sensRho").innerHTML = ""; $("sensVerdict").textContent = ""; return; }
    var years = [2030, 2032, 2035, 2038, 2040, 2045], rhos = [0, 2, 5, 7, 10];
    var ord = function (d, r) { return C.rank(state.assets, d, r).unified.map(function (s) { return s.id; }); };
    var baseY = null, sameY = true, rowsY = years.map(function (y, idx) {
      var o = ord(C.distWithMedianYear(y, BASE_YEAR, OPT.beta), state.rho / 100);
      if (idx === 0) baseY = o; else if (o.join() !== baseY.join()) sameY = false;
      return "<tr><th scope=\"row\">" + y + '</th><td class="order">' + orderRow(o, idx === 0 ? null : baseY) + "</td></tr>";
    }).join("");
    $("sensYears").innerHTML = '<thead><tr><th scope="col">If a quantum computer arrives around</th><th scope="col">Order, most urgent first</th></tr></thead><tbody>' + rowsY + "</tbody>";
    var d0 = currentDist(), baseR = null, sameR = true, rowsR = rhos.map(function (r, idx) {
      var o = ord(d0, r / 100);
      if (idx === 0) baseR = o; else if (o.join() !== baseR.join()) sameR = false;
      return "<tr><th scope=\"row\">" + r + '%</th><td class="order">' + orderRow(o, idx === 0 ? null : baseR) + "</td></tr>";
    }).join("");
    $("sensRho").innerHTML = '<thead><tr><th scope="col">If far-future losses are shrunk by</th><th scope="col">Order, most urgent first</th></tr></thead><tbody>' + rowsR + "</tbody>";
    $("sensVerdict").textContent = sameY && sameR ? "The order never changes across these dates or discounts. Guessing them does not decide anything for this system." :
      !sameY && !sameR ? "The order changes with both the arrival date and the discount. Those two guesses matter here." :
      !sameY ? "The order changes with the arrival date, but not with the discount. The date is the uncertainty that matters here." : "The order changes with the discount, but not with the arrival date. The discount is the judgement that matters here.";
  }

  // ---------- uncertainty ----------
  function runMc() {
    $("mcStatus").textContent = "Running…";
    setTimeout(function () {
      var t0 = performance.now();
      state.mc = C.simulate(state.assets, 2000, 11);
      $("mcStatus").textContent = "Done in " + Math.round(performance.now() - t0) + " ms.";
      renderMc();
    }, 20);
  }
  function renderMc() {
    var r = state.mc;
    if (!r) { $("mcFigure").hidden = true; $("mcSummary").innerHTML = ""; return; }
    $("mcFigure").hidden = false;
    var cl = {}; C.rank(state.assets, currentDist(), state.rho / 100).unified.forEach(function (s) { cl[s.id] = s.classicalRank; });
    var rows = r.assets.slice().sort(function (a, b) { return a.rankMedian - b.rankMedian; }), n = rows.length;
    var W = 760, left = 300, right = 24, top = 26, rh = 26, H = top + rh * n + 34, pw = W - left - right;
    var shortName = function (nm) { nm = nm.replace(/\s*\(.*$/, ""); return nm.length > 30 ? nm.slice(0, 29) + "…" : nm; };
    var X = function (k) { return left + pw * (k - 1) / Math.max(1, n - 1); };
    var s = "";
    for (var k = 1; k <= n; k++) s += '<line x1="' + X(k) + '" y1="' + (top - 8) + '" x2="' + X(k) + '" y2="' + (top + rh * n) + '" stroke="var(--rule)"/><text x="' + X(k) + '" y="' + (top + rh * n + 18) + '" text-anchor="middle" font-size="12" fill="var(--muted)">' + k + "</text>";
    s += '<text x="' + (left + pw / 2) + '" y="' + (H - 2) + '" text-anchor="middle" font-size="12" fill="var(--muted)">rank (1 = most urgent)</text>';
    rows.forEach(function (a, i) {
      var y = top + rh * i + rh / 2, name = shortName(a.name);
      s += '<text x="' + (left - 12) + '" y="' + (y + 5) + '" text-anchor="end" font-size="14" fill="var(--ink)">' + esc(a.id + "  " + name) + "</text>" +
        '<line x1="' + X(a.rankLo) + '" y1="' + y + '" x2="' + X(a.rankHi) + '" y2="' + y + '" stroke="var(--quantum-fill)" stroke-width="5" stroke-linecap="round" opacity="0.85"/>' +
        '<circle cx="' + X(a.rankMedian) + '" cy="' + y + '" r="4" fill="var(--ink)"/>' +
        '<path d="M' + X(cl[a.id]) + "," + (y - 6) + " l6,6 l-6,6 l-6,-6 Z\" fill=\"var(--paper)\" stroke=\"var(--classical)\" stroke-width=\"1.8\"/>";
    });
    $("mcSvg").setAttribute("viewBox", "0 0 " + W + " " + H);
    $("mcSvg").innerHTML = s;
    var movers = rows.filter(function (a) { return a.pDominant > 0.05; });
    var html = "<p>In <strong>" + pct(r.pSetChanges) + "</strong> of the what-if worlds the funded top " + r.k + " is not the same as on a hacker-only list. In <strong>" + pct(r.pAnyDominant) + "</strong> at least one asset is quantum-led.</p>";
    if (movers.length) {
      html += '<div class="tablewrap"><table class="plain compact"><thead><tr><th scope="col">Asset</th><th scope="col" class="num">Quantum-led</th><th scope="col" class="num">In top ' + r.k + '</th><th scope="col" class="num">…on a hacker-only list</th><th scope="col" class="num">Moves up 2 or more</th></tr></thead><tbody>' +
        movers.sort(function (a, b) { return b.pDominant - a.pDominant; }).slice(0, 8).map(function (a) {
          return "<tr><td>" + esc(a.id + " " + a.name.replace(/\s*\(.*$/, "")) + '</td><td class="num">' + pct(a.pDominant) + '</td><td class="num">' + pct(a.pTopUnified) + '</td><td class="num">' + pct(a.pTopClassical) + '</td><td class="num">' + pct(a.pUp2) + "</td></tr>";
        }).join("") + "</tbody></table></div>";
    }
    $("mcSummary").innerHTML = html;
  }

  // ---------- editor ----------
  var LABELS = {
    value: { NEGLIGIBLE: "Negligible ($0)", LOW: "Low ($10k)", MODERATE: "Moderate ($100k)", HIGH: "High ($1M)", SEVERE: "Severe ($10M)", CATASTROPHIC: "Catastrophic ($100M)" },
    likelihood: { RARE: "Rare (0.01)", UNLIKELY: "Unlikely (0.05)", POSSIBLE: "Possible (0.20)", LIKELY: "Likely (0.50)", FREQUENT: "Frequent (1.00)" },
    harvest: { NONE: "None (0)", LOW: "Low (0.1)", PARTIAL: "Partial (0.5)", HIGH: "High (0.9)", FULL: "Full (1.0)" },
    protection: { RSA_2048: "RSA 2048", RSA_4096: "RSA 4096", ECDH_P256: "Elliptic curve P-256", ECDH_P384: "Elliptic curve P-384", AES_256_PSK: "AES-256, shared key", ML_KEM_768: "ML-KEM-768", HYBRID_X25519_MLKEM: "Hybrid X25519 + ML-KEM", NONE: "None" },
  };
  function sel(field, v, i) {
    return '<select data-help="' + field + '" data-i="' + i + '" data-f="' + field + '" aria-label="' + HELP[field].title + '">' +
      FIELD_OPTIONS[field].map(function (o) { return "<option value=\"" + o + "\"" + (o === v ? " selected" : "") + ">" + LABELS[field][o] + "</option>"; }).join("") + "</select>";
  }
  function renderEditor() {
    var head = "<thead><tr><th scope=\"col\">Name</th><th scope=\"col\">Loss if exposed</th><th scope=\"col\">Hacker rate</th><th scope=\"col\">Years secret</th><th scope=\"col\">Lock</th><th scope=\"col\">Recordable</th><th scope=\"col\">Turnover</th><th scope=\"col\"><span class=\"sr\">Remove</span></th></tr></thead>";
    var rows = state.assets.map(function (a, i) {
      return '<tr><td><input type="text" data-i="' + i + '" data-f="name" value="' + esc(a.name) + '" aria-label="Asset name"></td>' +
        "<td>" + sel("value", a.value, i) + "</td><td>" + sel("likelihood", a.likelihood, i) + "</td>" +
        '<td><input type="number" min="0" step="any" data-help="lifetime" data-i="' + i + '" data-f="lifetime" value="' + esc(a.lifetime) + '" aria-label="Years the data must stay secret"></td>' +
        "<td>" + sel("protection", a.protection, i) + "</td><td>" + sel("harvest", a.harvest, i) + "</td>" +
        '<td><input type="number" min="0" step="any" data-help="turnover" data-i="' + i + '" data-f="turnover" value="' + esc(a.turnover) + '" placeholder="1" aria-label="Annual turnover"></td>' +
        '<td><button type="button" class="remove" data-del="' + i + '" aria-label="Remove ' + esc(a.name) + '">Remove</button></td></tr>';
    }).join("");
    $("editor").innerHTML = '<caption class="sr">Editable list of assets</caption>' + head + "<tbody>" + rows + "</tbody>";
    Array.prototype.forEach.call($("editor").querySelectorAll("[data-f]"), function (el) {
      var handler = function () {
        var i = +el.getAttribute("data-i"), f = el.getAttribute("data-f");
        state.assets[i][f] = el.value; state.mc = null; renderAll();
        if (el.tagName === "SELECT") showHelp(el.getAttribute("data-help"), el);
      };
      el.addEventListener(el.tagName === "SELECT" ? "change" : "input", handler);
    });
    Array.prototype.forEach.call($("editor").querySelectorAll("[data-del]"), function (b) {
      b.onclick = function () { state.assets.splice(+b.getAttribute("data-del"), 1); state.open = null; state.mc = null; renderEditor(); renderAll(); };
    });
  }
  function toCsv() {
    var q = function (s) { s = String(s == null ? "" : s); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
    var head = "asset_id,name,services,value_band,likelihood_band,data_lifetime_years,protection_class,harvest_band,turnover_per_year,migration_time_years,evidence_for_zeroing,rationale,provenance";
    var lines = state.assets.map(function (a) {
      var zero = a.harvest === "NONE" || Number(a.lifetime) === 0;
      return [a.id, a.name, "", a.value, a.likelihood, a.lifetime, a.protection, a.harvest, a.turnover, 1,
        zero ? "[exported from the explorer: add written evidence for this zero]" : "", a.note || "Exported from the explorer.", "ASSUMED_FROM_PUBLIC_DOCS"].map(q).join(",");
    });
    return head + "\n" + lines.join("\n") + "\n";
  }

  // ---------- table of contents ----------
  function bindToc() {
    var links = Array.prototype.slice.call(document.querySelectorAll("#tocList a"));
    if (!("IntersectionObserver" in window)) return;
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) links.forEach(function (a) { a.setAttribute("aria-current", a.getAttribute("href") === "#" + en.target.id ? "true" : "false"); });
      });
    }, { rootMargin: "-20% 0px -70% 0px" });
    links.forEach(function (a) { var s = document.querySelector(a.getAttribute("href")); if (s) io.observe(s); });
  }

  // ---------- wiring ----------
  function renderAll() {
    renderAssumptions(); renderLedger(); renderSensitivity(); renderMc();
  }
  function init() {
    // race controls
    $("raceL").value = invL(state.race.L); $("raceLam").value = invLam(state.race.lam);
    $("raceL").oninput = function () { state.race.L = sliderL(+this.value); renderRace(); };
    $("raceLam").oninput = function () { state.race.lam = sliderLam(+this.value); renderRace(); };
    var rs = function () { segmented($("raceScen"), [{ key: "optimistic", label: "Soon-ish" }, { key: "pessimistic", label: "Later" }], state.race.scen, function (k) { state.race.scen = k; rs(); renderRace(); }); };
    rs(); renderRace();
    // global assumptions
    $("year").oninput = function () { state.year = +this.value; $("yearOut").textContent = this.value; state.mc = null; renderAssumptions(); renderLedger(); renderSensitivity(); renderMc(); };
    $("rho").oninput = function () { state.rho = +this.value; state.mc = null; renderAssumptions(); renderLedger(); renderSensitivity(); renderMc(); };
    $("runMc").onclick = runMc;
    $("addRow").onclick = function () { state.assets.push({ id: "N" + (state.assets.length + 1), name: "New asset", value: "HIGH", likelihood: "POSSIBLE", lifetime: 10, protection: "ECDH_P256", harvest: "HIGH", turnover: "", note: "" }); state.mc = null; renderEditor(); renderAll(); };
    $("resetRows").onclick = function () { loadSystem(state.system); };
    $("download").onclick = function () {
      var blob = new Blob([toCsv()], { type: "text/csv" }), a = document.createElement("a");
      a.href = URL.createObjectURL(blob); a.download = "asset_register.csv"; document.body.appendChild(a); a.click(); a.remove();
    };
    $("theme").onclick = function () {
      var r = document.documentElement, dark = r.getAttribute("data-theme") === "dark" || (!r.getAttribute("data-theme") && window.matchMedia("(prefers-color-scheme: dark)").matches);
      r.setAttribute("data-theme", dark ? "light" : "dark"); this.setAttribute("aria-pressed", String(!dark));
    };
    bindHelp(); bindToc(); loadSystem(state.system); addInlineHelp();
  }
  init();
})();
