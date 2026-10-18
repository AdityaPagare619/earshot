# Inspiration sprint — ui-inspiration lane (2026-10-18)

Queries: dark dashboard UI / network-ops glowing nodes / smart-home floor plan /
awwwards dark. ~22 images scanned; 1 kept as reference, 1 kept as anti-reference.
Rule from DESIGN.md pre-mortem: every mockup cites the reference it stole from.

## KEPT

**ref-lumio-floorplan.png** — Lumio (framer) smart-home floor plan.
Stolen for mockup (b) room floor-plan: top-down room cells with soft walls,
the *active room outlined in a colored glow stroke* on near-black, big corner
radius, avatars/badges floating over the plan as pills. This is exactly the
walk-in visual: the room's outline IS the disclosure-state border
(`--ear-room-state`). Rejected from it: the phone-chrome framing (we're desktop).

**homeassistant.jpg** (viewed, not saved — cluttered 3D render, kept only the
idea): floating badge markers over a plan = avatar chips. Saved disk instead.

## REJECTED (kept one as anti-reference)

**rejected-dribbble-clutter.png** — floating neon dashboard cards, 6+ hues,
purple/pink/teal glow everywhere. This is the failure mode we're designing
*against*: glow without meaning. In EARSHOT every glow maps 1:1 to a lattice
level or a P0 state — if you can't name the rule the glow cites, the glow goes.

Also rejected without saving: SEO-spam "NOC wall" renders (generic), editorial
Awwwards dark pages (too sparse for operator density — 10s beats need data),
3D floor-plan renders (video-clutter at 10s, implies real person-ID we don't have).
