# room-viz — DESIGN

**Owner:** lane room-viz (single-threaded). **Problem (PR/FAQ-style):** the walk-in is
the demo's most important 30 seconds, and it must be *seen*, not explained: MIL's
avatar crosses the kitchen threshold → the room border shifts color → the
disclosure card collapses FULL→EXISTENCE. A dashboard-text readout of this would
kill the beat. The module must be a pluggable LEFT pane the simulator shell drives
via its event bus, and must look expensive on an AMOLED screen.

## Floor-plan visual language
SVG line-art floor-plan on near-black (`#05070a`), thin hairline walls
(`rgba(160,200,255,.14)`), rooms labeled in small caps with letter-spaced labels:
**Kitchen** (Echo Show glyph on the counter), **Living**, **Bedroom**, **Hall** +
front-door notch. Depth comes from glow, not texture: a soft radial vignette under
the active room, hairline grid at 8% opacity. No floor fill, no skeuomorphism.

## Avatar motion design
Avatars are glowing discs (initial letter, e.g. "P", "M") with a presence-confidence
ring. Entry/exit is a *glide*: 750ms `cubic-bezier(.22,1,.36,1)` translate along a
waypoint path (door → hall → room threshold → resting spot), with a fading motion
trail and a soft "settle" overshoot. Crossing a room threshold emits a subtle ripple
at the boundary line — the audience's eye is pulled exactly where the story
happens. Exit = fade + shrink + glide back to the door. Rejected: teleport
(breaks the walk-in narrative), linear tween (looks cheap), per-person colors
(clashes with disclosure semantics).

## Border-color semantics (tokenized, per disclosure level)
The active room's border is a 3px glowing stroke whose color = current disclosure
level for that room, pulse-eased over 400ms on change:
- `FULL` → emerald `#2fe8a4` — "open, private room"
- `ABSTRACT` → gold `#ffb03a` — "softened"
- `EXISTENCE` → ember `#ff5f3c` — "restricted, someone untrusted present"
- `SILENT` → crimson `#ff2e63` + double-stroke — "sealed"
- unknown/uncertain → violet `#8b7bff` — "fail-closed, re-sampling"
Placeholder CSS vars (`--esh-level-*`); adopting ui-inspiration's TOKENS.md names is
a one-block swap, never a stall. Rejected: monochrome intensity (unreadable at
video distance), icon badges alone (too small), whole-room color floods (noisy).

## API contract (bus-agnostic, mock until simulator-shell merges)
`new RoomViz({el, bus})`. `bus` = any EventTarget-like. Subscribed events:
`earshot:presence` `{person, room|null, confidence}`, `earshot:disclosure`
`{room, level, itemId, reasons[]}`, `earshot:wakeword` `{ts}` (fresh re-sample
pulse). Public `handleEvent(e)` mirror so the shell can call directly. `demo/`
ships a mock bus + scripted walk-in timeline, so the beat is verifiable in a
browser today with zero shell dependency.

## Pre-mortem
1. If the shell's real event names drift from this contract, the viz sits dead on
   merge — mitigate: contract frozen in README, demo harness logs every received
   event visibly, mock bus shaped exactly like the contract.
2. If the glide timing feels cheap in the browser screenshot pass, the walk-in
   beat dies — mitigate: headless-Chromium frame captures at 0/250/500/750ms,
   retune easing until it reads as motion, not teleport.
3. If ui-inspiration's token names differ, adoption must be trivial — mitigate:
   all color values behind one `:root` token block, documented one-line rename map.
