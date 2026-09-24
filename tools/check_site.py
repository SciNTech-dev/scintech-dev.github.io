#!/usr/bin/env python3
"""Site checker for scintech-dev.github.io (spec 0069 §5.5, §5.8). Stdlib only.

Prints one token per check; a check that fails prints <NAME>_FAIL plus the reasons.
Exit code is 1 if any check fails, but grep the tokens: exit 0 is not a pass.

  SITE_LINKS_OK n=<internal links> pending=<k> external=<e>
  SITE_NOEMAIL_OK files=<n> allowed=<k>
      (owner 2026-09-23 "email on privacy pages only": the one CONTACT_EMAIL may appear only
      in the contact/deletion section of the two app privacy policies, and must appear there)
  SITE_META_OK pages=<n>
  SITE_A11Y_OK pages=<n>
  SITE_THEME_OK tokens=<n> blocks=<b>
  SITE_CONTRAST_OK pairs=<n> min=<ratio>
  SITE_JSONLD_OK nodes=<n>
  SITE_DISCOVERY_OK sitemap=<n> llms_urls=<n>
  SITE_BUDGET_OK pages=<n> max_kb=<k> lcp_ms=<t> cls=<c> a11y_min=<s>
      (or SITE_BUDGET_SKIPPED when Lighthouse is not run: the chunk is then not green)
  SITE_CHECK_OK | SITE_CHECK_FAIL

Usage: python3 tools/check_site.py [--no-lighthouse] [--root DIR]
Lighthouse runs as `npx -y lighthouse@13.5.0` against a local http.server, one page at a
time, default mobile profile with simulated throttling.
"""
import argparse, functools, http.server, json, os, re, socketserver, subprocess, sys, threading
from html.parser import HTMLParser

HOST = "https://scintech-dev.github.io"
SKIP_DIRS = {".git", ".review", "tools", "__pycache__", "node_modules"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
BUDGET = {"html_kb": 60, "css_kb": 40, "js_kb": 6, "atf_img_kb": 250, "page_kb": 600,
          "lcp_ms": 2500, "cls": 0.1, "a11y": 0.95}
# Spec 0069 §5.5: every page <= 600 KB except the examples gallery, <= 2.5 MB with
# lazy-loaded cards. Applies to both the static byte count and Lighthouse's transfer.
# 2026-09-24 (saved-template gallery): the gallery spans three pages because 21 slider cards
# exceed the 60 KB HTML budget on one page; the gallery allowance applies to each of them.
PAGE_KB_OVERRIDE = {"watermark-remover/examples/index.html": 2500,
                    "watermark-remover/examples/single-marks/index.html": 2500,
                    "watermark-remover/examples/two-photos/index.html": 2500}
MIN_CONTRAST = 4.5
TEXT_EXT = {".html", ".css", ".js", ".txt", ".xml", ".md", ".json", ".svg", ".py"}
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
MAILTO = "mail" + "to:"
CONTACT_EMAIL = "scintech.dev" + "@" + "gmail.com"   # concatenated: tools/ is scanned too
# page -> the contact/deletion section of its policy: from the heading that opens it (after
# id="policy") to the </section> that closes the policy. The email is legal only in there.
EMAIL_PAGES = ("watermark-remover/privacy/index.html", "seamless-video-looper/privacy/index.html")
CONTACT_HEAD_RE = re.compile(r"<h[23][^>]*>Contact and deletion requests</h[23]>")


def email_region(txt):
    """(start, end) of the allowed contact section, or None if the page lacks one."""
    pol = txt.find('id="policy"')
    if pol < 0:
        return None
    m = CONTACT_HEAD_RE.search(txt, pol)
    if not m:
        return None
    end = txt.find("</section>", m.end())
    return (m.start(), end) if end > 0 else None
LIGHTHOUSE = ["npx", "-y", "lighthouse@13.5.0"]


class Page(HTMLParser):
    def __init__(self, rel):
        super().__init__(convert_charrefs=True)
        self.rel = rel
        self.errors = []
        self.stack = []
        self.ids = []
        self.links = []          # (attr, value)
        self.imgs = []           # attrs dicts
        self.lazy_links = set()  # hrefs of loading="lazy" images and their <source>s
        self._pic = None
        self.meta = {}
        self.canonical = None
        self.title = ""
        self.h = []              # heading levels in order
        self.jsonld = []
        self.tags = set()
        self.lang = None
        self.labelledby = []
        self.buttons = []        # [attrs, text]
        self.anchors = []        # [attrs, text]
        self._text_sinks = []
        self._script = None
        self._in_title = False
        self._svg_depth = 0

    def _pos(self):
        return f"{self.rel}:{self.getpos()[0]}"

    def handle_starttag(self, tag, attrs, selfclosing=False):
        a = dict(attrs)
        self.tags.add(tag)
        if "id" in a:
            self.ids.append(a["id"])
        for k in ("aria-labelledby", "aria-describedby"):
            if k in a:
                self.labelledby.extend((k, x) for x in a[k].split())
        if tag == "html":
            self.lang = a.get("lang")
        elif tag == "a" and "href" in a:
            self.links.append(("href", a["href"]))
        elif tag == "link" and "href" in a:
            self.links.append(("link", a["href"]))
            if a.get("rel") == "canonical":
                self.canonical = a["href"]
        elif tag == "script" and "src" in a:
            self.links.append(("script", a["src"]))
        elif tag == "picture":
            self._pic = []
        elif tag == "img":
            self.imgs.append(a)
            if "src" in a:
                self.links.append(("img", a["src"]))
            if a.get("loading") == "lazy":
                # the img and every <source> candidate of its <picture> load lazily
                self.lazy_links.update(([a["src"]] if "src" in a else []) + (self._pic or []))
        elif tag == "source" and "srcset" in a:
            for part in a["srcset"].split(","):
                href = part.strip().split()[0]
                self.links.append(("source", href))
                if self._pic is not None:
                    self._pic.append(href)
        elif tag == "meta":
            key = a.get("property") or a.get("name")
            if key:
                self.meta.setdefault(key, a.get("content", ""))
        elif tag == "title" and not self._svg_depth:
            self._in_title = True
        elif tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.h.append(int(tag[1]))
        if tag == "svg":
            self._svg_depth += 1
        if tag == "script" and a.get("type") == "application/ld+json":
            self._script = []
        if tag in ("button", "a"):
            rec = [a, ""]
            (self.buttons if tag == "button" else self.anchors).append(rec)
            self._text_sinks.append(rec)
        if tag in VOID or selfclosing:
            return
        self.stack.append((tag, self.getpos()[0]))

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs, selfclosing=True)

    def handle_endtag(self, tag):
        if tag == "picture":
            self._pic = None
        if tag in VOID:
            self.errors.append(f"{self._pos()} end tag for void <{tag}>")
            return
        if not self.stack:
            self.errors.append(f"{self._pos()} stray </{tag}>")
            return
        top, line = self.stack.pop()
        if top != tag:
            self.errors.append(f"{self._pos()} </{tag}> closes <{top}> opened at line {line}")
        if tag == "title":
            self._in_title = False
        if tag == "svg":
            self._svg_depth -= 1
        if tag == "script" and self._script is not None:
            self.jsonld.append("".join(self._script))
            self._script = None
        if tag in ("button", "a") and self._text_sinks:
            self._text_sinks.pop()

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._script is not None:
            self._script.append(data)
        for rec in self._text_sinks:
            rec[1] += data

    def close(self):
        super().close()
        for tag, line in self.stack:
            self.errors.append(f"{self.rel}:{line} <{tag}> never closed")


def walk(root, skip=SKIP_DIRS):
    for d, dirs, files in os.walk(root):
        dirs[:] = sorted(x for x in dirs if x not in skip)
        for f in sorted(files):
            yield os.path.relpath(os.path.join(d, f), root)


def url_path(rel):
    """Page file → site path: about/index.html → /about/, 404.html → /404.html."""
    p = "/" + rel.replace(os.sep, "/")
    return p[: -len("index.html")] if p.endswith("/index.html") or p == "/index.html" else p


def resolve(root, base_rel, href):
    """Internal href → (file relpath or None, fragment, site path). None for external."""
    if re.match(r"^[a-z][a-z0-9+.-]*:", href, re.I) or href.startswith("//"):
        if href.startswith(HOST + "/") or href == HOST:
            href = href[len(HOST):] or "/"
        else:
            return None
    path, _, frag = href.partition("#")
    path = path.split("?")[0]
    if not path:
        path = url_path(base_rel)
    elif not path.startswith("/"):
        path = os.path.normpath(os.path.join(os.path.dirname(url_path(base_rel)), path)) + ("/" if path.endswith("/") else "")
    rel = path.lstrip("/")
    if path.endswith("/"):
        rel = rel + "index.html"
    return rel, frag, path


# ---------------------------------------------------------------- CSS tokens & contrast

def css_blocks(css):
    """Flat list of (media, selector, {prop: value}) for one level of @media nesting."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out, i, n = [], 0, len(css)

    def parse(body, media):
        j = 0
        while True:
            m = re.compile(r"([^{}]+)\{").search(body, j)
            if not m:
                return
            sel = m.group(1).strip()
            depth, k = 1, m.end()
            while depth and k < len(body):
                depth += {"{": 1, "}": -1}.get(body[k], 0)
                k += 1
            inner = body[m.end():k - 1]
            if sel.startswith("@media"):
                parse(inner, sel)
            else:
                decls = {}
                for d in inner.split(";"):
                    if ":" in d:
                        p, v = d.split(":", 1)
                        decls[p.strip()] = v.strip()
                out.append((media, sel, decls))
            j = k
    parse(css, None)
    return out


def hex_rgb(v):
    v = v.strip().lower()
    m = re.fullmatch(r"#([0-9a-f]{6})", v)
    if not m:
        return None
    return tuple(int(m.group(1)[i:i + 2], 16) / 255 for i in (0, 2, 4))


def lum(rgb):
    f = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = map(f, rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


PAIRS = [("text", "bg"), ("text", "surface"), ("text", "surface-2"),
         ("muted", "bg"), ("muted", "surface"), ("muted", "surface-2"),
         ("accent", "bg"), ("accent", "surface"), ("accent", "surface-2"),
         ("accent-ink", "accent-bg"), ("accent", "accent-soft"), ("band-text", "band-bg")]
APPS = {"hub": None, "wmr": '[data-app="wmr"]', "looper": '[data-app="looper"]'}


def check_theme(css):
    blocks = css_blocks(css)
    fails, notes = [], []

    def get(media, sel):
        found = [d for m, s, d in blocks if m == media and s == sel]
        merged = {}
        for d in found:
            merged.update({k: v for k, v in d.items() if k.startswith("--c-")})
        return merged if found else None

    MQ = "@media (prefers-color-scheme: dark)"
    light_root = get(None, ":root")
    dark_mq_root = get(MQ, ':root:not([data-theme="light"])')
    dark_at_root = get(None, ':root[data-theme="dark"]')
    if not (light_root and dark_mq_root and dark_at_root):
        return ["missing :root light block or one of the two dark blocks"], [], 0, 0, []
    ntok, nblocks = len(light_root), 3
    for name, blk in (("prefers-color-scheme", dark_mq_root), ("[data-theme=dark]", dark_at_root)):
        miss = sorted(set(light_root) - set(blk))
        if miss:
            fails.append(f"dark block {name} misses {miss}")
    if dark_mq_root != dark_at_root:
        diff = sorted(k for k in set(dark_mq_root) | set(dark_at_root) if dark_mq_root.get(k) != dark_at_root.get(k))
        fails.append(f"the two dark :root blocks differ on {diff}")
    themes = {}
    for app, sel in APPS.items():
        lt, dk = dict(light_root), dict(dark_mq_root)
        if sel:
            la = get(None, sel)
            dm = get(MQ, f':root:not([data-theme="light"]) {sel}')
            da = get(None, f':root[data-theme="dark"] {sel}')
            if not (la and dm and da):
                fails.append(f"{app}: missing light or dark accent block")
                continue
            nblocks += 3
            for name, blk in (("prefers-color-scheme", dm), ("[data-theme=dark]", da)):
                miss = sorted(set(la) - set(blk))
                if miss:
                    fails.append(f"{app} dark block {name} misses {miss}")
            if dm != da:
                fails.append(f"{app}: the two dark accent blocks differ")
            lt.update(la)
            dk.update(dm)
        themes[(app, "light")] = lt
        themes[(app, "dark")] = dk
    results = []
    for (app, theme), toks in sorted(themes.items()):
        for fg, bg in PAIRS:
            a, b = hex_rgb(toks.get("--c-" + fg, "")), hex_rgb(toks.get("--c-" + bg, ""))
            if a is None or b is None:
                fails.append(f"{app}/{theme}: --c-{fg} or --c-{bg} is not a #rrggbb colour")
                continue
            r = contrast(a, b)
            results.append((r, app, theme, fg, bg))
            if r < MIN_CONTRAST:
                fails.append(f"{app}/{theme}: {fg} on {bg} = {r:.2f} < {MIN_CONTRAST}")
    return fails, results, ntok, nblocks, notes


# ---------------------------------------------------------------- Lighthouse

class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def lighthouse(root, paths):
    handler = functools.partial(QuietHandler, directory=root)
    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    rows = []
    try:
        for p in paths:
            url = f"http://127.0.0.1:{port}{p}"
            cmd = LIGHTHOUSE + [url, "--quiet", "--output=json", "--output-path=stdout",
                                "--only-categories=performance,accessibility,seo,best-practices",
                                "--chrome-flags=--headless=new --no-sandbox"]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
            if r.returncode != 0 or not r.stdout.strip().startswith("{"):
                return None, f"lighthouse failed on {p}: {r.stderr.strip()[-300:]}"
            j = json.loads(r.stdout)
            au, cat = j["audits"], j["categories"]
            rows.append({"path": p,
                         "lcp_ms": au["largest-contentful-paint"]["numericValue"],
                         "cls": au["cumulative-layout-shift"]["numericValue"],
                         "bytes": au["total-byte-weight"]["numericValue"],
                         "perf": cat["performance"]["score"], "a11y": cat["accessibility"]["score"],
                         "seo": cat["seo"]["score"], "bp": cat["best-practices"]["score"],
                         "a11y_fail": [k for k, v in au.items() if v.get("score") == 0
                                       and k in {a["id"] for a in cat["accessibility"]["auditRefs"]}]})
    finally:
        srv.shutdown()
    return rows, None


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--no-lighthouse", action="store_true")
    args = ap.parse_args()
    root = args.root
    files = list(walk(root))
    html_files = [f for f in files if f.endswith(".html")]
    ok_all = True

    def report(name, fails, ok_line):
        nonlocal ok_all
        if fails:
            ok_all = False
            print(f"{name}_FAIL n={len(fails)}")
            for f in fails[:40]:
                print("  -", f)
        else:
            print(ok_line)

    pages = {}
    for rel in html_files:
        p = Page(rel)
        with open(os.path.join(root, rel), encoding="utf-8") as fh:
            p.feed(fh.read())
        p.close()
        pages[rel] = p

    # pending paths owned by later chunks
    pending = {}
    pend_file = os.path.join(root, "tools", "pending_links.txt")
    if os.path.exists(pend_file):
        for line in open(pend_file, encoding="utf-8"):
            line = line.split("#", 1)[0].strip()
            if line:
                path, owner = line.split()[:2]
                pending[path] = owner

    # ---- links
    fails, n_int, n_ext, pend_used = [], 0, 0, set()
    for path in pending:
        rel = path.lstrip("/") + ("index.html" if path.endswith("/") else "")
        if os.path.exists(os.path.join(root, rel)):
            fails.append(f"pending path {path} now exists: remove it from tools/pending_links.txt")
    for rel, p in pages.items():
        for kind, href in p.links:
            r = resolve(root, rel, href)
            if r is None:
                n_ext += 1
                mail_ok = href.lower().startswith(MAILTO) and href[len(MAILTO):].split("?")[0] == CONTACT_EMAIL
                if not (href.startswith(("https://", "http://")) or mail_ok):  # where: SITE_NOEMAIL
                    fails.append(f"{rel}: unsupported link scheme {href}")
                continue
            n_int += 1
            target, frag, path = r
            if path in pending:
                pend_used.add(path)
                continue
            if not os.path.isfile(os.path.join(root, target)):
                fails.append(f"{rel}: broken {kind} {href}")
                continue
            if frag and target.endswith(".html") and target in pages and frag not in pages[target].ids:
                fails.append(f"{rel}: {href} — no id '{frag}' in {target}")
            if kind == "href" and target.endswith(".html") and not href.split("#")[0].endswith("/") and href.split("#")[0]:
                fails.append(f"{rel}: {href} — link to a page must end in '/' (rule R2)")
    report("SITE_LINKS", fails, f"SITE_LINKS_OK n={n_int} pending={len(pend_used)} external={n_ext}")
    if pend_used:
        print("  pending (owned by later chunks): " + ", ".join(f"{k} [{pending[k]}]" for k in sorted(pend_used)))

    # ---- no email anywhere, except the privacy policies' contact sections
    fails, nfiles, nallowed = [], 0, 0
    for rel in walk(root, SKIP_DIRS - {"tools"}):
        if os.path.splitext(rel)[1] not in TEXT_EXT:
            continue
        nfiles += 1
        txt = open(os.path.join(root, rel), encoding="utf-8", errors="replace").read()
        if rel.replace(os.sep, "/") in EMAIL_PAGES:
            reg = email_region(txt)
            if not reg:
                fails.append(f"{rel}: no 'Contact and deletion requests' section after id=policy")
            else:
                inner = txt[reg[0]:reg[1]]
                found = EMAIL_RE.findall(inner)
                if not found:
                    fails.append(f"{rel}: contact section does not show {CONTACT_EMAIL}")
                for e in found:
                    if e != CONTACT_EMAIL:
                        fails.append(f"{rel}: contact section has {e}, only {CONTACT_EMAIL} is allowed")
                for mm in re.finditer(re.escape(MAILTO) + r"([^\"'?>\s]*)", inner, re.I):
                    if mm.group(1) != CONTACT_EMAIL:
                        fails.append(f"{rel}: contact section {MAILTO} to {mm.group(1)!r}")
                nallowed += len(found)
                txt = txt[:reg[0]] + txt[reg[1]:]
        if MAILTO in txt.lower():
            fails.append(f"{rel}: contains {MAILTO}")
        for m in EMAIL_RE.finditer(txt):
            fails.append(f"{rel}: email-like string {m.group(0)}")
    report("SITE_NOEMAIL", fails, f"SITE_NOEMAIL_OK files={nfiles} allowed={nallowed}")

    # ---- meta
    fails, titles, descs = [], {}, {}
    for rel, p in pages.items():
        own = HOST + url_path(rel)
        if p.lang != "en":
            fails.append(f"{rel}: <html lang> is {p.lang!r}")
        if not p.title.strip():
            fails.append(f"{rel}: empty <title>")
        titles.setdefault(p.title.strip(), []).append(rel)
        for key in ("viewport", "description", "og:type", "og:title", "og:description", "og:url", "og:image", "twitter:card"):
            if not p.meta.get(key):
                fails.append(f"{rel}: missing meta {key}")
        descs.setdefault(p.meta.get("description", ""), []).append(rel)
        if p.canonical != own:
            fails.append(f"{rel}: canonical {p.canonical} != {own}")
        if p.meta.get("og:url") != own:
            fails.append(f"{rel}: og:url {p.meta.get('og:url')} != {own}")
        img = p.meta.get("og:image", "")
        r = resolve(root, rel, img) if img else None
        if not img.startswith(HOST) or not r or not os.path.isfile(os.path.join(root, r[0])):
            fails.append(f"{rel}: og:image {img} is not a file on this site")
        if len(p.meta.get("description", "")) > 170:
            fails.append(f"{rel}: description longer than 170 chars")
    for t, rels in titles.items():
        if len(rels) > 1:
            fails.append(f"duplicate <title> {t!r}: {rels}")
    for d, rels in descs.items():
        if len(rels) > 1:
            fails.append(f"duplicate description: {rels}")
    report("SITE_META", fails, f"SITE_META_OK pages={len(pages)}")

    # ---- accessibility (static)
    fails = []
    css = open(os.path.join(root, "assets", "site.css"), encoding="utf-8").read()
    for needle in (":focus-visible", "prefers-reduced-motion: reduce", ".skip-link:focus"):
        if needle not in css:
            fails.append(f"site.css lacks {needle}")
    for rel, p in pages.items():
        fails += p.errors
        if p.h.count(1) != 1:
            fails.append(f"{rel}: {p.h.count(1)} <h1>")
        prev = 0
        for lv in p.h:
            if lv > prev + 1:
                fails.append(f"{rel}: heading jumps from h{prev} to h{lv}")
                break
            prev = lv
        for t in ("header", "main", "footer", "nav"):
            if t not in p.tags:
                fails.append(f"{rel}: no <{t}> landmark")
        if "main" not in p.ids:
            fails.append(f"{rel}: no id=main")
        if not any(a.get("href") == "#main" and "skip-link" in a.get("class", "") for a, _ in p.anchors):
            fails.append(f"{rel}: no skip link to #main")
        dup = sorted({i for i in p.ids if p.ids.count(i) > 1})
        if dup:
            fails.append(f"{rel}: duplicate ids {dup}")
        for kind, ref in p.labelledby:
            if ref not in p.ids:
                fails.append(f"{rel}: {kind} -> missing id {ref}")
        for a in p.imgs:
            for att in ("alt", "width", "height"):
                if att not in a:
                    fails.append(f"{rel}: <img src={a.get('src')}> lacks {att}")
            if a.get("alt", "x") == "" and "aria-hidden" not in a and a.get("role") != "presentation":
                pass  # empty alt = decorative, allowed
        for a, text in p.buttons:
            if not (text.strip() or a.get("aria-label")):
                fails.append(f"{rel}: button without an accessible name")
        for a, text in p.anchors:
            if not (text.strip() or a.get("aria-label")):
                fails.append(f"{rel}: link {a.get('href')} without text")
    report("SITE_A11Y", fails, f"SITE_A11Y_OK pages={len(pages)}")

    # ---- theme tokens + contrast
    tfails, results, ntok, nblocks, _ = check_theme(css)
    theme_fails = [f for f in tfails if " < " not in f]
    report("SITE_THEME", theme_fails, f"SITE_THEME_OK tokens={ntok} blocks={nblocks}")
    cfails = [f for f in tfails if " < " in f]
    if results:
        worst = min(results)
        report("SITE_CONTRAST", cfails,
               f"SITE_CONTRAST_OK pairs={len(results)} min={worst[0]:.2f} ({worst[1]}/{worst[2]} {worst[3]} on {worst[4]})")
    else:
        report("SITE_CONTRAST", ["no pairs computed"], "")

    # ---- JSON-LD
    fails, nodes = [], 0
    for rel, p in pages.items():
        if not p.jsonld:
            fails.append(f"{rel}: no JSON-LD")
        for raw in p.jsonld:
            try:
                j = json.loads(raw)
            except ValueError as e:
                fails.append(f"{rel}: JSON-LD does not parse: {e}")
                continue
            graph = j.get("@graph", [j])
            nodes += len(graph)
            types = [g.get("@type") for g in graph]
            if "Organization" not in types:
                fails.append(f"{rel}: no Organization node")
            if url_path(rel) != "/" and not rel.startswith("404") and "BreadcrumbList" not in types:
                fails.append(f"{rel}: interior page without BreadcrumbList")

            def scan(o, path="$"):
                if isinstance(o, dict):
                    for k, v in o.items():
                        if k.lower() == "email":
                            fails.append(f"{rel}: JSON-LD has an email field at {path}.{k}")
                        scan(v, f"{path}.{k}")
                elif isinstance(o, list):
                    for i, v in enumerate(o):
                        scan(v, f"{path}[{i}]")
                elif isinstance(o, str) and o.startswith(HOST):
                    r = resolve(root, rel, o)
                    if r and r[2] not in pending and not os.path.isfile(os.path.join(root, r[0])):
                        fails.append(f"{rel}: JSON-LD url {o} does not resolve")
            scan(j)
    report("SITE_JSONLD", fails, f"SITE_JSONLD_OK nodes={nodes}")

    # ---- sitemap / robots / llms
    fails = []
    sm = open(os.path.join(root, "sitemap.xml"), encoding="utf-8").read()
    locs = re.findall(r"<loc>([^<]+)</loc>", sm)
    indexable = {HOST + url_path(r) for r, p in pages.items() if "noindex" not in p.meta.get("robots", "")}
    for loc in locs:
        r = resolve(root, "index.html", loc)
        if not r or not os.path.isfile(os.path.join(root, r[0])):
            fails.append(f"sitemap: {loc} is not a page")
    for u in sorted(indexable - set(locs)):
        fails.append(f"sitemap misses {u}")
    if len(re.findall(r"<lastmod>\d{4}-\d{2}-\d{2}</lastmod>", sm)) != len(locs):
        fails.append("sitemap: every <url> needs an ISO <lastmod>")
    robots = open(os.path.join(root, "robots.txt"), encoding="utf-8").read()
    if f"Sitemap: {HOST}/sitemap.xml" not in robots:
        fails.append("robots.txt lacks the Sitemap line")
    llms = open(os.path.join(root, "llms.txt"), encoding="utf-8").read()
    llms_urls = re.findall(re.escape(HOST) + r"[^\s)]*", llms)
    for u in llms_urls:
        r = resolve(root, "index.html", u)
        if r and r[2] not in pending and not os.path.isfile(os.path.join(root, r[0])):
            fails.append(f"llms.txt: {u} does not resolve")
    report("SITE_DISCOVERY", fails, f"SITE_DISCOVERY_OK sitemap={len(locs)} llms_urls={len(llms_urls)}")

    # ---- budgets (static bytes) + Lighthouse
    fails = []
    size = lambda rel: os.path.getsize(os.path.join(root, rel))
    css_kb = size("assets/site.css") / 1024
    js_kb = size("assets/site.js") / 1024
    if css_kb > BUDGET["css_kb"]:
        fails.append(f"site.css {css_kb:.1f} KB > {BUDGET['css_kb']}")
    if js_kb > BUDGET["js_kb"]:
        fails.append(f"site.js {js_kb:.1f} KB > {BUDGET['js_kb']}")
    max_page, max_html = 0.0, 0.0
    for rel, p in pages.items():
        h = size(rel) / 1024
        max_html = max(max_html, h)
        if h > BUDGET["html_kb"]:
            fails.append(f"{rel}: HTML {h:.1f} KB > {BUDGET['html_kb']}")
        total, atf, lazy_kb = h, 0.0, 0.0
        first_view_only = True  # spec 0069 §5.5 budgets are "on first view" for every page
        for kind, href in set(p.links):
            r = resolve(root, rel, href)
            if not r or not os.path.isfile(os.path.join(root, r[0])) or kind == "href":
                continue
            if first_view_only and href in p.lazy_links:
                # spec 0069 §5.5 "whole page ≤ 600 KB on first view" (examples: "≤ 2.5 MB
                # with lazy-loaded cards"): loading="lazy" images and their srcset
                # alternatives are not first-view weight; reported, not budgeted.
                # Lighthouse's transferred bytes (below) gate what a visit really fetches.
                lazy_kb += size(r[0]) / 1024
                continue
            if kind == "link" and not href.endswith((".css",)):
                continue  # canonical/icon links are not page weight (icon counted by browser lazily)
            kb = size(r[0]) / 1024
            total += kb
        for a in p.imgs:
            r = resolve(root, rel, a.get("src", ""))
            if r and os.path.isfile(os.path.join(root, r[0])) and a.get("loading") != "lazy":
                atf += size(r[0]) / 1024
        if atf > BUDGET["atf_img_kb"]:
            fails.append(f"{rel}: eager images {atf:.1f} KB > {BUDGET['atf_img_kb']}")
        page_kb = PAGE_KB_OVERRIDE.get(rel, BUDGET["page_kb"])
        if lazy_kb:
            print(f"  {rel}: first view {total:.1f} KB (budget {page_kb}); lazy candidates "
                  f"{lazy_kb:.1f} KB not counted (all srcset alternatives, never all fetched)")
        if total > page_kb:
            fails.append(f"{rel}: page {total:.1f} KB > {page_kb}")
        max_page = max(max_page, total)
    print(f"  static bytes: css={css_kb:.1f}KB js={js_kb:.1f}KB html_max={max_html:.1f}KB page_max={max_page:.1f}KB (first view: eager sources all counted, lazy images excluded)")
    if args.no_lighthouse:
        if fails:
            report("SITE_BUDGET", fails, "")
        print("SITE_BUDGET_SKIPPED reason=--no-lighthouse")
    else:
        paths = sorted(url_path(r) for r in pages)
        rows, err = lighthouse(root, paths)
        if err:
            fails.append(err)
            report("SITE_BUDGET", fails, "")
            print("SITE_BUDGET_SKIPPED reason=lighthouse-error")
        else:
            for r in rows:
                print(f"  lighthouse {r['path']:<16} lcp={r['lcp_ms']:.0f}ms cls={r['cls']:.3f} "
                      f"bytes={r['bytes']/1024:.1f}KB perf={r['perf']:.2f} a11y={r['a11y']:.2f} "
                      f"seo={r['seo']:.2f} bp={r['bp']:.2f}" + (f" a11y_fail={r['a11y_fail']}" if r['a11y_fail'] else ""))
                if r["lcp_ms"] > BUDGET["lcp_ms"]:
                    fails.append(f"{r['path']}: LCP {r['lcp_ms']:.0f} ms > {BUDGET['lcp_ms']}")
                if r["cls"] > BUDGET["cls"]:
                    fails.append(f"{r['path']}: CLS {r['cls']:.3f} > {BUDGET['cls']}")
                if r["a11y"] < BUDGET["a11y"]:
                    fails.append(f"{r['path']}: Lighthouse accessibility {r['a11y']:.2f} < {BUDGET['a11y']}")
                page_kb = PAGE_KB_OVERRIDE.get(r["path"].lstrip("/") + "index.html", BUDGET["page_kb"])
                if r["bytes"] / 1024 > page_kb:
                    fails.append(f"{r['path']}: transferred {r['bytes']/1024:.1f} KB > {page_kb}")
            report("SITE_BUDGET", fails,
                   f"SITE_BUDGET_OK pages={len(rows)} max_kb={max(r['bytes'] for r in rows)/1024:.1f} "
                   f"lcp_ms={max(r['lcp_ms'] for r in rows):.0f} cls={max(r['cls'] for r in rows):.3f} "
                   f"a11y_min={min(r['a11y'] for r in rows):.2f}")

    print("SITE_CHECK_OK" if ok_all else "SITE_CHECK_FAIL")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
