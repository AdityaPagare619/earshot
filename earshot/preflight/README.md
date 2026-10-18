# earshot/preflight

Cert-style harness grading the EARSHOT policy contract (MASTER_PLAN §4 component E —
the video's proof beat, 2:15–2:45).

## Run it

```bash
python3 preflight.py                 # full run, ~1s, prints one-screen summary
python3 preflight.py --self-test    # injects the override-escalation mutant: check 3 MUST fail
```

No dependencies (stdlib only). Writes `preflight-report.json` next to the script.

## What it checks (thresholds frozen in DESIGN.md before measurement)

1. **Latency** — 20,000 `decide_disclosure()` calls, p50/p95/p99; PASS iff p95 < 500ms.
2. **Fail-closed coverage** — 5,000 presence_confidence < 0.6 scenarios; PASS iff 100%
   engage fail-closed AND cap disclosure by sensitivity (HIGH→≤EXISTENCE, MEDIUM→≤ABSTRACT).
3. **Monotonic-downward** — 5,000 scenarios × 2 attacks (voice override "just tell
   everyone", audience growth); PASS iff 0 escalations.

Verdict PASS = all three pass. A failing check is a finding, not hidden.

## Policy source (reported honestly in the JSON)

1. `../policy-port/earshot/policy/policy.py` if the policy-port lane has landed it;
2. else `~/workspace/amazon-hackathon/worldsim/policy.py` (the sim-tested engine —
   what this tree runs against today);
3. else a built-in minimal mock, labeled `policy_source: "mock"`, never quoted as proof.

`decide_disclosure()` is the MCP tool contract from MASTER_PLAN §3, adapted over the
engine's `decide()`. Frozen fuzz seed `20261018` for reproducibility.

## Video line

```
pre-flight: PASS — p95 0.01ms / fail-closed 100% / monotonic ✓
```
