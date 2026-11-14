# Gap analysis: challenge, Pohde equity deck and national strategy versus the simulator, with cost, lives-saved and resource estimates

Prepared 2026-11-14. **No simulator code was changed for this document.** The only new files are this analysis, a copy of the slide deck in the project folder, and a small reproducible estimate script (`docs/analysis/lives_saved_estimate.py`).

Evidence tags: **[S]** sourced, **[S-weak]** read only as a search summary or secondary report, **[M]** recalled from published work and not re-verified, **[A]** our assumption, **[calc]** arithmetic on tagged inputs.

## 0. Bottom line

1. **The simulator answers one part of the challenge well: "recommend what to do" for lung CT screening delivery, with honest data labelling.** It does not yet answer "identify the gap" and "locate it in the pathway" from data. It only describes them, and mostly from team notes.
2. **Two facts found in the provided documents change our framing.** The implementation roadmap says a lung-cancer screening pilot **started in January 2026 (Helsinki and eight wellbeing counties in five regions; see section 9)**, and a **National Lung Cancer Programme 2026-2035** launched in May 2026. Our pitch and pilot proposal currently read as if no such activity exists. [S: roadmap, section 2.3.4; lung programme preprint]
3. **The deck's central message is structural inequity along the whole pathway** (parallel public, occupational and private systems; the inverse care law; delays that accumulate; education-linked differences in treatment and survival). The simulator models none of these except screening participation by language and education. It models a truck, which is a small lever compared with what the deck describes.
4. **Lives saved (indicative, steady state, trial effect assumed to transfer): about 40-65 lung-cancer deaths avoided a year nationally (plausible range about 20-110)**, roughly 2-3% of Finland's 2,293 yearly lung-cancer deaths. Two independent methods agree on the order of magnitude, not the figure. [calc; section 5.2]
5. **Screening itself costs about €8 million a year at national scale on our unit costs (range roughly €6-18 million) [A].** The strategy does **not** estimate any saving from earlier detection; its savings come from prevention (smoking and alcohol) and palliative care. Treatment-cost savings from earlier lung-cancer detection are therefore unproven, and on current evidence probably cover only part of the cost. The case rests on health gain, not on savings. [S for the strategy statement; A for the rest]
6. **Who pays:** wellbeing services counties organise and fund screening from state funding; it is free for participants; the roadmap says the state budget will earmark money to launch new national programmes but gives no figure. Benefits (lower treatment costs, fewer reimbursed outpatient drugs) partly fall on other budgets. [S; section 5.1]
7. **Top five changes, in order:** (1) align the app and pitch with the existing pilot and national programme; (2) add a cost-and-benefit panel tied to Goal 3 indicators; (3) add an education and income (SES) layer, the deck's main equity theme; (4) add a pathway-delay module with public versus occupational/private routes; (5) recalibrate baseline mortality and expose deaths avoided. Details in section 7.

## 1. What was read

| Source | Read | Notes |
|---|---|---|
| **Pohde deck**, "Equitable Cancer Care - How Can We Ensure It in Finland", H. Kuitunen, 30.10.2026, 16 pages | all pages | Copy saved in the project folder |
| **Challenge brief** (Junction) | full text, pasted earlier | Task, minimum requirements, judging weights, mentors |
| **National Cancer Strategy 2026-2035** (PDF) | targeted sections: the four goals and indicators, screening (2.3, 2.4), Goal 3 (3.1, 3.2), costs and savings | A 60-plus page document; not every page was re-read |
| **Implementation roadmap 2026-2031** (PDF) | targeted: screening actions 2.3.2-2.3.4, 2.4, costs and expected savings | Over 100 pages; targeted reading |
| **National Lung Cancer Programme 2026-2035**, preprint of 21.5.2026 (Filha) | text sections on burden, regional and education differences, early detection, costs | Found while researching costs; not in the challenge pack |

## 2. What the sources ask for

**Challenge brief:** identify the gap (differences in access or outcomes); locate it in the pathway (detection, primary-to-specialist referral, diagnosis, treatment start); recommend concrete, evidence-based actions implementable by a health centre or county; use reliable evidence with sources for every claim; cover at least one Goal 3 indicator; deliver a working demo; be readable by a non-technical decision-maker in under two minutes. Weights: actionability 30%, insight 25%, data quality and transparency 20%, execution 15%, clarity 10%. AstraZeneca wants to explore a follow-up with a county.

**Pohde deck (pages):**
- Equity is the goal: right patient, setting, treatment and time (p4). Persistent regional and socioeconomic gaps despite the reform (p4).
- **Parallel systems** (public, private, occupational, student) create different routes to faster access and an **inverse care law**, where access is least where need is greatest; out-of-pocket costs delay investigation and discourage screening (p5).
- Survival differs by education (p6); inequality accumulates across prevention, screening, symptom recognition, access, treatment, follow-up and palliative care (p7).
- About half of cancers may be preventable; tobacco is a major cause (p8).
- Screening participation is lower in low-SES groups, some migrant, Roma and sexual and gender minority groups; language and accessibility matter (p9).
- **Delays are patient-related and system-related, and accumulate** across eight steps from symptoms to treatment (p10). In DLBCL, time from symptom onset to treatment start was **207 days through public primary care versus 123 days through private or occupational care**; a symptom-to-diagnosis interval over 7 weeks went with inferior progression-free survival (p11, Kuitunen 2026, Tokola 2025) [S-weak: read from slides].
- Nordic review of 98 studies: lower SES goes with later stage, less active treatment and worse survival (p12-13). Finnish register study of 469,522 patients: surgery 51% versus 36%, radiotherapy 25% versus 14%, chemotherapy 24% versus 15% for higher versus lower education; cancer mortality 27% versus 47% (p14-15) [S-weak].
- Growing demand and limited resources: cancer care costs projected from €1.5 billion (2023) to €2.6 billion (2035) without targeted measures; the question is how to ensure equity when not every treatment can be offered to everyone, using **consistent, evidence-based criteria** (p16).
- Slide 2 discloses the speaker's consulting for AstraZeneca among other companies, relevant to how industry funding of screening would be perceived.

**Strategy and roadmap:** Goal 3 indicators (poor-prognosis cancers reach the Nordic survival level: lung +14 points, pancreas +6, liver +14; cancer mortality down 10%; treatment within target times); at least 80% screening participation in every county; risk-based screening; funded pilots within screening programmes; registry and stage data; the lung screening pilot already running; funding and savings figures (section 5).

## 3. Mapping: what the simulator does against each requirement

Status key: **Done** = implemented and tested; **Partial**; **Proxy** = derived with a shortcut; **Missing**.

| # | Requirement (source) | What the simulator does | Status | Where it falls short |
|---|---|---|---|---|
| C1 | Identify the gap in access or outcomes by area (brief) | Gap finder: screening participation by county and group (verified); lung deaths per 100k aged 50-74 by county (verified deaths, proxy denominator); modelled CT pressure | Partial | No observed access data: no CT waits, no stage by county, no survival by county. Gap shown is screening participation and mortality, not diagnostic access |
| C2 | Locate the gap in the pathway (brief) | Four-stage pathway map with sourced items | Partial | Items are mostly team notes [N]; nothing computed by region; the simulator itself acts only at the screening-scan step |
| C3 | Concrete recommendations a county could implement (brief) | Six recommendations with owner, evidence and KPI; stop and route planner; pilot protocol | Partial | No cost, no budget impact, no timeline per recommendation; recommendations R2-R3 (pathway clock, fast CT) are not modelled |
| C4 | Cover a Goal 3 indicator (brief) | Goal 3 indicators displayed with sources | Partial | None is computed by the simulator. Its headline output (extra participants) is not a Goal 3 indicator; deaths avoided per year is not shown, and cost per death avoided appears only in the optional uncertainty table |
| C5 | Reliable evidence, sources for every claim (brief) | Tags S/N/A, data-status table, facts card, assumptions register | Done | Many S items are search summaries; key team-note figures (17% survival, 36-38 days) not re-verified |
| C6 | Working demo (brief) | Local app and deployed copy; 70 tests | Done | Analyst layer never run against the live API |
| C7 | Clear in two minutes (brief) | Gap page and readout | Partial | The planner screen is dense; no single-page decision brief |
| C8 | Follow-up with a county (brief) | Pilot protocol and calculator | Partial | Not aligned with the pilot that already exists in Helsinki and eight counties |
| D1 | Equity along the whole pathway (deck p7) | Screening step and CT access only | Partial | Prevention, symptom recognition, treatment and follow-up are not modelled |
| D2 | Education and income gradient (deck p6, 12-15) | Screening participation by education (verified); equity weight uses language only | Partial | Education and income are not used in planning; Finnish lung survival and mortality by education (in the lung programme) are not in the app |
| D3 | Parallel systems and inverse care law (deck p5) | Treats "hospital CT" as one uniform channel | **Missing** | No public versus occupational/private routes; no model of faster access for some groups; no out-of-pocket or travel-cost effect beyond distance |
| D4 | Patient delay versus system delay across eight steps (deck p10-11) | Described on the Gap page | **Missing** | No interval model; no symptom-to-CT or referral-to-diagnosis data by county or sector; the DLBCL 207 versus 123 days example is not used |
| D5 | Regional differences between counties (deck p3-4) | County tables for deaths, smoking, participation, modelled capacity | Partial | Differences within counties and between delivery models are not captured |
| D6 | Vulnerable groups: migrants, Roma, gender and sexual minorities (deck p9) | Language group only | Partial | No data or model for Roma or sexual and gender minorities |
| D7 | Prevention, mainly tobacco (deck p8; strategy; lung programme) | Cessation cost per scan only | **Missing** | The strategy's savings come from prevention; the simulator does not model cessation effects or combine screening with cessation |
| D8 | Limited resources; consistent criteria for what is offered (deck p16) | Capacity and campaign pressure model | Partial | No cost-effectiveness or priority-setting view; capacity inputs are assumptions |
| S1 | At least 80% participation in every county (strategy) | Shown on Gap page by county | Done | Not linked to any action in the planner |
| S2 | Risk-based screening (strategy 2.4) | Risk group defined and estimated by municipality | Proxy | Pack-year data missing; eligible count is smoking prevalence times an assumed factor |
| S3 | Funded pilots within the screening programme (strategy) | Randomised pilot protocol | Done (design) | Not coordinated with the existing national pilot |
| S4 | Stage and registry data (strategy 2.2, 3.2) | Recommendation R1; stage coverage shown as 42% | Partial | No stage data in any model |
| S5 | Lung screening pilot already running (roadmap 2.3.4) | Not mentioned in the app; report says no programme | **Missing, and the app is out of date** | Needs correction (priority 1) |
| S6 | Costs and savings (strategy, roadmap) | Programme cost model for one unit | Partial | No programme-level budget, payer split, savings or cost per life-year in the app |

## 4. Where it answers the challenge and where it falls short

**Answers it:**
- *Actionability:* a stop-by-stop plan, a data request list, and a pilot design with sample size, outcome definition and decision rules.
- *Data quality and transparency:* every number is tagged; the data-status table separates verified, proxy, assumed and gap; the robustness sweep shows which unknowns matter.
- *Execution:* works live, locally and deployed; 70 tests.

**Falls short:**
1. **Scope.** The brief names three bottlenecks. The simulator addresses one narrow slice of one (access to a screening scan). Nothing handles primary-to-specialist referral or diagnosis-to-treatment.
2. **Insight is described, not derived.** The pathway map is a static panel of team notes. The deck's strongest numbers (207 versus 123 days; 51% versus 36% surgery; 47% versus 27% mortality) are not used to ground any computation.
3. **Equity is thin.** Language and education appear in screening participation, but planning weights use only language, and nothing models routes (public versus occupational/private).
4. **Outputs are not decision currencies.** Decision-makers think in euros, deaths avoided and Goal 3 indicators, not "extra participants".
5. **It is out of step with the existing programme.** The roadmap and lung programme show activity we do not acknowledge.
6. **The key inputs for the headline numbers are missing or assumed** (pack-years, CT capacity, waits, campaign effect).
7. **The truck is a distraction risk.** On our own numbers it is not cheaper than a hospital CT, and the deck's evidence points to structural, pathway and navigation causes. The strongest version of the story is "a planner for rolling out and testing delivery models", with the truck as one option.

## 5. Cost, lives and resources

### 5.1 Who would pay

| Component | Who pays today or under current rules | Evidence |
|---|---|---|
| Organising screening: invitations, booking, scans | Wellbeing services counties and the City of Helsinki | [S] strategy section 2.3: counties and Helsinki organise screening under the Health Care Act |
| Participant fees | None: screening is voluntary and free | [S-weak] Ministry of Social Affairs and Health screening page (search summary) |
| County money | State funding, about €27.1 billion nationally in 2026, allocated with need coefficients from morbidity registers | [S-weak] Ministry of Finance, 2026 funding calculation |
| Screening registers | State funding to the Cancer Registry | [S] strategy 2.3 |
| Launching a new national programme | The roadmap says the state budget will reserve calculation-based separate funding; the size is not estimated | [S] roadmap 2.3.4 |
| Expanding an existing programme (breast 46-74) | Needs additional county funding | [S] roadmap 2.3.3 |
| Diagnostic follow-up and treatment | Counties (hospital care and hospital drugs); Kela reimburses outpatient drugs | County role [S] indirectly; Kela role [M] |
| Pilots and evaluation | Research funding; the strategy proposes securing funding for pilots within screening programmes | [S] strategy action 4 |
| Industry (e.g. AstraZeneca) | Could fund independent evaluation or data infrastructure; funding screening delivery itself raises conflict-of-interest questions (deck p2 shows how disclosures are handled) | [A]: confirm with AstraZeneca compliance and the county |

Mismatch to flag [A, reasoning from structure]: counties pay for screening, while part of the later savings (reimbursed outpatient drugs, reduced future budgets) accrue elsewhere. The financing law is said not to steer sufficiently toward prevention (strategy 2.2 [S]). No quantification exists.

**What screening would cost.** From our unit costs (about €340 per scan at a hospital CT with spare capacity including reading and follow-up; about €370 for a well-used mobile unit) [A], national steady state of about 25,000-30,000 scans a year gives **about €8 million a year (roughly €6-18 million across the uptake and cost ranges)** [calc]. Invitation, eligibility identification, cessation support and registry work are partly in that figure and partly extra. For scale: the lung programme's own coordination budget is €150,000 a year, with screening costs explicitly excluded [S]; the strategy's total five-year investment is about €140-156 million [S].

### 5.2 How many lives earlier detection could save

Scope: **lung cancer CT screening of the high-risk group only**, since that is the only CT-detectable cancer with randomised evidence. Method and code: `docs/analysis/lives_saved_estimate.py` (reproducible; pulls Statistics Finland deaths).

| Input | Value | Tag |
|---|---|---|
| Lung-cancer deaths per year, 2021-25 (C34) | 2,293, of which 1,127 aged 50-74 | [S] Statistics Finland 11be |
| Eligible high-risk people | about 120,000 (5-10% of those 50-74 across the assumed factor range) | [proxy] verified smoking x assumed factor |
| Effect of screening on lung-cancer death | rate ratio 0.76 (95% CI 0.61-0.94) | [S] NELSON 10-year |
| Uptake | 50% (30-72%) | [S range] |
| Repeat-round adherence | 66% (55-80%) | [S] one US mobile unit |
| Share of lung deaths aged 50-74 in the eligible group | 60% (45-75%) | [M/A] US data suggest roughly 55-60% of cases under 2021 criteria; verify |
| Baseline mortality in the eligible group, method 1 | 3.3 per 1,000 person-years (2.0-4.5) | [S] NELSON control arm (volunteers) |

| Method | Deaths avoided per year at steady state, median (5th-95th) | Share of Finnish lung deaths |
|---|---|---|
| 1. Trial mortality rates applied to the eligible group | **38 (17-69)** | 1.7% |
| 2. Finnish registry deaths aged 50-74 x share in the eligible group | **64 (30-108)** | 2.8% |

Reading it:
- Both methods give tens, not hundreds, a year. Method 2 implies a baseline of about 5.6 deaths per 1,000 person-years in the eligible group, higher than the trial's 3.3. **Our simulator's default baseline (3.3) is therefore probably conservative**; recalibrating would lower the simulator's cost per death avoided by roughly 40% [calc].
- Benefit lags: trial effects appear over years; the figures are steady state after several rounds.
- The trial effect may not transfer (lower adherence, different risk mix, harms of false positives and overdiagnosis).
- For scale: the strategy's mortality target is about 1,330 fewer deaths a year across all cancers [S]; lung screening of this group could supply roughly 3-5% of it [calc].
- Life-years: lung cancer causes about 34,600 years of life lost a year [S] over about 2,300 deaths, about 15 per death [calc]. The life-years gained per avoided death are unknown; at 8-15 [A], 40-65 deaths avoided is about 300-1,000 life-years a year.

**Other routes to earlier detection (symptomatic pathway, fast-track CT, primary-care access):** no reliable estimate of lives saved is possible yet. The deck shows a delay-outcome link in DLBCL, and the Nordic lung study shows Finland has the longest waits, but there is **no Finnish data linking symptom-to-CT interval to stage or survival for lung cancer**, and lung cancer has a known waiting-time paradox (sicker patients are fast-tracked). Needs the data in 5.5.

### 5.3 What healthcare resources it could save, and what it would consume

**Baselines [S]:** cancer care costs about €1.5 billion (2023), projected to €2.6 billion by 2035 (+74%) without measures; respiratory-organ cancer care about €120 million a year, over half (about €77 million) from specialist care; hospital drugs are the growing component. The lung programme states that identifying lung cancer earlier "could clearly lower treatment costs" but gives no figure.

**What the strategy itself counts as savings [S]:** €298-305 million over the strategy period, of which about €157-164 million is from prevention (smoking and alcohol falling 10% a year for ten years), €19 million from palliative care, €120 million from more clinical trials, €2 million from participation. **The strategy states that savings from equal and effective care and earlier detection cannot yet be estimated and need better data.**

**Stage-cost evidence (international, mixed):**
- Netherlands 2012-2021: monthly cost of initial care about €8,293 for stage IV versus €3,228 for stage IA [S-weak].
- Veneto (Italy): first-year cost similar across stages (stage I about €20,200, stage IV about €22,900); the gap opens in year two (about €2,700 versus €13,400) [S-weak].
- Catalonia: differences between stages not statistically significant [S-weak].
- Sweden, metastatic NSCLC: first-year mean about €105,000 with immunotherapy [S-weak].
- Finnish stage-specific lung cancer costs: **not found**.

**Illustrative offset (assumptions, not an estimate):** national screening finds roughly 250-350 cancers a year in our model [A]. If each avoided late-stage pathway saved between €0 and €40,000 in net treatment cost [A, spanning the Veneto and Dutch findings], offsets would be €0-12 million a year against screening costs of roughly €6-18 million: from none to roughly full cost recovery, most plausibly partial.

**Resources it would consume [calc from model rates]:** about 25,000-30,000 CT examinations a year; about 10% need an extra CT (about 3,000), about 2.5% reach diagnostic work-up (about 650-750 PET, biopsy or MDT episodes); incidental findings send about 1 in 20 to primary care and 1 in 25 to specialist care (roughly 1,300-1,500 and 1,000-1,200 a year). National CT volume cannot be pinned down (Eurostat series swings between about 3,300 and 9,300 exams per 100,000), so the share of CT capacity used is somewhere between about 5% and 15% [S-weak range, calc].

**Where savings could plausibly come from (not yet evidence-based):** more curative surgery or radiotherapy and fewer years of systemic therapy; fewer emergency presentations; lower palliative demand. Each needs Finnish stage-linked cost data.

### 5.4 Evidence versus assumption at a glance

| Item | Status |
|---|---|
| Screening reduces lung-cancer deaths in heavy smokers | Evidence [S] (trials); Finnish effect untested |
| Lung deaths, smoking prevalence, population | Verified [S] |
| Eligible group size | Proxy; pack-year data missing |
| Deaths avoided per year | Indicative range from two methods; assumptions listed in 5.2 |
| Screening cost per scan and national cost | Assumption [A] |
| Who pays | Mostly sourced from strategy and roadmap; Kela role and industry funding not verified |
| Net treatment-cost savings | No Finnish evidence; strategy declines to estimate |
| Campaign effects | Assumption, no evidence |
| CT capacity and waits by county | Missing |

### 5.5 Data needed for reliable estimates (priority order)
1. **Finnish pack-year distribution** by age, sex and county (THL FinHealth or Terve Suomi microdata via Findata). Fixes the eligible count and the baseline-risk denominator.
2. **Stage-specific lung-cancer costs in Finland**: Cancer Registry stage linked to Hilmo/Avohilmo care use, Kela drug reimbursements and county hospital drug costs. Stage is recorded for only about 42% of cases, so this needs a registry improvement or a restricted sample.
3. **Results and design of the 2026 lung screening pilot in Helsinki and eight counties**: uptake, stage shift, harms, unit costs, who pays.
4. **County CT capacity, volumes and waiting times** (radiology departments; THL registers). Replaces three assumptions behind the capacity and campaign results.
5. **Screening unit costs** from county procurement and the pilot.
6. **Symptom-to-diagnosis and referral intervals by county and by sector (public, occupational, private)** linked to stage: needed for any estimate of lives saved from faster pathways and for the deck's inequity argument.
7. **Payer split of lung cancer spend** (county versus Kela) to see who gains from earlier detection.
8. **Age-standardised county lung-cancer rates and incidence by stage** (Cancer Registry).
9. **Campaign effect on uptake and on demand from ineligible people**, for example from the pilot or other countries' campaigns.

## 6. Implemented, assumed and missing

| Implemented and tested | Assumed | Missing data |
|---|---|---|
| Municipality, county and screening data pipelines; verified county lung deaths and smoking | Eligible factor 0.8; uptake curves; distance decay | Finnish pack-year distribution |
| Researched CT list (36 towns) | Free CT capacity 5% of volume; CT volume 35-90 per 1,000 | County CT capacity, volumes, waits |
| Route and stop optimiser; robustness sweep (local, Modal) | Baseline wait 4 weeks; unit costs | Stage by county; lung cost by stage |
| Area model: eligibility, mortality weights, capacity limit, campaign pressure | Campaign: +30% uptake and 3% spill-over per unit | Occupational and private route data |
| Cost model; deaths-avoided calculation in code (UI shows only cost per death avoided, in the optional uncertainty table) | Fixed-site cost €130 per scan | Education and income of the eligible group |
| Randomised pilot sizing and simulations | Effect transfers from NELSON | Roma and gender and sexual minority data |
| Gap page with data-status table; readout; analyst (mocked only) | Additionality | Pilot details and results |

## 7. Recommended changes, prioritised

Impact on the judging criteria and on a real decision-maker; feasibility given the data and the time left. Effort is an estimate for one person.

| Priority | Change | Impact | Feasibility | Effort | Depends on |
|---|---|---|---|---|---|
| **1** | **Align with reality.** Add the 2026 lung pilot (Helsinki plus eight counties) and the National Lung Cancer Programme to the Gap page, planner banner, report and demo script; reposition the planner as a tool for the 2026-2028 pilot expansion and our pilot as an add-on that measures additionality. Fix "no programme" statements | High (credibility; avoids a factual error before judges and AstraZeneca) | High (content only) | Hours | Ask mentors which counties and what design |
| **2** | **Cost and benefit panel** tied to Goal 3: programme cost by component and payer, deaths avoided (both methods, with range), cost per death avoided and per life-year, offset scenarios, evidence versus assumption labels, contribution to the lung survival gap and the 10% mortality target | High (actionability 30%; answers "who pays, what it saves") | High (inputs exist) | 1-2 days | Section 5 numbers |
| **3** | **Recalibrate baseline mortality** to Finnish registry deaths (method 2) and show both methods; expose deaths avoided in results instead of leading with "extra participants" | High (removes a likely underestimate; right currency) | High | Half a day | Statistics Finland age-specific deaths (done) |
| **4** | **SES layer:** education and income by municipality (Statistics Finland) as planning weights; show lung mortality and survival by education from the Cancer Registry; stratify pilot by education | High (deck's main theme; insight 25%) | Medium-high | 1-2 days | Statistics Finland tables; registry figures |
| **5** | **Pathway-delay module:** inputs for symptom-to-CT-to-diagnosis-to-treatment intervals by county and route (public, occupational, private), seeded with the deck's DLBCL example; scenarios such as fast-track CT or direct primary-care access; show the effect on the interval and, clearly labelled, no claim on survival without data | High (covers bottlenecks 2 and 3 and the deck's delays slide) | Medium (data missing; build input-driven with "no data" states) | 2-3 days | Data request 6 |
| **6** | **Programme options comparison:** compare invitation only, extra hours at hospital CT, pop-up venue, mobile unit on cost per additional high-risk scan and capacity effect; the truck becomes one option | High (decision usefulness; reduces the "truck" risk) | Medium | 1-2 days | Existing model |
| **7** | **Dual-route access (public versus occupational/private):** model faster access for people with occupational care, using employment rates by municipality as a proxy until Kela or STM data arrive; show inverse-care-law exposure by county | Medium-high (deck p5) | Medium (proxy only) | 1-2 days | Employment data; later Kela |
| **8** | **Capacity data hooks:** upload county CT volumes and waits (template exists), rank counties by real waits, flag assumed versus observed on the map | Medium-high | High | 1 day | Data request 4 |
| **9** | **Campaign pacing planner:** maximum invitations per month per county that keep added waits under a threshold; staged waves | Medium-high | High | 1 day | Existing campaign model |
| **10** | **Cessation bundle:** add smoking cessation to the screening pathway with cost and assumed effect, aligned with the lung programme and the strategy's prevention emphasis | Medium | Medium (effect evidence needed) | 1 day | Literature check |
| **11** | **One-page decision brief** for a county director: three numbers, one recommended action, one risk, one data request | Medium (clarity 10%) | High | Half a day | Items 1-3 |
| **12** | **Align the pilot protocol** with the national pilot's design (stepped wedge by county if randomisation is already used) | Medium | Depends | Hours once known | Pilot details |
| **13** | Run the Claude analyst live and review answers | Medium (AI requirement) | High once a key is set | Hours | API key |

**Suggested order if time is short:** 1, 3, 2, 11, then 4. Items 5-7 are the most valuable structural additions but depend on data we do not have, so build them as inputs with explicit gaps rather than as invented numbers.

## 8. Questions for the mentors

- Which eight counties and Helsinki run the 2026 lung pilot, what is its design (randomised?), eligibility rule, uptake so far, who funds it, and is there room for an additionality add-on?
- Is any county willing to share CT volumes, waits and capacity, and symptom-to-diagnosis intervals by route?
- Can AstraZeneca fund independent evaluation or data infrastructure, and what are the compliance limits on funding screening delivery?
- Is stage-linked lung cancer cost data available from the Cancer Registry, Kela or THL?
- Does the National Lung Cancer Programme plan an early-detection or screening workstream with a budget?

## 9. The 2026 lung screening pilot: what is known (added after checking the announcements)

Sources: Syöpäjärjestöt press releases via STT (21 and 27 January 2026), Yle (21 January 2026), FICAN/Tyks page (24 March 2026), plus the roadmap. Read as fetched text; I did not find a protocol or registry entry.

| Item | What the sources say |
|---|---|
| Name and funding | "Keuhkosyövän seulontapilotti", part of the EU co-financed **EUCanScreen** project; no amounts given |
| Run by | Oulu University Hospital (OYS) and the Finnish Cancer Registry |
| Where | Regions Uusimaa, Pirkanmaa, Pohjanmaa, Pohjois-Pohjanmaa, Southwest Finland; sites are the university hospitals of Helsinki, Oulu, Tampere and Turku plus Vaasa central hospital. The roadmap's "Helsinki and eight wellbeing counties" fits these regions if Uusimaa is counted as its four counties plus Helsinki; that is my inference, not stated |
| Who | Ages 50-74 with more than 15 cigarettes a day for over 25 years, or more than 10 a day for over 30 years (about 15-19 pack-years at the minimum). Smoking history is not in any register, so **people cannot be invited; they register themselves** (keuho.fi) |
| Size and speed | 1,200 participants; the target was reached within about a week (27 January) and recruitment closed except around Vaasa |
| Design | Described inconsistently: Yle says 600 get lung imaging at the start and end and 600 are offered smoking-cessation support; the Cancer Organisations release says cessation support is offered to all. **Randomisation is not stated.** Participation lasts two years with two research-nurse visits; a phone app ("Suunta", developed in Oulu) supports cessation |
| Aims | Feasibility in Finnish healthcare, early detection, cessation, how screening works across hospital districts and how national registration works. "Decisions on continuing and expanding screening will be made later" (Cancer Registry) |
| Not stated | Funding amount, randomisation, how many scans, results timing, what follows the pilot. An Oslo symposium report mentions a planned nationwide trial of about 1,800 participants with the same app and AI nodule detection; the numbers differ from the announcements [S-weak] |
| Earlier study | LDCT-SC-FI in Oulu: 200 current smokers, 96.7% uptake over two rounds, six cancers (five stage I) [S] |

**What it means for us**
- It is a **volunteer, self-registered, small** study. It cannot tell how many people an invitation-based programme would reach, how many scans are additional, or how a mobile or pop-up site compares; our randomised-invitation protocol answers a different question and complements it. Our pilot would still face the same identification problem (no smoking register), so the invitation step must use a questionnaire or self-registration, and the control arm needs a defined comparison.
- It already covers four university hospitals, so it provides **existing CT sites, scanner capacity use and real-world workflow data**; asking OYS and the Cancer Registry for its operational numbers (scans per week, queue effects, positive findings, follow-up load) would replace several of our capacity and cost assumptions.
- It uses cigarettes-per-day-times-years rules worth roughly 15-19 pack-years at the minimum, close to the 20 pack-year definition we use (the earlier report text calling it "stricter" was wrong and is corrected).
- The recruitment speed (1,200 in about a week) is itself weak evidence of strong interest among long-term smokers, but volunteers differ from the people missed by existing services, so it does not bear on the equity question.
- Roadmap action 2.3.4 expects the small pilot to expand regionally in 2026-2028 and to invite the EU-recommended target population, with the state budget reserving separate launch funding. That is the window our planner and pilot design should target.
