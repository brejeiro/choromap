#!/usr/bin/env python3
"""
Weekly refresh for the Roda de Choro Map.

What this does (and does NOT do):
  1. Re-visits every confirmed entry in data/rodas.json whose checkUrl is
     NOT social media, and notes whether the page's text has changed since
     the last run (a cheap, free "did anything move?" signal — it does not
     understand the page, it just hashes the visible text).
  2. Scans a small curated list of HUB_SOURCES (below) — public event
     listings / cultural-agenda / city sites, never social media, never
     anything requiring login — for the word "choro" appearing near a
     known European city name that ISN'T already in data/rodas.json, and
     appends anything new to data/candidates.json as an UNVERIFIED lead
     for a human to check and promote (never auto-added to the map).

Deliberately out of scope, on purpose:
  - Facebook/Instagram: not fetchable without login, and the whole point
    of this project was to avoid needing a social media account.
  - Anything disallowed by a site's robots.txt: skipped and logged, same
    as a well-behaved search crawler would do.
  - Guessing at exact dates/times: this script only flags "something on
    this page changed" or "this looks like a new lead" — a human still
    decides what it means.

Run it locally with:  python3 scripts/refresh.py
It's meant to be run automatically by .github/workflows/refresh.yml
(GitHub Actions, on a weekly schedule, for free).
"""

import json
import re
import sys
import time
import hashlib
import datetime
import urllib.robotparser
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
RODAS_PATH = ROOT / "data" / "rodas.json"
CANDIDATES_PATH = ROOT / "data" / "candidates.json"

USER_AGENT = (
    "RodaDeChoroMapBot/1.0 "
    "(personal, non-commercial travel tool; polite weekly check, "
    "respects robots.txt; not affiliated with any listed venue)"
)
REQUEST_TIMEOUT = 15
POLITE_DELAY_SECONDS = 2

# ---------------------------------------------------------------------------
# Curated "hub" sources to scan for brand-new cities/venues.
# Add more over time — each is just {"url", "label"}. Keep them to public,
# no-login, non-social pages (cultural agendas, club/venue sites, public
# event-listing search-result pages).
# ---------------------------------------------------------------------------
HUB_SOURCES = [
    {"url": "https://agendaculturalporto.org/?s=choro", "label": "Porto cultural agenda"},
    {"url": "https://clubduchorodeparis.org/wp/", "label": "Club du Choro de Paris"},
    {"url": "https://deutschland-brasilien.org/?s=roda+de+choro", "label": "Deutsch-Brasilianische Gesellschaft"},
    {"url": "https://www.splendoramsterdam.com/agenda", "label": "Splendor Amsterdam agenda"},
    {"url": "https://www.eventbrite.com/d/spain/roda-de-choro/", "label": "Eventbrite Spain search"},
    {"url": "https://www.eventbrite.com/d/italy/roda-de-choro/", "label": "Eventbrite Italy search"},
    {"url": "https://www.eventbrite.co.uk/d/united-kingdom/roda-de-choro/", "label": "Eventbrite UK search"},
    {"url": "https://www.eventbrite.fr/d/france/roda-de-choro/", "label": "Eventbrite France search"},
    {"url": "https://www.eventbrite.com/d/germany/roda-de-choro/", "label": "Eventbrite Germany search"},
    {"url": "https://www.eventbrite.pt/d/portugal/roda-de-choro/", "label": "Eventbrite Portugal search"},
    {"url": "https://www.eventbrite.ie/d/ireland/roda-de-choro/", "label": "Eventbrite Ireland search"},
    {"url": "https://www.eventbrite.com/d/poland/roda-de-choro/", "label": "Eventbrite Poland search"},
    {"url": "https://www.eventbrite.com/d/czech-republic/roda-de-choro/", "label": "Eventbrite Czech Republic search"},
    {"url": "https://www.eventbrite.com/d/hungary/roda-de-choro/", "label": "Eventbrite Hungary search"},
    {"url": "https://www.eventbrite.com/d/greece/roda-de-choro/", "label": "Eventbrite Greece search"},
    {"url": "https://www.songkick.com/search?query=roda+de+choro", "label": "Songkick search"},
]

# Extend this list any time — it only needs to be broad enough to catch
# "choro ... <city>" mentions on the hub pages above.
CITY_KEYWORDS = [
    "Lisbon", "Lisboa", "Porto", "Coimbra", "Braga",
    "Paris", "Lyon", "Marseille", "Toulouse", "Bordeaux", "Strasbourg",
    "London", "Manchester", "Bristol", "Edinburgh", "Glasgow", "Leeds",
    "Brussels", "Antwerp", "Ghent",
    "Berlin", "Munich", "Hamburg", "Cologne", "Frankfurt", "Leipzig",
    "Amsterdam", "Rotterdam", "The Hague", "Utrecht",
    "Vienna", "Salzburg",
    "Madrid", "Barcelona", "Valencia", "Seville", "Bilbao",
    "Milan", "Milano", "Turin", "Torino", "Rome", "Roma", "Bologna",
    "Florence", "Naples", "Venice", "Genoa",
    "Zurich", "Geneva", "Basel", "Bern",
    "Dublin", "Cork",
    "Copenhagen", "Stockholm", "Oslo", "Helsinki",
    "Warsaw", "Krakow", "Wroclaw", "Prague", "Brno", "Budapest",
    "Athens", "Thessaloniki", "Bucharest", "Sofia",
]

CHORO_WORD_RE = re.compile(r"\bchoro\b", re.IGNORECASE)


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


def step_discover_candidates(rodas, candidates):
    print("\n== Scanning hub sources for new cities/venues ==")
    known_text = " ".join(
        f"{r.get('name','')} {r.get('city','')} {r.get('venue','')}".lower()
        for r in rodas
    )
    known_candidate_urls = {c["source_url"] for c in candidates}
    today = datetime.date.today().isoformat()
    new_count = 0

    for hub in HUB_SOURCES:
        print(f"- {hub['label']} -> {hub['url']}")
        html = fetch_text(hub["url"])
        time.sleep(POLITE_DELAY_SECONDS)
        if html is None:
            continue
        _, text = normalized_text_hash(html)

        for m in CHORO_WORD_RE.finditer(text):
            window = text[max(0, m.start() - 120): m.start() + 120]
            for city in CITY_KEYWORDS:
                if city.lower() in window.lower() and city.lower() not in known_text:
                    candidate_key = f"{hub['url']}::{city}"
                    if candidate_key in known_candidate_urls:
                        continue
                    candidates.append({
                        "source_url": candidate_key,
                        "hub_label": hub["label"],
                        "hub_url": hub["url"],
                        "city_guess": city,
                        "snippet": window.strip(),
                        "discovered_date": today,
                    })
                    known_candidate_urls.add(candidate_key)
                    new_count += 1
                    print(f"  -> possible new lead: {city} (via {hub['label']})")

    print(f"\nNew candidates found this run: {new_count}")


def main():
    rodas = load_json(RODAS_PATH, [])
    candidates = load_json(CANDIDATES_PATH, [])

    if not rodas:
        print(f"No data found at {RODAS_PATH}, aborting.", file=sys.stderr)
        sys.exit(1)

    step_recheck_known_entries(rodas)
    step_discover_candidates(rodas, candidates)

    save_json(RODAS_PATH, rodas)
    save_json(CANDIDATES_PATH, candidates)
    print("\nDone. data/rodas.json and data/candidates.json updated.")


if __name__ == "__main__":
    main()
