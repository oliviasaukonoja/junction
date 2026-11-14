# Junction 2026 monorepo

**Product direction (decided 2026-11-14).** There is no data specific to cancer types and to how the care pathway runs, so gaps in the pathway cannot be identified. The main product is therefore a **data bank**: a backend that joins pathway data by cancer type, built separate from Omakanta but designed to connect to it, with a **dashboard that gives recommendations to professionals**. Its first and largest recommendation is a **screening pilot**. The visible product is a mobile CT **bus pilot in Lapland, Kymenlaakso and Satakunta**, which the demo video features most. Built so far: the lung-screening planner and Gap finder (`ct-sim/`), the Keuhkodata dashboard (`landing-page/`) and public-data analyses. Not built: the data bank itself and any Omakanta/Kanta connection. See [ct-sim/docs/demo_script.md](ct-sim/docs/demo_script.md) for the story and the rules on what to claim.

Four separate components live here. Each has its own folder; only `ct-sim/` is documented in detail in the repo itself.

| Folder | What it is | Main author (from git) | Start here |
|---|---|---|---|
| [`ct-sim/`](ct-sim/) | Mobile low-dose CT lung-cancer screening planner for Finland (AstraZeneca challenge): simulator, routing, area model, Claude analyst, map front end, gap finder, pilot design and the data analyses behind them | Ida Oittinen | [ct-sim/README.md](ct-sim/README.md), then [ct-sim/mobile_ct_screening_report.md](ct-sim/mobile_ct_screening_report.md) |
| [`landing-page/`](landing-page/) | "Polku hoitoon" public pages and waitlist, plus the Keuhkodata dashboard, with sign-up, feedback and analyst APIs | Olivia Saukonoja, Kristine Saralidze | [landing-page/app.py](landing-page/app.py) |
| [`calmsight/`](calmsight/) | Calmsight: an AI coach backend (`brain/`) and an Android app (`stepcloser/`) for guided fear exposure on smart glasses. The repo does not say how it relates to the AstraZeneca challenge | Kristine Saralidze | [calmsight/stepcloser/README.md](calmsight/stepcloser/README.md) |
| [`map/`](map/) | Pilot map for the website: hospital CT and screening-bus pilot areas in Lapland, Kymenlaakso and Satakunta, with an animated bus route, per-stop explanations and a password-protected tools layer. Includes a Modal preview app | Ida Oittinen | [map/README.md](map/README.md) |

## ct-sim (lung screening planner)
- Python engine in `ct-sim/src/ctsim/` (standard library only, Python 3.10 or newer), plus a local server and a map front end in `ct-sim/web/`.
- Evidence is tagged in the report and in `ct-sim/data/analyst/facts.md`: sourced, assumed or not known.
- Docs in `ct-sim/docs/`:
  - `pilot_design.md`: randomised-invitation pilot and fit with the national cancer strategy.
  - `demo_script.md`: demo flow and Q&A.
  - `gap_analysis_and_cost.md`: gap analysis, cost and lives-saved estimates.
  - `wait_times_syopataudit_2023_2026.md` and `incidence_by_area_2020_2024.md`: oncology queues, referrals, cancer incidence and deaths by welfare area.
- Reproducible analysis scripts in `ct-sim/docs/analysis/`. Raw registry data in `ct-sim/data/registry/`.

## landing-page (Polku hoitoon)
- One Modal app (`landing-page/app.py`, app name `vayla-waitlist`) serves the pages and the APIs. Pages: `/` (bus), `/sovellus` (app), `/ammattilaisille` (professionals), `/paattajille` (decision-makers), `/keuhkodata` (the data dashboard: regions, risk, recommendation, AI analyst), `/ukk`, `/meista`, `/palaute`, `/tietosuoja`. APIs: `POST /api/signup`, `GET /api/count`, `GET /api/regions`, `POST /api/analyst`, `POST /api/feedback`. Region data is in `regions.json`. `polku-hoitoon-pitch-context.md` is the team's pitch and video context.
- Deploy: `modal deploy app.py` from `landing-page/`. Sign-ups are stored in a Modal Volume and are readable only with your own Modal login: `python signups.py` (summary without contact details) or `python signups.py --csv` (includes names and contacts, kept out of git).
- There is deliberately no admin page on the website.
- The decision-makers page says this is a concept made for a hackathon challenge, not a real service. The sign-up should reserve nothing and promise no screening; keep that wording on every page (I only checked `/paattajille`).

## calmsight
- `brain/calmsight_brain.py`: a Modal-hosted coach backend with endpoints such as `/start`, `/turn`, `/feedback`, `/insights/{uid}` and `/glasses`. It learns per person which technique helps, using a Thompson-sampling bandit with safety guardrails. API keys live in Modal Secrets, never in the repo.
- `stepcloser/`: the Android project (Meta Ray-Ban Display glasses or phone preview) with its own README, changelog and tests.
- `deploy.sh` deploys the brain to Modal and pushes `calmsight/` to GitHub. `voice.sh` re-voices the guide clips.

## Working in this repo
- Secrets and `.env` files are ignored; do not commit keys.
- Pull before you push: several people commit to `main` and to short branches such as `polku-no-promise`.
