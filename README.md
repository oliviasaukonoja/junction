# Polku hoitoon · Junction 2026

**Team Polku Labs** (Olivia Saukonoja, Ida Oittinen, Kristine Saralidze, Eugeniu Vezeteu) · AstraZeneca challenge *Equal Care Across Finland* · live at **[polkuhoitoon.fi](https://polkuhoitoon.fi)**

Lung cancer in Finland is found late as delays build up for patients and in healthcare. We show decision-makers where, screen those most at risk, and help doctors spot it earlier.

## The solution

| Part | For whom | What it does | Where |
|---|---|---|---|
| **Keuhkodata dashboard** | Decision-makers | Brings scattered public data into one view: age-standardised mortality by region (SMR), the care pathway, risk group, inequality. An AI analyst explains each region using only cited facts. | [`/keuhkodata`](https://polkuhoitoon.fi/keuhkodata) |
| **Screening bus** | 50–74-year-olds who smoke or have smoked | Low-dose CT close to home, first as a randomised-invitation pilot in Lapland, with hospital-CT invitations in Kymenlaakso and Satakunta. | [`/`](https://polkuhoitoon.fi) (waitlist), [`/kartta`](https://polkuhoitoon.fi/kartta) (pilot map) |
| **AI flagging** | Health-centre professionals | Concept: connects warning signs scattered across visits and systems and shows one flag in the doctor's view. Decision support, not diagnosis. Starts as a timeline (not a medical device); the AI flag would be a CE-marked medical device after a silent-mode study. | [`/ammattilaisille`](https://polkuhoitoon.fi/ammattilaisille) (linked from the footer only) |

**Key numbers** (all sourced on the site): about 155 days from symptoms to treatment in Finland vs 67 in Denmark (Yle MOT 2026, unpublished); Lapland has 29% more lung cancer deaths than its age structure predicts (our SMR from Statistics Finland, 95% CI +19% to +41%); Kymenlaakso, Satakunta and East Uusimaa are also significantly above the national level.

**Not built:** a national pathway data bank and any real Kanta connection. Every page says this is a hackathon concept: the sign-up reserves nothing and promises no screening.

## Repository

| Folder | What it is | Main author | Start here |
|---|---|---|---|
| [`landing-page/`](landing-page/) | The website and its Modal app: bus page and waitlist, Keuhkodata, professional view, FAQ, about, feedback, privacy, and the APIs | Olivia Saukonoja, Kristine Saralidze | [`landing-page/app.py`](landing-page/app.py), [`DESIGN_RULES.md`](landing-page/DESIGN_RULES.md) |
| [`map/`](map/) | Pilot map (`/kartta`): bus routes in Lapland, Kymenlaakso and Satakunta, impact cards, AI route chat and a password-protected tools layer | Ida Oittinen | [map/README.md](map/README.md) |
| [`ct-sim/`](ct-sim/) | Lung-screening planner: simulator, routing, area model, gap finder, pilot design and the data analyses behind the site | Ida Oittinen | [ct-sim/README.md](ct-sim/README.md), [mobile_ct_screening_report.md](ct-sim/mobile_ct_screening_report.md) |
| [`calmsight/`](calmsight/) | Separate project: AI coach backend and Android app for guided fear exposure on smart glasses; not part of the AstraZeneca entry | Kristine Saralidze | [calmsight/stepcloser/README.md](calmsight/stepcloser/README.md) |

Product framing and users: [PRODUCT.md](PRODUCT.md). Demo flow and what to claim: [ct-sim/docs/demo_script.md](ct-sim/docs/demo_script.md).

## Website (`landing-page/`)

One Modal app (`app.py`, app name `vayla-waitlist`), proxied to polkuhoitoon.fi through a Cloudflare Worker.

- **Pages:** `/` bus and waitlist (8 languages) · `/keuhkodata` (also `/data`) · `/kartta` pilot map · `/ammattilaisille` (also `/pro`) professional view · `/ukk` · `/meista` · `/palaute` · `/tietosuoja`. `/sovellus` redirects to `/`, `/paattajille` to `/keuhkodata`.
- **APIs:** `POST /api/signup`, `GET /api/count`, `POST /api/feedback`, `GET /api/regions`, `POST /api/analyst`, `POST /api/ai`; map chat and tools are served from `map/map_server.py`.
- **Shared look:** `site.css` and `layout.js` (header, footer, languages). Fonts and libraries are self-hosted; no CDN at runtime.

### Deploy

```
cd junction && git pull
pip install anthropic
python3 ct-sim/docs/analysis/build_pilot_map_data.py   # builds map/private/pilot_map_advanced.json (not in git)
git checkout map/pilot_map.json                        # undo the script's change to the tracked file
cd landing-page && modal deploy app.py
```

**Modal secret `polku-ai`:** `ANTHROPIC_API_KEY` (analyst and map chat; paste the full key) and `MAP_PASSWORD` (map tools; any password you choose). Without them the AI panels show their fallback messages and the map tools stay locked.

**Sign-ups** live in a Modal Volume, readable only with your own Modal login: `python signups.py` (summary) or `python signups.py --csv` (includes contacts; kept out of git). There is deliberately no admin page.

## Working in this repo

- Secrets and `.env` files are ignored; never commit keys.
- Several people push to `main`: pull before you push, and keep commits small.
- Every number on the site carries its source and a tag (observed, model or assumption). Keep it that way.
