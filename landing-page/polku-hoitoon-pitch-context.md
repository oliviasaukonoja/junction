# Polku hoitoon: context for the pitch deck and video

*Junction 2026 · AstraZeneca challenge "Equal Care Across Finland" · Team Polku Labs (Olivia + Ida) · written 14.11.2026*

Read this first. It covers what we're building, what the judges score, which numbers we can safely use (with sources), and what to avoid.

---

## 1. The challenge in one paragraph

AstraZeneca asks for an **AI-powered solution for equal and effective cancer care across Finland**. Our solution should do three things:

1. **Identify the gap.**
2. **Show where in the care pathway it appears.** The options are detection, referral from primary to specialist care, diagnosis, or treatment start.
3. **Recommend concrete actions.** This is the most important of the three.

**Hard requirements:**
- Use public data and/or mentor insight, and **cite every claim**.
- Cover at least one indicator tied to **Goal 3 of the national cancer strategy 2026–2035**.
- Give actionable recommendations.
- **Show a working demo.** Slides alone fail.

A strong solution makes the situation clear to a **non-technical decision-maker in under 2 minutes**. AstraZeneca may continue with the best idea together with a wellbeing services county (hyvinvointialue).

**Judging is Sunday 15.11 at 14:00.** The judges are AstraZeneca's marketing and business-excellence people (Hanna Rusila, Laura Aaltonen and Joanna Tuormaa), not clinicians.

| Criterion | Weight | What it means for the deck |
|---|---|---|
| Actionability | **30 %** | Name *who* does *what*: a wellbeing services county runs the bus, a health centre uses the dashboard |
| Insight | 25 % | Show the gap and *where* it forms on the pathway |
| Data quality & transparency | 20 % | A source on every number, plus one honest "limitations" line |
| Execution | 15 % | Live demo works |
| Clarity | 10 % | One key message, one action |

---

## 2. Our concept: Polku hoitoon ("Path to care")

**Focus: lung cancer.** It kills more Finns than any other cancer, it is usually found late, and it has clear socioeconomic and regional differences.

The concept has three parts that work together:

1. **Screening bus**
   - Low-dose CT for the risk group: ages 55–74 who smoke or used to smoke.
   - Goes to areas with high lung cancer mortality and a long distance to hospital.
   - Also raises awareness and encourages people to seek care.
   - Modelled on the **NHS Targeted Lung Health Check**.
2. **Patient app**
   - Shows the patient's own Kanta health records as a timeline, with their consent.
   - Symptom and wellbeing tracking.
   - AI translation of care texts into the patient's own language and plain language (selkokieli).
   - A visible care pathway: what happens next, and whether the patient has to book the next step themselves.
   - Feedback channel.
3. **Professional dashboard**
   - Brings app answers and Kanta data into one view.
   - Raises **attention flags** based on agreed criteria (e.g. cough over 3 weeks + smoker + third visit).
   - Shows translated answers and the visible pathway.
   - **It does not diagnose.** v1 is read-only decision support.

**Where it acts on the pathway**, using Kuitunen's 8-stage delay model:
- The bus works on stages 1–5: symptom → decision to seek care → first contact → doctor assessment → tests and referral.
- The app and dashboard work on stages 2–5: navigation, fewer calls, and missed symptoms.

**Wording rules:**
- Don't say "ilman jonottelua" ("no queuing") about the app.
- The service is free for patients.
- Frame the flags as **decision support**. A tool that triages patients could fall under the EU Medical Device Regulation (MDR).

---

## 3. Demo assets

| What | Where |
|---|---|
| Public site (bus, 8 languages) | https://polkuhoitoon.fi/ |
| Patient app | https://polkuhoitoon.fi/sovellus |
| Professional view | https://polkuhoitoon.fi/ammattilaisille |
| **Keuhkodata** dashboard (lung cancer public data, checkbox views) | https://claude.ai/artifact/CBV3DFPMTZAuUGeRAGwEpp. It is private until Olivia shares it. |

**About Keuhkodata:**
- It pulls lung cancer data from Statistics Finland (Tilastokeskus) and THL Sotkanet, plus figures from Cancer Registry, ECIS and NORDCAN reports.
- **Use it for the "Insight" part of the pitch.** The slides that make the case are the regional, education and Finland vs. Norway views.
- Caveat: its regional mortality is a **crude** rate, not age-standardised, so ageing regions look worse. Say so if you show it.

---

## 4. Evidence we can use (with sources)

### The gap forms before diagnosis, in public primary care
- **Yle MOT, Oct 2026.** Unpublished study coordinated by Prof. Outi Kuittinen (University of Eastern Finland):
  - Lung cancer symptom → treatment takes on average **155 days in Finland, vs. 107 in Sweden and 67 in Denmark**.
  - Split: patient >50 d, primary care 41 d, specialist care 58 d.
  - Source: yle.fi/a/74-20251023. Call it unpublished.
- **Kuitunen et al., Cancer Medicine 2026.** DLBCL (lymphoma), *not* lung cancer: from first symptoms to treatment start, the public route took about **207 days** vs. **123 days** for private/occupational care.
  - Use it only to show that *the route you are on* matters.
  - Values are read from a chart, so say "about".
- **Mentor input:**
  - Diagnosis → treatment is mostly on time.
  - The problem is earlier: vague symptoms are missed, tests are rationed, patients make too many calls, and pathways are fragmented.
  - Cite as "AstraZeneca expert interview, Junction 2026".

### Lung cancer in numbers (Keuhkodata sources)
| Figure | Source |
|---|---|
| ~3,000 new lung cancers/year (2022: 1,740 men, 1,207 women) | Finnish Cancer Registry, Syöpä 2022 (via Valtakunnallinen keuhkosyöpäohjelma 2026–2035) |
| 2,253 lung cancer deaths in 2025 (C34: 1,376 men, 877 women) | Statistics Finland, cause-of-death table 11be |
| 65–70 % diagnosed at an advanced stage | Valtakunnallinen keuhkosyöpäohjelma 2026–2035 |
| Only **27 %** receive curative treatment (2019–2023) | Finnish Cancer Registry lung cancer report, via Verkkouutiset |
| 5-year relative survival **21 %** (2020–2022) | Cancer Registry, via OECD/EU Country Cancer Profile Finland 2025 |
| 5-year survival, men: Finland ~17 % vs Norway ~27 % (Nordic best) | NORDCAN, via keuhkosyöpäohjelma. Note: the IHE 2026 report says 30 % for Norway. Pick one source and cite it. |
| 34,600 life years lost per year | Syöpä 2022 |

### Inequality: the core of "Equal Care"
- **Lung cancer incidence by education, men (2018–2022):**
  - basic education 128.7 vs. higher education 48.5 per 100,000
  - mortality 108.1 vs. 39.2
  - That is roughly 2.5–2.8 times higher with basic education.
  - Source: Syöpä 2022, via keuhkosyöpäohjelma.
- **5-year survival by education, women:** ~20 % with basic vs. ~30 % with higher education. Same source.
- **Daily smoking 2024:** 14.1 % with low education vs. 4.4 % with high education (THL Sotkanet).
- **Zai et al., BMJ Public Health 2025** (469,522 Finnish patients):
  - Lower socioeconomic status (SES) → later stage at diagnosis.
  - Cancer mortality 47 % in the lowest vs. 27 % in the highest education group.
- **Nordic meta-analysis**, Acta Oncologica 2022 (98 studies): the same SES pattern appears in every Nordic country.
- **Inverse care law** (Kuitunen, Pohde): the least care goes where the need is greatest. Parallel systems (public, occupational, private) favour people with jobs and money.
- **Stage data:** stage at diagnosis was recorded in only **42 %** of cancers nationally (Syöpä 2024). Finland can't even measure the gap well, which also justifies the dashboard.

### Why a targeted bus is realistic
- **NHS Targeted Lung Health Check:** more than 5,000 lung cancers found, **76 % at stage 1–2** (GOV.UK 2023).
- Lung cancer screening is **not** a national programme in Finland today. Some wellbeing services counties may offer it (OECD/EU profile 2025).
- The keuhkosyöpäohjelma 2026–2035 targets **+10 % curative treatment** and at least **+14 % 5-year survival**. Our concept supports those targets.
- Mentor: be innovative but realistic. "An MRI for every Finn" is the kind of idea to avoid. Keeping the bus to the risk group keeps the cost reasonable.

### Link to national strategy Goal 3 (required)
**Goal 3** of the national cancer strategy covers care pathways, treatment recommendations, the quality registry and timely access. Use these Goal 3 indicators:
- **hoitoonpääsyajat** (time to treatment)
- **levinneisyys** (stage at diagnosis)
- **share receiving curative treatment**
- **survival**

The bus and dashboard aim to shorten time to treatment and to raise the share of cancers found early. Source: Toimeenpanon tiekartta 2026–2031.

---

## 5. Suggested pitch storyline (about 3 minutes)

1. **Hook:** "In Finland it takes about 155 days from first lung cancer symptom to treatment. In Denmark, 67." (Yle MOT)
2. **Who loses:** Lung cancer is roughly 2.5× more common with basic education. Survival is lower too, and only 27 % get curative treatment.
3. **Where the gap forms:** Show the 8-stage delay chart. The gap forms before diagnosis, in public primary care: missed symptoms, many calls, a fragmented path.
4. **Solution:** One slide each for the bus, the app and the dashboard, each with the pathway stage it fixes.
5. **Live demo:**
   - Open the Keuhkodata regional and education views.
   - Show the patient app timeline and translation.
   - Show a dashboard flag.
6. **Action plan:**
   - Pilot in one wellbeing services county with high mortality and long distances. Choose the region from the data, e.g. Lapland, Kymenlaakso or Kainuu, but remember the rates are crude.
   - Restrict screening to the risk group.
   - Define metrics: symptom → imaging time, visits before referral, number of calls, share found at stage 1–2.
7. **Honesty slide:**
   - Data limits: crude rates, missing stage data.
   - Kanta API: read-only, and consent is needed for the dashboard.
   - The flags are decision support only.
8. **Ask:** A pilot partner wellbeing services county, together with AstraZeneca.

**Message priority:** lead with **effectiveness + equality**. Cost savings are a secondary argument, because public care pays either way (mentor).

## 6. Video tips
- The judges are non-technical, so tell it as a patient story. A 62-year-old ex-smoker in Kainuu coughs for weeks, calls the health centre three times and ends up with late-stage cancer. Then replay the story *with* Polku hoitoon.
- Put the source on screen as small text with every number.
- Show the real working product (site, app, dashboard), not only mockups.
- Polkuhoitoon.fi has 8 languages. Show a translated view to make the equality point visible.

---

## 7. Do NOT say
- **"30 % gap for minorities/foreign-language speakers."** No source, and the mentor couldn't confirm it.
- **DLBCL numbers (207 vs. 123 days) as if they were lung cancer.** They come from lymphoma.
- **"Health centres need a specialist referral before CT, which is the main bottleneck."** This came from our own leading question, not from the mentor, so it is unverified.
- **That the dashboard reads Kanta directly for professionals.** The Kanta wellbeing-app API only lets the patient fetch their own data into the app, with consent. Passing it on to the dashboard needs separate explicit consent and certification.
- **That the app diagnoses or that it removes queues.**
- **Precise numbers that are marked "~".** Keep the "about".

## 8. Open questions (if a mentor is around)
- Would a GP order imaging based on a clear flag, or do budgets and guidelines block it?
- Is a risk-group CT bus affordable for a wellbeing services county?
- Would the bus raise participation in low-participation areas?
- Which 2–3 MVP metrics would AstraZeneca find most convincing?

## 9. More material in the "junction" Claude Project
- **"AZ haaste"** document: full brief.
- **"1. AZ haastattelu"** document: notes from the first mentor interview.
- **Kuitunen's slides:** "Equity in Cancer Care", Espoo 13.11.
- **National cancer strategy** and its implementation roadmap (PDFs).
- **Source link pack.**
- **Skeptic judge skill:** run your deck through it before Sunday.
