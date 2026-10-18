# simulator-shell — the EARSHOT mission-control web client (SIMULATED)

Three-pane shell: **LEFT** room chrome + simulated presence panel (room-viz lane
mounts its floor-plan into `#mount-room`) · **CENTER** chat owned by this shell
(what the speaker hears vs what the phone receives, side by side) · **RIGHT**
inspector chrome (inspector-ui lane mounts into `#mount-inspector`).

## Run it (one command, ₹0, no build)

```bash
cd earshot/simulator && python3 -m http.server 8080
# → http://localhost:8080
```

Optional: `http://localhost:8080/?server=http://127.0.0.1:8765` overrides the
documented MCP base URL.

## What it does

- **🎙 WAKE WORD** button → fresh presence re-sample *before* any disclosure
  (P0-1). The top-bar stamp shows the last re-sample time; the bus emits
  `wakeword.resample` so the inspector lane can animate the pipeline.
- **SIMULATED presence panel** — per-person toggle + confidence bar, honestly
  labeled (manual control, never a camera feed). Confidence < 0.6 fails closed →
  treated as present. Priya (speaker) is pinned present.
- **ASK / chat input** → `get_audience` → `decide_disclosure` per calendar item →
  each turn renders the lattice level pill (FULL/ABSTRACT/EXISTENCE/SILENT) with
  the speaker column and the phone column side by side; withheld items also emit
  `send_to_second_channel` (P0-2: SILENT/EXISTENCE always pairs with a private
  nudge — never a dead end). Unknown topics default HIGH (P0-3); voice narrows
  monotonically within a session; the winning deny-rule is cited by name.
- **▶ Play walk-in: FULL → EXISTENCE** — the scripted demo turn: Priya alone asks
  "Alexa, what's my day?" → FULL (prenatal visit spoken); Meera (MIL) walks in →
  wake-word re-sample → same question → EXISTENCE ("one private item sent to your
  phone", phone pane gets the private card). LEFT border shifts color with the
  disclosure state.
- **MOCK MODE badge** — transport probes `EARSHOT_SERVER_BASE/mcp` (Streamable
  HTTP JSON-RPC) on load; flips to **LIVE** when the mcp-server lane's endpoint
  answers. Until then every tool call runs through the mock (shapes mirror
  MASTER_PLAN §3, mechanically swappable).

## Contracts for other lanes

- Mounts (frozen): `#mount-room`, `#mount-inspector`. Append DOM, never move them.
- Bus: `window.EarshotBus` — topics `presence.snapshot`, `presence.changed`,
  `wakeword.resample`, `disclosure.decision`, `tool.call`, `channel.card`,
  `rule.changed`. See DESIGN.md.
- Tokens: placeholder `--es-*` CSS vars with `TOKEN-MAP` comments — re-skin with
  the exact ui-inspiration `TOKENS.md` names on merge.
- Debug handle: `window.Earshot = { bus, store, client, rules, calendar }`.
