#!/usr/bin/env python3
"""
Weekly refresh for the Choro Map.

What this does (and does NOT do): re-visits every confirmed entry in
data/rodas.json whose checkUrl is NOT social media, and notes whether the
page's text has changed since the last run (a cheap, free "did anything
move?" signal — it does not understand the page, it just hashes the
visible text).

Deliberately out of scope, on purpose:
  - Facebook/Instagram: not fetchable without login, and the whole point
    of this project was to avoid needing a social media account.
  - Anything disallowed by a site's robots.txt: skipped and logged, same
    as a well-behaved search crawler would do.
  - Guessing at exact dates/times: this script only flags "something on
    this page changed" — a human still decides what it means.

Run it locally with:  python3 scripts/refresh.py
It's meant to be run automatically by .github/workflows/refresh.yml
(GitHub Actions, on a weekly schedule, for free).
"""

import re
import sys
import time
import json
import hashlib
import datetime
import urllib.robotparser
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
RODAS_PATH = ROOT / "data" / "rodas.json"

USER_AGENT = (
    "ChoroMapBot/1.0 "
    "(personal, non-commercial travel tool; polite weekly check, "
    "respects robots.txt; not affiliated with any listed venue)"
)
REQUEST_TIMEOUT = 15
POLITE_DELAY_SECONDS = 2


def load_json(path, default):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def robots_allows(url):
    """Be a polite bot: check robots.txt before fetching. Fail open only
    if robots.txt itself can't be fetched (many small sites don't have one)."""
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = urllib.robotparser.RobotFileParser()
    try:
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(USER_AGENT, url)
    except Exception:
        return True  # no robots.txt reachable — assume allowed


def fetch_text(url):
    if not robots_allows(url):
        print(f"  skip (robots.txt disallows): {url}")
        return None
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"  fetch failed for {url}: {e}")
        return None


def normalized_text_hash(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = re.sub(r"\s+", " ", soup.get_text()).strip()
    return hashlib.sha256(text.encode("utf-8")).hexdigest(), text


def step_recheck_known_entries(rodas):
    print("\n== Re-checking known non-social entries for page changes ==")
    today = datetime.date.today().isoformat()
    for r in rodas:
        url = r.get("checkUrl")
        if not url or url.startswith("https://www.facebook.com") or "instagram.com" in url:
            continue
        print(f"- {r['name']} -> {url}")
        html = fetch_text(url)
        time.sleep(POLITE_DELAY_SECONDS)
        if html is None:
            continue
        new_hash, _ = normalized_text_hash(html)
        old_hash = r.get("contentHash")
        r["lastPolled"] = today
        if old_hash is not None and old_hash != new_hash:
            r["changedSinceLastCheck"] = True
            print("  -> page content changed since last check")
        r["contentHash"] = new_hash


def main():
    rodas = load_json(RODAS_PATH, [])

    if not rodas:
        print(f"No data found at {RODAS_PATH}, aborting.", file=sys.stderr)
        sys.exit(1)

    step_recheck_known_entries(rodas)

    save_json(RODAS_PATH, rodas)
    print("\nDone. data/rodas.json updated.")


if __name__ == "__main__":
    main()
