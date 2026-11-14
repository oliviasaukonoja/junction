# ctsim: mobile CT lung screening simulator (Junction 2026, AstraZeneca challenge)

Simulation and planning toolkit for a mobile low-dose CT (LDCT) lung screening unit in Finland.
Read [mobile_ct_screening_report.md](mobile_ct_screening_report.md) first (and [docs/gap_analysis_and_cost.md](docs/gap_analysis_and_cost.md) for the 2026-11-14 gap analysis against the challenge, the Pohde deck and the strategy, with cost and lives-saved estimates): it states what is sourced, what is assumed, and what the numbers do and do not show.

## Layout
```
src/ctsim/        engine (standard library only, Python >= 3.10)
  model.py        cost / capacity / outcome model, Monte Carlo, sensitivity (parameters carry source tags)
  routing.py      stop and route optimiser for one unit, equity weighting, sensitivity table
  robust.py       robustness sweep: stability map, plan regret on fresh worlds, value of information; splits into jobs run by a pluggable mapper (sequential, process pool, Modal)
  scenario.py     one JSON scenario in -> one JSON result out (shared by CLI, server, Modal, DB)
  fetch.py        refresh Statistics Finland inputs and rebuild data/routing/municipalities.csv
  screening.py    download Cancer Registry screening tables, extract CSVs, county participation table
  area.py         risk group, eligible estimate by municipality, county CT capacity and campaign demand (the 'area model')
  areadata.py     fetch verified county data (Statistics Finland deaths, THL smoking, Eurostat CT exams)
  pilot.py        sample size, power and bias simulations for the randomised-invitation pilot
  readout.py      rule-based two-minute summary of a scenario: no AI, no key (analyst fallback)
  gap.py          data for the gap-finder page (real Cancer Registry participation by county and group + tagged indicators)
  analyst.py      Claude analyst: question -> tool calls (run_scenario, run_robustness, get_assumptions, get_ct_sites) -> grounded answer
  ctsites.py      compile researched CT site rows (data/ct_sites) and expose them to routing
  geo.py          EPSG:3067 -> lat/lon
  server.py       local development HTTP server that also serves the map front end (not for public exposure)
  cli.py          python -m ctsim <command>
web/              map front end (index.html) and gap-finder page (gap.html): index.html + vendored Leaflet 1.9.4 (OpenStreetMap tiles load from the internet)
configs/scenarios/  example scenarios
tests/            44 tests (unittest; 1 skipped without the anthropic package)
data/             model outputs, routing inputs/outputs, population, screening tables; data/raw is a download cache (git-ignored)
api/modal_app.py  Modal app: run_one / sweep / run_robust functions and a web endpoint (smoke-tested; web endpoint not yet served)
db/schema.sql     MariaDB schema for run history (UNTESTED draft)
```

## Run
From this folder:
```bash
export PYTHONPATH=src            # or: pip install -e .
python -m ctsim tests            # 70 tests, ~12 s
python -m ctsim readout configs/scenarios/tampere_100km.json   # rule-based summary, no key needed
python -m ctsim area             # refresh county data (deaths, smoking, CT exams) into data/area
python -m ctsim pilot            # size the randomised pilot: python -m ctsim pilot --p-a 0.4 --delta 0.15
python -m ctsim gap              # rebuild data/gap/gapdata.json for /gap
python -m ctsim ask "Where should one truck stop in Lapland?"   # Claude analyst; needs .venv/bin/pip install anthropic and ANTHROPIC_API_KEY
python -m ctsim ctsites          # compile data/ct_sites/raw_group*.csv + overrides.csv -> ct_sites.csv
python -m ctsim model            # writes data/model/*.csv
python -m ctsim routes           # writes data/routing/route_results.csv
python -m ctsim sensitivity      # writes data/routing/sensitivity.csv
python -m ctsim robust configs/scenarios/tampere_100km.json --n 100 --workers 4   # writes data/robust/*.csv (national: ~25 s on one core, ~10 s with 4 workers)
modal run api/modal_app.py::robust_bench --n 100 --chunk 3   # same sweep sequentially here vs spread over Modal containers; checks results are identical
python -m ctsim scenario configs/scenarios/tampere_100km.json
python -m ctsim serve            # http://127.0.0.1:8000  map UI at /, API: GET /health, GET /municipalities, POST /scenario, POST /robust
modal run api/modal_app.py::smoke   # remote smoke test (needs `modal setup`)
python -m ctsim fetch            # refresh public inputs from Statistics Finland (about 10 s)
python -m ctsim screening        # refresh Cancer Registry tables (about 2 min, ~28 MB)
python -m ctsim counties         # rebuild county participation table from data/screening
```

## Status
| Part | State |
|---|---|
| Model, routing, scenario runner, local server, data refresh | Working. 70 tests pass. Refactor reproduces earlier outputs byte for byte |
| Map front end (`web/index.html`) | Working in the in-app browser: presets, sliders, route and stops on a map, KPIs, comparison with population-greedy, Monte Carlo cost table. Not tested on other browsers or phones. Basemap tiles need internet; without them the circles and route still draw on a blank background |
| Data refresh (`fetch`, `screening`) | Verified against the live sources on 2026-11-13. Table ids and variable codes can change when Statistics Finland publishes new years |
| `api/modal_app.py` | Tested on Modal 1.6.4: remote scenario matches local exactly; the robustness sweep runs across containers (`run_robust` + `robust_task`) with results identical to the local sequential run. National sweep, 100 worlds: 24 s local sequential, 12 s on Modal first run (container start), 4.4 s on a warm second run. The web endpoint (map UI + API) was served temporarily with `modal serve` and answered `/`, `/health` and a 100-world `/robust` in 15 s; deployed on 2026-11-14 for the demo (unauthenticated public URL; stop with `modal app stop ctsim`; the `/ask` analyst route is not available on Modal). Web `/robust` is capped at 400 worlds but only 100 was tested |
| `db/schema.sql` | Draft. Not loaded into MariaDB. No loader code yet |
| Robustness sweep (`robust.py`, CLI, `/robust`, stability map and what-to-measure panel in the UI) | Working. Regret is measured on independent validation worlds; with 30-50 validation worlds, differences of a few points between plans are noise |
| Claude analyst (`analyst.py`, `/ask`, panel in the UI, `ctsim ask`) | Built and tested against a mocked API only (the real Anthropic SDK 2.8 parses scripted responses; request shape checked). NOT run against the live API: no API key was available. First live run may need fixes (for example if the model or `fallbacks` parameter is rejected) |
| Road-network travel times, pathway simulation | Not built |

## Known limits (do not hide these in a demo)
- CT sites: `routing.FIXED_SITE_NAMES` is the old placeholder. The researched list (`data/ct_sites/ct_sites.csv`, 36 towns) is the UI default but is incomplete: 24 confirmed, 12 likely, built mostly from search summaries, 3 rows spot-checked. No capacity or waiting times.
- Uptake curves, costs, eligible share and additionality are assumptions (`data/model/assumptions.csv`, tag ASSUME).
- Distances are straight line x 1.3 at 60 km/h, not road times.
- Foreign-language share is for all ages, used as a proxy for the 50-74 group.
- The analyst is only as good as its facts card (`data/analyst/facts.md`), which repeats the report's numbers with tags. Check it before a demo. Answers cost API credits (Opus 5.5 default; set CTSIM_MODEL to change).
- Most [S] sources in the report were read as web-search summaries; primary papers were not opened.
