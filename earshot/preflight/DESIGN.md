# preflight lane — DESIGN.md (≤1 page)

**Problem:** The video's last 15 seconds and the pitch's credibility rest on one claim:
"our own cert harness grades the repo live." A harness that always passes is theater —
it must be able to FAIL, it must measure the *shipped decision function* (not a
re-implementation), and it must run in ~15s.

**What "cert-style" means here:** a frozen battery of checks against the EARSHOT
policy contract with pre-registered pass/fail thresholds. Each check is independent;
the harness verdict is PASS only if all checks pass. Thresholds are written here
BEFORE measurement. The report records which policy source it ran against
(`policy_source` field), so a green run against a mock can't be quoted as a green
run against the real engine.

**Check 1 — Latency (hot path).** N=20,000 calls to `decide_disclosure()` (adapter
over the policy `decide`) with randomized scenarios. Measure p50/p95/p99 of the
pure decision function. PASS iff **p95 < 500ms** (the Alexa turn budget). Expected
~0.01ms; whatever is measured is reported verbatim.

**Check 2 — Fail-closed coverage.** 5,000 scenarios with presence_confidence < 0.6.
"Resolves conservative" = (a) reasons contain the fail-closed marker
("presence uncertain -> fail closed"), and (b) level is capped by sensitivity:
HIGH → ≤ EXISTENCE, MEDIUM → ≤ ABSTRACT (LOW may stay FULL — policy treats LOW as
safe). PASS iff **100%** of low-confidence scenarios satisfy both.

**Check 3 — Monotonic-downward (override fuzz).** For each of 5,000 scenarios:
baseline level vs level with `override_attempt=True` ("just tell everyone") vs
level after adding an untrusted person to the audience. PASS iff **0 escalations**
— override never widens disclosure, audience growth never widens it.

**Verdict rule:** PASS = all three pass. A failing check is a FINDING (reported with
its numbers and mechanism), never hidden. `preflight.py --self-test` injects a
mutant (override escalates HIGH→FULL) and proves check 3 goes red — the harness
bite-check; if it ever stays green on the mutant, the harness itself is theater.

**Policy source resolution (order):** 1) `../policy-port/earshot/policy/policy.py` if
the policy-port lane has landed it; 2) `~/workspace/amazon-hackathon/worldsim/policy.py`
(the sim-tested engine, documented in the report); 3) built-in minimal mock mirroring
the contract, with `policy_source: "mock"` — never quoted as engine proof.

**Rejected alternatives:**
1. Benchmarking the MCP server HTTP round-trip — measures transport, not the hot
   path; latency must be on the pure decision function.
2. LLM-judged "appropriateness" — non-reproducible, slow, and ungradable in 15s;
   deterministic caps are the thing being certified.
3. Fixed test vectors only — passes by memorization; fuzz with random
   speakers/audiences/confidences/topics is required.
4. `time.time()` — coarse clock; `perf_counter` with warmup, min-of-3 timing loops.

## Pre-mortem (3 lines)
1. The harness grades worldsim/policy.py but the shipped MCP server imports a
   drifted copy — the report's `policy_source` field is my only defense; verify the
   import path on merge, not just today.
2. I set thresholds after seeing numbers — freezing them in this file first is the
   one ritual keeping this from becoming theater; deviations get labeled exploratory.
3. Fuzz scenarios may not cover the one audience composition that breaks
   monotonicity — the check proves resistance on the sampled space, never the
   property in general; the report says exactly that.
