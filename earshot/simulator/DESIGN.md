# simulator-shell — DESIGN.md (lane: simulator-shell, owner: single-threaded)

## Problem
One web shell hosts the three mission-control panes (room-viz LEFT, chat CENTER,
inspector-ui RIGHT), drives the MCP server's tools + fixture upstreams, owns room
presence state honestly labeled as simulated, and must keep working before any of
lanes 2/3/5/6 merge. Contract-first: build against frozen contracts + mocks now,
skin/integrate on merge — never stall waiting.

## Architecture (static, zero build, zero deps, ₹0)
`index.html` + `styles.css` + `app.js`, served by `python3 -m http.server 8080`.
Three layers:
1. **PresenceStore** — the SSOT for who's in the room (person, role, present,
   confidence). Shell owns it; other panes subscribe read-only via the bus.
2. **EarshotBus** — tiny pub/sub (`on/once/emit`), frozen topics below.
3. **EarshotClient** — transport adapter for the 12 MCP tools. `mock` transport
   now (payload shapes copied from MASTER_PLAN §3, mechanically swappable);
   `mcp` transport = `fetch()` JSON-RPC to `EARSHOT_SERVER_BASE`
   (default `http://127.0.0.1:8765/mcp`, overridable via `?server=`).
   Auto-fallback: probe the server on load; badge shows **MOCK MODE** until a
   real response lands, then flips to **LIVE**. Mock implements P0-1/2/3,
   fail-closed 0.6, monotonic-downward, unknown-topic→HIGH.
4. **Mounts** — shell owns pane chrome (headers, presence panel, wake-word bar);
   lanes 5/6 render INTO `<div id="mount-room">` / `<div id="mount-inspector">`
   and subscribe to the bus. They never touch the store internals. Mounts are
   frozen here and never moved.

## Event bus (frozen contract)
`presence.snapshot` {people, ts} · `presence.changed` {personId, present,
confidence, ts} · `wakeword.resample` {ts, reason} — emitted BEFORE every
disclosure (P0-1) · `disclosure.decision` {itemId, level, reasons, audience, ts}
· `tool.call` {tool, args, result, ms, ts} — inspector lane animates these
· `channel.card` {card} — phone-pane cards · `rule.changed` {rules}.

## Composition
LEFT: shell header + SIMULATED presence panel (per-person toggle + confidence bar,
honestly labeled, never a feed) → mount-room. CENTER: chat (each turn = two
columns: 🔊 SPEAKER HEARS / 📱 PHONE RECEIVES) + wake-word button + scripted
FULL→EXISTENCE walk-in demo. RIGHT: inspector chrome → mount-inspector.

## Alternatives rejected
- **React/Vite build pipeline** — the demo needs pixels, not components; build
  toil for a 5-day client is negative value. Rejected.
- **Shell owning the room visualization** — violates single-owner lanes;
  shell provides mount + bus only. Rejected.
- **Polling the server for presence** — presence changes are operator-driven
  (toggle/script); events suffice, polling is theater. Rejected.
- **WebSocket to MCP server** — server speaks Streamable HTTP; a third transport
  path buys nothing for this demo. Rejected (fetch per the brief).

## Tokens
Placeholder `--es-*` CSS variables with `TOKEN-MAP` comments marking each;
re-skin with the exact ui-inspiration `TOKENS.md` names on merge.

## Pre-mortem (as if this lane already failed)
1. **MockTransport drifted** from the real server's JSON shapes → merge-day
   integration broke the chat pane. (Mitigation: mock marked mechanically
   swappable; shapes pinned in README.)
2. **Placeholder token names diverged** from TOKENS.md → the skin was a rewrite,
   not a mapping. (Mitigation: TOKEN-MAP comments on every var; skin = rename.)
3. **Mount contract changed** after lanes started → room/inspector panes stayed
   empty in the video. (Mitigation: mounts frozen in this doc, never moved;
   placeholder content renders until lanes land.)
