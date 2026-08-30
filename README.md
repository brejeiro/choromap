# Choro Map — Europe

A small self-hosted website — a map + list of roda de choro (Brazilian
choro jam session) venues and organizers across Europe — plus a free,
automated weekly check that keeps it from going stale, with **no Claude,
no subscription, and no social media account** required to keep running.

## Running it

The map's data lives separately, in `data/rodas.json`, so the automated
weekly check (below) has something to update on its own. That means
`index.html` needs to be
served over http(s) rather than opened directly — double-clicking the
file will show a "could not load data" message, since browsers block
that kind of file loading for plain local files.

To run it locally: from this folder, run `python3 -m http.server` (on
Windows, try `python -m http.server`, or `py -m http.server` if that's
not recognized) and open `http://localhost:8000` in a browser. That's
enough to preview and test changes. The automation only does anything
useful once this is hosted somewhere with GitHub Actions attached to
it — that part isn't covered here.

## Automated weekly refresh

Every Monday, a GitHub Actions job (`.github/workflows/refresh.yml`) runs
`scripts/refresh.py`, which revisits every entry's `checkUrl` — skipping
any that point to Facebook or Instagram, since those can't be fetched
without logging in — and compares the page's text to what it saw last
time. If it changed, the entry gets a blue **"changed"** badge on the map
so you know to go look, plus a `lastPolled` date. It does *not* try to
understand what changed — that's still a human judgment call.

**Triggering it manually.** The workflow already has `workflow_dispatch: {}`
turned on, which gives you a **"Run workflow"** button on GitHub itself —
go to your repo's **Actions** tab → the refresh workflow → **Run workflow**.
No code required. For convenience, the map's footer also has a "Run the
refresh manually on GitHub" link that jumps straight to that screen — if
you rename or fork this repo, update the URL in that link (in
`index.html`'s `<footer>`) to point at your own repo's Actions page.

A true one-click "run it right now" button living inside the page itself
is deliberately not included: doing that from client-side JavaScript would
mean embedding a GitHub access token directly in a public page, where
anyone visiting could read and reuse it. Routing through GitHub's own
Actions UI (one extra click, using your own logged-in session) avoids that
risk entirely.

**What this does *not* do:** it can't read Facebook or Instagram — this
project deliberately avoids requiring any social media login — and it
only re-checks entries already in `data/rodas.json`; it doesn't go
looking for brand-new cities or venues on its own. Finding new entries is
still a manual research step.

## Updating things by hand

**To edit or add a confirmed entry:** open `data/rodas.json` in any text
editor. Each entry looks like:

```json
{
  "name": "...",
  "city": "...", "country": "...",
  "lat": 0, "lon": 0,
  "venue": "...",
  "frequency": "...",
  "confidenceLevel": "high | medium | low",
  "checkUrl": "...", "checkUrlLabel": "...",
  "socialUrl": "...", "socialLabel": "...",
  "notes": "...",
  "lastChecked": "YYYY-MM-DD",
  "contentHash": null,
  "lastPolled": null,
  "changedSinceLastCheck": false,
  "lastFetchStatus": null,
  "consecutiveFailures": 0
}
```

Copy an existing block, edit the text fields, and leave `contentHash` /
`lastPolled` / `changedSinceLastCheck` / `lastFetchStatus` /
`consecutiveFailures` as `null` / `null` / `false` / `null` / `0` for a
brand-new entry — the weekly job fills those in on its own. Get `lat`/`lon`
for a city by searching e.g. "Porto latitude longitude". Save the file and
push/re-upload it to GitHub.

### Field meanings
- **confidenceLevel** — `high` = active organization with its own real
  website/contact; `medium` = confirmed to exist but the exact schedule is
  loose/seasonal; `low` = thin evidence, worth double-checking.
- **socialUrl / socialLabel** — a Facebook/Instagram link for the group,
  when one exists, shown as a "Follow" link on the map. It's a normal,
  first-class way to keep up with a roda — for many of these groups it's
  genuinely the best place to check for the next date — and it's separate
  from `checkUrl`, which is what the automated weekly check actually polls
  for changes.
- **notes** — free-text research context (how an entry was verified, any
  caveats). Kept in the data file for whoever edits it by hand, but not
  shown on the map itself — the map favors the confidence dot plus links,
  so open `data/rodas.json` directly if you want the fuller story on an
  entry.
- **contentHash / lastPolled / changedSinceLastCheck** — bot-managed,
  don't hand-edit these except to reset `changedSinceLastCheck` to `false`
  once you've looked into a change.
- **lastFetchStatus / consecutiveFailures** — also bot-managed. Every
  weekly run records whether that entry's `checkUrl` actually loaded:
  `lastFetchStatus` is `"ok"` on success, or a short reason why not
  (`"404"`, `"403"`, `"timeout"`, `"connection-error"`, etc.), and
  `consecutiveFailures` counts how many runs in a row have failed,
  resetting to `0` on the next success. This is what drives the grey
  **"link unreachable"** marker on the map (shown once
  `consecutiveFailures` reaches 2) — without it, a dead link would look
  identical to one that's simply unchanged. If you see that marker, the
  `checkUrl` needs a human look and probably a replacement.

## Adapting this for another region

Nothing here is specific to choro or to Europe — the map, the data
schema, and the weekly refresh script all work the same way for any
recurring event type in any region. To repurpose it: replace the
entries in `data/rodas.json` with your own and swap the map's starting
view and title in `index.html`.
