#!/usr/bin/env python3
"""
LuckNooz generator — runs on a schedule (e.g. GitHub Actions), writes lucknooz.json.

Pipeline:
  1. Fetch real headlines from RSS feeds.
  2. Parse + remix via the determinative core (lucknooz.py).
  3. Write a JSON file the static page reads. No NLP runs in the browser.

If feeds are unreachable, falls back to corpus.py so the build never produces
an empty file.
"""

import json
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from lucknooz import find_split, remix

FEEDS = [
    "https://feeds.bbci.co.uk/news/world/rss.xml",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "https://feeds.npr.org/1001/rss.xml",
    "https://www.theguardian.com/world/rss",
]

OUTPUT = "lucknooz.json"
MAX_OUTPUT = 24          # headlines to publish
USER_AGENT = "LuckNooz/1.0 (+https://luckism.org)"


def fetch_titles(url, timeout=15):
    """Fetch one RSS feed and return a list of item titles."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    root = ET.fromstring(raw)
    titles = []
    # RSS 2.0: channel/item/title ; also handle Atom entry/title
    for item in root.iter():
        tag = item.tag.split("}")[-1]
        if tag in ("item", "entry"):
            for child in item:
                if child.tag.split("}")[-1] == "title" and child.text:
                    titles.append(child.text.strip())
                    break
    return titles


def gather_headlines():
    """Pull from all feeds; fall back to the test corpus if none respond."""
    titles = []
    for url in FEEDS:
        try:
            got = fetch_titles(url)
            print(f"  {len(got):3d} from {url}", file=sys.stderr)
            titles.extend(got)
        except Exception as e:
            print(f"  ERR  {url}: {e}", file=sys.stderr)
    if not titles:
        print("  no live feeds reachable -> falling back to corpus", file=sys.stderr)
        from corpus import CORPUS
        titles = [h for h, _ in CORPUS]
    return titles


def clean(title):
    """Light normalization: collapse whitespace, drop obvious source suffixes."""
    t = " ".join(title.split())
    # strip trailing " - BBC News" style source tags
    for sep in (" - ", " | "):
        if sep in t:
            head, _, tail = t.rpartition(sep)
            if len(tail) <= 20:  # looks like a source tag, not content
                t = head
    return t.strip()


def main():
    titles = [clean(t) for t in gather_headlines()]
    # dedupe, keep order
    seen = set()
    titles = [t for t in titles if t and not (t in seen or seen.add(t))]

    parsed = [p for p in (find_split(t) for t in titles) if p]
    remixed = remix(parsed, n=MAX_OUTPUT)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_count": len(titles),
        "parsed_count": len(parsed),
        "headlines": remixed,
    }
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"wrote {OUTPUT}: {len(remixed)} headlines "
          f"from {len(titles)} sources ({len(parsed)} parsed)", file=sys.stderr)


if __name__ == "__main__":
    main()
