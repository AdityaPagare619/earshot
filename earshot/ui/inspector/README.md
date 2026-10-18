# inspector-ui — RIGHT pane (lattice pipeline + four-room grid)

Pluggable, framework-free web component for the simulator shell's RIGHT pane.
No build step. Dark AMOLED mission-control aesthetic, `--ear-*` token contract
(ui-inspiration lane); zero terminal text anywhere in the video path.

## Files

- `DESIGN.md` — ≤1-page design decision record + 3-line pre-mortem (governance).
- `inspector.js` — the module. Defines `window.EarshotBus` (tiny pub/sub) and
  `<earshot-inspector>` (Shadow DOM). Two views, tabbed:
  - **LIVE PIPELINE** — glowing 4-stage rail (wake-word → fresh presence
    snapshot → policy evaluation → lattice level). Every MCP tool call arrives
    as an animated card at its stage (tool name, args summary, confidence bar,
    result level badge, latency). A deny-rule hit renders a **citation ribbon
    with the winning rule by name** + the user's own rule text (P1).
  - **LATTICE GRID** — same calendar payload across four audiences
    (alone / spouse / mother-in-law / kids' friends) → FULL / ABSTRACT /
    EXISTENCE / SILENT. The class-limiter, legible in 10 seconds.
- `mock-payloads.js` — mock payloads shaped **exactly** like
  `worldsim/policy.py`'s `Decision` contract
  (`{level, reasons, latency_ms, untrusted_seen, rule_hit}`) plus bus-shaped
  tool-call traces. Includes the walk-in scenario (P0-1 wake-word re-sample,
  P0-2 SILENT/EXISTENCE pairs with a phone nudge, voice-override resisted).
  All labeled simulated.
- `inspector.html` — standalone demo page (header + scenario buttons +
  auto-play). Open in any browser; `#grid` deep-links the lattice view.

## Contract for simulator-shell

Post on `window.EarshotBus`:
`wake {trace_id}` · `toolcall {trace_id, stage, tool, args, result}` where
`stage ∈ {wake, snapshot, policy, level}` and
`result = {level?, latency_ms, confidence?, rule_hit?, rule_nl?}` ·
`decision {trace_id, item_label, audience, confidence, decision, rule_nl?}` ·
`grid [{audience_label, who, level, rule_hit?}]` · `room {present, room_state}`
(which binds the dynamic `--ear-room-state` token).

When mcp-server merges, post real `Decision.to_dict()` payloads — no inspector
changes needed. Tokens: every color is `var(--ear-*)` with local fallbacks;
adopt ui-inspiration's `TOKENS.md` verbatim on merge (same names, per their
DESIGN.md convention).

## Verification (visual, 2026-10-18)

Rendered headless via puppeteer + chrome-headless-shell (`.verify/shoot.js`):
6 tool cards, 3 decision banners, 4 grid columns, 5 rule-name citations, 0 JS
errors. Screenshots inspected: pipeline cards glow per level, the MIL
`decide_disclosure` card cites `never-mention-clinic-in-front-of-mom` by name
with its Hinglish text, the EXISTENCE decision shows the phone-nudge, and the
voice-override decision reads "override attempt resisted". Grid shows
FULL/ABSTRACT/EXISTENCE/SILENT with per-column deny-rule names.
