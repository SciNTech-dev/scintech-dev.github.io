/* SciNTech site script. Every block is progressive: each page is complete without it.
   1. Theme toggle: <button data-theme-toggle hidden> is revealed here. Pressed = dark.
      The choice is kept in localStorage (try/catch); with no stored choice the system
      preference applies. The inline <head> snippet applies a stored choice before paint.
   2. Before/after slider (S4): each <figure data-cmp> gets .cmp-on; its native range input
      (arrows, Home/End) sets --pos, the restored side left of the divider is clipped to it,
      and a pointer drag on the picture moves the same input. "Zoom to 100 %" shows the
      pictures at natural size (1024 px) with scroll to pan. The Output / Clean / Heat map
      toggle is CSS-only (radios + :has) and needs no script. */
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

(function(){var figs=document.querySelectorAll("[data-cmp]");for(var i=0;i<figs.length;i++)(function(f){var frame=f.querySelector(".cmp-frame"),stage=f.querySelector(".cmp-stage"),ctl=f.querySelector(".cmp-controls"),range=f.querySelector(".cmp-range"),zoom=f.querySelector(".cmp-zoom"),drag=false;if(!frame||!stage||!range)return;f.classList.add("cmp-on");ctl.hidden=false;function set(v){v=Math.max(0,Math.min(100,Math.round(v)));range.value=v;stage.style.setProperty("--pos",v+"%");}function at(e){var b=stage.getBoundingClientRect();set((e.clientX - b.left)/ b.width * 100);}range.addEventListener("input",function(){set(+range.value);});stage.addEventListener("pointerdown",function(e){if(frame.classList.contains("is-zoom"))return;e.preventDefault();drag=true;try{stage.setPointerCapture(e.pointerId);}catch(x){/* capture unsupported */}at(e);});stage.addEventListener("pointermove",function(e){if(drag)at(e);});stage.addEventListener("pointerup",function(){drag=false;});stage.addEventListener("pointercancel",function(){drag=false;});zoom.addEventListener("click",function(){var on=!frame.classList.contains("is-zoom"),s=f.querySelectorAll("source[sizes]");frame.classList.toggle("is-zoom",on);zoom.setAttribute("aria-pressed",on?"true":"false");for(var k=0;k<s.length;k++){if(!s[k].getAttribute("data-sizes"))s[k].setAttribute("data-sizes",s[k].getAttribute("sizes"));s[k].setAttribute("sizes",on?"1024px":s[k].getAttribute("data-sizes"));}});set(+range.value||50);})(figs[i]);})();
