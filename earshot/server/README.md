# EARSHOT MCP server (`earshot/server/`)

Streamable HTTP MCP server (spec 2025-11-25) for the EARSHOT disclosure
gateway. Built on the frozen reference SDK (`mcp` 2.x → `MCPServer`;
`FastMCP` was renamed in 2.x), the real policy engine
(`earshot.policy.engine`, contract FROZEN), and the merged
`earshot.notify_ledger` tool implementations. No AI in the hot path.

## Install

```bash
cd ~/workspace/earshot-trees/mcp-server
python3 -m venv .venv
.venv/bin/pip install -e ~/workspace/amazon-hackathon/resources/mcp-python-sdk/src/mcp-types
.venv/bin/pip install --no-deps -e ~/workspace/amazon-hackathon/resources/mcp-python-sdk
.venv/bin/pip install 'anyio>=4.9' 'httpx2>=2.10.0' 'pydantic>=2.12.0' 'starlette>=0.27' \
  'python-multipart>=0.0.9' 'sse-starlette>=3.0.0' 'uvicorn>=0.31.1' \
  'jsonschema>=4.20.0' 'typing-extensions>=4.13.0' 'opentelemetry-api>=1.28.0' \
  'pyjwt[crypto]>=2.10.1' pytest
```

## Run

```bash
# Streamable HTTP (MCP Inspector / browser simulator route), default :8000
.venv/bin/python -m earshot.server.server --port 8000
# stdio (elicitation-capable route)
.venv/bin/python -m earshot.server.server --transport stdio
```

MCP Inspector → **Streamable HTTP** → `http://127.0.0.1:8000/mcp`.
Expect 14 tools + the `ui://earshot/inspector` resource.

## Tools (MASTER_PLAN §3 lists 12; the inventory names 14 — all implemented)

`decide_disclosure` · `set_rule` / `list_rules` / `delete_rule` ·
`declare_speaker` · `get_audience` · `explain_withholding` · `get_ledger` ·
`send_to_second_channel` · `request_approval` / `approve` ·
`rescope_context` · `undo_last` · `gate_notification`

Resource: `ui://earshot/inspector` (live lattice state JSON: audience, rules,
recent decisions, ledger head, pending phone cards — the phone lane reads its
cards here too).

## Key behaviors

- **P0-1:** `decide_disclosure` goes through `decide_after_resample` — the
  snapshot is re-read at decision time; the simulator shell owns wake-word
  freshness (presence is honestly labeled simulated).
- **P0-2:** SILENT decisions auto-queue a phone nudge card (never a dead end).
- **P0-3:** unknown sensitivity defaults HIGH (engine).
- **Both-channel context turns:** voice (`decide_disclosure`) AND phone
  (`gate_notification` phone path, `send_to_second_channel`) decisions are
  recorded in the shared `ContextStore`, so `rescope_context` re-disclosure
  sees phone-sent items (cross-lane contract with notify-ledger).
- **Approval flow:** `request_approval` → plan-hash-bound token + approval
  card on the second channel; `approve(token, plan_hash)` enforces the hash
  binding and queues the signed EXISTENCE card. Verified SDK reality: the
  modern protocol forbids server-initiated requests (`NoBackChannelError`),
  so MCP `ctx.elicit` is attempted but the phone is the real elicitation
  surface (spec's out-of-band pattern).
- **Rules:** structured fields are the contract; `rule_nl` is stored verbatim
  (language-blind) and parsed best-effort (EN + Hinglish deny patterns).
  Unparsed rules are flagged and NEVER enforce.
- **Ledger:** append-only hash chain; `undo_last` retracts pending phone
  cards, logs honest corrections for spoken words (history never rewritten).

## Tests

```bash
.venv/bin/python -m pytest tests/test_rules.py -q          # 8 unit tests
# live-server e2e (28 checks: all tools, dual-channel rescope, approval flow):
.venv/bin/python -m earshot.server.server --port 8126 &
.venv/bin/python tests/test_e2e_streamable_http.py http://127.0.0.1:8126/mcp
```

## Friction (also in `~/workspace/amazon-hackathon/ops/WAVE_FRICTION.md`)

- SDK is mcp 2.x: `FastMCP` → `MCPServer`; `streamable_http_client` (not
  `streamablehttp_client`); `MCPError` (not `McpError`); `Client(transport)`
  takes the transport CM directly; yields 2 streams.
- Editable install of the reference SDK fails: pinned `mcp-types` dev version
  isn't on PyPI → install workspace member `src/mcp-types` + PyPI runtime
  deps (see Install).
- `httpx2` crashes parsing bracketed IPv6 (`[::1]`) in `NO_PROXY` at client
  creation → sanitize env before creating SDK clients.
