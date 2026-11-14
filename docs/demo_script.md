# Demo script and Q&A prep (Junction, AstraZeneca challenge)

Judging is Sunday 14:00. Weights: Actionability 30, Insight 25, Data quality and transparency 20, Execution 15, Clarity 10. A decision-maker must get the message in under two minutes, and the demo must work live.

## Before you present (10 minutes)
1. Start the local app: `cd ct-sim`, `export PYTHONPATH=src`, `.venv/bin/python -m ctsim serve`. Open http://127.0.0.1:8000/gap and http://127.0.0.1:8000/.
2. If you want the deployed copy as a backup: `PYTHONPATH=src modal deploy api/modal_app.py`, open its URL, run one scenario to warm it. Stop it after: `modal app stop ctsim`.
3. If an API key is set, ask one analyst question and keep `CTSIM_ANALYST_RECORD=1` on so answers are recorded. If not, use the **Readout (no AI)** button; it works with no key and no internet (map tiles aside).
4. Have the report open (`mobile_ct_screening_report.md`, sections 0, 4 and 7) for questions.

## Three-minute path
**0:00-0:30, the gap (Gap finder page).** "Finland loses lung cancer patients before diagnosis, not between diagnosis and treatment." Point at the Nordic survival bars (men 17% vs about 30%), then the pathway row: red at detection and primary-to-specialist, green at treatment start (median 36-38 days). Say once: these survival and wait figures are tagged N, team notes, and we show the tag on screen.

**0:30-1:00, who is missed (same page, Equity).** Click Breast, Colorectal, Cervical. "Participation falls to 53-61% for people whose native language is not Finnish, Swedish or Sámi, and to 62-64% with primary education. Helsinki, Vantaa-Kerava and West Uusimaa have the lowest county rates." These are Cancer Registry tables read directly. Note: distance is not the main barrier in these data.

**1:00-2:15, what to do (Mobile CT planner).** "Only lung has randomised evidence that CT screening saves lives, and Finland has no programme. So our recommendation is a pilot, not a rollout." Run Tampere, then Lapland. Show: stops and route, extra participants, cost per extra participant. Point out the comparison table (reach the most people vs reach people hospital CTs miss). Then **Run robustness sweep**: "Whatever route we pick matters less than three unknowns: which towns really have CT capacity, the eligible share, and real uptake. The pilot measures those."

**2:15-2:45, the analyst.** Ask: "What should we measure first before a pilot?" or press Readout (no AI). Read the bottom line and the caveats aloud.

**2:45-3:00, the ask.** "We would like a wellbeing services county and AstraZeneca to run a two-year pilot with randomised invitations to measure how many scans a mobile or pop-up site really adds. Gap finder recommendation R5 has the KPIs."

## What to say about data quality (20% of the score)
- Every number has a tag: S sourced, N team notes or mentor interview, A assumption.
- The CT site list is researched, not an official register: 36 towns, 24 confirmed, 12 likely; three rows were checked directly and a second pass found no contradictions.
- The route model's uptake curves, eligible share and costs are assumptions. "Extra participants" are not lives saved and the app never converts them into survival.
- Stage-specific survival gaps are not treated as proof that screening causes improvement (lead-time bias, overdiagnosis).
- The sweep is reproducible: same seed gives the same result whether it runs on one core, local processes or Modal containers.

## Likely questions
- **Why a truck?** "On our own numbers it is not cheaper than a hospital CT. It only pays off if it reaches people a hospital CT does not, and Finnish screening data suggest the barriers are language, education and metropolitan areas more than distance. So the pilot tests exactly that before anyone buys one."
- **Where do the 17% and 30% come from?** "IHE's cancer dashboard via our research notes, and NORDCAN is the primary source. We tag them N and have not re-verified them."
- **Is this AI?** "The analyst layer uses Claude with tool calls over the simulator and refuses numbers not in the facts card or tool results. The planner itself is an optimiser plus Monte Carlo, not machine learning. We say so."
- **Can it identify who should be screened?** "No. It is a planning tool with no patient-level data, and it gives no individual advice."
- **How do you find eligible smokers in Finland?** "That is an open problem: we found no national smoking-history register. Health-centre questionnaires and self-referral are options; self-referral can widen inequity."
- **What if the CT list is wrong?** "It is the largest single unknown nationally in the sweep (about 18-19% expected loss), which is why verifying it with the counties is our first request."
- **Cost per death avoided?** "Roughly €0.25-1.2 million in our model (median about €0.5 million), assuming the NELSON effect transfers to Finland. It is not a cost-per-QALY figure and is not comparable with published Nordic ICERs."
- **What would change your recommendation?** "If counties show real CT waiting-time gaps, add capacity first; if additionality in the pilot is below about 15%, spend on invitations and interpreters instead."

## If something breaks
- No internet: the app runs locally; the map background goes blank but circles and routes still draw. The Readout button needs no key.
- Analyst error: use Readout (no AI) or the recorded answer box. The UI falls back to the readout automatically if /ask fails.
- Modal cold start: have the local server as the main demo and Modal as backup only.
- Port busy: `python -m ctsim serve --port 8001`.
