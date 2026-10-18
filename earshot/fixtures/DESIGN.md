# Fixture upstreams — DESIGN.md (≤1 page)

## Problem
The demo (simulator shell, MCP server, 3-minute video) needs calendar/bank/message/
health data that a disclosure gateway can reason over — but there is no real Alexa
account, no bank API, and the honest-simulation boundary forbids claiming real data.
We ship a *labeled simulation of the upstreams*: the Priya household's data, scripted
to the video beats, consumed through wrapper accessors that always self-identify as
synthetic.

## Dataset shape
`earshot/fixtures/{calendar,bank,messages,health}.json` — flat item lists. Every item:
`{id, label, domain, sensitivity, topics, detail?, beat?, fixture: true}`.
`wrap.py` accessors (`get_calendar()`, `get_bank()`, `get_messages()`,
`get_health()`, `get_all()`, `get_item(id)`) return envelopes
`{"fixture": true, "domain": ..., "items": [...]}` — so the label survives even a
consumer that flattens items. Loader validates schema on read (required keys,
sensitivity ∈ {PUBLIC,LOW,MEDIUM,HIGH}, topics ⊆ the worldsim vocabulary).
Schema is Type 2 (reversible, fixture-only) — versioned informally via `schema` field.

## Tagging schema
- `sensitivity`: PUBLIC/LOW/MEDIUM/HIGH — the *static* upstream label; the lattice
  (policy lane) computes the dynamic disclosure level from (sensitivity × audience).
  Upstreams never decide disclosure themselves.
- `topics`: subset of the worldsim REQUEST_BANK vocabulary
  (`schedule health work money family relationship errand legal home security`) —
  so fixtures plug straight into policy.py's deny/allow rule matching. P0-3
  (unknown topics → HIGH) is preserved by validating topics at load.
- `beat`: optional video-beat anchor (`walk-in`, `lattice-grid`, `instax`,
  `explain-silence`, `deny-rule`) — metadata for the simulator, invisible to the
  lattice. Loader test pins beat-critical facts (e.g. prenatal at 3:40pm).

## Why fixtures, and the honest-simulation boundary
The gateway under test needs *plausible private data with known ground truth*.
Synthetic fixtures give deterministic, reproducible beats (the walk-in needs the
prenatal visit at exactly 3:40pm every take). Hard boundary: names/amounts/OTP are
invented; nothing here is Priya's real data; every accessor response carries
`fixture: true`; consumers (simulator, MCP server) are required to surface that
label in the UI. An item that arrives without `fixture: true` is a schema violation,
not a judgment call.

## Alternatives rejected
1. **Live API integrations (Google Calendar, real bank)** — rejected: needs real
   credentials, violates ₹0 and the honest-sim boundary; nondeterministic beats.
2. **Runtime-generated random fixtures** — rejected: unseeded randomness breaks the
   pinned video beats (3:40pm) and makes the regression rig non-reproducible.
3. **One mega JSON** — rejected: per-domain files map 1:1 to the wrapped upstream
   tools in MASTER_PLAN §3; per-domain accessors keep the contract surface minimal
   (single-threaded ownership per accessor stays clean).

## Pre-mortem (3 lines)
1. *A fixture leaks through another lane labeled as real data* → both item AND
   envelope carry `fixture: true`; test asserts it on every accessor.
2. *Video beats drift* (someone edits 3:40pm → 4pm) → loader test pins
   beat-critical items by id+label; CI runs it.
3. *Topic vocabulary drift* (policy.py adds topics, fixtures silently become
   unknown→HIGH) → loader validates topics against the policy vocabulary file at
   load time, failing loudly instead of degrading silently.
