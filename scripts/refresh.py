#!/usr/bin/env python3
"""
Weekly refresh for the Choro Map.

What this does (and does NOT do): re-visits every confirmed entry in
data/rodas.json whose checkUrl is NOT social media. On a successful fetch,
it notes whether the page's text has changed since the last run (a cheap,
free "did anything move?" signal — it does not understand the page, it
just hashes the visible text). Either way — success or failure — it
records lastPolled and lastFetchStatus for that entry, and updates a
consecutiveFailures counter (up on failure, reset to 0 on success), so a
dead link shows up on the map instead of silently looking unchanged.

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
    """Returns (html_text_or_None, status_label). status_label is "ok" on
    success, or a short string describing why it failed: an HTTP status
    code as a string (e.g. "404", "403"), "timeout", "connection-error",
    "robots-disallowed", or "error" for anything else unexpected."""
    if not robots_allows(url):
        print(f"  skip (robots.txt disallows): {url}")
        return None, "robots-disallowed"
    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
        if resp.status_code >= 400:
            print(f"  fetch failed for {url}: HTTP {resp.status_code}")
            return None, str(resp.status_code)
        return resp.text, "ok"
    except requests.exceptions.Timeout:
        print(f"  fetch failed for {url}: timeout")
        return None, "timeout"
    except requests.exceptions.ConnectionError:
        print(f"  fetch failed for {url}: connection error")
        return None, "connection-error"
    except Exception as e:
        print(f"  fetch failed for {url}: {e}")
        return None, "error"


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
        html, status = fetch_text(url)
        time.sleep(POLITE_DELAY_SECONDS)

        # Always record what happened this run, even on failure — a dead
        # link should be visible, not silently skipped.
        r["lastPolled"] = today
        r["lastFetchStatus"] = status

        if html is None:
            r["consecutiveFailures"] = r.get("consecutiveFailures", 0) + 1
            print(f"  -> fetch failed ({status}); consecutiveFailures={r['consecutiveFailures']}")
            continue

        r["consecutiveFailures"] = 0
        new_hash, _ = normalized_text_hash(html)
        old_hash = r.get("contentHash")
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
