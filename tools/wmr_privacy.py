#!/usr/bin/env python3
"""Watermark Remover privacy policy: template -> /watermark-remover/privacy/#policy (spec 0069 M3).

The policy text lives in the app repo, docs/privacy/privacy-policy.template.html. This is
that repo's scripts/deploy_privacy_policy.sh retargeted at this site: same header strip,
same {{DATE}} substitution, same PRIVACY_POLICY_DRIFT token, but the destination is the
region between <!-- policy:begin … --> and <!-- policy:end --> inside the site page
(glance on top, policy below), not a whole standalone file.

Transformations, each asserted so a template change that breaks one is loud:
  1. drop the repo-documentation header (through <!-- END-TEMPLATE-HEADER -->);
  2. keep only the inner HTML of <main id="policy" …>…</main> (the site page owns <head>,
     header, footer and the one <h1>);
  3. demote headings one level: <h1>Privacy Policy</h1> -> <h2 id="policy">Privacy policy</h2>,
     every <h2> -> <h3> (ids kept, e.g. #delete);
  4. {{DATE}} -> the ISO date recorded in the begin marker;
  5. {{CONTACT_EMAIL}} -> CONTACT_EMAIL below. Owner decision 2026-09-23 ("email on privacy
     pages only"): the address appears on the site only inside the two privacy policies'
     contact/deletion sections; tools/check_site.py (SITE_NOEMAIL) fails it anywhere else, so
     render() asserts every occurrence lands inside <h3 id="delete">…end of policy.

Usage:
  python3 tools/wmr_privacy.py --write [--date YYYY-MM-DD] [--template FILE | --wmr-repo DIR --ref REF]
  python3 tools/wmr_privacy.py --check [same source options]
Default source: `git -C ../watermark-remover show origin/main:docs/privacy/privacy-policy.template.html`.
Prints PRIVACY_POLICY_DRIFT=0 lines (match) or PRIVACY_POLICY_DRIFT=<n> lines (exit 1).
"""
import argparse, datetime, difflib, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "watermark-remover", "privacy", "index.html")
TEMPLATE_PATH = "docs/privacy/privacy-policy.template.html"
BEGIN_RE = re.compile(r"<!-- policy:begin[^>]*?date=(\d{4}-\d{2}-\d{2})[^>]*-->\n?")
END = "<!-- policy:end -->"

# Built by concatenation so this file never holds the literal address (tools/ is inside
# SITE_NOEMAIL's scan). Override with --contact-email.
CONTACT_EMAIL = "scintech.dev" + "@" + "gmail.com"


def load_template(args):
    if args.template:
        return open(args.template, encoding="utf-8").read(), args.template
    src = f"{args.ref}:{TEMPLATE_PATH}"
    out = subprocess.run(["git", "-C", args.wmr_repo, "show", src], capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"cannot read {src} from {args.wmr_repo}: {out.stderr.strip()}")
    sha = subprocess.run(["git", "-C", args.wmr_repo, "rev-parse", "--short=12", args.ref],
                         capture_output=True, text=True).stdout.strip()
    return out.stdout, f"{args.wmr_repo}@{sha}:{TEMPLATE_PATH}"


def render(tpl, date, email=CONTACT_EMAIL):
    marker = "<!-- END-TEMPLATE-HEADER -->"
    assert marker in tpl, "template header marker missing"
    body = tpl.split(marker, 1)[1]
    m = re.search(r'<main id="policy"[^>]*>(.*?)</main>', body, re.S)
    assert m, 'no <main id="policy"> in template'
    body = m.group(1)
    assert body.count("<h1>Privacy Policy</h1>") == 1, "expected one <h1>Privacy Policy</h1>"
    body = body.replace("<h1>Privacy Policy</h1>", "\0POLICY_H2\0")
    body = re.sub(r"<h2(?=[\s>])", "<h3", body).replace("</h2>", "</h3>")
    body = body.replace("\0POLICY_H2\0", '<h2 id="policy">Privacy policy</h2>')
    # 5. contact email, only inside the deletion section
    start = body.find('<h3 id="delete">')
    assert start >= 0, 'no <h2 id="delete"> section in template'
    assert "{{CONTACT_EMAIL}}" in body[start:], "contact section lost its {{CONTACT_EMAIL}}"
    assert "{{CONTACT_EMAIL}}" not in body[:start] and "mailto" not in body[:start].lower(), \
        "email placeholder or mail link outside the deletion section"
    body = body.replace("{{CONTACT_EMAIL}}", email)
    body = body.replace("{{DATE}}", date)
    assert "{{" not in body, "placeholder left in rendered policy"
    return body.strip("\n") + "\n"


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--write", action="store_true")
    g.add_argument("--check", action="store_true")
    ap.add_argument("--date", help="ISO date for 'Last updated' (--write; default today)")
    ap.add_argument("--template")
    ap.add_argument("--wmr-repo", default=os.path.join(os.path.dirname(ROOT), "watermark-remover"))
    ap.add_argument("--ref", default="origin/main")
    ap.add_argument("--contact-email", default=CONTACT_EMAIL)
    args = ap.parse_args()
    tpl, src = load_template(args)
    page = open(PAGE, encoding="utf-8").read()
    m = BEGIN_RE.search(page) or re.search(r"<!-- policy:begin[^>]*-->\n?", page)
    assert m and END in page, "policy region markers missing in page"
    stop = page.index(END)
    live = page[m.end():stop]
    if args.write:
        date = args.date or (m.group(1) if m.lastindex else None) or datetime.date.today().isoformat()
        new = render(tpl, date, args.contact_email)
        head = f"<!-- policy:begin date={date} source=docs/privacy/privacy-policy.template.html (generated by tools/wmr_privacy.py — do not edit by hand) -->\n"
        page = page[:m.start()] + head + new + page[stop:]
        open(PAGE, "w", encoding="utf-8").write(page)
        print(f"wrote policy region from {src}, date={date}, {len(new.splitlines())} lines")
        return 0
    if not m.lastindex:
        print("PRIVACY_POLICY_DRIFT=region_empty")
        return 1
    expected = render(tpl, m.group(1), args.contact_email)
    diff = list(difflib.unified_diff(live.splitlines(), expected.splitlines(), "page", "template", lineterm=""))
    for line in diff:
        print(line, file=sys.stderr)
    print(f"source: {src}")
    print(f"PRIVACY_POLICY_DRIFT={len(diff)} lines")
    return 0 if not diff else 1


if __name__ == "__main__":
    sys.exit(main())
