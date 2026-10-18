# EARSHOT — friction log (seeded 2026-10-18)

Format per entry: task / steps / expected vs actual / severity / workaround /
suggestion. New lanes append under "Lane entries" in the same format. Wave-level
copy: `~/workspace/amazon-hackathon/ops/WAVE_FRICTION.md` (coordinator merges at
submit).

## Seeded entries (sim-driven, pre-wave — banked before the build started)

### 1. Presence lag on new arrivals
- Task: run the 3,000-person worldsim with and without the EARSHOT gateway.
- Steps: parameterized personas → day schedules → unannounced visitors (45% of
  households) → camera perception noise (15% person-miss) → `decide()` per request.
- Expected: the rules engine handles all cases. Actual: 5 residual HIGH leaks out
  of 5,866 sensitive decisions — ALL from visitors not yet registered by presence at
  decision time (e.g. Kavya's HIV test result read at FULL because the visitor wasn't
  in the perceived audience yet).
- Severity: high (the only leak class in 8,918 decisions).
- Workaround: **the wake word triggers a fresh presence re-sample before every
  disclosure** (P0-1). Re-ran the full sim: 0 leaks, over-withhold unchanged at
  1.35%, overrides still 100% resisted.
- Suggestion (for Amazon): an audience-scoped presence API with arrival *events*,
  not polling — the failure mode is stale presence at decision time, not rules.

### 2. "Can't script what Alexa says"
- Task: design the enforcement point for disclosure policy.
- Expected: control Alexa's wording directly. Actual: Amazon's design guidance
  forbids scripting Alexa's speech — you can only influence it via the data your
  tools return.
- Severity: medium (architectural — it dictated the whole design).
- Workaround: **the gateway sits BEFORE the model.** EARSHOT doesn't touch Alexa's
  words; it grades the information the tools hand her. Alexa can't leak what she
  was never told.
- Suggestion: audience-scoped context API for Alexa+ (submitted in
  PRODUCT_FEEDBACK.md) so the platform itself can withhold tool data by audience.

### 3. Partner-gated builder toolkit
- Task: connect to a real Alexa+ device or the official builder tooling.
- Expected: the hackathon grants builder access. Actual: the MCP Toolkit and
  Category SDK are select-partners-only — no application path exists for
  participants.
- Severity: medium (forced the demo architecture).
- Workaround: an honest web simulator as a real MCP client (a permitted path) —
  room state, manual presence toggle, and wake-word re-sample, all labeled
  simulated in the UI. No real-device claims anywhere in the submission.
- Suggestion: open the MCP Toolkit to hackathon participants — the Alexa+ track
  currently judges demos nobody is allowed to build for real.

## Lane entries (append below in the same format)

<!-- TODO(build-lanes): each lane appends its real friction here as it lands. -->
