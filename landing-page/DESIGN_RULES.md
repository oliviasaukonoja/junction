# Polku hoitoon: design rules
Audience: AstraZeneca judges (marketing/business), a wellbeing-county decision-maker with two minutes, the public signing up. Topic: people dying of lung cancer. Feel: clinical, calm, precise, trustworthy, with one moment of drama per page.

## Banned (AI slop)
Purple/violet/indigo gradients, mesh/aurora blobs; glassmorphism as default card; three equal icon/emoji feature cards; emoji as icons; gradient pill buttons with glow; Inter/system-ui/Roboto as the only font; default Tailwind greys; centered hero + grey subline + two buttons + "trusted by"; same 16px radius and shadow on everything; gradient text; sparkles, "AI-powered" badges, robots, glowing brains, DNA helices, stethoscopes, stock doctors; fake sparklines or invented numbers; lorem ipsum, fake testimonials; counters on every number; parallax everywhere; scroll-jacking; neon-on-black hacker look; cards inside cards.

## Medical look
Palette (refine, don't replace): paper #F7F5F0, ink #0F1A24, secondary #5B6670, lines #E4E1DA, accent #0B5563 (buttons, links, active menu); signal red #D92D20 ONLY for "significantly worse than expected"; calm blue #2F6FB5 ONLY for "significantly better"; map routes amber #E39A2D (Lapland), teal #2BA39A (Kymenlaakso), slate blue #6C8EBF (Satakunta). Light paper pages; dark ink only for the hero and the map. Type: editorial serif for the few human sentences, precise grotesk for UI, tabular figures for numbers, mono only for sources/tags; all self-hosted woff2. Every number shows its source and tag (observed/model/assumption) within one glance. 8px spacing grid, generous whitespace, fewer elements, plain language.

## Motion and 3D
Motion explains, never decorates. Max one signature moment per page: Keuhkodata hero = 3D Finland from the 308 municipalities, the four significantly high areas rising in red, gentle drift that settles; map = route drawing on real roads, bus moving stop to stop. Easing cubic-bezier(.2,.8,.2,1), 200–600ms UI, up to 1.5s signature. No bounce. Parallax max 10–20px, hero only. Section reveals: fade + 12px rise, once. Smooth scroll only if native scroll and accessibility stay (e.g. Lenis, vendored). prefers-reduced-motion: still version of everything; 3D falls back to a static image. Usable within 2s; 3D lazy-loads, pauses off-screen, pixel ratio max 2.

## Product rules (never break)
No number, source, tag or limitation changes; no new claims. Never promise screening, a slot, a date or that it is free. No patient app. No "language matters more than distance". Risk group 50–74. All libraries and fonts vendored, no CDN (map tiles excepted). fi/sv/en on Keuhkodata and map; 8 languages on the bus page incl. Arabic RTL. WCAG AA, visible focus, 44px touch targets, works at 390 and 1440px. AI panels keep working with source tags and fallback messages.

## Quality gate
Impeccable critique on every page, fix anything called slop. Screenshots at 390 and 1440px in fi and en, inspect them. "Would a designer recognise this as AI-generated?" If yes, not done. Zero console errors, zero CDN requests, all /api routes respond.
