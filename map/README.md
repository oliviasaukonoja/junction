# Pilot map

A clean, data-backed map of where lung-cancer CT screening pilots could start in **Lapland, Kymenlaakso and Satakunta**. The default view shows two pilot types: a **hospital CT pilot** (blue: municipalities within 45 minutes of a CT site) and a **screening bus** (orange: beyond that), with the bus route animated along real roads and a card explaining why each stop was chosen. Every figure is labelled observed, modelled, assumption or missing. It is a concept; it promises no screening, place or queue spot.

## Files
| Path | What |
|---|---|
| `kartta.html` | The page (fi / sv / en). Static, one file, Leaflet vendored in `vendor/` |
| `pilot_map.json` | Public data the default view shows, with source checksums in `meta.sources` |
| `private/pilot_map_advanced.json` | Assumption scenarios, earlier-model comparison, factor correlations. **Not in git** (the repo is public): regenerate it, see below |
| `map_gate.py` | Server-side password gate: `POST /api/map/unlock`, `GET /api/map/advanced` |
| `preview_app.py` | Map-only Modal app for review (no sign-up form, no AI analyst, no volume) |
| `integration/website_integration.patch` | The change that adds the map to the live website app. **Not applied** |
| `../ct-sim/docs/analysis/fetch_pilot_inputs.py` | Downloads the observed inputs into `ct-sim/data` (needs internet) |
| `../ct-sim/docs/analysis/build_pilot_map_data.py` | Builds both JSON files from repo data (offline, deterministic) |

## Rebuild the data
```bash
python3 ct-sim/docs/analysis/fetch_pilot_inputs.py        # only to refresh inputs; they are already in the repo
python3 ct-sim/docs/analysis/build_pilot_map_data.py      # writes map/pilot_map.json and map/private/pilot_map_advanced.json
```

## Review it on Modal (separate from the live site)
```bash
cd map
modal secret create polku-map-preview MAP_PASSWORD=<your password>   # you choose it; never commit it
modal deploy preview_app.py                                          # needs map/private/pilot_map_advanced.json: run the build script first
modal app stop polku-map-preview                                     # when finished
```
The URL is public (noindex). Without `MAP_PASSWORD` the advanced tools stay locked.

## Put it on the live website
1. `git apply map/integration/website_integration.patch` (edits `landing-page/app.py` and adds a menu link in `landing-page/keuhkodata.html`).
2. Add the key `MAP_PASSWORD` to the Modal secret the website app already uses.
3. Run the build script so `map/private/pilot_map_advanced.json` exists, then deploy the website app as usual.

## What the model does
Road travel times (OpenStreetMap via the OSRM demo server, free-flow, no winter or ferries) between municipality main settlements; eligible people from smoking rates and an assumed factor (age 50-74); county SMR (capped 0.8-1.3) and the basic-education share aged 55-74 as weights; the `ctsim` route optimiser unchanged. 81 assumption scenarios show which stops are stable.

## Known gaps (also shown on the page)
- Hospital CT capacity is not verified for any site; free capacity is an assumption applied county-wide. CT is unconfirmed in Lapland and Satakunta.
- No CT waiting times by county; the oncology queue data is a different measure.
- No pack-year data; no lung mortality below county level.
- Travel times are not Digiroad and not winter conditions; points are main settlements, not homes (Hamina, Huittinen and Simo use centroids).
- Swedish text needs checking by a native speaker.

## Password gate
Protects the layer and threshold controls and the scenario data on the server. One shared password, 4-hour tokens, failed attempts limited in memory. It does not make the underlying modelled data private: the code and inputs in this repository reproduce it.
