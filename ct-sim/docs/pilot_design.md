# Pilot protocol: randomised invitations to measure how many scans are genuinely additional

Status: a design to refine with clinicians, a statistician, the county and an ethics board. Numbers are planning values from `python -m ctsim pilot` (code in `src/ctsim/pilot.py`, tests in `tests/test_pilot.py`), not Finnish measurements.

## 1. Question
When eligible people are offered a scan at a mobile or pop-up site near home, how many more complete a screening scan than would have anyway, with the existing hospital CT available? "Anyway" includes scans a campaign would trigger in either case.

## 2. Design
Individually randomised, parallel-group, 1:1, stratified. One wellbeing services county, 12 months of invitations, 6 months of follow-up per person.
- **Arm A (control, standard pathway):** invited to book a screening scan at an existing hospital CT. Slots are reserved so the control arm is not rationed more than usual.
- **Arm B (offer):** the same invitation plus a bookable slot at a mobile or pop-up site within the municipality or a neighbouring one. Mobile slots are bookable only with the invitation code, so nobody in arm A can use them.
- **Optional second factor (2x2):** interpreter and outreach support, to separate "access" from "language barrier". Adds sample size; recommended only if the county can recruit enough.

## 3. Who is invited
The high-risk group: age 50-74, at least 20 pack-years, current smoker or quit within 15 years. This group cannot be listed from public data and Finland has no national smoking register as far as we found. Options to identify people (to decide with the county and an ethics board): a short health-centre questionnaire, occupational or primary-care records, or a mailed screening questionnaire to all aged 50-74 (this adds a response-bias problem that must be reported). Randomise after eligibility is confirmed, so ineligible people cannot dilute the comparison.

How many are available: the model estimates about 9,000 eligible people in Pirkanmaa and 11,600 in Southwest Finland, about 120,000 nationally (proxy: verified smoking rates times an assumed factor; see data status). Smaller counties may not supply the numbers below.

## 4. Randomisation
Permuted blocks within strata: distance band to the nearest hospital CT (under 20 km, 20-60 km, over 60 km), language group (Finnish/Swedish/Sámi vs other or missing) and sex. Oversample language minorities so that each arm has at least 150 of them, because the language-minority subgroup is where documented participation gaps are largest (53-61% vs 75-83% in existing screening, 2024). Randomisation is done by someone outside the booking team; the allocation is concealed until eligibility is confirmed.

## 5. Outcomes
- **Primary:** completed screening scan within 6 months of the invitation, from booking and imaging records.
  - Additional scans per 100 invitees = 100 x (uptake B - uptake A).
  - Scans that would have happened anyway = uptake A.
  - Additionality share of arm B's scans = (uptake B - uptake A) / uptake B.
- **Secondary (pre-specified, exploratory):** uptake by language group, distance band and education; time from invitation to scan; additional imaging and diagnostic work-up per 100 scans; incidental findings needing referral; no-show rate; cost per additional scan; stage of screen-detected cancers (process indicator only, not evidence of benefit).

## 6. Keeping the estimate clean
- **Campaign.** A population-wide campaign raises uptake in both arms and cancels in the difference between them. Do not report a before/after change as "additional": with a +30% campaign effect and the planning values below, a before/after comparison would show 27 extra scans per 100 invitees where the randomised answer is 15.
- **Leakage.** Mobile slots only through the invitation code; log every booking channel; analyse as randomised (intention to treat). In simulation, if 30% of the control arm gets the mobile offer, the estimated uplift falls from about 15 to about 10 points and power drops from 82% to about 53% at 173 per arm.
- **Self-referral outside the invitation list** (campaign spill-over from people who are not eligible or not invited) is counted separately from booking records. It consumes capacity and is part of the campaign-pressure result, not of the primary comparison.
- **Capacity.** Record weekly CT queue length and waiting time at the county's hospital CTs for the whole pilot, so a rise in waits can be attributed. Agree a stopping rule with radiology (for example, pause invitations if added wait exceeds an agreed number of weeks).

## 7. Sample size
Two-sided 5% test, normal approximation, individual randomisation, no dropout inflation (the primary analysis includes everyone randomised).

| Control uptake | Uplift to detect | Per arm at 80% power | Per arm at 90% power |
|---|---|---|---|
| 40% | 20 points | 97 | 130 |
| 40% | 15 points | 173 | 231 |
| 40% | 10 points | 388 | 519 |
| 40% | 5 points | 1,534 | 2,053 |
| 30% | 15 points | 163 | 217 |
| 50% | 15 points | 170 | 227 |

(From `data/pilot/design_table.csv`; 90% columns are from the same formula.) Stratified simulation at control 40%, uplift 15%: 150 per arm gives about 80% power, 250 gives about 95%, and the confidence interval covers the true difference about 94-95% of the time.

Two sizes matter:
1. **For statistical power:** at least 600 per arm (1,200 total) powers a 10-point uplift at 90% and the language-minority subgroup (150 per arm: 80% power for about 15-20 points at a 25% baseline).
2. **For running a unit at realistic utilisation:** one mobile unit does about 2,900 scans a year at 75% slot fill. At 55% uptake in arm B, that takes about 4,000-5,000 invitees in arm B alone. Without that volume the cost per additional scan will be measured at an artificially low utilisation. Inviting 4,000-5,000 per arm needs a county with that many eligible people, or a longer invitation window.

## 8. Analysis plan (pre-registered)
Risk difference in uptake, stratified estimator (weights by stratum size), 95% confidence interval; conditional on the stratification variables. Primary comparison only, no adjustment for multiplicity; subgroup analyses are descriptive and reported with their intervals. Missing outcomes: none by design (records are complete for bookings), but scans done outside the county are captured through the Cancer Registry/imaging records link and a sensitivity analysis counts them.

## 9. Decision rules (proposals, to agree before the pilot starts)
| Result | Action |
|---|---|
| Additionality share at least 30% and the lower confidence limit of the uplift above 0 | The mobile model adds scans; plan a larger or multi-county study and cost it at measured utilisation |
| Additionality share 15-30% | Marginal; compare with cheaper ways to raise uptake (interpreters, evening hours, navigation) before scaling |
| Additionality share below 15%, or uplift not distinguishable from 0 | Do not buy a truck; spend on invitations and fixed-site access |
| Uplift concentrated in language minorities or a distance band | Target the model there |
| Added CT wait over the agreed threshold | Pause and add capacity before inviting more |
Also report harms (extra imaging, work-up, incidental findings) against the NELSON-like range, not the NLST-like range.

## 10. Safety, ethics and data
Screening of people at high risk only; harms (radiation about 0.7-2 mSv per scan, false positives, incidental findings, overdiagnosis) are explained in the invitation; mortality benefit and overdiagnosis cannot be measured in a 12-18 month pilot and are not claimed. Needs ethics approval, a STUK radiation licence for a mobile unit, a written incidental-findings protocol, a data-protection assessment, and a linkage permit for imaging, booking and Cancer Registry data (Findata or the county's own). A written agreement with the hospital to accept referrals within a defined time.

## 11. Time and budget
Preparation 3-6 months (approvals, identification method, vehicle or pop-up venues, interpreters), invitations 12 months, follow-up 6 months. Running one mobile unit costs about €1.0 million a year in the cost model (assumptions; see data/model/assumptions.csv). A pop-up site in rented rooms with a hospital scanner would be far cheaper to try first and answers the same additionality question for the access barrier, though not for travel.

## 12. What this pilot will not tell us
Whether screening saves lives in Finland; the true overdiagnosis rate; how many eligible people exist (it needs the pack-year data); whether results transfer to other counties. It tells us whether an extra delivery channel adds scans, for whom, and at what cost and capacity impact.
