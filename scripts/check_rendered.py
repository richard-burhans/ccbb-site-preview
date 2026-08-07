#!/usr/bin/env python3
"""Check the built site for two failures html-proofer cannot see.

Both of these happened, both looked fine to every other check, and both are the
same shape as everything else this repo guards against: the build is green and
the page is wrong.

  1. Links with no text. Six pages carry only `short_title` -- a convention from
     the old theme -- and no `title`, so a template reading .Title produced
     <a href="..."></a>. The link is present, valid, and invisible. The WEMSA
     workshop editions vanished from the site this way while html-proofer
     reported every link as fine, because the href resolved.

  2. Internal links missing the site's base path. When the site is served from a
     subdirectory, an href of "/seminar/" points at the server root rather than
     the site root. html-proofer resolves it against the output directory, where
     it exists, so it passes -- and 404s in a browser.

Usage: python3 scripts/check_rendered.py <build-dir> [--base-path /prefix]
"""

import argparse
import os
import re
import sys
from html.parser import HTMLParser


class Anchors(HTMLParser):
    """Collect (href, text) for every <a> in a document."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self._href = None
        self._text = []
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            if self._href is not None:      # nested <a> is invalid; take the outer
                return
            self._href = dict(attrs).get("href", "")
            self._text = []
            self._depth = 1
        elif self._href is not None:
            # An image or icon inside a link counts as its content.
            if tag in ("img", "svg", "use"):
                self._text.append("•")

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.links.append((self._href, "".join(self._text).strip()))
            self._href, self._text = None, []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("build")
    ap.add_argument("--base-path", default="",
                    help="e.g. /ccbb-site-preview when served from a subdirectory")
    args = ap.parse_args()
    base = args.base_path.rstrip("/")

    empty, unprefixed = [], []
    pages = 0

    for dirpath, _, files in os.walk(args.build):
        for fn in files:
            if not fn.endswith(".html"):
                continue
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, args.build)
            pages += 1
            p = Anchors()
            p.feed(open(path, encoding="utf-8").read())
            for href, text in p.links:
                if not text and href and not href.startswith("#"):
                    empty.append((rel, href))
                if base and href.startswith("/") and not href.startswith(base + "/") \
                        and href != base:
                    unprefixed.append((rel, href))

    problems = 0

    if empty:
        problems += len(empty)
        print(f"{len(empty)} link(s) with no text -- present, valid, and invisible:\n")
        for rel, href in sorted(set(empty))[:20]:
            print(f"  - {rel}: <a href=\"{href}\"></a>")
        print("\n  Usually a page with `short_title` but no `title`, so .Title is empty.\n")

    if unprefixed:
        problems += len(unprefixed)
        print(f"{len(unprefixed)} internal link(s) missing the base path '{base}':\n")
        for rel, href in sorted(set(unprefixed))[:20]:
            print(f"  - {rel}: {href}")
        print("\n  These resolve on disk, so html-proofer passes, but 404 in a browser.\n")

    if problems:
        print("Nothing was deployed.")
        return 1

    print(f"Rendered output is sound: {pages} pages, every link has text"
          + (f" and carries '{base}'" if base else "") + ".")
    return 0


if __name__ == "__main__":
    sys.exit(main())
