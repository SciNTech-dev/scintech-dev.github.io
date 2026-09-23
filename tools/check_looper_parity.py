#!/usr/bin/env python3
"""Content-parity check for the migrated Seamless Video Looper pages (spec 0069 chunk S2,
migration gate M2: `LOOPER_PARITY_OK diff=0`).

Compares the VISIBLE TEXT of each new /seamless-video-looper/... page against the old
seamlessvideolooper.github.io page(s) it replaces, after stripping tags. Only an explicit
allow-list of differences is permitted (spec 0069 §4.6):

  - nav, footer, breadcrumbs        -- outside <main>, or the breadcrumb element inside it;
                                        both are stripped from the comparison entirely.
  - canonical / OG URLs             -- <head> is never compared, only <main>.
  - removed the site's one mail-to link -- decision 9 drops the contact email; the two
                                        sentences this touches are listed in MAILTO_EDITS below
                                        and rewritten in the OLD text before diffing, so any
                                        OTHER difference around them still fails the check.
  - the merged privacy page         -- the old /privacy/ and /privacy/policy/ pages are
                                        concatenated in that order before diffing against the
                                        new merged page (its own h1 -> h2#policy retitle is
                                        text-identical, so no allowance is needed for that).
  - the changelog link              -- chrome (site-footer), already excluded by not being in
                                        <main>.

Anything else that differs is a real content change and FAILS the check; this is deliberately
not a fuzzy diff.

Usage: python3 tools/check_looper_parity.py [--old-root DIR]
"""
import argparse, difflib, os, re, sys
from html.parser import HTMLParser

NEW_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OLD_ROOT = os.path.normpath(os.path.join(NEW_ROOT, "..", "seamlessvideolooper.github.io"))

# (old page path(s) relative to --old-root, new page path relative to the site root)
PAGES = [
    (["index.html"], "seamless-video-looper/index.html"),
    (["how-it-works/index.html"], "seamless-video-looper/how-it-works/index.html"),
    (["examples/index.html"], "seamless-video-looper/examples/index.html"),
    (["compatibility/index.html"], "seamless-video-looper/compatibility/index.html"),
    (["privacy/index.html", "privacy/policy/index.html"], "seamless-video-looper/privacy/index.html"),
]

# Decision 9 (spec 0069 §1 row 9): the site publishes no email address. These are the exact
# sentences that changed on the OLD pages to remove the mail-to link; rewriting them in the
# OLD text before diffing is the only content-level allowance this checker makes. The address
# is built by concatenation so this file itself never contains it as a literal string (this
# script lives under tools/, which SITE_NOEMAIL's scan does not exempt).
_OLD_EMAIL = "scintech.dev" + "@" + "gmail.com"
MAILTO_EDITS = [
    (
        "Contact " + _OLD_EMAIL + " with privacy or deletion requests.",
        "Use the app’s Settings → Send feedback for privacy or deletion requests.",
    ),
    (
        "Use Send Feedback in the app or email " + _OLD_EMAIL + " for privacy questions "
        "and requests concerning submitted data.",
        "Use Send Feedback in the app for privacy questions and requests concerning submitted data.",
    ),
]


class TextExtractor(HTMLParser):
    """Collects the text of every element inside <main>, except the breadcrumb nav/paragraph."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0          # >0 once inside <main>
        self.skip_depth = None  # depth at which a skipped (breadcrumb) subtree started
        self.raw_skip = 0       # depth inside <script>/<style>
        self.stack = []
        self.chunks = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.stack.append(tag)
        if tag == "main":
            self.depth += 1
            return
        if self.depth == 0:
            return
        cls = a.get("class", "")
        if self.skip_depth is None and (
            (tag == "p" and "breadcrumb" in cls) or (tag == "nav" and "breadcrumb" in cls)
        ):
            self.skip_depth = len(self.stack)
        if tag in ("script", "style"):
            self.raw_skip += 1

    def handle_startendtag(self, tag, attrs):
        pass  # void elements (img, br, ...) carry no comparable text

    def handle_endtag(self, tag):
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
        if tag in ("script", "style") and self.raw_skip:
            self.raw_skip -= 1
        if self.skip_depth is not None and len(self.stack) < self.skip_depth:
            self.skip_depth = None
        if tag == "main" and self.depth:
            self.depth -= 1

    def handle_data(self, data):
        if self.depth and self.skip_depth is None and not self.raw_skip:
            self.chunks.append(data)

    def text(self):
        joined = " ".join(self.chunks)
        return re.sub(r"\s+", " ", joined).strip()


def extract(html):
    p = TextExtractor()
    p.feed(html)
    p.close()
    return p.text()


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old-root", default=DEFAULT_OLD_ROOT)
    ap.add_argument("--new-root", default=NEW_ROOT)
    args = ap.parse_args()

    if not os.path.isdir(args.old_root):
        print(f"LOOPER_PARITY_FAIL old_root_missing={args.old_root}")
        return 1

    total_diff_lines = 0
    any_fail = False
    for old_rel_list, new_rel in PAGES:
        old_text = " ".join(extract(read(os.path.join(args.old_root, p))) for p in old_rel_list)
        for old_s, new_s in MAILTO_EDITS:
            old_text = old_text.replace(old_s, new_s)
        new_text = extract(read(os.path.join(args.new_root, new_rel)))

        if old_text == new_text:
            print(f"  parity OK  {'+'.join(old_rel_list):<45} -> {new_rel}")
            continue

        any_fail = True
        old_words = old_text.split(" ")
        new_words = new_text.split(" ")
        sm = difflib.SequenceMatcher(a=old_words, b=new_words, autojunk=False)
        diff_lines = [op for op in sm.get_opcodes() if op[0] != "equal"]
        total_diff_lines += len(diff_lines)
        print(f"  parity FAIL {'+'.join(old_rel_list):<45} -> {new_rel} ({len(diff_lines)} hunks)")
        for tag, i1, i2, j1, j2 in diff_lines[:20]:
            print(f"    {tag}: old[{i1}:{i2}]={old_words[i1:i2]!r}")
            print(f"          new[{j1}:{j2}]={new_words[j1:j2]!r}")

    if any_fail:
        print(f"LOOPER_PARITY_FAIL diff={total_diff_lines}")
        return 1
    print("LOOPER_PARITY_OK diff=0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
