# Choro Map — Europe

A small self-hosted website — a map + list of roda de choro (Brazilian
choro jam session) venues and organizers across Europe — plus a free,
automated weekly check that keeps it from going stale, with **no Claude,
no subscription, and no social media account** required to keep running.

## Running it

The map's data lives separately, in `data/rodas.json` and
`data/candidates.json`, so the automated weekly check (below) has
something to update on its own. That means `index.html` needs to be
served over http(s) rather than opened directly — double-clicking the
file will show a "could not load data" message, since browsers block
that kind of file loading for plain local files.

To run it locally: from this folder, run `python3 -m http.server` (on
Windows, try `python -m http.server`, or `py -m http.server` if that's
not recognized) and open `http://localhost:8000` in a browser. That's
enough to preview and test changes. The automation only does anything
useful once this is hosted somewhere with GitHub Actions attached to
it — that part isn't covered here.

## What's covered right now

31 confirmed entries across 11 countries: Portugal, France, United
Kingdom, Belgium, Germany, Netherlands, Austria, Spain, Italy, Denmark,
and Ireland. See the map's own legend for what each confidence-level
color means. The map itself shows each entry as a confidence dot plus its
check/follow links, kept deliberately free of longer descriptions —
`notes` in the data file below is where any extra research context lives.

## Automated weekly refresh

There are two moving pieces, both free, both running on GitHub's
infrastructure once you've hosted the repo there:

**1. Re-checking entries you already have.** Every Monday, a GitHub
Actions job (`.github/workflows/refresh.yml`) runs `scripts/refresh.py`,
which revisits every entry's `checkUrl` — skipping any that point to
Facebook or Instagram, since those can't be fetched without logging in —
and compares the page's text to what it saw last time. If it changed, the
entry gets a blue **"changed"** badge on the map so you know to go look,
plus a `lastPolled` date. It does *not* try to understand what changed —
that's still a human judgment call.

**2. Looking for brand-new cities/venues.** The same weekly run also
scans a short curated list of public, no-login "hub" sources — city
cultural agendas, club umbrella sites, and public event-search pages
(Eventbrite, Songkick) — for the word "choro" appearing near a European
city name that isn't already on the map. Anything new gets appended to
`data/candidates.json` as an **unverified lead**, shown in the
collapsible "🔍 Auto-discovered leads" section at the bottom of the page.
Candidates are never auto-promoted to the map — you (or an AI assistant,
or a friend) check the source link and, if it's real, copy it into
`data/rodas.json` in the same format as the other entries, using the
lead's source link as the new `checkUrl`.

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
project deliberately avoids requiring any social media login — and the
hub-source list is intentionally small and curated rather than "search
the whole internet" — that would need a paid search/AI API. You can grow
`HUB_SOURCES` in `scripts/refresh.py` over time as you find more good
public listing pages.

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
  "changedSinceLastCheck": false
}
```

Copy an existing block, edit the text fields, and leave `contentHash` /
`lastPolled` / `changedSinceLastCheck` as `null` / `null` / `false` for a
brand-new entry — the weekly job fills those in on its own. Get `lat`/`lon`
for a city by searching e.g. "Porto latitude longitude". Save the file and
push/re-upload it to GitHub.

**To promote a candidate:** open `data/candidates.json`, find the entry,
open its `hub_url` to verify it's real, then write a proper entry for it
in `data/rodas.json` (as above) and delete the candidate's block from
`data/candidates.json`.

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

## Social media & other contacts

Most of these groups are easiest to keep up with on Facebook or
Instagram — that's simply where this scene posts its dates. Each line
below matches a map entry's `socialUrl`/`socialLabel`; a plain email is
listed instead where one was found and no dedicated social account
exists.

**Portugal**
- Clube do Choro de Lisboa — Instagram: @clubedochorodelisboa
- Clube do Choro do Porto (runs the "Choro no Nery" series) — Facebook: @clubedochoroporto
- Área Metropolitana do Porto (regional cultural agenda) — iporto@amp.pt

**France**
- Club du Choro de Paris — Instagram: @clubduchorodeparis
- La Roda de l'Ouest (Paris) — Facebook: @roda.choro.mardi
- Roda de Choro des Lauriers (Paris) — Facebook: @rodalauriers
- Roda de Choro, Strasbourg — Facebook: Quero Quero Choro
- Roda de Choro de Marseille (Zoumaï) — Facebook: @rodadechorodemarseille

**United Kingdom**
- London Choro Festival — Instagram: @londonchorofestival · YouTube: @LondonChoroFestival
- Choro East (London) — Instagram: @choroeast · info@threecoltstavern.co.uk
- Zucca Roda de Choro (London, Portobello Market) — Instagram: @zucca.uk,
  also promoted via Regional do Grafton (@regionaldografton)
- Roda de Choro @ The Harrison (London) — promoted via Regional do
  Grafton's Instagram (@regionaldografton), with Alvorada performing —
  Alvorada can also be reached at contact@alvoradamusic.com
- Chora Cambridge — Instagram: @choracambridge · choracambridge@gmail.com
- Roda de Choro & Samba (Leeds) — no dedicated social account found; see
  the Visit Leeds listing linked from the map entry

**Belgium**
- GC Pianofabriek (Brussels) — Instagram: @gc_pianofabriek

**Germany**
- Berliner Roda de Choro — Facebook: @berlinerrodadechoro · info@matthiashaffner.com
- Roda de Choro City West (Berlin) — Facebook event series (linked from the map entry)
- Choro München — Instagram: @choromuenchen
- Festival de Chôro München — no dedicated social account; info@luise-kultur.de
- Roda de Choro de Dresden — Facebook: @rodadechorodedresden

**Netherlands**
- Roda de Choro @ Splendor Amsterdam — Instagram: @splendoramsterdam · info@splendoramsterdam.com

**Austria**
- Wiener Choro Klub — Facebook: @WienerChoroKlub

**Spain**
- Roda de Choro de Madrid — Facebook: @rodadechorodemadrid
- Los Choros de Madrid — Instagram: @los_choros_de_madrid · Facebook: @choromadrid
- Roda de Choro (Centres Cívics de Barcelona) — Facebook: @CentresCivicsBCN (network-wide, not roda-specific)

**Italy**
- Clube do Choro de Torino — Instagram: @marcoruviaro (organizer)
- Roda de Choro — Corte dei Miracoli (Milan) — Facebook: @associazionelataiga
- Conjunto Choro di Napoli — Facebook: @conjuntochorodinapoli
- Circolo Odeòn / Roda de Choro Bologna — circoloodeon@gmail.com
- Choro Camp Italia (near Bologna) — Instagram: @chorocamp.italia · info@choroderua.com

**Denmark**
- Roda de Choro (OBA), Copenhagen — Facebook: @obamusic1

**Ireland**
- Regional Massapê (Dublin) — no dedicated social account found; see the
  Eventbrite search linked from the map entry

## Honesty check

This list was compiled by searching public websites, press articles,
cultural-agenda listings, and venue pages, then supplemented with each
group's own social media presence where one exists. Roda de choro is an
informal, word-of-mouth scene, and for a good number of these entries
Facebook or Instagram really is where real dates get posted — the
`socialUrl` link on each entry is there for exactly that reason. What no
automation here can do is read those posts for you: the weekly refresh
only re-checks each entry's `checkUrl` (skipping Facebook/Instagram,
since those need a login to fetch), so a low-confidence (orange) entry
can still go stale between visits — you'd still want a friend to check,
or the organizer's email if one was found. Treat the whole map as a
curated *starting point* to investigate before a trip, not a live events
calendar, even with the weekly refresh running.

## Adapting this for another region

Nothing here is specific to choro or to Europe — the map, the data
schema, and the weekly refresh script all work the same way for any
recurring event type in any region. To repurpose it: replace the
entries in `data/rodas.json` with your own, swap the map's starting
view and title in `index.html`, and update `HUB_SOURCES` /
`CITY_KEYWORDS` in `scripts/refresh.py` to match the sources and
places relevant to your own search.
