# notify-ledger — DESIGN.md (≤1 page)

## Problem
Five server-side capabilities behind EARSHOT's MCP tools (§3): gate unprompted
notifications (Instax branch-8 beat), re-scope memory on room change, tamper-evident
decision log, deterministic "why didn't you tell me?" answers, and undo of the last
disclosure-affecting action. All pure-Python, stdlib only, no AI in the hot path.
Built against the policy `Decision` contract
`{level, reasons, latency_ms, untrusted_seen, rule_hit}` — a mock mirrors
`worldsim/policy.py` semantics until policy-port merges; `mcp-server` swaps in the
real engine via injection (every function takes an optional `policy=`).

## Decisions
- **Ledger = append-only hash chain.** Each entry stores `prev_hash`; `hash =
  sha256(canonical_json(entry_without_hash + prev_hash))`. Entries frozen at write.
  `get_ledger(since)` verifies the whole chain on read and reports `valid`.
- **gate_notification(notif, audience, confidence, speaker, rules)** → decision →
  channel: FULL/ABSTRACT → voice announce; EXISTENCE/SILENT → phone-only card +
  queued in `second_channel_queue` (phone-channel lane drains it). P0-2: SILENT
  always pairs with a private nudge, never a dead end. Every gating decision lands
  in the ledger with the audience snapshot + confidence.
- **rescope_context(new_audience, confidence, speaker, context)** → re-runs `decide`
  over context turns withheld under the old audience; items that now qualify move to
  a `redisclosures_queued` list (voice re-prompt); everything logged as
  `rescope_context` entries. Cut-order safe: the mechanic is minimal by design.
- **explain_withholding(item_id)** → latest ledger entry for the item; cites the
  WINNING RULE BY NAME (`rule_hit`) plus the recorded audience before/after the
  change (P1). No rule_hit → cites fail-closed ("presence uncertain"). Pure lookup;
  no LLM generation.
- **undo_last()** → finds the last ledger entry with disclosure effect. Phone cards:
  retracted from the queue + undo entry appended. Voice announcements: cannot be
  un-spoken — appends an undo entry recording the correction honestly (ledger stays
  truthful, never rewrites history).
- Default module singletons so MCP tools bind the five function names directly;
  factories (`new_ledger()`, `new_context_store()`) for isolated tests.

## Rejected alternatives
1. Mutable ledger / editable entries — kills tamper-evidence. Rejected.
2. LLM-written explanations — non-deterministic, slow; cite recorded rule + audience
   diff instead. Rejected (Limitation Principle: one mechanism, not per-case prose).
3. Announce-by-default for notifications — the Instax incident proves this default
   leaks; fail-closed phone-only wins. Rejected.
4. Deriving rescope from raw chat transcript — needs per-turn audience annotations;
   the annotated `ContextStore` is the honest, minimal contract. Rejected.

## Contracts
`gate_notification(notif, audience, confidence, speaker, rules) -> {channel, level,
text, decision, ledger_seq}` · `rescope_context(new_audience, confidence, speaker,
ctx, rules) -> {rescoped, redisclosures_queued}` ·
`get_ledger(since=None) -> {entries, valid, head_hash}` ·
`explain_withholding(item_id) -> {rule_hit, audience_before, audience_after, sentence}` ·
`undo_last() -> {reversed, action, note}`

## Pre-mortem (3 lines)
1. If the mock's fail-closed 0.6 threshold drifts from policy-port's, notifications
   default to announce under uncertainty — Instax replays. (Pin: shared constant,
   cross-checked test.)
2. A mutated ledger entry silently breaks the chain → entries frozen at write; verify
   on every `get_ledger`.
3. `undo_last` on a voice announcement must never claim the words were unsaid — log
   the correction, own the limit.
