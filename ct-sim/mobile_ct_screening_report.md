# Mobile CT screening unit for Finland: evidence, cost model, routing design and pilot

Working paper for the Junction AstraZeneca challenge. Prepared 2026-11-13.
**How the sources were read:** the Cancer Registry screening tables, Statistics Finland tables and the national strategy PDFs were read directly. Every other [S] source (trials, reviews, cost studies, salary pages) was read as a web-search summary only; the primary papers were not opened. Verify each before it goes on a slide.
**Status:** every number is tagged **[S]** sourced (link given), **[M]** from memory of published trials and not re-verified here, or **[A]** our own assumption. Nothing in this paper is a forecast. The model and code are in `src/ctsim/` and `data/`.

---

## 0. Bottom line

1. **Only lung cancer has randomised evidence that CT screening reduces deaths**, and only in heavy current/former smokers aged roughly 50–74. For every other cancer, CT is either the wrong test (pancreas) or used for diagnosis/surveillance by other methods. Everything else a CT truck finds is an *incidental finding*, which is a cost to manage, not a screening benefit.
2. **Finland has no public lung CT screening programme** [S: [Oulu trial paper](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12171981/)]. A truck is a *delivery mode* for a programme that does not yet exist. Pitch it as a pilot to answer the access question, not as a screening programme.
3. **Order of magnitude (central case, wide ranges):** about 120,000 eligible people, about 25,000 scans per year if screening ran nationally at NELSON-like intervals, roughly 40 lung cancer deaths avoided per year (range about 16–76) if trial effects transfer. That is roughly 1–3% of Finland's ~2,400 lung cancer deaths a year [S: [Verkkouutiset/Cancer Registry, 2022](https://www.verkkouutiset.fi/a/tahan-syopaan-kuollaan-nyt-eniten/)].
4. **A truck is not cheaper than a fixed scanner.** At ~75% slot utilisation, one unit costs about €370 per scan versus about €340 at a hospital CT with spare capacity (both [A]). The truck only pays off through **additionality**: people who would not otherwise get scanned. Additionality is the single number the pilot must measure.
5. **Finnish data point away from distance as the main barrier.** In 2024 screening, the lowest participation was in Helsinki and Uusimaa (breast 74.3% in Helsinki vs 85.6% in North Ostrobothnia), and among people whose native language is not Finnish/Swedish/Sámi (breast 60.8% vs 83.2%; colorectal 53.4% vs 74.5%; cervical 56.3% vs 76.2%) [S: Cancer Registry tables in `data/screening/`]. A truck serving remote areas alone would be underused (our prototype: ~700 scans/year in Lapland, about 25% of capacity). Urban outreach to groups with documented barriers is the stronger case.
6. **Recommended next step:** a two-year, single-unit pilot in one mixed urban/semi-rural region with randomised invitation to measure additionality, harms and follow-up capacity. The pilot cannot measure mortality; it measures whether the model is worth a larger trial.

---

## 1. What CT can find before symptoms

### 1.1 Evidence-backed use: lung cancer in high-risk smokers

| Evidence | Result | Source |
|---|---|---|
| NELSON (NL/BE), 10-year follow-up | Lung cancer mortality rate ratio 0.76 (95% CI 0.61–0.94); 2.50 vs 3.30 deaths/1000 person-years. Women 0.67 (CI 0.38–1.14, not significant) | [S] [NEJM 2020 abstract](https://www.pubmed.gov/31995683/), [ESMO](https://esmo.org/oncology-news/ct-screening-reduces-lung-cancer-mortality) |
| NLST (US) | 20.0% relative reduction in lung cancer mortality (CI 6.8–26.7); 6.7% reduction in all-cause death | [S] [NCI PDQ](https://www.cancer.gov/types/lung/hp/lung-screening-pdq), [NLST summary](https://pmc.ncbi.nlm.nih.gov/articles/PMC4356534) |
| EU policy | 2022 Council Recommendation asks member states to extend screening stepwise to lung (current/former heavy smokers, 50–75), prostate and, in some circumstances, gastric, based on further research | [S] [Council doc](https://data.consilium.europa.eu/doc/document/ST-12652-2022-INIT/en/pdf), [Commission release](https://ec.europa.eu/commission/presscorner/api/files/document/print/en/ip_22_7548/IP_22_7548_EN.pdf) |
| Finland | LDCT lung screening is not publicly funded. A 200-person Oulu feasibility trial of current smokers found 6 cancers, 5 at stage I, uptake 96.7% (volunteers) | [S] [Oulu trial](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12171981/) |
| Nordic position | A 2017 Nordic expert review recommended pilot studies; a 2026 Nordic review says implementation needs further evaluation | [S] [Nordic review (KU)](https://researchprofiles.ku.dk/da/publications/lung-cancer-screening-in-the-nordic-countries-approaching-impleme/) |

Eligibility rules differ between trials (US 2021: age 50–80, ≥20 pack-years, quit ≤15 years [S: [AAFP](https://www.aafp.org/about/news/20210325uspstflungcancer)]; Oulu: age 50–74 and ≥15 cigarettes/day for ≥25 years or ≥10/day for ≥30 years [S: Oulu paper]). Women gain less certain evidence in NELSON; that matters for equity framing.

### 1.2 Other cancers: not evidence-backed CT screening uses

| Cancer | CT screening? | Why |
|---|---|---|
| Pancreas | No | CT is "unsuited for surveillance"; EUS and MRI are preferred in high-risk (genetic) individuals; CT sensitivity 53–74% [S: [Springer 2024 review](https://link.springer.com/article/10.1007/s10689-024-00380-5)]. No population screening exists |
| Liver | No (CT) | Surveillance in cirrhosis uses ultrasound ± AFP [M, verify with a hepatologist] |
| Colorectal | No (CT) | Finland uses stool testing (FIT), 73.5% participation in 2024 [S: [Cancer Registry via STT](https://www.sttinfo.fi/tiedote/72173590/kolme-aluetta-erottuu-edukseen-syopaseulonnoissa-helsingissa-osallistuminen-jaa-selvasti-jalkeen?lang=fi)]. CT colonography is a diagnostic option [M] |
| Gastric | No | EU approach is H. pylori testing/surveillance in high-incidence areas [S: Council Recommendation] |
| Breast, cervix | No | Established non-CT programmes (82% and 74% participation 2024) |
| Kidney, others | No | No screening programme; found incidentally [M] |

### 1.3 Incidental findings are not screening benefits

On lung LDCT, most people have non-cancer findings. In the SUMMIT cohort (11,115 UK participants) coronary calcification was seen in 64.2% and emphysema in 33.4%; with a protocol, about 1 in 20 needed primary-care review and 1 in 25 secondary-care review [S: [SUMMIT summary](https://doaj.org/article/692746dcaaef4d76b3535374a9068d7e), [Radiology Business](https://radiologybusiness.com/topics/medical-imaging/diagnostic-screening/incidental-findings-evident-70-lung-screening-exams-few-reported)]. Reported prevalence depends on thresholds (8–40% in older reviews; Korea's programme counts only moderate-or-worse findings, 14–15%) [S: same searches].

I found **no randomised evidence that detecting incidental cancers (thyroid, kidney, etc.) on lung CT reduces mortality**. Treat them as costs and risks to plan for (§3), and say so in the pitch.

### 1.4 Do not treat stage survival gaps as proof screening causes the improvement

Stage I patients live longer than stage IV patients partly because of lead-time bias (the clock starts earlier), length bias (screening finds slow tumours) and overdiagnosis. The model therefore **never converts a stage shift into lives saved**. Outcomes use the trials' measured mortality ratios only, and stage shift appears only as a process indicator. The Oulu result (5 of 6 cancers at stage I) is a feasibility signal from 200 volunteers, not an effect size.

---

## 2. Eligible population, cases found, effect

Computed in `src/ctsim/model.py`; full table in [data/model/monte_carlo_summary.csv](data/model/monte_carlo_summary.csv). Ranges are 5th–95th percentile of 20,000 draws over the assumption ranges; the central column is the mode (a favourable-looking point), so also read the median.

| Quantity | Central | Median | 5th–95th pct | Basis |
|---|---|---|---|---|
| Population aged 50–74 | 1,695,391 | | | [S] Statistics Finland table 11re, 31 Dec 2025 (`pop_50_74` column of `data/routing/municipalities.csv`) |
| Eligible share of 50–74 | 7% | | 4–12% | [A] No Finnish pack-year analysis found. Replace with THL Terve Suomi/FinSote analysis |
| Eligible people | ~119,000 | ~127,000 | 86,000–180,000 | derived |
| Screened people (uptake) | ~59,000 | ~64,000 | 39,000–99,000 | uptake 30–72% [S: London cohort 31% responded; Yorkshire trial 56.5–73.2% by reminder stage] |
| Scans per year (national, steady state) | ~24,600 | ~32,200 | 18,800–54,200 | biennial interval [A] |
| Cancers found per year | ~250 | ~350 | 200–620 | 0.8–1.5% per scan [M] |
| Lung cancer deaths avoided per year | ~39 | ~39 | 16–76 | NELSON baseline 3.3/1000 person-years, RR 0.61–0.94 [S] |
| One-unit equivalents needed | ~9 | ~13 | 7–24 | capacity per unit below |

Context for scale: Finland had about 2,947 new lung and trachea cancers and 2,410 deaths in 2022 [S: deaths from Verkkouutiset/Cancer Registry; cases from a thesis citing the registry, verify at source]. The national target is a 10% cut in cancer mortality [S: National Cancer Strategy 2026–2035], about 1,330 deaths a year, so even full national lung screening would deliver on the order of 1–6% of it. Be careful not to oversell.

Finland-specific caveats: the Finnish eligible group may have a different baseline risk than NELSON's; trials ran multiple rounds with high adherence; women had weaker evidence; the estimate assumes trial effects transfer to Finnish services.

---

## 3. Harms and constraints

| Issue | Evidence | What it means for a mobile unit |
|---|---|---|
| **Radiation** | One LDCT ≈ 0.7 mSv on a modern scanner [S: [PubMed](https://pubmed.ncbi.nlm.nih.gov/29651767/)]; ≈2 mSv in NLST, ≈8 mSv for the diagnostic follow-up CT [S: [ATM](https://atm.amegroups.org/article/view/15840/html)]. Annual scans from 55 to 80 raise nominal lifetime cancer risk by ~0.13% (men) to ~0.30% (women) [S: PubMed]. Milan COSMOS: roughly one radiation-induced major cancer per 108 lung cancers detected [S: [Diagnostic Imaging](https://diagnosticimaging.com/view/radiation-exposure-ct-lung-cancer-screening)]. Linear no-threshold risk is debated | Small but not zero; weighted against mortality benefit in trials. Dose protocol, shielding and STUK licensing must be pre-approved [A: STUK role not verified] |
| **False positives** | NLST per-round false-positive 23.3%; NELSON 10.4%; Lung-RADS lowers NLST-style rates [S: [NLST summary](https://pmc.ncbi.nlm.nih.gov/articles/PMC4356534), PubMed]. NELSON: referral 2.1%, 9.2% had ≥1 extra CT [S] | Each truck stop generates follow-up demand at fixed hospitals. Model includes 5–23% extra CT |
| **Overdiagnosis** | "Varies greatly" (NCI); editorialists judge ~10% at worst in NELSON [S: [NCI PDQ](https://www.cancer.gov/types/lung/hp/lung-screening-pdq), Radiology Business]. NLST had 1,060 vs 941 cancers; interpretation disputed | Cannot be measured in a 2-year pilot. Needs registry follow-up |
| **Follow-up capacity** | Positives need diagnostic CT/PET, bronchoscopy/biopsy and multidisciplinary review. Finland has ~16.3 radiologists per 100,000 [S: [AuntMinnie Europe](https://www.auntminnieeurope.com/medical-legal-and-practice/organized-radiology-issues/article/15828586/uk-radiologist-staffing-lags-eu-peers-rcr-census-shows)] and ~17 CT scanners per million [S, weak aggregator: [theglobaleconomy.com](https://www.theglobaleconomy.com/rankings/computed_tomography_scanners_per_million_people/European-union/)] | A screening truck adds no downstream capacity. I found **no Finnish CT waiting-time data**. Ask counties |
| **Incidentals** | §1.3 | Needs a written protocol for who acts on coronary calcium, emphysema, nodules outside the lung |
| **Eligibility identification** | Finland has no national smoking register as far as I know [M, verify] | How you find the right 50–74 smokers is unsolved: questionnaire via health centres, Kela/occupational data, or self-referral. Self-referral favours the already-engaged and could widen inequity |

---

## 4. Would a mobile unit improve access over existing services?

**Evidence for access gains elsewhere:** UK community CT units were designed because travel was a barrier [S: [Yorkshire trial](https://eprints.whiterose.ac.uk/id/document/3455626); [Cheshire/Merseyside](https://www.siemens-healthineers.com/en-uk/press-room/press-features/lhch-mobile-lung-screening); [scoping review](https://jtd.amegroups.org/article/view/92337/html)]. Lower response in the UK was linked to current smoking (adjusted OR 0.44) and deprivation (OR 0.58, most vs least deprived) [S: search summary of the Yorkshire Lung Screening Trial; verify]. A 2026 Swedish risk-based pilot (Region Stockholm) reportedly found equitable attendance, a counterexample [S: secondary summary only; study not opened].

**Finnish evidence, from our extracted Cancer Registry tables (2024):**

| Group | Breast | Colorectal | Cervical |
|---|---|---|---|
| Domestic native language | 83.2% | 74.5% | 76.2% |
| Other / missing | 60.8% | 53.4% | 56.3% |
| Primary education | 63.5% | 61.5% | n/a |
| Tertiary education | 85.9% | 79.3% | n/a |
| Lowest county | Helsinki 74.3% | Helsinki 69.6% | North Karelia ~68% |
| Highest county | N. Ostrobothnia 85.6% | South Savo 76.9% | S. Ostrobothnia / S. Savo ~82% |

The gaps follow language, education and (partly) metropolitan areas, not remoteness (Kainuu breast 84.1%). That shifts the truck from "reach the countryside" toward "reach people who face other barriers". Limits: this is existing screening participation, not lung; the language group includes missing data; the remote-vs-urban comparison is county-level.

**Verdict:** a truck improves access only where (a) people live far from a CT or (b) the unit's location, hours and staffing remove non-distance barriers (interpreters, workplace or community venues, walk-in). In our prototype (§6), remote-only deployment is underused; mixed urban-fringe/semi-rural routes work better. Present the truck as one of several delivery options and compare it with cheaper alternatives (fixed-site pop-up hours, interpreter-supported invitations, evening slots, patient navigation).

---

## 5. Cost and feasibility model

Code: [src/ctsim/model.py](src/ctsim/model.py). Parameters with ranges and tags: [data/model/assumptions.csv](data/model/assumptions.csv). Regenerate with `python -m ctsim model`.

### 5.1 Central case, one unit (EUR, annual)

| Item | Central | Range | Tag |
|---|---|---|---|
| Vehicle/trailer, shielding, power, heating (capex) | 400,000 | 250,000–700,000 | [A]; US sources put whole units at $300k–1.5M [S: [STS](https://www.sts.org/node/8300)] |
| CT scanner, install, QA (capex) | 350,000 | 250,000–550,000 | [A]; US source: scanner alone $150–300k [S: STS] |
| Annualised capex (8-yr life, 3%, 10% residual) | ~98,000 | 83,000–143,000 | derived |
| Scanner service contract | ~35,000 | 7–12% of scanner price | [A] |
| Vehicle maintenance | 18,000 | 10,000–30,000 | [A] |
| Fuel/energy, 45,000 km at €0.8/km | 36,000 | 10,000–84,000 | [A] |
| Insurance | 14,000 | 8,000–25,000 | [A] |
| Staff: 3.5 FTE × €3,600/month × 12 × 1.35 on-costs × 1.15 cover | ~235,000 | 210,000–297,000 | salary [S: [Duunitori](https://duunitori.fi/palkat/rontgenhoitaja) 3,576; [Työmarkkinatori](https://tyomarkkinatori.fi/ammatit/rontgenhoitaja) median 3,557]; FTE and multipliers [A] |
| Host sites, 60 stops × €600 | 36,000 | 12,000–150,000 | [A] |
| **Fixed cost per year** | **~472,000** | 458,000–594,000 (5–95th pct) | |
| Variable per scan: reading (4 min at €150/h) €10 + admin €10 + extra CTs + work-up + incidental review + cessation | ~208 | 199–358 | [A], proportions from NELSON/SUMMIT [S] |

### 5.2 Throughput and utilisation

Capacity = scanning days × slots/day × fill rate. Central: 170 days × 22.5 slots × 75% ≈ **2,870 scans/year** (5–95th pct 1,760–3,460). Slot length 15–30 minutes (one UK source puts the scan itself at about 10 minutes [S: Siemens]); 120–200 scanning days to allow for winter, relocation and servicing [A].

| Slot fill rate | Scans/year | Cost per scan (€) | vs fixed-site scan (€338) |
|---|---|---|---|
| 50% | 1,912 | 454 | 1.35× |
| 60% | 2,295 | 413 | 1.22× |
| 70% | 2,678 | 384 | 1.14× |
| 80% | 3,060 | 362 | 1.07× |
| 100% | 3,825 | 331 | 0.98× |

The fixed-site comparator (€130 acquisition + same variable costs) is [A]; I found no Finnish per-scan cost. **A truck does not beat a fixed scanner on cost even at full use**, so viability depends on additionality, not utilisation alone.

### 5.3 The metric that decides: cost per additional participant

Incremental cost = truck fixed cost − (non-additional scans × fixed-site cost) + (additional scans × variable cost). With additionality *a* (share of truck scans who would otherwise not be scanned):

| Additionality | Cost per additional scan (€) | Deaths avoided per unit-year (additional only) | Cost per death avoided (€) |
|---|---|---|---|
| 10% | 683 | 0.5 | 431,000 |
| 20% | 510 | 0.9 | 322,000 |
| 35% (central) | 436 | 1.6 | 275,000 |
| 50% | 407 | 2.3 | 257,000 |
| 100% | 372 | 4.5 | 235,000 |

Monte Carlo (all assumptions varying): cost per death avoided has a median of ~€510,000 and a 5th–95th range of ~€260,000–1.24M. For reference, a fixed-site scan comes to ~€213,000 per death avoided under the same assumptions. These are cost-per-death figures, not cost-per-QALY, so they are not directly comparable with published Nordic cost-effectiveness results, which range widely (Norway ~NOK 212,000 to 704,000 per QALY in two models; Denmark found higher costs than current care) [S: [Norway study 1](https://duo.uio.no/handle/10852/97045), [Norway study 2](https://duo.uio.no/handle/10852/104200)].

**What moves the answer most** (one-at-a-time, [data/model/tornado.csv](data/model/tornado.csv)): the assumed mortality effect (RR), screening interval (annual doubles the cost per death avoided), baseline risk in the screened group, slot length, scanning days and fill rate, and additionality. Vehicle price matters much less than whether the unit is busy and whether it reaches the right people.

### 5.4 Operational feasibility notes
Winter operation at −20 °C and below needs a heated, power-connected shelter or garage at each stop (cost in "host sites" is a guess). Radiation licensing, vehicle homologation and software (RIS/PACS, teleradiology reporting) are real lead-time items; I have not verified Finnish lead times. Radiologist reading capacity should be pre-agreed with the county.

---

## 6. Route optimisation

### 6.1 Problem
Choose where one unit stops, for how many days, and in which order, to maximise screening of people who are at high risk and would otherwise be missed, within a working-day budget.

### 6.2 Data inputs

| Input | Status | Source / need |
|---|---|---|
| Municipality centroids (308) | **Have** | Statistics Finland geoserver (EPSG:3067) |
| Population aged 50–74 by municipality | **Have** | Statistics Finland 11re, 2025 |
| Foreign-language share by municipality (all ages) | **Have** (proxy) | Statistics Finland 11rm; 50–74 share would be better |
| Sparsely populated share | **Have** | Statistics Finland 15k6 |
| Uptake ratio for non-domestic language | **Have** | Cancer Registry 2024: 0.73 breast, 0.72 colorectal, 0.74 cervical |
| Eligible share per municipality (pack-years) | **Missing** | Needs THL Terve Suomi/FinSote analysis by region, education, sex. Used uniform 7% [A] |
| Fixed CT locations | **Partly have** | Researched list of 36 towns (24 confirmed, 12 likely), see §6.7. No national register found. Waiting times and scanner capacity still missing |
| Road travel times | **Missing** | Used straight line × 1.3 at 60 km/h [A]. Replace with Digiroad/OSRM |
| Municipality → wellbeing county mapping | **Missing** | Needed to align with county pilots |
| Stop venues (car parks, heated halls) | **Missing** | Ask municipalities |
| Deprivation/income/education by area | **Missing** | Statistics Finland small-area data (not used) |

### 6.3 Formal model
- Eligible persons in municipality *m*: E_m = pop50–74_m × eligible share.
- Fixed-site uptake: u_fixed(m) = u0 · exp(−d_fixed(m)/D_F) · (1 − f_m·(1−0.73)).
- Mobile uptake at stop *s*: u_mob(m,s) = u0 · exp(−d(m,s)/D_M) · (1 − f_m·(1−θ)), with θ = 0.90 meaning outreach recovers part of the minority gap [A].
- Additional participants: Δ(m,s) = E_m · max(0, u_mob − u_fixed) / interval.
- **Objective:** maximise Σ w_m · Δ(m, s(m)), with equity weight w_m = 1 + λ·min(f_m/0.10, 3) (λ is a policy choice, default 0.5).
- **Constraints:** scanning days + setup (0.5 day per stop visit) + driving days ≤ 200; scans at a stop ≤ days × scans/day; each municipality served by one stop within 60 km; two visits per stop per year (winter/summer).
- **Algorithm:** sequential greedy (maximal-coverage / orienteering heuristic). At each step add 2 scanning days at the stop with the best equity-weighted additional scans per marginal day, where marginal days include setup and cheapest-insertion travel. Final route by nearest-neighbour + 2-opt. It runs in under a second on all 308 municipalities.
- **Cost:** feeds route km and stop count into the §5 model.

### 6.4 Prototype results (not recommendations)
Source: [data/routing/route_results.csv](data/routing/route_results.csv). All depend on the assumed uptake curves and the placeholder CT list.

| Scenario | Stops | Scans/yr | Additional/yr | km/yr | Working days used | € per additional |
|---|---|---|---|---|---|---|
| National, population-greedy | 30 | 2,778 | 565 (20%) | 2,332 | 199 | 474 |
| National, access-gap objective | 50 | 2,205 | 1,170 (53%) | 8,713 | 199 | 492 |
| National, access + equity weight 2.0 | 42 | 2,324 | 1,150 (50%) | 9,474 | 199 | 473 |
| Helsinki metro (40 km) | 6 | 3,240 | 264 (8%) | 242 | 198 | 286 |
| Tampere 100 km | 27 | 2,844 | 578 (20%) | 1,795 | 199 | 449 |
| Seinäjoki 120 km | 33 | 1,863 | 448 (24%) | 2,394 | 148 | 783 |
| Kajaani 150 km | 25 | 1,048 | 267 (26%) | 2,694 | 93 | 1,446 |
| Rovaniemi 150 km (Lapland) | 12 | 702 | 139 (20%) | 1,728 | 57 | 2,671 |

Reading it honestly:
- A single unit can serve far more people than live far from a CT in most counties. **Remote-only regions leave the unit idle for 100+ days.** Lapland: 702 scans a year.
- The Helsinki-metro result looks cheap per additional scan (€286) only because the unit is busy; it adds few extra participants (8%) because the model's only urban barrier is language. The real Helsinki participation deficit (74.3% vs 81.6% national breast) is not explained by distance or language alone, so the model understates the urban case. Calibrating to county data is the next step.
- The "53% additional" national figure is produced by the assumed distance-decay (D_F = 120 km). It is a modelling artefact, not evidence of additionality.

### 6.5 How I tested it
Run `python -m ctsim tests` (19 tests across model, routing, scenarios and the local server) and `python -m ctsim sensitivity` (writes [data/routing/sensitivity.csv](data/routing/sensitivity.csv)). All checks pass:
1. **Planted structure:** on a synthetic map with a large city that has CT and three remote villages, the optimiser never spends days in the city, matches the best brute-force subset (170 vs 170 additional), and beats population-greedy by 4× under a tight budget.
2. **Determinism, budget and capacity constraints:** working days ≤ 200; scans ≤ capacity; adding working days never lowers the objective.
3. **Sensitivity and regret:** each key parameter perturbed (decay scales, minority factor, eligible share, base uptake). The central-optimal plan loses 1–4% of benefit under changes to distance decay and minority factor, but **13–28% when eligible share or base uptake changes**. That means the route must be re-optimised once the pilot measures real uptake. The "<35%" pass threshold I chose is arbitrary, so read the regret table, not the green tick.
4. **Fixed-site leave-out:** dropping six placeholder CT towns raises additional participants (1,587 vs 1,178), as it should.

Still to do before trusting it: validate uptake curves against real participation by distance (needs municipality-level screening data); replace straight-line distances with road network times; add time windows and venue availability; model repeat rounds and return visits; compare with an exact solver (e.g., a MILP on a county-sized instance); test equity weights with stakeholders.

### 6.6 Robustness sweep (what survives wrong assumptions)
`python -m ctsim robust <scenario> --n 100` (and the "Run robustness sweep" button in the map UI) draws many plausible worlds that vary eligible share, base uptake, both distance-decay scales and minority uptake with outreach, and drops a random 15% of the placeholder CT towns in each. It re-optimises in every world and scores candidate plans by regret on 50 fresh worlds not used to build any plan. Outputs: [data/robust/](data/robust/). The ranges are planning ranges, not estimates.

| Scenario | Best plan's mean regret | 90th percentile | Biggest unknowns (expected loss from not knowing) |
|---|---|---|---|
| Tampere 100 km | 11% | 25% | eligible share 13.5%, CT sites 5.0%, base uptake 4.9% |
| Whole country | 26% | 40% | CT sites 18.5%, eligible share 9.6%, base uptake 7.5% |
| Helsinki metro 40 km | 13-15% | 35% | eligible share 8.2%, base uptake 6.3%, CT sites 5.2% |

What it says, and its limits:
- **The route matters less than the inputs.** Candidate plans differ by only a few points of regret, which is within the noise of 50 validation worlds. Even the best plan loses 11-26% of its benefit on average. Measuring eligible share, base uptake and which towns have CT capacity would reduce the loss more than polishing the route.
- **Nationally, the CT site list is the largest single unknown (18.5%).** That list is a placeholder in this project, so getting the real one is the first data task.
- **Distance decay and the minority-outreach factor barely change where the truck goes** (about 0-1%). Practically, in these scenarios the equity weighting does not move the route, because the foreign-language share is a coarse all-age proxy. A better minority indicator (50-74, by area) is needed before the equity claim can be tested.
- Regret is measured against the best plan found by a greedy heuristic, not a proven optimum.
- **Speed:** the worlds are independent, so the sweep runs in parallel (local processes, or Modal containers) with results identical to the sequential run for the same seed. Whole country, 100 worlds: 24 s sequential, about 10 s on 4 local workers, 4-12 s on Modal (warm vs first run). Timings are from one machine and one run each.

### 6.7 Researched CT site list
No national open register of CT scanner locations turned up, so the list was assembled from public county, hospital and procurement pages by four parallel research passes (south, southwest and west, east, north). Result: [data/ct_sites/ct_sites.csv](data/ct_sites/ct_sites.csv), 48 rows covering 36 municipalities, with source URL, evidence, and a confirmed/likely flag per row. Manual corrections are in [overrides.csv](data/ct_sites/overrides.csv) with reasons. Build it with `python -m ctsim ctsites`; choose it in a scenario with `"ct_sites": "confirmed+likely"` (also the map UI default).

How far to trust it:
- **Spot-checked directly:** Joensuu (CT only at the central hospital), Kokkola (CT only at the central hospital) and Peijas in Vantaa. All three matched the source pages.
- **Second verification pass (2026-11-14, two research agents, results in [verify_south_west.csv](data/ct_sites/verify_south_west.csv) and [verify_east_north.csv](data/ct_sites/verify_east_north.csv)):** nothing was contradicted. Upgraded to confirmed: Lahti, Riihimäki, Pietarsaari. Downgraded to likely: Kuusamo (a new CT is only being procured), Iisalmi and Varkaus (old snippet only). Forssa is excluded from routing on weak negative evidence. Åland's central hospital is added as an inferred row. Tyks (Turku) and Pori could not be checked because the county pages failed to load, so they stay 'likely'. Many checks again relied on search snippets, so treat 'confirmed' as 'a source says so', not as audited.
- **Weaker evidence:** Iisalmi and Varkaus (an old page seen only as a snippet), Mikkeli and Savonlinna (inferred), and the Lapland rows (Rovaniemi and Kemi are inferred from central-hospital status). Turku, Lahti and Pori are 'likely' only, which understates them: Turku is a university hospital and Lahti and Pori have PET/CT or SPECT/CT hybrids.
- **Rules applied:** hybrid-only evidence (PET/CT, SPECT/CT) is downgraded to likely; dental cone-beam and coronary-only private sites and the mobile truck never count as fixed sites; private providers are excluded from routing by default.
- **Gaps, not "no CT":** Salo, Rauma, Jämsä, Ylivieska, Kemijärvi and Sotkamo were in the placeholder list but have no evidence either way, so they are absent from the researched list. Five towns appear that the placeholder lacked (Forssa, Oulainen, Riihimäki, Sastamala, Valkeakoski). Private provider coverage is thin. Presence of a scanner says nothing about capacity or waiting time.

Effect on the plan (one unit; [route results](data/routing/route_results.csv) were not regenerated, these were run with `ctsim scenario` variants):

| Scenario | CT list | Stops | Extra participants/yr | km/yr | € per extra |
|---|---|---|---|---|---|
| National | placeholder | 49 | 1,178 | 9,132 | 490 |
| National | researched, confirmed + likely | 45 | 1,226 | 8,468 | 472 |
| National | confirmed only (stress test) | 19 | 1,755 | 2,380 | 367 |
| Tampere 100 km | placeholder / researched | 27 / 26 | 578 / 483 | 1,795 / 1,737 | 449 / 468 |
| Rovaniemi 150 km | placeholder / researched | 12 / 12 | 139 / 167 | 1,728 / 1,728 | 2,671 / 2,284 |

- **Swapping the placeholder for the researched list barely changes the plan** (national extra participants +4%). The placeholder was not badly wrong.
- **"Confirmed only" changes it a lot, but that is an artefact:** it drops Turku, Lahti, Pori, Rovaniemi and others for lack of a source, which invents gaps. Treat it as a lower bound on CT access (an upper bound on the gap), not as a scenario.
- **The CT list is still the largest single unknown nationally** in the robustness sweep (19.4% expected regret with the researched list, 18.5% with the placeholder; both vary a few points with the random draws), which is why it should be verified with the counties.
- **A mobile CT already operates in Finland:** Oulun Sydänkeskus runs a CT truck for coronary imaging in Northern Finland, built with Siemens Healthineers. Its sites were reported as Oulu and Rovaniemi; the only source found is an old Yle article, so its current status is unverified. It is a feasibility reference and a possible partner, not evidence for lung screening.

---

## 7. Realistic pilot proposal

**Question:** does a mobile LDCT unit reach people a fixed site does not, at acceptable harm and follow-up burden, in Finland?

**Design (proposal, to be refined with clinicians and a statistician)**
- **Setting:** one wellbeing services county with a mix of urban fringe, semi-rural municipalities and documented minority communities. Candidates by prototype: Pirkanmaa-type (Tampere region) for utilisation, or Uusimaa for minority outreach. The county must also agree to take referrals.
- **Population:** age 50–74 with heavy smoking history (Oulu-style criteria or a risk model), identified through health-centre records and a short questionnaire. How eligible people are identified is the first thing to resolve.
- **Randomisation:** eligible invitees randomly offered (a) fixed-site CT only or (b) choice of fixed-site or mobile stop. Additionality = difference in completed scans between arms, overall and by language and education. Back-of-envelope sample for a 15-point uptake difference (45% vs 60%, 80% power, 5% significance): roughly 170 invitees per arm, and several times more for subgroup analysis (my own calculation). Check with a statistician.
- **Duration and volume:** 24 months, one unit, about 5,700 scans at central capacity (roughly 3,500–6,900 across the range), about 55 screen-detected cancers.
- **Budget:** about €1.0M per year at central assumptions (€380–610 per scan, 1,800–3,500 scans); about €2M over two years. All [A].
- **Prerequisites:** ethics approval, STUK radiation licence, written incidental-findings protocol, hospital agreement to a defined time standard for follow-up, data linkage with the Cancer Registry, interpreter and cessation services.

**Pre-registered measures (proposed thresholds, to agree with mentors and clinicians):**

| Measure | Go if | Why |
|---|---|---|
| Additionality | ≥30% of mobile attendees would not have attended a fixed site | At ≥70% fill this keeps cost per additional scan ≲ €500 in our model |
| Slot fill | ≥70% | Below ~60% the truck costs >1.2× a fixed scan |
| Minority uptake ratio | ≥0.85 of domestic-language uptake (vs 0.72–0.74 in current screening) | Tests the equity claim directly |
| Extra-imaging rate and diagnostic work-up | NELSON-like (≈9% extra CT, ≈2% work-up), not NLST-like (≈23% false positive) | Controls harm and downstream load |
| Time from positive scan to work-up | Agreed with the county (e.g., within 28 days for ≥90%) | The truck adds no capacity downstream |
| Stage at diagnosis | Reported as a process indicator only | Not evidence of benefit (§1.4) |
| Radiation, incidental findings, adverse events | Reported | Needed for any scale-up decision |

**Stop rule:** if additionality is below about 15%, the money is better spent on invitations, fixed-site hours and navigation.

**What the pilot cannot show:** mortality benefit and overdiagnosis. Those rely on the trials (NELSON, NLST) and long-term registry follow-up.

### Evidence that decides whether the idea is worth pursuing
1. Finnish pack-year data to size the eligible population and its regional spread.
2. Fixed-site CT capacity and waiting times by county, to prove real gaps or spare capacity.
3. Measured additionality and minority uptake from the pilot.
4. Whether a decision to introduce lung screening in Finland is made at all (FICAN, the Ministry, or a county research-led pilot).
5. A Finnish cost per scan and a mobile-unit quote.
6. Comparison against cheaper ways to raise uptake among the same groups.

---

## 8. What I could not verify, and what to ask mentors

**Not verified (treat as open):**
- Finnish eligible-population share, smoking pack-year distribution by age, and regional smoking prevalence.
- Lung cancer new cases for 2023–2024 and stage-specific Finnish survival (stage missing for 58% of cases).
- Finnish CT waiting times and scanner capacity, teleradiology availability and STUK licensing timelines. The CT site list is researched but incomplete (see section 6.7).
- Per-scan cost in Finland; mobile-unit prices in euros.
- Detection rate per scan (~1%), liver/colon statements in §1.2 and the absence of a Finnish national smoking register (marked [M]).
- Cost-effectiveness: only context from Norwegian and Danish studies; no Finnish analysis found.

**Questions for AstraZeneca mentors:**
- Kaisa Kaitila (Medical Affairs): current Finnish view on lung LDCT screening; stage and survival numbers she would stand behind; how to identify eligible smokers.
- Hanna Toivola (Diagnostics): realistic CT capacity and radiologist reading constraints; incidental-finding handling.
- Joanna Tuormaa (Business Excellence): which wellbeing county could host a pilot and what evidence its leaders would need.

---

## 9. Files

| File | What |
|---|---|
| [src/ctsim/model.py](src/ctsim/model.py) | Cost, capacity and outcome model with Monte Carlo and sensitivity |
| [src/ctsim/routing.py](src/ctsim/routing.py) | Route/stop optimiser and tests |
| [src/ctsim/fetch.py](src/ctsim/fetch.py), [src/ctsim/screening.py](src/ctsim/screening.py) | Data extraction |
| `data/model/` | Assumptions, Monte Carlo summary, tornado, utilisation and additionality sweeps |
| `data/routing/` | Municipality table (308 rows, with lat/lon), route results, sensitivity table |
| `data/screening/` | Cancer Registry 2022–2024 screening tables (breast, cervical, colorectal) |


---

## 10. Update 2026-11-14: risk group, area data, CT capacity, campaign demand and a randomised pilot

The map planner now defaults to an **area model** (`risk_model: "area"`): eligibility from verified smoking rates, places weighted by lung-cancer mortality, county CT capacity limiting existing access, and an optional awareness campaign. The old uniform-share model is still available (`"risk_model": "uniform"`) and reproduces sections 5-6.

### 10.1 What is verified, proxy, assumed or missing
Full table with actions: the **Gap finder page, section "Data status"** (also `data/gap/indicators.json`).

| Item | Status | Source or reason |
|---|---|---|
| Lung-cancer deaths by county, 2021-25 (ICD-10 C32-C34) | verified | Statistics Finland table 13u5, read via API (about 2,340 deaths a year) |
| Daily smoking by county, 20-64 and 65+ | verified | THL Sotkanet 4405 and 4406, 2024 |
| Population by municipality and age | verified | Statistics Finland 11re, 2025 |
| Screening participation by county and group | verified | Cancer Registry tables, 2024 |
| Lung deaths per 100k aged 50-74 | proxy | all-age deaths over the 50-74 population; not age-standardised |
| Eligible high-risk people by municipality | proxy | verified smoking x an assumed factor 0.8 (0.55-1.1); central total about 120,000 (7.1% of those aged 50-74) |
| Hospital CT locations | proxy | researched list, 36 towns (section 6.7) |
| Finnish pack-year distribution | **gap** | none found; needed from THL/Findata |
| CT volume and spare capacity by county | **gap / assumed** | Eurostat national hospital CT exams swing 3,300-9,300 per 100k (series breaks); model uses 35-90 per 1,000 inhabitants and 5% (2-10%) free for screening |
| **CT waiting times by county** | **gap** | none found anywhere. Template for counties' figures: `data/area/ct_waits_TEMPLATE.csv`; a filled `ct_waits.csv` replaces the 4-week assumption |
| Campaign effect on uptake and spill-over | assumed | +30% uptake and 3% of non-eligible people seeking a scan per unit of intensity |

### 10.2 The risk group and where it lives
Group: age 50-74, at least 20 pack-years, current smoker or quit within 15 years. Basis: US Preventive Services Task Force 2021, the EU Council 2022 recommendation (50-75, heavy current or former smokers) and the NELSON and NLST trials; the Oulu pilot used a stricter definition. Only lung cancer has randomised evidence that CT screening reduces deaths. People cannot be listed from public data; the model estimates counts per municipality.
- **Most eligible people (estimate):** Southwest Finland 11,600; Helsinki 9,400; Pirkanmaa 9,200; West Uusimaa 8,800; North Ostrobothnia 8,500.
- **Highest lung-cancer deaths per 100,000 aged 50-74 (verified deaths, proxy denominator):** Lapland 186; Satakunta 176; Kymenlaakso 175; Päijät-Häme 160; Kainuu 158. Lowest: Vantaa and Kerava 110.
- The planner weights places by this county mortality (relative to the national rate) as well as by language-minority share, so with the same effort it prefers high-mortality areas.

### 10.3 CT capacity and waiting times: what can and cannot be said
**Observed county CT waiting times and capacity do not exist in anything I could find, so the "areas with the longest waits" cannot be identified from data.** What the model gives instead is **modelled pressure**: with CT volume spread per head and 5% free for screening, eligible demand exceeds free capacity in every county, most in Kymenlaakso (+4.0 weeks), East Uusimaa and Satakunta (+2.8), Kanta-Häme (+2.4). These rankings mainly reflect high smoking rates under uniform capacity per head; they are not measurements. Under these assumptions existing CTs cover about **28% of the annual need** of the high-risk group (about 60,000 scans a year; about 17,000 free), and one truck adds about 2,000 scans.

### 10.4 Optimising for reach of high-risk people (area model, one unit)
| Area | Extra participants/yr | Stops | km/yr | € per extra | High-risk need covered: hospital CTs only to with truck |
|---|---|---|---|---|---|
| Whole country | 1,727 | 32 | 6,658 | 400 | 28% to 31% |
| Lapland (Rovaniemi 150 km) | 476 | 12 | 1,825 | 969 | 23% to 50% |
| Tampere 100 km | 890 | 27 | 1,778 | 413 | 34% to 49% |
| Whole country, old uniform 7% model | 1,226 | 45 | 8,468 | 472 | n/a |
Coverage is measured on the municipalities in the area shown and depends on the assumed capacity; it is not an observed figure. Existing access (distance to the nearest CT, county free capacity) lowers fixed-site uptake before the truck's plan is optimised, so the truck goes where hospital access is weakest or saturated and where mortality is higher.

### 10.5 Campaign demand: staying targeted without overwhelming services
National, one year, modelled (`campaign_intensity`, `triage`, `priority_eligible`):
| Scenario | Scans wanted by eligible / ineligible people | Free capacity | Eligible need covered (hospital CTs only) | Longest added wait |
|---|---|---|---|---|
| No campaign | 25,000 / 0 | 17,000 | 28% | +4.0 weeks (Kymenlaakso) |
| Campaign 2, 60% of ineligible requests filtered, eligible booked first | 40,000 / 38,000 | 17,000 | 28% | +14.8 weeks |
| Campaign 2, 80% filtered, eligible booked first | 40,000 / 19,000 | 17,000 | 28% | +11.4 weeks |
| Campaign 2, no filtering, everyone queues together | 40,000 / 94,000 | 17,000 | 8% | +24.8 weeks |
What it shows: a campaign mostly generates demand from people who are not eligible. Filtering requests and booking eligible people first protects screening of the high-risk group, but the queue grows anyway (the gap equals about 21 truck-years at intensity 2); the plan stays targeted only if capacity is added or invitations are paced. All campaign effects are assumptions; the pilot should measure them.

### 10.6 Randomised pilot
Full protocol: [docs/pilot_design.md](docs/pilot_design.md); calculator and simulation on the Gap finder page. Randomise eligible residents 1:1, stratified by distance to CT, language and sex: control invited to an existing hospital CT, treatment invited with a mobile or pop-up slot as well. Outcome: a scan within 6 months. Additional scans per 100 invitees = 100 x (uptake B - uptake A); scans that would have happened anyway = uptake A. At control uptake 40% and a 15-point uplift, 173 invitees per arm give 80% power; 600 per arm give 90% power for a 10-point uplift. Simulations: 30% leakage of controls to the mobile offer shrinks the estimate from 15 to about 10 points; a before/after comparison during a +30% campaign would report 27 extra scans per 100 invitees instead of 15.

### 10.7 What still needs confirming
1. Finnish pack-year distribution (THL FinSote/Terve Suomi via Findata): the biggest uncertainty in the eligible estimate.
2. County CT volumes, spare capacity and waiting times (counties' radiology departments; THL Hilmo/Avohilmo): replaces the three assumptions behind section 10.3 and 10.5.
3. Age-standardised county lung-cancer rates from the Cancer Registry (replaces the proxy).
4. The CT site list (section 6.7), especially Turku (Tyks), Pori and the Lapland hospitals.
5. Whether a campaign is planned and its design, so the spill-over and uptake assumptions can be replaced.
