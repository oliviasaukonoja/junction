# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
Primary: decision-makers and professionals in Finnish cancer care (regional health-care managers, officials, clinicians) who read the Keuhkodata dashboard and the pilot map to decide whether and where to run a lung-screening pilot. Secondary: citizens aged 50-74 with a smoking history, who meet the bus pilot through sign-up and the public pages, including groups with lower screening participation (lower education, non-native speakers, metropolitan areas).

## Product Purpose
Finland has no data specific to cancer types and how the care pathway runs, so gaps in the pathway cannot be identified. The product is a data bank that joins pathway data by cancer type (separate from Omakanta, designed to connect to it) with a dashboard that gives recommendations to professionals. Its first and largest recommendation is a screening pilot: a mobile low-dose CT bus pilot in Lapland, Kymenlaakso and Satakunta, with hospital-CT invitations first in Kymenlaakso and Satakunta. Made for Junction 2026 (AstraZeneca challenge). Success: a decision-maker can see where the gap is, why the pilot goes where it does, and what is and is not known.

## Positioning
A pathway data bank that turns registry data into recommendations for professionals, with a randomised-invitation bus pilot as the first recommendation. Every number carries its evidence status, which most pitch material does not.

## Operating Context
Public pages (Polku hoitoon): bus sign-up, Keuhkodata (regions, risk, recommendation, AI analyst), pilot map (`/kartta`), FAQ, about, feedback, privacy. Backed by the ct-sim Python engine (routing, area model, pilot design, gap finder). Modal-hosted app in `landing-page/`. Source material: Finnish national cancer strategy 2026-2035, Cancer Registry tables, Statistics Finland, THL.

## Capabilities and Constraints
- Built: lung-screening planner, Gap finder, Keuhkodata dashboard, pilot map, public analyses. Not built: the data bank itself and any Omakanta/Kanta connection; do not imply otherwise.
- Terminology: Finnish is the source language; the site ships in 8 languages.
- The README states the site is a hackathon concept, not a real service; sign-up reserves nothing and promises no screening. Keep that wording (confirm scope with the team).
- Open: stack is existing (static HTML + `layout.js`, Modal app); no change planned.

## Brand Commitments
Name: "Polku hoitoon" for public pages. Shared site header and footer via `layout.js`. No further identity constraints confirmed.

## Evidence on Hand
Facts card with tags in `ct-sim/data/analyst/facts.md`: [S] sourced, [N] team notes, [M] recalled trials, [A] assumption. Report in `ct-sim/mobile_ct_screening_report.md`; gap analysis and cost in `ct-sim/docs/gap_analysis_and_cost.md`. Absent: real waiting times by county, Finnish pack-year data, testimonials, pilot results. Lives-saved figures are estimates under assumptions; never present as fact.

## Product Principles
1. Show the evidence status next to every claim (sourced, assumed, not known); say "not known" rather than guess.
2. Recommendations for professionals come first, with the reasoning visible; the public bus pages stay modest and promise nothing.
3. Plain language for the groups screening misses; Finnish first, equal quality across all 8 languages.
4. Equity is the point: show who is missed (language, education, region), not only averages.
5. Do not claim what is not built (data bank, Kanta connection).

## Accessibility & Inclusion
WCAG AA as the floor. Readable by people with lower education and non-native speakers, since these are the groups with the lowest screening participation (F11 in the facts card).
