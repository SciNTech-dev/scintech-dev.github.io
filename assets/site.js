/* SciNTech site script. Every block is progressive: each page is complete without it.
   1. Theme toggle: <button data-theme-toggle hidden> is revealed here. Pressed = dark.
      The choice is kept in localStorage (try/catch); with no stored choice the system
      preference applies. The inline <head> snippet applies a stored choice before paint.
   S4 adds the before/after slider and heat-map toggle below this block. */
(function () {
  var root = document.documentElement, KEY = "theme";
  var mq = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;
  function current() {
    var t = root.getAttribute("data-theme");
    if (t === "dark" || t === "light") return t;
    return mq && mq.matches ? "dark" : "light";
  }
  var buttons = document.querySelectorAll("[data-theme-toggle]");
  function sync() {
    var dark = current() === "dark";
    for (var i = 0; i < buttons.length; i++) buttons[i].setAttribute("aria-pressed", dark ? "true" : "false");
  }
  function choose(t) {
    root.setAttribute("data-theme", t);
    try { localStorage.setItem(KEY, t); } catch (e) { /* storage blocked: choice lasts this page only */ }
    sync();
  }
  for (var i = 0; i < buttons.length; i++) {
    buttons[i].hidden = false;
    buttons[i].addEventListener("click", function () { choose(current() === "dark" ? "light" : "dark"); });
  }
  if (mq && mq.addEventListener) mq.addEventListener("change", sync);
  sync();
})();
