# DESIGN.md — lane inspector-ui (RIGHT pane: pipeline + lattice grid)

**Owner:** single-threaded lane owner (me). **Consumers:** simulator-shell (CENTER
host), room-viz (shares `--ear-room-state`), video-readme (shot list beat 1:50–2:15
architecture, beat 0:45–1:05 lattice grid).

## Problem
The judge must *see* the gateway deciding in real time — not read a log. Two views
in one RIGHT-pane module, driven by the shell's event bus until the MCP server
merges: (a) LIVE PIPELINE — every disclosure decision as a glowing 4-stage pipeline
(wake-word → fresh presence snapshot → policy evaluation → lattice level) with each
MCP tool call as an animated card flowing through it; (b) LATTICE GRID — the same
calendar payload across four audiences side by side, the class-limiter legible in
10 seconds. A deny-rule decision must visibly cite the winning rule **by name**
(MASTER_PLAN P1). Zero raw terminal text anywhere in the video path.

## Chosen design: "the pipeline is the story"
- **Module contract (pluggable):** a framework-free web component
  `<earshot-inspector>` + `earshot/ui/inspector/mock-payloads.js` for standalone
  demos. Listens on `window.EarshotBus` (tiny pub/sub: `decision`, `toolcall`,
  `room` events) — the shell posts, the inspector renders; when mcp-server merges,
  it posts real `Decision.to_dict()` payloads (contract shape `{level, reasons,
  latency_ms, untrusted_seen, rule_hit}`) with zero inspector changes.
- **Live pipeline:** four glowing stage nodes connected by a hairline rail; the
  current stage pulses its level accent (semantic glow only). Each tool call
  becomes a card that *enters at its stage* and slides left-to-right:
  `wake_word` (arrival pulse) → `get_audience` (snapshot: who + confidence bar) →
  `decide_disclosure` (policy: args summary + **winning-rule citation ribbon when
  `rule_hit` fires**) → `send_to_second_channel` (level: badge + latency). Stagger
  ≤600ms; mono only for trace-IDs/hashes; body text never monospace.
- **Lattice grid:** 4 columns — Alone / Spouse / Mother-in-law / Kids' friends —
  same fixture item ("Prenatal visit — Tue 10:30"), each column showing only what
  that audience hears: FULL detail card / ABSTRACT redaction / EXISTENCE title-only
  with approval-signature chip / SILENT withheld card + "sent to your phone" nudge
  (P0-2: SILENT never a dead end). Each column's ring and badge carry its level
  accent; the monotonic-downward order (FULL→ABSTRACT→EXISTENCE→SILENT) is the
  10-second read. Tab switches views; the pipeline keeps animating in background.
- **Tokens:** build on ui-inspiration's `--ear-*` names verbatim (I coded the flat
  palette from their DESIGN.md convention — `canvas/surface/line/text`,
  `level-full/abstract/existence/silent`, `presence/lowconf/approve`, dynamic
  `--ear-room-state`); a `:root` fallback block ships inside the component so it
  renders before TOKENS.md merges, overridden verbatim when it lands.

## Rejected (with reasons)
- **Log/trace console view** — terminal-adjacent; MASTER_PLAN §5 hard rule: the
  video never shows terminal. Rejected outright.
- **One mega-pipeline showing all four rooms** — four parallel pipelines double
  the glow and halve the 10s legibility; the grid's column-comparison wins.
- **Cards as raw JSON** — machine prose breaks the "no terminal text" rule;
  cards show tool name + human args summary + level badge, full args in title
  tooltip only.
- **SVG floor-plan duplicate of room-viz** — presence belongs to the LEFT pane;
  inspector only consumes `room` events to set `--ear-room-state`.

## Pre-mortem (3 lines)
- Shell emits payloads in a different shape → mitigate: payload schema documented
  here and validated at ingestion; mismatch logged once, never rendered as text.
- ui-inspiration merges TOKENS.md with different values → mitigate: no ad-hoc
  hex in lane code; every color is a `var(--ear-*)` with local fallback defaults.
- Mock payloads drift from real policy behavior (e.g. citing a rule name that
  could never hit) → mitigate: every mock mirrors an actual worldsim rule shape
  (kind deny, in_front_of scope, cap) and cites one real fixture rule.
