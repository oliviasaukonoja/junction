# Demo script and Q&A prep (Junction, AstraZeneca challenge)

Judging is Sunday 14:00. Weights: Actionability 30, Insight 25, Data quality and transparency 20, Execution 15, Clarity 10. A decision-maker must get the message in under two minutes, and the demo must work live.

## One story (say this first, 20 seconds)
"Finnish lung-cancer patients wait 155 days from first symptom to treatment; Danes wait 67. **Keuhkodata** (polkuhoitoon.fi/keuhkodata) shows where the gap is: Lapland has 29% more lung-cancer deaths than its age structure predicts, and four regions are significantly above the national level. Pick a region and you get the team's rule-based recommendation and an AI analyst that explains the gap using only cited sources and says what is unknown.
Our recommendation: (1) a **risk-group screening bus** for the significantly high regions, started as a pilot with randomised invitations so we learn whether it reaches people a hospital CT misses (this planner sizes and routes it); (2) the **patient app** for a visible care path. The waitlist in eight languages is our demand evidence."

Rule for the whole pitch: say what we would measure, never that screening or a slot is coming.

## Product framing (decided 2026-11-14)
**Main product, where the value is: a data bank.** A backend data system that joins cancer-type-specific pathway data, built separate from Omakanta but designed to connect to it, with the Keuhkodata dashboard on top giving recommendations to professionals. Its first and largest recommendation is a screening pilot. **Visible product, featured most in the video: the bus** (mobile CT) and a bus pilot in **Lapland, Kymenlaakso and Satakunta**.
**Why a data bank:** there is no data specific to cancer types and to how the care pathway (hoitopolku) runs, so pathway gaps cannot be identified today. What we found (public, reproducible: `wait_times_syopataudit_2023_2026.md`, `incidence_by_area_2020_2024.md`):
- THL queue data is by specialty (oncology), not by cancer type, so a lung patient cannot be followed through the pathway.
- Oncology referral counts are not comparable across areas: 0.7 to 12.4 per 1000 residents, and 0.10 to 1.83 per new cancer case. That is how areas register referrals, not demand.
- Kainuu and Helsinki city report nothing for the specialty; assessment-wait data is mostly missing in 8 of 19 areas.
**Why these three areas:** lung-cancer deaths per 100,000 aged 50-74 in the Gap finder (Lapland 186, Satakunta 176, Kymenlaakso 175); lung incidence in the Cancer Registry (Lapland men 77 and women 43 per 100,000 against 62 and 35 nationally; Kymenlaakso men 70); and, for Lapland, assessment waits over 90 days in all four years 2023-26. Indicative only: about 19 areas, crude death rates, different time windows. (The pitch-context file mentions Kainuu as an alternative; decide before recording.)
**What is real:** Gap finder, Keuhkodata, planner, analyst, and the public-data analyses. **Not built:** the data bank itself and any Omakanta/Kanta connection. Say "designed to connect", never "integrated". Connecting needs approvals we have not sought; do not name legal bases on stage until checked.
**Planner check, 2026-11-14.** All three regions run without errors in the planner (`python -m ctsim scenario <file>`, researched CT list incl. likely, lam 0.5). The region is a circle around a town, not the county, so some stops fall outside it:

| Region (base, radius) | Stops | Outside the county | Eligible in area | Coverage hospital CT only to with truck | Additional scans a year (modelled) |
|---|---|---|---|---|---|
| Lapland (Rovaniemi, 150 km) | 12 | None, but the county's northern municipalities are outside the circle (3,571 of 5,213 eligible are inside) | 3,571 | 23% to 50% | about 480 |
| Kymenlaakso (Kouvola, 60 km) | 6 | Lapinjärvi, Iitti, Luumäki (eligible figure includes them) | 5,178 | 19% to 48% | about 780 |
| Satakunta (Pori, 80 km) | 8 | Isojoki, Sastamala | 6,721 | 21% to 43% | about 750 |

These come from assumed uptake curves, eligible share and costs. They are not lives saved. Say so if shown.

## Before you present (10 minutes)
1. Start the local app: `cd ct-sim`, `export PYTHONPATH=src`, `.venv/bin/python -m ctsim serve`. Open http://127.0.0.1:8000/gap and http://127.0.0.1:8000/.
2. If you want the deployed copy as a backup: `PYTHONPATH=src modal deploy api/modal_app.py`, open its URL, run one scenario to warm it. Stop it after: `modal app stop ctsim`.
3. If an API key is set, ask one analyst question and keep `CTSIM_ANALYST_RECORD=1` on so answers are recorded. If not, use the **Readout (no AI)** button; it works with no key and no internet (map tiles aside).
4. Have the report open (`mobile_ct_screening_report.md`, sections 0, 4 and 7) for questions.

## Three-minute path
**0:00-0:30, the gap (Gap finder page).** "Finland loses lung cancer patients before diagnosis, not between diagnosis and treatment." Point at the Nordic survival bars (men 17% vs about 30%), then the pathway row: red at detection and primary-to-specialist, green at treatment start (median 36-38 days). Say once: these survival and wait figures are tagged N, team notes, and we show the tag on screen.

**0:30-1:00, who is missed (same page, Equity).** Click Breast, Colorectal, Cervical. "Participation falls to 53-61% for people whose native language is not Finnish, Swedish or Sámi, and to 62-64% with primary education. Helsinki, Vantaa-Kerava and West Uusimaa have the lowest county rates." These are Cancer Registry tables read directly. Note: distance is not the main barrier in these data.

**1:00-1:30, who is at risk and where (Gap finder, county table).** "The high-risk group is people 50-74 with at least 20 pack-years who smoke or quit within 15 years: about 120,000 people on our estimate. Lung-cancer deaths per head are highest in Lapland, Satakunta and Kymenlaakso." Say plainly: the 120,000 comes from verified smoking rates times an assumed factor, because Finnish pack-year data was not found, and CT waiting times by county do not exist in any source we could find; the waits on screen are modelled.

**1:30-2:30, what to do (Mobile CT planner).** "Only lung has randomised evidence that CT screening saves lives, and Finland has no programme. So our recommendation is a pilot, not a rollout." Run Lapland. Show: stops and route, extra participants, and the box 'Reach of the high-risk group' (hospital CTs only vs with the truck). Switch 'Colour circles by' to eligible people or lung mortality. Then raise the campaign slider to 2 and show the pressure table: filtering and booking eligible people first protects the high-risk group, but the queue still grows, so a campaign needs capacity or paced invitations. Point out the comparison table (reach the most people vs reach people hospital CTs miss). Then **Run robustness sweep**: "Whatever route we pick matters less than three unknowns: which towns really have CT capacity, the eligible share, and real uptake. The pilot measures those."

**2:30-2:50, the analyst.** Ask: "What should we measure first before a pilot?" or press Readout (no AI). Read the bottom line and the caveats aloud.

**2:50-3:00, the ask.** Strategy line first (confirm action numbers in the roadmap PDF before saying them): "Roadmap action 2.3.4 expects the lung pilot to expand regionally by 2028. We propose the equity and access arm of that expansion, funded under 2.4.4." Then: "We would like a county and AstraZeneca to run a pilot that randomises invitations: control gets the usual hospital CT, treatment also gets a mobile slot. 173 people per arm detect a 15-point uplift; a campaign cancels out in the comparison. The protocol and calculator are on the Gap finder page."

## What to say about data quality (20% of the score)
- The Gap finder page has a data-status table: verified, proxy, assumed, gap. Lead with it when asked where numbers come from.
- Every number has a tag: S sourced, N team notes or mentor interview, A assumption.
- The CT site list is researched, not an official register: 36 towns, 24 confirmed, 12 likely; three rows were checked directly and a second pass found no contradictions.
- The route model's uptake curves, eligible share and costs are assumptions. "Extra participants" are not lives saved and the app never converts them into survival.
- Stage-specific survival gaps are not treated as proof that screening causes improvement (lead-time bias, overdiagnosis).
- The sweep is reproducible: same seed gives the same result whether it runs on one core, local processes or Modal containers.

## Likely questions
- **What is the data bank, and does it exist?** "It is the design for a backend that joins pathway data by cancer type. Today we have the joined public data and the Keuhkodata prototype. The data bank itself is not built."
- **Is it integrated with Omakanta?** "No. It is designed to be separate and connectable. Connecting needs approvals from the Kanta services and permits for secondary use of health data, which we have not sought." Check the exact route before naming it.
- **Why Lapland, Kymenlaakso and Satakunta?** "They combine high lung-cancer death rates and incidence; Lapland also has long assessment waits. It is indicative, from about 19 areas and crude rates, which is why the pilot and the data bank come first."
- **Why a truck?** "On our own numbers it is not cheaper than a hospital CT. It only pays off if it reaches people a hospital CT does not, Participation in Finland's other screening programmes is lowest by language, education and in the capital region, but breast screening often uses mobile units already (check before saying it), so those data don't tell us whether distance matters for a lung CT. Lapland, the most remote region, has the highest excess lung cancer mortality. The pilot measures uptake by distance and by language before anyone buys a bus."
- **Where do the 17% and 30% come from?** "IHE's cancer dashboard via our research notes, and NORDCAN is the primary source. We tag them N and have not re-verified them."
- **Is this AI?** "The analyst layer uses Claude with tool calls over the simulator and refuses numbers not in the facts card or tool results. The planner itself is an optimiser plus Monte Carlo, not machine learning. We say so."
- **Can it identify who should be screened?** "No. It is a planning tool with no patient-level data, and it gives no individual advice."
- **How do you find eligible smokers in Finland?** "That is an open problem: we found no national smoking-history register. Health-centre questionnaires and self-referral are options; self-referral can widen inequity."
- **What if the CT list is wrong?** "It is the largest single unknown nationally in the sweep (about 18-19% expected loss), which is why verifying it with the counties is our first request."
- **Cost per death avoided?** "Roughly €0.25-1.2 million in our model (median about €0.5 million), assuming the NELSON effect transfers to Finland. It is not a cost-per-QALY figure and is not comparable with published Nordic ICERs."
- **What would change your recommendation?** "If counties show real CT waiting-time gaps, add capacity first; if additionality in the pilot is below about 15%, spend on invitations and interpreters instead."

- **How did you get the high-risk population?** "Verified county smoking rates times an assumed factor; central estimate 120,000, 7% of 50-74s. We have no pack-year data and say so; it is request number one."
- **Which areas have the longest CT waits?** "Nobody publishes county CT waits, so we cannot say. We show modelled pressure under stated capacity assumptions and a template for counties to fill in real waits."
- **Do oncology waits explain where people die of cancer?** "No. We pulled THL's oncology queue data for 2023-2026 by wellbeing area (`wait_times_syopataudit_2023_2026.md`). Waits over 90 days are rare nationally (3.3%) and show up mostly in small queues such as Keski-Suomi and Keski-Pohjanmaa, where one or two people move the percentage. They do not correlate with cancer death rates. Referral counts differ about 18-fold per new cancer case (0.10 to 1.83), which is a recording difference, so we do not use them as demand. Our reading: the delay is before the oncology queue, which is why the pilot targets detection."
- **Where is lung cancer most common?** "Cancer Registry 2020-2024, age-standardised: Lapland (men 77, women 43 per 100,000 vs 62 and 35 nationally) and Kymenlaakso for men (70). That matches the high-mortality areas we already show." Source: `incidence_by_area_2020_2024.md`.
- **Would a campaign overwhelm CT?** "On our assumptions yes: eligible demand alone is about twice the free capacity, and an unfiltered campaign pushes eligible coverage from 28% to 8%. Filtering and priority booking protect the high-risk group but do not remove the queue."
- **How will you know the scans are genuinely additional?** "Randomised invitations. The campaign hits both arms, so it cancels. A before/after count would report 27 per 100 where the answer is 15."

## If something breaks
- No internet: the app runs locally; the map background goes blank but circles and routes still draw. The Readout button needs no key.
- Analyst error: use Readout (no AI) or the recorded answer box. The UI falls back to the readout automatically if /ask fails.
- Modal cold start: have the local server as the main demo and Modal as backup only.
- Port busy: `python -m ctsim serve --port 8001`.
