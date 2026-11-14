# Polku hoitoon: design rules (read before every UI change)

Audience: AstraZeneca judges (marketing and business people), a wellbeing-county decision-maker who has two minutes, and members of the public signing up. The product is about people dying of lung cancer. It must feel clinical, calm, precise and trustworthy, with one moment of drama per page, never a party.

## 1. Banned: typical AI slop (do not produce any of these)
- Purple, violet or indigo gradients; blue-to-purple anything; "aurora" or mesh-gradient blobs in the background.
- Glassmorphism cards (frosted blur panels) used as the default card style.
- Three equal feature cards in a row with an emoji or icon on top and a two-line blurb.
- Emoji as icons. Generic stock icon sets used as decoration.
- Big rounded "pill" buttons with a gradient fill and glow.
- Inter / system-ui / Roboto as the only typeface. Default Tailwind grey palette.
- Centered hero with a huge headline, a grey subline and two buttons, followed by "Trusted by" logos.
- Uniform 16 px border radius and the same drop shadow on everything.
- Gradient text on headlines.
- Sparkles, "✨ AI-powered" badges, robot imagery, glowing brains, DNA helices, stethoscopes, doctors in stock photos.
- Fake dashboard decorations: random sparkline charts, made-up KPIs, numbers that are not in our data.
- Lorem ipsum, placeholder names, invented testimonials or quotes.
- Animated counters on every number; parallax on every section; scroll-jacking that hijacks normal scrolling.
- Dark mode "hacker" look with neon green or cyan on black.
- Cards inside cards inside cards.

## 2. Medical vibe: what to do instead
- Palette: warm paper white or very dark ink as the base (pick one per page and keep it), one deep neutral ink colour, one clinical cool accent. Signal red is reserved for one meaning only: "significantly worse than expected". A cool blue for "significantly better". Never use red for decoration or buttons.
- Type: an editorial serif for the few human sentences (the headline, the one key finding), a precise grotesk for UI, tabular figures for numbers, a mono only for source lines and tags. All fonts self-hosted.
- Every number on screen shows its source and its tag (observed / model / assumption) within one glance. Data honesty is part of the look, not a footnote.
- Generous whitespace, a strict 8 px spacing grid, aligned baselines, fewer elements. If a block does not help the decision, remove it.
- Plain language. Short sentences. No jargon on the main path.

## 3. Motion and 3D
- Motion explains, it does not decorate. Each animation must answer: what changed, what is connected, where to look next.
- Allowed signature moments (max one per page):
  - Keuhkodata hero: a 3D Finland built from the 308 municipalities (three.js, data from the repo), the four significantly high areas rising in red; gentle camera drift; it settles and becomes still.
  - Pilot map: the route drawing along real roads, the bus moving stop to stop.
- Smooth, physical easing (cubic-bezier(.2,.8,.2,1)), durations 200–600 ms for UI, up to 1.5 s for the signature moment. No bounce, no elastic.
- Subtle depth: light parallax (max 10–20 px) on the hero only; soft scroll-linked reveals for sections (fade + 12 px rise, once).
- Smooth scrolling library allowed only if it keeps native scroll and accessibility (e.g. Lenis, vendored).
- prefers-reduced-motion: every animation has a still version. 3D falls back to a static image.
- Performance budget: the page is usable within 2 s on a mid laptop; the 3D scene lazy-loads, pauses when off screen, caps pixel ratio at 2, and never blocks reading.

## 4. Non-negotiable product rules
- No number, source, tag or limitation changes during redesign. No new claims.
- Never promise screening, a slot, a date or that it is free ("could", "pilot", "planned").
- No patient app. No "language matters more than distance" claim.
- Risk group is 50–74 everywhere.
- Every external library and font is vendored; no CDN at runtime (map tiles excepted).
- fi / sv / en on Keuhkodata and the map; all 8 languages on the bus page, including Arabic right-to-left.
- WCAG AA contrast, keyboard focus visible, 44 px touch targets, works at 390 px and 1440 px.
- The AI panels stay functional and keep their source tags and fallback messages.

## 5. Quality gate (run before saying "done")
- Run the Impeccable critique (or equivalent) on every page; fix anything it calls AI slop.
- Screenshot every page at 390 and 1440 px in fi and en; look at them; fix overlap, cut text, empty states.
- Ask: would a designer immediately recognise this as AI-generated? If yes, it is not done.
- Zero console errors, zero CDN requests, all /api routes respond.
