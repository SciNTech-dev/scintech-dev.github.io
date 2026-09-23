/* SciNTech site script. Every block is progressive: each page is complete without it.
   1. Theme toggle: <button data-theme-toggle hidden> is revealed here. Pressed = dark.
      The choice is kept in localStorage (try/catch); with no stored choice the system
      preference applies. The inline <head> snippet applies a stored choice before paint.
   2. Before/after slider (S4): each <figure data-cmp> gets .cmp-on; its native range input
      (arrows, Home/End) sets --pos, the restored side left of the divider is clipped to it,
      and a pointer drag on the picture moves the same input. "Zoom to 100 %" shows the
      pictures at natural size (1024 px) with scroll to pan; the range and the button are
      created here, since without JS the pictures simply stack. The Output / Clean / Heat map
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

(function(){var figs=document.querySelectorAll("[data-cmp]");for(var i=0;i<figs.length;i++)(function(f){var frame=f.querySelector(".cmp-frame"),stage=f.querySelector(".cmp-stage"),drag=false;if(!frame||!stage)return;var ctl=document.createElement("div");ctl.className="cmp-controls";ctl.innerHTML='<input class="cmp-range" type="range" min="0" max="100" value="50" aria-label="Reveal restored image"><button class="cmp-zoom" type="button" aria-pressed="false">Zoom to 100 %</button>';frame.parentNode.insertBefore(ctl,frame.nextSibling);var range=ctl.firstChild,zoom=ctl.lastChild;f.classList.add("cmp-on");function set(v){v=Math.max(0,Math.min(100,Math.round(v)));range.value=v;stage.style.setProperty("--pos",v+"%");}function at(e){var b=stage.getBoundingClientRect();set((e.clientX - b.left)/ b.width * 100);}range.addEventListener("input",function(){set(+range.value);});stage.addEventListener("pointerdown",function(e){if(frame.classList.contains("is-zoom"))return;e.preventDefault();drag=true;try{stage.setPointerCapture(e.pointerId);}catch(x){/* capture unsupported */}at(e);});stage.addEventListener("pointermove",function(e){if(drag)at(e);});stage.addEventListener("pointerup",function(){drag=false;});stage.addEventListener("pointercancel",function(){drag=false;});zoom.addEventListener("click",function(){var on=!frame.classList.contains("is-zoom");frame.classList.toggle("is-zoom",on);zoom.setAttribute("aria-pressed",on?"true":"false");});set(+range.value||50);})(figs[i]);})();
