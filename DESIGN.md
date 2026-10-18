# policy-port — design note (≤1 page)

**Owner:** policy-port lane (single-threaded). Type-2 decision (reversible internal
library); Type-1-adjacent contract FROZEN (see below).

## Problem
Ship the sim-tested EARSHOT decision function as the production engine under the MCP
server: deterministic disclosure lattice, deny-first precedence, fail-closed 0.6 —
plus the three P0 hard requirements from the master plan (P0-1 wake-word fresh
re-sample, P0-2 SILENT pairs with a private nudge, P0-3 unknown topics default
HIGH). Wire the 3000-person worldsim as an in-repo regression so every future policy
change must re-clear the gauntlet before merge.

## What ships
- `earshot/policy/engine.py` — faithful port of `worldsim/policy.py`.
- `earshot/regression/` — verbatim `world.py` + `simulate.py` re-wired to import
  the **shipped** engine (not a dead copy); `run_regression.py` CLI asserting
  0 leaks on 3000 personas.
- `tests/test_engine.py` — unit tests: P0-1/2/3, monotonic-downward,
  deny-beats-allow, fail-closed at low confidence, frozen-contract checks.
- `tests/test_regression.py` — full 3000-person regression, seed 99, fresh snapshot.

## Alternatives considered and REJECTED
1. **Clean rewrite** (dataclasses/enums/strategy classes) — REJECTED: the
   sim-tested function is the evidence asset (42.4% → 0 leaks measured on
   exactly this code). Restatement would void the measurement; cosmetic gain
   isn't worth re-verifying the gauntlet. Chesterton's fence.
2. **Presence re-sampling inside `decide()`** (engine calls camera) — REJECTED:
   impure core kills testability and breaks the "pure function of snapshot"
   contract. P0-1 ships as a thin wrapper `decide_after_resample(resample_fn,
   ...)`; the harness's fresh-snapshot flag covers the regression.
3. **SILENT as reason-string only** — REJECTED: phone-channel and preflight lanes
   need a machine-readable flag. Added derived property `nudge_required`
   (= level == SILENT) + reason text. Constructor fields untouched; `to_dict()`
   gains one additive key (`nudge_required`).
4. **Unknown topics default LOW/PUBLIC** — REJECTED: P0-3, fail-closed by design.
   Missing/invalid `sensitivity` defaults HIGH with a voice-correction path
   downstream (production concern, other lanes).
5. **New syntax / dependencies** — REJECTED: stdlib only, 3.12-compatible, zero
   install cost for MCP server, preflight, and Kiro spike lanes.

## API contract (FROZEN)
```
decide(speaker, audience_perceived, presence_confidence, item, rules,
       device_kind="echo_show", override_attempt=False) -> Decision
```
- `item`: `{topics:set, label:str, sensitivity:str (optional — absent/invalid → HIGH)}`
- `rules`: `[{kind: allow|deny, topics:set, persons:set (allow),
  in_front_of: set|"any_untrusted" (deny), cap:str, name:str}]`
- `Decision(level, reasons, latency_ms, untrusted_seen, rule_hit)`; property
  `nudge_required` = (level == SILENT); `to_dict()` = five frozen fields +
  `nudge_required`.
- `FAIL_CLOSED_CONFIDENCE = 0.6`; level names FULL/ABSTRACT/EXISTENCE/SILENT.
- Guarantees: pure, deterministic, no I/O, no AI; deny caps compose before allow
  trust; voice override logs and never escalates (monotonic-downward);
  confidence < 0.6 → `__unknown__` untrusted (fail closed).
- `decide_after_resample(resample, speaker, item, rules, ...)` — P0-1 path:
  `resample()` returns `(audience, confidence)`; then `decide()`.
- `naive_decide(item)` — the no-gateway baseline, for the regression only.

## Pre-mortem (why this lane fails)
1. The "faithful" port silently diverges from `policy.py` (renamed field, reordered
   check) — guard: the regression imports the shipped engine, so divergence shows
   as leak movement, not as drift in a dead copy.
2. A future lane "extends" the engine (e.g. caching snapshots) and reintroduces
   presence lag — guard: regression gate mandatory before any merge touching
   `engine.py`; stale-snapshot behavior is covered by the fresh-snapshot flag.
3. `nudge_required` ships as text-only reasons and the phone lane misses SILENT
   cards — guard: P0-2 unit test asserts the flag, not the string.

Kill condition: pytest or regression still failing after ~3h → report BLOCKED to
the coordinator with the mechanism; do not re-tune the engine to make tests pass.
