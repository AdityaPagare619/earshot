# EARSHOT second-channel protocol — v1 (frozen 2026-10-18)

Consumer: `mcp-server` lane (`send_to_second_channel`, `request_approval`, `approve`
tools) implements the HTTP side; `simulator-shell` emits on it. This page is the
contract; `channel.js` is the reference client.

## Transport
Two interchangeable transports, identical payloads:
1. **broadcast** (demo/default): `BroadcastChannel('earshot-2ch-<room>')`. Both tabs
   MUST share an origin — serve with `mock_gateway.py` (or the simulator server).
2. **http** (production path, mcp-server implements):
   - `GET /second-channel/events?room=<room>` — SSE stream, `event: earshot`,
     `data: <message JSON>`.
   - `POST /second-channel/respond` — phone → server, JSON body = message.
   - `GET /second-channel/health?room=<room>` → `{"ok":true,"room":"<room>"}`.

## Canonical plan hash
`plan_hash = sha256_hex(canonical_json(plan))` where `canonical_json` = JSON with
object keys sorted recursively, no whitespace, UTF-8. Reference: `crypto.js`
`planHash()`. Both sides MUST use the identical canonicalization.

## Messages (all: `{"v":1, "type":..., "trace_id":...}`)

### withheld_card — gateway → phone
```json
{
  "v": 1, "type": "withheld_card", "id": "msg_01J...",
  "trace_id": "tr_9f2...", "ts": 1760786137000, "room": "demo",
  "card": {
    "item_id": "cal_20261018_prenatal",
    "level": "EXISTENCE",
    "title": "One private item",
    "detail": "Prenatal checkup — City Clinic, 4:30 PM (Dr. Rao)",
    "speaker_heard": "One private item, sent to your phone.",
    "winning_rule": "never mention the clinic in front of Mom",
    "reasons": ["audience includes mother-in-law", "topic=health is HIGH sensitivity"],
    "audience": ["you", "mother-in-law"],
    "nudge": true
  }
}
```
`level` ∈ FULL, ABSTRACT, EXISTENCE, SILENT. `nudge:true` on SILENT (P0-2) — the
phone MUST buzz + show tap-to-reveal; a SILENT card is never a dead end.

### notification_card — gateway → phone (branch 8, Instax beat)
Same envelope; `"type":"notification_card"`, card has `source:"package_tracker"`,
`title:"Package delivered"`, `detail:"Instax Mini 12 delivered to the door."`,
`announcement_suppressed:true`, and the speaker heard nothing.

### approval_request — gateway → phone
```json
{
  "v": 1, "type": "approval_request", "id": "msg_01J...",
  "trace_id": "tr_9f2...", "ts": 1760786137000, "room": "demo",
  "request_id": "apr_7d21", "expires_at": 1760786257000,
  "plan": {
    "action": "reorder", "merchant": "Blinkit",
    "items": [{"name": "Detergent 1kg", "qty": 1}],
    "amount_cents": 1240, "currency": "INR"
  },
  "plan_hash": "9f2c...ab",
  "speaker_heard": "Reordering detergent — check your phone to confirm."
}
```
The phone MUST render the plan EXACTLY (merchant, items, total) — this is the
"signature" the room never sees.

### approval_token — phone → gateway
```json
{
  "v": 1, "type": "approval_token",
  "trace_id": "tr_9f2...", "ts": 1760786141000,
  "request_id": "apr_7d21", "decision": "approve",
  "token": "sha256_hex(plan_hash + '|' + request_id + '|' + decision + '|' + ts)"
}
```
`decision` ∈ `approve` | `deny`.

### approval_result — gateway → phone
```json
{
  "v": 1, "type": "approval_result", "trace_id": "tr_9f2...",
  "ts": 1760786142000, "request_id": "apr_7d21",
  "outcome": "executed",
  "note": "Detergent reordered — Blinkit, ₹12.40."
}
```
`outcome` ∈ `executed` | `denied` | `rejected:expired` | `rejected:replay` |
`rejected:plan_mismatch`.

## Server verification algorithm (mcp-server `approve`)
```
on approval_token t:
  req = store.get(t.request_id) or REJECT unknown
  if now > req.expires_at: REJECT expired
  if req.consumed: REJECT replay
  expect = sha256(req.plan_hash | t.request_id | t.decision | t.ts)
  if expect != t.token: REJECT plan_mismatch
  req.consumed = true
  if t.decision == approve: execute(req.plan) → executed
  else: denied
```
Tampering with ANY plan field changes `plan_hash`, so the recomputed token will
not match. `|ts` binds the decision to a moment (replay window = TTL).

## Security scope (honest)
This is a plan-binding commitment scheme, not authentication: anyone on the
channel can mint a token for a plan they can see. It proves *integrity of the
approved plan*, not *identity of the approver*. Production: replace the sha256
with `HMAC_SHA256(device_key, ...)` provisioned at phone pairing; the verify
algorithm is otherwise unchanged.

## Versioning
`v` integer; v1 frozen. v2 (device-key HMAC) adds `key_id` to `approval_token`.
Receivers MUST ignore unknown `type` values and unknown fields (Postel).
