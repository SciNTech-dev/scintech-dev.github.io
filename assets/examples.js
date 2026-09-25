/* Watermark Remover examples gallery (spec 0072): renders every card from
   /assets/ex/gallery.json. Chips filter by kind (All / Repeating / Single mark / Declined, the
   last judged for the method shown); the method toggle swaps each card's result (Watermark file /
   Saved mark / Two photos). Without JS the page keeps its static list of watermark-file results.
   gallery.json: cases[].r[method] = [[status, delta, dB in, dB out, output stem, heat stem] x2]. */
(function () {
  var app = document.getElementById("ex-app"), ctl = document.getElementById("ex-controls");
  if (!app || !ctl || !window.fetch) return;
  var A = "/assets/ex/", G, cat = "all", meth = "file";
  var NAME = { file: "watermark file", saved: "saved mark (learned from 8 photos)", two: "two photos" };
  var PH = ["train", "hiking"];
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }
  function sg(x) { return (x > 0 ? "+" : x < 0 ? "−" : "") + Math.abs(x).toFixed(2); }
  function pic(s, alt, cls, small) {
    var b = A + s, ss = small ? b + "-512.avif" : b + "-512.avif 512w," + b + "-1024.avif 1024w";
    return '<picture' + (cls ? ' class="' + cls + '"' : "") + '><source type="image/avif" srcset="' + ss +
      '"><img src="' + b + '-512.webp" width="1024" height="1024" alt="' + esc(alt) + '" loading="lazy" decoding="async"></picture>';
  }
  function declined(c) { return c.r[meth].some(function (p) { return p[0] !== "ok"; }); }
  function badge(r) {
    var ok = r.filter(function (p) { return p[0] === "ok"; }), n = r.length;
    var mean = (r[0][1] + r[1][1]) / 2, better = ok.filter(function (p) { return p[1] > 0; }).length;
    if (!ok.length) return '<p class="ex-badge declined">Declined — both pictures left unchanged.</p>';
    var cls = better === n ? "better" : (better === 0 && ok.length === n ? "worse" : "mixed");
    var t = cls === "better" ? "Closer to the true pictures" : cls === "worse" ? "Further from the true pictures" :
      "Closer on " + better + " of " + n + (ok.length < n ? ", declined on " + (n - ok.length) : "");
    return '<p class="ex-badge ' + cls + '">' + t + " (mean " + sg(mean) + " dB).</p>";
  }
  function card(c) {
    var r = c.r[meth], id = c.id, all = r.every(function (p) { return p[0] !== "ok"; });
    var before = "", after = "", rows = "";
    r.forEach(function (p, j) {
      var w = PH[j], ok = p[0] === "ok";
      before += '<div class="p' + (j + 1) + '">' + pic(c.id + (j + 1) + "i", "Marked " + w + " picture") + "</div>";
      after += '<div class="p' + (j + 1) + '">' + pic(p[4], (ok ? "Restored " : "Unchanged ") + w + " picture", "l-output") +
        pic("k" + (j + 1), "Clean " + w + " picture", "l-clean") + pic(p[5], "Heat map, " + w + " picture", "l-heat", 1) + "</div>";
      rows += '<tr><th scope="row">Picture ' + (j + 1) + " (" + w + ")</th><td>" + p[2].toFixed(2) + "</td><td>" +
        (ok ? p[3].toFixed(2) : "declined") + "</td><td>" + sg(p[1]) + "</td></tr>";
    });
    var radio = function (n, v, l, on) { return '<label><input type="radio" name="' + n + id + '" value="' + v + '"' + (on ? " checked" : "") + "> " + l + "</label>"; };
    var sets = '<div class="cmp-sets"><fieldset class="cmp-layer" aria-describedby="heat-legend"><legend>Show</legend>' +
      radio("l", "output", all ? "Input" : "Output", 1) + radio("l", "clean", "Clean") + radio("l", "heat", "Heat map") +
      '</fieldset><fieldset class="cmp-layer"><legend>Picture</legend>' + radio("p", "p1", "1", 1) + radio("p", "p2", "2") + "</fieldset></div>";
    var table = '<table class="ex-mini"><thead><tr><th scope="col">dB</th><th scope="col">Input</th><th scope="col">Output</th><th scope="col">Change</th></tr></thead><tbody>' + rows + "</tbody></table>";
    var cap = '<figcaption>' + table + '<p class="fine">Synthetic. Method: ' + NAME[meth] + ".</p></figcaption>";
    var fig = all ? '<figure class="cmp"><div class="cmp-frame">' + after + "</div>" + cap + "</figure>" :
      '<figure class="cmp" data-cmp><div class="cmp-frame"><div class="cmp-stage"><div class="cmp-before"><span class="cmp-tag">Input</span>' +
      before + '</div><div class="cmp-after"><span class="cmp-tag">Restored</span>' + after + "</div></div></div>" + cap + "</figure>";
    var wm = c.wm;
    return '<article class="ex-card" id="ex-' + id + '"><h3>' + esc(c.cap) + '</h3><p class="ex-kind">' + (c.rep ? "Repeating mark" : "Single mark") +
      "</p>" + badge(r) + '<figure class="ex-file"><img class="ex-wm" src="' + A + wm.s + '-512.webp" width="' + wm.w + '" height="' + wm.h +
      '" alt="The watermark file, shown over a checkerboard" loading="lazy" decoding="async"><figcaption class="fine">Watermark file: ' +
      wm.px[0] + " × " + wm.px[1] + " px, drawn at full strength here; in the file its strongest point is " + Math.round(wm.peak * 100) + " % opaque." +
      (meth === "file" ? "" : " Not used by this method; shown for reference.") + "</figcaption></figure>" +
      '<div class="cmp-wrap">' + sets + fig + "</div></article>";
  }
  function render() {
    var list = G.cases.filter(function (c) {
      return cat === "all" || (cat === "rep" && c.rep) || (cat === "single" && !c.rep) || (cat === "declined" && declined(c));
    });
    app.innerHTML = list.length ? list.map(card).join("") : '<p class="fine">No case was declined with this method.</p>';
    if (window.scnCmp) [].forEach.call(app.querySelectorAll("[data-cmp]"), window.scnCmp);
    var t = G.totals[meth];
    document.getElementById("ex-status").textContent = "Showing " + list.length + " of " + G.cases.length + " marks. " +
      NAME[meth].charAt(0).toUpperCase() + NAME[meth].slice(1) + ": " + t.better + " of " + t.images + " pictures closer, " +
      t.worse + " further, " + t.declined + " declined; mean " + sg(t.mean) + " dB.";
    [].forEach.call(ctl.querySelectorAll("[data-cat]"), function (b) {
      b.setAttribute("aria-pressed", b.getAttribute("data-cat") === cat ? "true" : "false");
      if (b.getAttribute("data-cat") === "declined")
        b.textContent = "Declined (" + G.cases.filter(declined).length + ")";
    });
    [].forEach.call(ctl.querySelectorAll("[data-method]"), function (b) {
      b.setAttribute("aria-pressed", b.getAttribute("data-method") === meth ? "true" : "false");
    });
  }
  ctl.addEventListener("click", function (e) {
    var b = e.target.closest("button");
    if (!b || !G) return;
    if (b.hasAttribute("data-cat")) cat = b.getAttribute("data-cat");
    if (b.hasAttribute("data-method")) meth = b.getAttribute("data-method");
    render();
  });
  fetch(A + "gallery.json").then(function (r) { if (!r.ok) throw r.status; return r.json(); }).then(function (g) {
    G = g;
    var st = document.getElementById("ex-static");
    if (st) st.hidden = true;
    ctl.hidden = false;
    app.hidden = false;
    render();
  }).catch(function () { /* keep the static list */ });
})();
