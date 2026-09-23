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
  5. the section from <h2 id="delete"> through the deletion-steps </ol>, i.e. the
     paragraph and steps that say "Email {{CONTACT_EMAIL}}", is replaced by NO_EMAIL_CONTACT
     below — owner decision 2026-09-23: no email anywhere on the site; the in-app feedback
     button is the channel. The template itself still carries {{CONTACT_EMAIL}}; the app repo
     should adopt the same wording (see docs/wmr-claims.md, TO-VERIFY row "deletion channel").

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

NO_EMAIL_CONTACT = """<h3 id="delete">Contact and deletion requests</h3>
    <p>Privacy questions and requests concerning submitted data go through the app: tap the
    feedback button in the corner of the screen, or open Settings → Send feedback. This site and
    the app publish no email address.</p>
    <p>To have the data Watermark Remover collected about you deleted:</p>
    <ol>
      <li>Send feedback from the app with the words "Watermark Remover data deletion".</li>
      <li>Nothing else is needed: the request carries the same Android ID as your earlier
      reports, so they can be matched without an account. If the app is no longer installed,
      install it again to send the request.</li>
    </ol>"""


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


def render(tpl, date):
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
    # 5. contact section without email
    start = body.find('<h3 id="delete">')
    assert start >= 0, 'no <h2 id="delete"> section in template'
    end_list = body.find("</ol>", start)
    assert end_list >= 0, "deletion steps list missing"
    old = body[start:end_list + len("</ol>")]
    assert "{{CONTACT_EMAIL}}" in old and old.count("<li>") == 2, "contact section changed shape; review NO_EMAIL_CONTACT"
    body = body[:start] + NO_EMAIL_CONTACT + body[end_list + len("</ol>"):]
    body = body.replace("{{DATE}}", date)
    assert "{{" not in body and "mailto" not in body.lower(), "placeholder or mail link left in rendered policy"
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
    args = ap.parse_args()
    tpl, src = load_template(args)
    page = open(PAGE, encoding="utf-8").read()
    m = BEGIN_RE.search(page) or re.search(r"<!-- policy:begin[^>]*-->\n?", page)
    assert m and END in page, "policy region markers missing in page"
    stop = page.index(END)
    live = page[m.end():stop]
    if args.write:
        date = args.date or (m.group(1) if m.lastindex else None) or datetime.date.today().isoformat()
        new = render(tpl, date)
        head = f"<!-- policy:begin date={date} source=docs/privacy/privacy-policy.template.html (generated by tools/wmr_privacy.py — do not edit by hand) -->\n"
        page = page[:m.start()] + head + new + page[stop:]
        open(PAGE, "w", encoding="utf-8").write(page)
        print(f"wrote policy region from {src}, date={date}, {len(new.splitlines())} lines")
        return 0
    if not m.lastindex:
        print("PRIVACY_POLICY_DRIFT=region_empty")
        return 1
    expected = render(tpl, m.group(1))
    diff = list(difflib.unified_diff(live.splitlines(), expected.splitlines(), "page", "template", lineterm=""))
    for line in diff:
        print(line, file=sys.stderr)
    print(f"source: {src}")
    print(f"PRIVACY_POLICY_DRIFT={len(diff)} lines")
    return 0 if not diff else 1


if __name__ == "__main__":
    sys.exit(main())
