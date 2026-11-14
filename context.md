# Session context for teammates (written 2026-11-14)

Handover of what was done and decided in one working session. Judging is Sunday 2026-11-15 at 14:00. Criteria: actionability 30%, insight 25%, data quality and transparency 20%, execution 15%, clarity 10%.

## Project
Lung-cancer low-dose CT screening planner (`ct-sim/`) plus a proposed equity-and-access pilot for the AstraZeneca challenge at Junction 2026. The team goes by "Polku Labs" (site polkuhoitoon.fi, decision-maker page polkuhoitoon.fi/paattajille). I have not seen the content of either page.

## Standing rules (agreed in the session)
- Do not name AstraZeneca or the call speaker in outreach without permission. Say "lääkeyrityksen haasteessa" or "haasteen järjestäjä".
- Never promise screening, a place or a queue spot. The sign-up reserves nothing.
- Use "matala-annos TT" in Finnish text. Max three questions in registry emails.
- No claim that the pilot is part of, endorsed by or funded under the national programme. No claim it can show survival or stage shift.
- Nobody has been contacted. All emails, call scripts and messages are drafts for a human to send.
- Do not paste the API key anywhere. Use Artifact, Modal, deploy and push tools only with explicit approval.
- Earlier instruction still in force: do not implement the 13 recommended simulator changes until chosen.

## Done this session
1. **Strategy fit.** Read the national cancer strategy 2026-2035 and its 2026-2031 roadmap (PDFs in the project folder). Added section 13 to `ct-sim/docs/pilot_design.md`: pilot outcomes mapped to roadmap actions (2.3.4 lung pilot, 2.4.4 about EUR 2.5M for screening pilots, 2.4.2 register law, 2.3.1/2.3.2 governance, 1.1.1/1.3.1 language participation, 2.2.2 cessation) and a "what not to claim" list. The roadmap was keyword-searched, not read cover to cover; check each cited action number before presenting.
2. **Outreach drafts (in chat, not in files):** sign-up message (long, short, SMS), call script for kehityspäällikkö at a hyvinvointialue, email plus subject lines, interest-signal criteria. Strongest signals: a named next step, a written one-line statement, internal facts shared, an introduction to a decision-maker.
3. **Funders and contacts:** list of possible funders (from memory, unverified) and contacts at STM/FICAN, Syöpäyhdistys and Syöpäsäätiö from fetched pages. Phone numbers and emails came from summarised page text. Verify before use.
4. **UK evidence:** NHS Targeted Lung Health Check final evaluation: 2,748 diagnoses, about 75% stage 1-2 (vs 36% in a comparison group), about 781 extra early cancers (modelled), lower uptake in deprived areas. From search summaries; reports not opened. Stage shift is not survival (lead-time bias, overdiagnosis).
5. **Wait-time analysis (oncology, by welfare area):** see below.
6. **Cancer incidence by welfare area:** in progress, see below.

## Wait-time analysis
Files in `ct-sim/docs/`: `wait_times_syopataudit_2023_2026.md` (tables, flags, caveats), `.csv` (per area and year), `analysis/wait_times_syopataudit.py` (re-downloads everything: `python3 wait_times_syopataudit.py CACHE_DIR OUT_DIR`).

The nine CSVs in Downloads are all THL cube `eshjono/jonotilanne`, specialty 65 Syöpätaudit. They are unlabelled ("val") exports.

Main findings, with the weaknesses stated:
- Longer treatment waits (over 90 days, national 3.3%): Keski-Suomi 17.5%, Keski-Pohjanmaa 14.4%, Pohjois-Savo 10.2%, Pohjois-Pohjanmaa 8.2%, Etelä-Pohjanmaa 8.8%, Satakunta 6.7%. Most have only 2-25 patients in the queue, so one or two people move the percentage.
- Longer assessment waits (national 3.8%): Lappi 14% (consistent in all four years), Pirkanmaa 65% (one year, then data stops), Päijät-Häme 19%, Pohjois-Pohjanmaa 8.8%.
- HUS has half the national queue and the most cancer deaths (about 3,350 a year) but almost no long waits.
- Highest crude cancer death rates: Kymenlaakso 339, Satakunta 321, Etelä-Savo 319 per 100,000 (national 238). Satakunta and Kymenlaakso stay above the age-structure line.
- Waits and cancer death rates do not correlate (Spearman -0.23 to +0.44, p of 0.15 or more).
- **Referral counts are not comparable across areas** (0.7 per 1000 in Pohjois-Karjala and 0.9 in HUS, 12.4 in Pohjanmaa; Pirkanmaa 821 to 2,997 in one year). This looks like registration differences. Do not present referral volume as demand.
- Kainuu and Helsinki city report nothing for this specialty. Assessment-queue data is mostly missing in 8 of 19 areas. Blank cells cannot be told apart from zero or suppressed.
- Oncology specialty only: cancer surgery is in other specialties. Deaths are by residence, queues by provider. Deaths do not measure the effect of the waits.

## Incidence by welfare area (done, not committed)
Source: Finnish Cancer Registry statistics app, https://tilastot.syoparekisteri.fi/syovat/ (a Shiny app). Latest full year is 2024; the 2025 preliminary release has counts only. Its CSV button returns HTML, so I read the on-screen table.
Files: `ct-sim/data/registry/cancer_registry_incidence_2020_2024.csv` (raw: new cases and age-standardised rates, all cancers and lung C33-34, men and women separately, five-year total 2020-2024) with a README; `ct-sim/docs/incidence_by_area_2020_2024.md` (table next to deaths and referrals); `ct-sim/docs/analysis/incidence_crossref.py` (builds it).
Findings: about 38,300 new cancers a year nationally (areas sum to 38,066; gap mostly Åland, not checked). HUS area about 10,400 a year, then Varsinais-Suomi 3,550 and Pirkanmaa 3,470. Lung age-standardised rate is highest in Lappi (men 77, women 43 per 100,000; national 62 and 35) and Kymenlaakso for men (70). Deaths per new case are 0.32 to 0.40 everywhere, with Satakunta highest (0.40). Oncology referrals per new case range from 0.10 (Pohjois-Karjala) to 1.83 (Pohjanmaa), which confirms the referral counts are a registration artefact. HUS rates in the table are population-weighted averages (approximation). Rates for men and women are not combined.

## Open or unverified
- Content of polkuhoitoon.fi and /paattajille unseen. They must not name AstraZeneca, promise screening or claim Finnish testing, and need a privacy notice naming the controller.
- Whether the team has AstraZeneca's permission to be named.
- The roadmap says the national lung pilot runs in Helsinki and eight wellbeing counties. An earlier note said five hospitals. Check.
- Not opened: `Equility in Cancer Care_Espoo 13.11.26_distribution.pdf` and `Syöpästrategiat ja syöpädata_linkkikokoelma.pdf`.
- Registry and OYS answers (Sarkeala, Koivunen) pending. The Claude analyst has not been run live. The Modal copy lacks the analyst. CT list lacks Tyks and Pori checks.
- Pitch sentence for `demo_script.md` not added: "Roadmap action 2.3.4 expects the lung pilot to expand regionally by 2028. We propose the equity and access arm of that expansion, funded under 2.4.4."

## Git
Repo `oliviasaukonoja/junction`, branch `main`. Pushed today: commit 7a8daab (pilot_design section 13, wait-time files and script), rebased on the remote's Calmsight and landing-page commits. Still uncommitted and not mine: `ct-sim/README.md`, `data/analyst/facts.md`, `mobile_ct_screening_report.md`, `src/ctsim/area.py`, `docs/gap_analysis_and_cost.md`, `docs/analysis/lives_saved_estimate.py`. Whoever wrote those should commit them.
