# mcp-server — DESIGN.md (≤1 page)

## Problem
Expose EARSHOT's deterministic disclosure gateway as an MCP server (spec
2025-11-25, Streamable HTTP) so the simulator shell, phone channel, inspector UI,
and MCP Inspector can drive the 12 §3 tools against the real policy engine, with
every decision ledgered, explained, and undoable. No AI in the hot path.

## Decisions
- **SDK: `MCPServer` (mcp 2.x) from the frozen reference SDK**, not `FastMCP`
  (renamed in 2.x — same role) and not raw `lowlevel.Server`. MCPServer gives
  tool/resource decorators, `ctx.elicit`, lifespan, and Streamable HTTP wiring
  battle-tested; lowlevel would re-implement dispatch for zero gain.
- **Transport: Streamable HTTP** (`run(transport="streamable-http")`,
  default 127.0.0.1:8000, path `/mcp`). stdio rejected: browser clients and
  MCP Inspector need HTTP.
- **Policy: the real merged engine** `earshot.policy.engine` (decide contract
  FROZEN by policy-port). No adapter, no mock. The engine module's
  module-level `decide()` is passed as `policy=` into the merged
  `earshot.notify_ledger` functions (they call `policy.decide(...)` — module
  attribute access works). Fresh per-server state via the factories
  `new_ledger()/new_context_store()/new_second_channel_queue()` (their
  `__init__` explicitly prefers these over module singletons).
- **P0-1 in the call path:** `decide_disclosure` goes through
  `decide_after_resample(resample=lambda: (audience, confidence), ...)` — the
  engine never caches presence; the *freshness* of the snapshot is the
  simulator shell's wake-word responsibility (honestly documented; server-side
  state only re-reads at decision time).
- **P0-2:** SILENT decisions (`nudge_required`) auto-enqueue a phone nudge card —
  certification forbids dead ends.
- **Cross-lane contract (parent order):** the server records context turns for
  BOTH voice-channel (`decide_disclosure`) AND phone-channel
  (`gate_notification` phone path, `send_to_second_channel`) decisions in the
  shared `ContextStore`, so `rescope_context` re-disclosure can see phone-sent
  items (the "safe again" moment). The merged store's `add_turn` contract is
  used as-is; nothing in `notify_ledger` is modified.
- **Elicitation for approvals — verified SDK reality:** the frozen SDK's modern
  protocol (2026-07-28) *forbids server-initiated JSON-RPC requests by
  construction* (`NoBackChannelError` on every transport, including stdio —
  verified with a spy). So `ctx.elicit` is attempted but the REAL elicitation
  surface is the phone, exactly the spec's out-of-band pattern: 
...[truncated 1188 chars]
- **Rules:** structured fields (`kind/topics/persons/in_front_of/cap`) are the
  real contract; `rule_nl` is stored/displayed (language-blind) and parsed
  best-effort (EN + Hinglish deny patterns, deterministic regex). An unparsed
  rule is flagged `parsed:false` and NEVER enforces — silent enforcement is
  worse than no rule.
- **undo scope extension:** merged `undo_last` only sees `gate_notification`
  entries; the server extends it lane-locally to its own voice/phone entries
  (retract pending phone cards; voice corrections logged honestly, never
  rewritten). Ledger stays append-only.
- **Trace:** every tool appends a ledger entry (the visualizer's animation
  feed); `ui://earshot/inspector` returns the live lattice state as JSON for
  the MCP Apps card.

## Rejected alternatives
1. Raw lowlevel Server — re-implements routing/elicitation/session. Rejected.
2. stdio transport — Inspector and the browser shell need HTTP. Rejected.
3. Worldsim-path adapter — moot; policy-port merged with the identical frozen
   contract plus P0-1/2/3. Rejected.
4. LLM NL→rule parsing — non-deterministic, slow; deterministic regex +
   structured fields instead. Rejected (Limitation Principle).
5. Modifying merged `notify_ledger` for undo scope — single-owner lanes; extend
   in the server wrapper instead. Rejected.

## Pre-mortem (3 lines)
1. Server-initiated elicitation is impossible under the modern protocol
   (verified: NoBackChannelError on every transport) — so the approval flow
   must never depend on `ctx.elicit` succeeding. (Phone-channel token flow is
   the primary path; the elicitation attempt is a harmless no-op fallback.)
2. NL rule parse fails silently → an unenforced rule looks enforced.
   (parsed:false rules never enforce; the response says so loudly.)
3. Only voice turns recorded → re-disclosure silently degrades on room change.
   (Both-channel turn recording is a binding in every disclosure wrapper.)
