# DESIGN.md — lane ui-inspiration (token contract + reference visuals)

**Owner:** single-threaded lane owner (me). **Contract consumers:** lanes 4/5/6/7
(simulator-shell, room-viz, inspector-ui, phone-channel), which code against the
token names blind. This is a Type-1-ish decision for the video: every visual lane
builds on it, so the token names are frozen on merge and versioned afterward.

## Problem
Three panes (room floor-plan / conversation / lattice inspector) + phone page must
look like *one crafted product* in a 3-minute video, on an AMOLED near-black
canvas, "dark mission control, never terminal." The tokens must carry narrative
weight: the walk-in (room border color shift), the four-room lattice grid, and the
pipeline animation all read through color/state, not prose. Judge attention is
~10s per beat — semantics must be instant.

## Chosen visual language: "calm black, opinionated glow"
- Near-black AMOLED scale (canvas → panes → cards, one direction only), hairline
  borders, layered glow shadows instead of gradients.
- Glow is **semantic, never decorative**: 4 lattice-level accents (FULL mint,
  ABSTRACT amber, EXISTENCE violet, SILENT rose) + arrival pulse (white) +
  low-confidence lockdown (orange) + approval signature (cyan). Each accent has a
  usage rule in TOKENS.md; nothing else glows.
- Density like a network-ops wall (Linear/Vercel-grade compact cards), calm like
  mission control: mono reserved for hashes/trace-IDs/labels only — body text is
  never monospace, the video never shows terminal.
- Motion: avatars glide (translate, not fade-pop), room border crossfades color,
  pipeline cards stagger-in, withheld cards collapse. All transitions ≤600ms,
  `prefers-reduced-motion` respected.

## Rejected (with reasons)
- **Neon cyberpunk / multi-hue glow** — glow without meaning is noise; a 10s beat
  can't carry 12 colors. Each surviving accent maps 1:1 to a lattice level or P0
  requirement (fail-closed, wake-word arrival).
- **Generic SaaS dark dashboard (Linear-clone blue)** — "a bored dashboard is a
  design failure." Kept the *density discipline*, killed the default indigo/blue.
- **Awwwards editorial dark** — beautiful but sparse; our beats need operator
  density (presence confidence, pipeline stages, lattice grid) — editorial spacing
  would bury the evidence.
- **Sci-fi HUD / wireframe-tech** — reads as terminal-adjacent and fictional;
  MASTER_PLAN §5 forbids terminal in the video path; HUD also implies real
  person-ID, which we honestly simulate.

## Token architecture
One flat namespace `--ear-*`, grouped: `canvas/surface/line/text` (neutral scale),
`level-*` (lattice semantics), `presence/approve/lowconf` (operational),
`font/scale/spacing/radius/glow/motion/room` (primitives). Downstream lanes use
the names verbatim — no ad-hoc hex in lane code. Rooms expose one dynamic
variable, `--ear-room-state`, bound to the current level accent; lanes 5/6/7 never
branch on color directly. Versioned in TOKENS.md §"Contract stability."

## Pre-mortem (3 lines)
- Lanes misread a semantic color as decoration and double it up (e.g. two glows on
  one card) — mitigate: usage rules + one dynamic `--ear-room-state` variable.
- Token names drift between mockups and TOKENS.md — mitigate: names written once,
  mockups generated FROM the token block (single source, checked by script).
- References saved but never looked at; sprint becomes theater — mitigate: each
  mockup cites the specific reference it stole from in its file header.
