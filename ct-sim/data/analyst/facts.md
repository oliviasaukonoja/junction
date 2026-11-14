# Facts card for the ctsim analyst

Tags: [S] sourced (link), [N] from team research notes or mentor interview, not re-verified in this project, [M] recalled from published trials, not re-verified, [A] planning assumption. Most [S] items were read as search summaries, except where marked "read directly".
The analyst may state a fact only as written here, with its tag, or from tool results. Anything not listed is unknown.

## Burden and gaps (Finland)
- F1 [S] 2024: 38,853 new cancers and 13,490 cancer deaths. Syöpä 2024 report via Verkkouutiset/STT: https://www.sttinfo.fi/tiedote/72173590/
- F2 [S] 2022: 2,410 lung and trachea cancer deaths (1,495 men, 915 women), the leading cancer death for both sexes. https://www.verkkouutiset.fi/a/tahan-syopaan-kuollaan-nyt-eniten/
- F3 [S, verify] 2022: about 2,947 new lung and trachea cancers (a thesis citing the Cancer Registry).
- F4 [N] Lung cancer 5-year survival: men Finland 17% vs Norway 30%, Sweden 29%, Denmark 27%; women 29% vs 37%, 37%, 35% (IHE Cancer Dashboard Finland 2026, via team notes). Breast cancer survival is 92%, close to Sweden, so lung is the large gap.
- F5 [N] A single-centre study found 59% of lung cancer patients diagnosed at stage IV (2007-2019); only 27% were referred to curative treatment in the national quality report. Single centre: do not present as national.
- F6 [N] Diagnosis-to-treatment is mostly fine: median 36-38 days (2018-2022); about 600-700 patients (<2%) exceeded the 180-day limit in 2024. The delay is mainly before diagnosis (primary care).
- F7 [N] 2025 lung study: Finland had the longest Nordic waits: symptom appointment 14 days vs 2-7 elsewhere; specialist consultation 2-4 weeks vs 1-2 weeks.
- F8 [N] Stage is recorded for only 42% of Finnish cancers; no national cancer quality registry.

## National strategy 2026-2035, Goal 3 (read directly from the strategy PDF)
- F9 [S] Goal 3 indicators: five-year survival of poor-prognosis cancers reaches the Nordic level (lung +14 percentage points, pancreas +6, liver +14 versus the 2023 NORDCAN level; Nordic level = average of Sweden and Norway); cancer mortality falls 10% (from about 13,300 a year, so about 1,330 fewer deaths); patients reach treatment within target times.

## Screening participation (read directly from Cancer Registry annual statistics tables, 2024; data/screening)
- F10 [S] National participation: breast 81.6%, colorectal 73.5%, cervical about 74% (73.5% in the press release, 73.8% summing the tables; target 80% in every county). Lowest counties: Helsinki breast 74.3%, colorectal 69.6%; highest: North Ostrobothnia breast 85.6%, South Savo colorectal 76.9%.
- F11 [S] Native language "other/missing" vs domestic: breast 60.8% vs 83.2%; colorectal 53.4% vs 74.5%; cervical 56.3% vs 76.2%. Primary vs tertiary education: breast 63.5% vs 85.9%; colorectal 61.5% vs 79.3%.
- F12 [S] Gaps follow language, education and metropolitan areas more than remoteness (Kainuu breast 84.1%).

## Lung CT screening evidence
- F13 [S] Finland has no publicly funded lung LDCT screening programme. An Oulu feasibility trial (200 smokers, volunteers) found 6 cancers, 5 at stage I. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12171981/
- F14 [S] NELSON (10-year): lung cancer mortality rate ratio 0.76 (95% CI 0.61-0.94); women 0.67 (CI 0.38-1.14, not significant). NLST: 20% relative reduction (CI 6.8-26.7). https://www.pubmed.gov/31995683/
- F15 [S] EU Council Recommendation 2022: extend screening stepwise to lung (current or former heavy smokers, 50-75), prostate and gastric, based on further research.
- F16 [S] Harms: one LDCT about 0.7 mSv on a modern scanner (about 2 mSv in NLST; 8 mSv for a diagnostic follow-up CT); per-round false positives 23.3% (NLST) vs 10.4% (NELSON); NELSON referral 2.1%; overdiagnosis estimates vary widely (about 10% at worst in NELSON per editorialists); incidental findings: about 1 in 20 need primary-care review and 1 in 25 secondary-care review (SUMMIT).
- F17 [S] Only lung has randomised evidence for CT screening. CT is poorly suited to pancreas surveillance (EUS and MRI preferred). Do not treat stage-specific survival differences as proof that screening causes them (lead-time and length bias, overdiagnosis).

## Mobile CT and CT sites
- F18 [S, weak] A mobile CT truck for coronary imaging, run by Oulun Sydänkeskus, has operated in Northern Finland (sites reported: Oulu, Rovaniemi). The only source is an old Yle article; current status unverified.
- F19 [A] The CT site list (data/ct_sites/ct_sites.csv) has 36 towns: 24 confirmed, 12 likely, researched mostly from search summaries; 3 rows spot-checked and a second pass (2026-11-14) found no contradictions but could not check Turku (Tyks) or Pori; Åland is an inferred row. Private providers and many regional hospitals are missing. Presence of a scanner says nothing about capacity or waiting time.
- F20 [A] The route model's uptake curves, eligible share (7%), costs and "additional participant" estimates are assumptions. "Additional participants" = people the model says would not be screened at a hospital CT; it is not evidence of lives saved.

## Cost model (all assumptions unless noted; ranges in the assumptions register)
- F21 [A] One mobile unit: about 2,900 scans a year at 75% slot fill, about €370 per scan versus about €340 at a hospital CT with spare capacity. A truck does not beat a fixed scanner on cost; it pays off only through additional participants.
- F22 [S] Radiographer pay about €3,560 per month (Duunitori 3,576; Työmarkkinatori median 3,557).

## Area, risk group, capacity and campaign (added 2026-11-14)
- F23 [S + proxy] Risk group: age 50-74, >=20 pack-years, current smoker or quit within 15 years (US 2021 guidance; inside the EU 2022 range). Estimated eligible people: about 120,000 (7.1% of 1.7 million aged 50-74), from verified county smoking rates (THL Sotkanet 4405/4406, 2024) x an assumed factor 0.8 (range 0.55-1.1). No Finnish pack-year data was found.
- F24 [S] Lung-cancer deaths (ICD-10 C32-C34) 2021-2025 from Statistics Finland 13u5: about 2,340 a year. Highest per 100,000 aged 50-74 (proxy: all-age deaths / population 50-74): Lapland 186, Satakunta 176, Kymenlaakso 175, Päijät-Häme 160, Kainuu 158; lowest: Vantaa and Kerava 110, North Savo 120, Central Uusimaa 121. County CT waiting times: not found anywhere; the model assumes 4 weeks (range 2-8) and shows only MODELLED added waits.
- F25 [A] CT volume 35-90 exams per 1,000 inhabitants (Eurostat hospital CT per 100k swings 3,300-9,300 over 2019-2024, series breaks); 5% (2-10%) of it assumed free for screening. Under these assumptions existing CTs cover only about 28% of the annual need of the high-risk group (about 60,000 scans a year), and one truck adds roughly 2,000 scans.
- F26 [A] Campaign model: each unit of intensity raises uptake 30% and sends 3% of non-eligible people aged 50-74 for a scan. At intensity 2 with 60% of ineligible requests filtered and eligible people booked first, national demand is about 78,000 scans a year against 17,000 assumed free; protecting eligible people does not remove the queue (longest added wait about 15 weeks in Kymenlaakso). Without filtering or priority booking, eligible coverage falls sharply.
- F27 [A] Pilot: randomise invitations 1:1 (stratified): control = existing hospital CT, treatment = same invitation plus a mobile or pop-up slot. Primary outcome = scan within 6 months. With control uptake 40% and a 15-point uplift, 173 invitees per arm give 80% power; if 30% of controls leak to the mobile offer the estimate falls to about 10 points; a before/after comparison during a +30% campaign would report 27 extra scans per 100 invitees instead of 15.

## Known unknowns (say "not known" rather than guess)
Finnish pack-year distribution; CT scanners, volumes and spare capacity by county; lung cancer stage by county; symptom-to-diagnosis time by county; CT capacity and waiting times by county; emergency-presentation share; per-scan cost in Finland; whether any county will host a pilot; real uptake of a Finnish lung CT programme.
