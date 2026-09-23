#!/usr/bin/env python3
"""Redirect-shell checker for the two retired sites (spec 0069 §7 M4, chunk S6). Stdlib + node.

The old hosts keep serving, forever (M7), a <=1 KB shell per old page:
  <link rel=canonical href=NEW> + <meta http-equiv=refresh content="0; url=NEW"> +
  <meta name=robots content=noindex> + <script>location.replace(BASE+(location.hash||FRAG))</script>
where NEW = BASE + FRAG is the mapped URL on scintech-dev.github.io.

Default (local) mode serves each old repo's working tree over http.server on 127.0.0.1 and
fetches every old path from it, then asserts for each mapping row:
  - HTTP 200, body <= 1024 bytes, noindex;
  - canonical, meta-refresh URL, JS target (no hash) and the visible link all equal NEW;
  - the JS, executed in node with a stubbed `location`, lands on NEW for no hash and on
    BASE#id for every id the OLD page had (read from git at OLD_REF, i.e. before the shells),
    and each such id exists in the new page: the fragment is preserved AND still means something;
  - NEW exists in the new site's local tree (--site-root), its fragment as an id there.
Also: every *.html in each old repo is covered by a row (no page left un-shelled); the Looper
404.html path-mapper lands known old paths on their mapped URL and unknown ones on the Looper
home; the old sitemap.xml lists only mapped new URLs that exist; robots.txt still points at
a sitemap; every scintech-dev URL in the old llms.txt exists.

--live instead fetches the real old URLs over HTTPS and checks each NEW returns 200 there
(the quarterly M7 run; before the old repos are pushed it reports their pre-cutover pages).

Token: SITE_REDIRECTS_OK n=<rows> hashes=<k> js=node|static   (else SITE_REDIRECTS_FAIL)
Exit code 1 on failure, but grep the token.

Usage: python3 tools/check_redirects.py [--site-root DIR] [--looper-dir DIR] [--wmr-dir DIR] [--live]
"""
import argparse, functools, http.server, json, os, re, shutil, socketserver, subprocess, sys, threading
import urllib.error, urllib.request
from html.parser import HTMLParser

NEW = "https://scintech-dev.github.io"
SITE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GH = os.path.dirname(SITE_ROOT)
LP = NEW + "/seamless-video-looper/"
WP = NEW + "/watermark-remover/privacy/"

# repo key -> (old public base, default local checkout, url prefix the repo is served under,
#              git ref of the last pre-shell content commit, for the old pages' ids)
REPOS = {
    "looper": ("https://seamlessvideolooper.github.io", os.path.join(GH, "seamlessvideolooper.github.io"), "/", "544df9d"),
    "wmr": ("https://di2g.github.io", os.path.join(GH, "watermark-remover-privacy"), "/watermark-remover-privacy/", "ed9c336"),
}
# (repo, old path under the old host, file in the old repo, mapped NEW url)
MAPPING = [
    ("looper", "/", "index.html", LP),
    ("looper", "/how-it-works/", "how-it-works/index.html", LP + "how-it-works/"),
    ("looper", "/examples/", "examples/index.html", LP + "examples/"),
    ("looper", "/compatibility/", "compatibility/index.html", LP + "compatibility/"),
    ("looper", "/privacy/", "privacy/index.html", LP + "privacy/"),
    ("looper", "/privacy/policy/", "privacy/policy/index.html", LP + "privacy/#policy"),
    ("looper", "/values/", "values/index.html", NEW + "/about/"),
    ("wmr", "/watermark-remover-privacy/", "index.html", WP),
    ("wmr", "/watermark-remover-privacy/privacy/", "privacy/index.html", WP),
]
# Looper 404.html: pathname -> expected landing (unknown paths land on the Looper home)
PATH_404 = [("/values", NEW + "/about/"), ("/privacy/policy/index.html", LP + "privacy/#policy"),
            ("/examples", LP + "examples/"), ("/no-such-page/", LP), ("/assets/gone.png", LP)]
MAX_BYTES = 1024


class Shell(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.canonical = self.refresh = self.robots = self.link = None
        self.script, self._in_script, self.ids = "", False, set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "link" and a.get("rel") == "canonical":
            self.canonical = a.get("href")
        elif tag == "meta" and (a.get("http-equiv") or "").lower() == "refresh":
            self.refresh = a.get("content")
        elif tag == "meta" and a.get("name") == "robots":
            self.robots = a.get("content")
        elif tag == "a" and self.link is None:
            self.link = a.get("href")
        elif tag == "script":
            self._in_script = True

    def handle_endtag(self, tag):
        if tag == "script":
            self._in_script = False

    def handle_data(self, data):
        if self._in_script:
            self.script += data


def parse(html):
    p = Shell()
    p.feed(html)
    p.close()
    return p


def refresh_url(content):
    m = re.fullmatch(r"\s*0\s*;\s*url=(.+)", content or "", re.I)
    return m.group(1).strip() if m else None


NODE = shutil.which("node")


def run_js(script, pathname, hash_):
    """Execute the shell's script with a stubbed location; return the replace() target."""
    if not NODE:
        return None
    prog = ("let out=null;const location={pathname:%s,hash:%s,replace:u=>{out=u}};%s\n"
            "process.stdout.write(JSON.stringify(out));") % (json.dumps(pathname), json.dumps(hash_), script)
    r = subprocess.run([NODE, "-e", prog], capture_output=True, text=True, timeout=20)
    if r.returncode != 0:
        return f"<node error: {r.stderr.strip()[-200:]}>"
    return json.loads(r.stdout)


def static_js(script, hash_):
    m = re.fullmatch(r'\s*location\.replace\("([^"]+)"\+\(location\.hash\|\|"([^"]*)"\)\)\s*', script)
    return (m.group(1) + (hash_ or m.group(2))) if m else None


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve(directory):
    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=directory))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def fetch(url):
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except OSError as e:
        return None, str(e).encode()


def new_page(site_root, url):
    """NEW url -> (file path in the site tree, fragment)."""
    assert url.startswith(NEW + "/"), url
    path, _, frag = url[len(NEW):].partition("#")
    rel = path.lstrip("/") + ("index.html" if path.endswith("/") else "")
    return os.path.join(site_root, rel), frag


def ids_of(path):
    return parse(open(path, encoding="utf-8").read()).ids if os.path.isfile(path) else set()


def old_ids(repo_dir, ref, rel):
    r = subprocess.run(["git", "-C", repo_dir, "show", f"{ref}:{rel}"], capture_output=True, text=True)
    return (parse(r.stdout).ids if r.returncode == 0 else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site-root", default=SITE_ROOT)
    ap.add_argument("--looper-dir", default=REPOS["looper"][1])
    ap.add_argument("--wmr-dir", default=REPOS["wmr"][1])
    ap.add_argument("--live", action="store_true")
    args = ap.parse_args()
    dirs = {"looper": args.looper_dir, "wmr": args.wmr_dir}
    fails, nhash = [], 0
    servers, base_of = {}, {}
    for key, (public, _, prefix, _) in REPOS.items():
        if not os.path.isdir(dirs[key]):
            fails.append(f"{key}: old repo checkout missing at {dirs[key]}")
            continue
        if args.live:
            base_of[key] = public
        else:
            servers[key] = serve(dirs[key])
            base_of[key] = f"http://127.0.0.1:{servers[key].server_address[1]}"
    try:
        # every old page covered by a row
        for key in dirs:
            if not os.path.isdir(dirs[key]):
                continue
            ls = subprocess.run(["git", "-C", dirs[key], "ls-files", "*.html"], capture_output=True, text=True).stdout.split()
            mapped = {f for k, _, f, _ in MAPPING if k == key} | ({"404.html"} if key == "looper" else set())
            for f in sorted(set(ls) - mapped):
                fails.append(f"{key}: {f} has no mapping row (page left un-shelled)")

        for key, old_path, rel, target in MAPPING:
            if key not in base_of:
                continue
            prefix = REPOS[key][2]
            url = base_of[key] + (old_path if args.live else "/" + old_path[len(prefix):])
            where = f"{REPOS[key][0]}{old_path}"
            status, body = fetch(url)
            if status != 200:
                fails.append(f"{where}: HTTP {status}")
                continue
            if len(body) > MAX_BYTES:
                fails.append(f"{where}: shell is {len(body)} bytes > {MAX_BYTES}")
            p = parse(body.decode("utf-8", "replace"))
            for name, got in (("canonical", p.canonical), ("meta refresh", refresh_url(p.refresh)), ("link", p.link)):
                if got != target:
                    fails.append(f"{where}: {name} = {got!r}, expected {target}")
            if (p.robots or "") != "noindex":
                fails.append(f"{where}: robots meta {p.robots!r}, expected noindex")
            base, _, frag = target.partition("#")
            # JS: no hash, then every id the old page had
            ids = old_ids(dirs[key], REPOS[key][3], rel)
            if ids is None:
                fails.append(f"{where}: cannot read {rel} at {REPOS[key][3]} for its ids")
                ids = set()
            new_file, _ = new_page(args.site_root, target)
            new_ids = ids_of(new_file)
            for h in [""] + sorted("#" + i for i in ids):
                want = base + (h or ("#" + frag if frag else ""))
                got = run_js(p.script, old_path, h) if NODE else static_js(p.script, h)
                if got != want:
                    fails.append(f"{where}{h}: JS lands on {got!r}, expected {want}")
                if h:
                    nhash += 1
                    if h[1:] not in new_ids:
                        fails.append(f"{where}{h}: id {h[1:]!r} missing in {os.path.relpath(new_file, args.site_root)}")
            # target exists in the new tree (and live, in --live)
            if not os.path.isfile(new_file):
                fails.append(f"{where}: target {target} has no file {new_file}")
            elif frag and frag not in new_ids:
                fails.append(f"{where}: target fragment #{frag} not an id in {new_file}")
            if args.live:
                st, _ = fetch(base)
                if st != 200:
                    fails.append(f"{target}: live HTTP {st}")
            print(f"  row {where:<58} -> {target}  ({len(body)} B, {len(ids)} ids)")

        # Looper 404 path mapper, sitemap, robots, llms
        if "looper" in base_of:
            lb = base_of["looper"]
            st, body = fetch(lb + "/404.html")
            if st != 200 or len(body) > MAX_BYTES:
                fails.append(f"looper 404.html: HTTP {st}, {len(body)} bytes")
            p = parse(body.decode("utf-8", "replace"))
            if refresh_url(p.refresh) != LP:
                fails.append(f"looper 404.html: meta refresh {p.refresh!r}, expected {LP}")
            if NODE:
                for path, want in PATH_404 + [(o, t) for k, o, _, t in MAPPING if k == "looper"]:
                    got = run_js(p.script, path, "")
                    if got != want:
                        fails.append(f"looper 404.html at {path}: lands on {got!r}, expected {want}")
                got = run_js(p.script, "/how-it-works/", "#find-the-loop-point")
                if got != LP + "how-it-works/#find-the-loop-point":
                    fails.append(f"looper 404.html: hash not preserved ({got!r})")
            st, sm = fetch(lb + "/sitemap.xml")
            locs = re.findall(r"<loc>([^<]+)</loc>", sm.decode("utf-8", "replace")) if st == 200 else []
            if not locs:
                fails.append(f"looper sitemap.xml: HTTP {st}, no <loc>")
            mapped_new = {t.split("#")[0] for k, _, _, t in MAPPING if k == "looper"}
            for loc in locs:
                if loc not in mapped_new or not os.path.isfile(new_page(args.site_root, loc)[0]):
                    fails.append(f"looper sitemap.xml: {loc} is not a mapped, existing new URL")
            st, rb = fetch(lb + "/robots.txt")
            if st != 200 or b"Sitemap: " + NEW.encode() + b"/sitemap.xml" not in rb:
                fails.append("looper robots.txt: missing the new site's Sitemap line")
            st, lt = fetch(lb + "/llms.txt")
            for u in re.findall(re.escape(NEW) + r"[^\s)]*", lt.decode("utf-8", "replace")):
                u = u.rstrip(".,")
                f, frag = new_page(args.site_root, u)
                if not os.path.isfile(f):
                    fails.append(f"looper llms.txt: {u} does not exist in the new tree")
                elif frag and frag not in ids_of(f):
                    fails.append(f"looper llms.txt: {u} fragment #{frag} missing")
            if b"@" in lt:
                fails.append("looper llms.txt: contains an @ (email?)")
    finally:
        for s in servers.values():
            s.shutdown()
    if fails:
        print(f"SITE_REDIRECTS_FAIL n={len(fails)}")
        for f in fails[:60]:
            print("  -", f)
        return 1
    print(f"SITE_REDIRECTS_OK n={len(MAPPING)} hashes={nhash} js={'node' if NODE else 'static'}"
          f" mode={'live' if args.live else 'local'} 404_paths={len(PATH_404)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
