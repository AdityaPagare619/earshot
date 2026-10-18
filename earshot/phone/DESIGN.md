# phone-channel — DESIGN.md (lane/phone-channel, single owner)

## Problem
The speaker is a broadcast device. EXISTENCE/SILENT decisions (and plan approvals)
need a private screen the room can't hear: the phone. This lane builds
`earshot/phone/`: the second-channel page that receives withheld cards + approval
requests, fires a REAL buzz, and closes an approval loop whose token is bound to the
exact plan hash — "EXISTENCE with a signature."

## Contract (v1, frozen) — see PROTOCOL.md for full shapes
- Transport: `BroadcastChannel('earshot-2ch-<room>')` for the demo (serverless,
  two-tab round trip, crash-proof); `EarshotChannel` also ships an HTTP/SSE adapter
  (`GET /second-channel/events?room=`, `POST /second-channel/respond`) that the
  mcp-server lane implements later. Message shapes are transport-independent JSON.
- Message types: `withheld_card` (EXISTENCE/ABSTRACT/SILENT/FULL private detail +
  `winning_rule` citation + reasons), `approval_request` (exact plan + `plan_hash`),
  `approval_token` (decision + token), `approval_result` (executed/denied),
  `notification_card` (gated notification, phone-only).
- Approval token: `token = sha256(plan_hash | request_id | decision | ts)`.
  Server verifies by recomputation against the plan_hash it issued, marks
  `request_id` consumed (replay rejected), rejects expired requests. Plan tampering
  breaks the token. Honest scope: a binding commitment scheme, NOT PKI — production
  upgrades to a device-key HMAC; documented in PROTOCOL.md.
- Buzz: `navigator.vibrate(200)` on real hardware; audible (WebAudio) + visual
  (flash/pulse) fallback ALWAYS fires alongside — iOS ignores vibrate, desktop has
  no motor. No silent failure: the status chip names which paths fired, and a
  "Test buzz" button arms audio on first user gesture.
- P0-2: SILENT cards render as "silenced — private nudge" with the same buzz and
  tap-to-reveal; never a dead end. Every card carries "why withheld?" citing the
  winning rule by name (pipe-through from `explain_withholding`).

## Alternatives rejected
1. **HTTP/SSE against a live server for the demo** — rejected: a server crash kills
   the video beat. Broadcast keeps the walk-in + phone-buzz beats serverless;
   the HTTP adapter is specified, not required, for DONE.
2. **WebSocket push** — rejected: heavier infra for zero demo gain; SSE spec covers
   the server path.
3. **Server-issued opaque token echoed by the phone** — rejected: weaker binding; a
   swapped plan would still verify. Recompute-from-plan-hash gives real plan-hash
   binding with no shared secret.
4. **Native app / SMS gateway for buzz** — rejected: ₹0 budget, no credentials,
   unfilmable. The web Vibration API is real on the Android device in the shoot.

## Verification plan (no live-browser tool in this lane)
- Node: crypto round trip (binding, tamper rejection, replay rejection, expiry).
- Node: full protocol round trip over real `BroadcastChannel` (gateway ↔ phone
  channel instances) — the DONE round trip minus DOM.
- Node: buzz path-selection logic unit-tested; DOM/audio reviewed + "Test buzz"
  button for the human two-tab check before the shoot.
- `mock_gateway.py` serves both pages same-origin (BroadcastChannel splits across
  origins — documented).

## Pre-mortem (prospective hindsight)
1. **It is 6 months later and the video shoot failed:** we assumed both tabs shared
   an origin — the judge opened the phone via `file://` and the simulator via
   `localhost`, so the channel silently split and the buzz never came. Mitigation:
   both pages served by `mock_gateway.py` from one origin; phone page shows a
   persistent "channel: waiting" state until first contact — silence is visible.
2. **The approval beat backfired on camera:** the token verified but for a stale
   plan after a mid-flight edit, and the speaker announced the wrong amount.
   Mitigation: `request_id` is single-use and TTL-bound (120s); any re-plan issues
   a new `request_id`; server rejects unknown/consumed IDs.
3. **The "real buzz" claim embarrassed us:** the demo phone was an iPhone, which
   ignores `navigator.vibrate()`, and the room heard nothing while we claimed a
   buzz. Mitigation: audible+visual fallback always fires and the status chip
   reports the actual path (`vibrate` vs `audio+visual`); the shoot uses the
   Android device per founder decision, fallback is the honest documented story.
