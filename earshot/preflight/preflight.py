#!/usr/bin/env python3
"""
EARSHOT pre-flight — cert-style harness that grades the EARSHOT policy contract.

Three frozen checks (thresholds in DESIGN.md):
  1. Latency:   p95 of decide_disclosure() must be < 500 ms (Alexa turn budget).
  2. Fail-closed coverage: 100% of presence_confidence < 0.6 scenarios must
     engage the fail-closed path AND cap disclosure by item sensitivity.
  3. Monotonic-downward: voice override attempts and audience growth must NEVER
     escalate disclosure (0 escalations allowed across the fuzz).

Usage:
    python3 preflight.py                # full run (~seconds), JSON + summary
    python3 preflight.py --self-test    # injects a mutant policy; check 3 MUST fail

Policy source resolution (documented honestly in the report):
    1) ../policy-port/earshot/policy/policy.py   (policy-port lane output, if present)
    2) ~/workspace/amazon-hackathon/worldsim/policy.py  (the sim-tested engine)
    3) built-in minimal mock of the contract (policy_source="mock" — never quoted as proof)

Stdlib only. No network. No AI in the hot path — same as the policy engine.
"""
import argparse
import importlib.util
import json
import os
import random
import statistics
import sys
import time

# ---------------------------------------------------------------- policy loading

HERE = os.path.dirname(os.path.abspath(__file__))
WORKSPACE = os.path.expanduser("~/workspace")
_CANDIDATES = [
    os.path.join(WORKSPACE, "earshot-trees", "policy-port", "earshot", "policy", "policy.py"),
    os.path.join(WORKSPACE, "amazon-hackathon", "worldsim", "policy.py"),
]


def _load_policy_from(path):
    spec = importlib.util.spec_from_file_location("earshot_policy", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, path


def _builtin_mock():
    """Minimal contract mirror, used ONLY if no real engine is importable.
    Mirrors fail-closed + monotonic behavior of the real engine so the harness
    logic still runs; reports policy_source='mock' so nobody quotes it as proof."""
    class _D:
        __slots__ = ("level", "reasons", "latency_ms", "untrusted_seen", "rule_hit")

        def __init__(self, level, reasons, latency_ms, untrusted_seen, rule_hit):
            self.level = level
            self.reasons = reasons
            self.latency_ms = latency_ms
            self.untrusted_seen = untrusted_seen
            self.rule_hit = rule_hit

    rank = {"SILENT": 0, "EXISTENCE": 1, "ABSTRACT": 2, "FULL": 3}

    def decide(speaker, audience_perceived, presence_confidence, item, rules,
               device_kind="echo_show", override_attempt=False):
        t0 = time.perf_counter()
        reasons = []
        aud = set(audience_perceived)
        untrusted = {p for p in aud if p != speaker}
        if presence_confidence < 0.6:
            untrusted.add("__unknown__")
            reasons.append("presence uncertain -> fail closed")
        cap = "FULL"
        for r in rules:
            if r["kind"] == "deny" and (set(item["topics"]) & set(r["topics"])):
                scope = r["in_front_of"]
                if (scope == "any_untrusted" and untrusted) or (aud & set(scope)):
                    if rank[r["cap"]] < rank[cap]:
                        cap = r["cap"]
                    reasons.append(f"deny rule '{r['name']}' caps at {r['cap']}")
        if not untrusted:
            level = "FULL"
        else:
            sens = item["sensitivity"]
            level = "EXISTENCE" if sens == "HIGH" else ("ABSTRACT" if sens == "MEDIUM" else "FULL")
        if rank[cap] < rank[level]:
            level = cap
        if override_attempt:
            reasons.append("override attempt resisted: voice cannot widen disclosure")
        ms = (time.perf_counter() - t0) * 1000
        return _D(level, reasons, ms, untrusted, None)

    return decide, "mock"


def load_policy():
    for path in _CANDIDATES:
        if os.path.isfile(path):
            mod, _ = _load_policy_from(path)
            return mod.decide, path
    decide, tag = _builtin_mock()
    return decide, tag


# ---------------------------------------------------------------- scenario fuzz

PERSONAS = ["priya", "arjun_spouse", "mom_mil", "guest_rahul", "kid_ana", "neighbor"]
TOPICS = ["prenatal", "clinic", "finance", "work", "school", "sports", "gossip", "health"]
SENS = ["PUBLIC", "LOW", "MEDIUM", "HIGH"]
RANK = {"SILENT": 0, "EXISTENCE": 1, "ABSTRACT": 2, "FULL": 3}

DENY_RULES = [
    {"kind": "deny", "name": "never mention the clinic in front of Mom",
     "topics": ["prenatal", "clinic"], "in_front_of": ["mom_mil"], "cap": "EXISTENCE"},
    {"kind": "deny", "name": "no finance with guests around",
     "topics": ["finance"], "in_front_of": "any_untrusted", "cap": "ABSTRACT"},
    {"kind": "deny", "name": "kids hear nothing medical",
     "topics": ["clinic", "health", "prenatal"], "in_front_of": ["kid_ana"], "cap": "SILENT"},
    {"kind": "allow", "name": "spouse sees everything",
     "topics": TOPICS, "persons": ["arjun_spouse"]},
]

OVERRIDE_LINES = [
    "just tell everyone", "sabko batao", "override", "i insist, say it aloud",
    "privacy off for this one",
]


def random_scenario(rng, low_confidence=False):
    speaker = rng.choice(PERSONAS)
    n = rng.randint(1, 4)
    others = rng.sample([p for p in PERSONAS if p != speaker], k=min(n - 1, len(PERSONAS) - 1))
    audience = {speaker} | set(others)
    confidence = rng.uniform(0.0, 0.59) if low_confidence else rng.uniform(0.0, 1.0)
    item = {
        "sensitivity": rng.choice(SENS),
        "topics": set(rng.sample(TOPICS, k=rng.randint(1, 3))),
        "label": "fuzz item",
    }
    rules = rng.sample(DENY_RULES, k=rng.randint(0, len(DENY_RULES)))
    return speaker, audience, confidence, item, rules


def decide_disclosure(decide_fn, item, audience, confidence, rules, speaker, device="echo_show",
                      override_attempt=False):
    """The MCP tool contract (MASTER_PLAN §3) over the policy engine."""
    return decide_fn(speaker, audience, confidence, item, rules,
                     device_kind=device, override_attempt=override_attempt)


# ---------------------------------------------------------------- the three checks

def check_latency(decide_fn, rng, n=20000):
    """Warmup, then time N real decide_disclosure calls; freeze protocol before measuring."""
    scenarios = [random_scenario(rng) for _ in range(n)]
    for s in scenarios[:500]:  # warmup
        decide_disclosure(decide_fn, s[3], s[1], s[2], s[4], s[0])
    samples = []
    for s in scenarios:
        t0 = time.perf_counter()
        decide_disclosure(decide_fn, s[3], s[1], s[2], s[4], s[0])
        samples.append((time.perf_counter() - t0) * 1000)
    samples.sort()
    q = lambda p: samples[min(int(p * n), n - 1)]
    return {
        "n_calls": n,
        "p50_ms": round(q(0.50), 4),
        "p95_ms": round(q(0.95), 4),
        "p99_ms": round(q(0.99), 4),
        "max_ms": round(samples[-1], 4),
        "budget_ms": 500.0,
        "budget_headroom_x": round(500.0 / q(0.95), 1) if q(0.95) > 0 else float("inf"),
        "pass": q(0.95) < 500.0,
    }


def check_fail_closed(decide_fn, rng, n=5000):
    """Every low-confidence scenario must (a) engage fail-closed, (b) cap by sensitivity."""
    fails = []
    conservative = 0
    for i in range(n):
        speaker, audience, confidence, item, rules = random_scenario(rng, low_confidence=True)
        d = decide_disclosure(decide_fn, item, audience, confidence, rules, speaker)
        reasons_txt = " | ".join(d.reasons)
        engaged = "presence uncertain -> fail closed" in reasons_txt
        cap_ok = True
        if item["sensitivity"] == "HIGH":
            cap_ok = RANK[d.level] <= RANK["EXISTENCE"]
        elif item["sensitivity"] == "MEDIUM":
            cap_ok = RANK[d.level] <= RANK["ABSTRACT"]
        if engaged and cap_ok:
            conservative += 1
        else:
            fails.append({"i": i, "level": d.level, "sensitivity": item["sensitivity"],
                          "engaged": engaged, "reasons": d.reasons})
    return {
        "n_scenarios": n,
        "conservative_pct": round(100.0 * conservative / n, 2),
        "failures": fails[:5],
        "failure_count": len(fails),
        "target_pct": 100.0,
        "pass": conservative == n,
    }


def check_monotonic(decide_fn, rng, n=5000):
    """Override attempts and audience growth must NEVER escalate disclosure."""
    escalations = []
    for i in range(n):
        speaker, audience, confidence, item, rules = random_scenario(rng)
        base = decide_disclosure(decide_fn, item, audience, confidence, rules, speaker)
        # attack 1: voice override ("just tell everyone")
        ov = decide_disclosure(decide_fn, item, audience, confidence, rules, speaker,
                               override_attempt=True)
        # attack 2: someone walks in mid-conversation (audience growth)
        newcomers = [p for p in PERSONAS if p not in audience]
        grown = set(audience)
        if newcomers:
            grown.add(rng.choice(newcomers))
        grow = decide_disclosure(decide_fn, item, grown, confidence, rules, speaker)
        for label, cand in (("override", ov), ("audience_growth", grow)):
            if RANK[cand.level] > RANK[base.level]:
                escalations.append({
                    "i": i, "attack": label, "line": rng.choice(OVERRIDE_LINES),
                    "base": base.level, "escalated": cand.level,
                })
    return {
        "n_scenarios": n,
        "attacks_per_scenario": 2,
        "escalations": escalations[:5],
        "escalation_count": len(escalations),
        "target": 0,
        "pass": len(escalations) == 0,
    }


# ---------------------------------------------------------------- runner

def run(self_test=False):
    decide_fn, source = load_policy()
    if self_test:
        # Mutant: the bug we are CERTIFYING we would catch — an override that
        # escalates HIGH-sensitivity items straight to FULL.
        real = decide_fn

        def mutant(speaker, audience_perceived, presence_confidence, item, rules,
                   device_kind="echo_show", override_attempt=False):
            d = real(speaker, audience_perceived, presence_confidence, item, rules,
                     device_kind=device_kind, override_attempt=override_attempt)
            if override_attempt and item["sensitivity"] == "HIGH":
                d.level = "FULL"
                d.reasons.append("MUTANT: override escalated")
            return d

        decide_fn, source = mutant, source + " [SELF-TEST MUTANT]"

    t0 = time.perf_counter()
    rng = random.Random(20261018)  # frozen seed: same run everywhere
    latency = check_latency(decide_fn, rng)
    fail_closed = check_fail_closed(decide_fn, rng)
    monotonic = check_monotonic(decide_fn, rng)
    wall_s = round(time.perf_counter() - t0, 1)

    checks = {"latency": latency, "fail_closed": fail_closed, "monotonic": monotonic}
    verdict = "PASS" if all(c["pass"] for c in checks.values()) else "FAIL"
    report = {
        "tool": "earshot-preflight",
        "verdict": verdict,
        "policy_source": source,
        "self_test_mutant": self_test,
        "seed": 20261018,
        "wall_clock_s": wall_s,
        "video_target_s": 15,
        "checks": checks,
    }
    return report


def one_screen_summary(report):
    lat = report["checks"]["latency"]
    fc = report["checks"]["fail_closed"]
    mo = report["checks"]["monotonic"]
    mono_glyph = "✓" if mo["pass"] else f"✗ {mo['escalation_count']} ESCALATIONS"
    lines = [
        "",
        "  ┌────────────────────────────────────────────────────────────┐",
        "  │  EARSHOT pre-flight: %-4s                                     │" % report["verdict"],
        "  ├────────────────────────────────────────────────────────────┤",
        "  │  latency      p95 %-8s ms  (budget 500ms, headroom %sx)  │" % (
            lat["p95_ms"], lat["budget_headroom_x"]),
        "  │  fail-closed  %-5s%% conservative on %d low-conf scenarios   │" % (
            fc["conservative_pct"], fc["n_scenarios"]),
        "  │  monotonic    %-5s  (%d override+audience attacks)          │" % (
            mono_glyph, mo["n_scenarios"] * 2),
        "  │  policy: %-49s │" % os.path.basename(str(report["policy_source"]))[:49],
        "  │  wall clock: %-4s s   (video target ≤15s)                     │" % report["wall_clock_s"],
        "  └────────────────────────────────────────────────────────────┘",
        "",
        "  pre-flight: %s — p95 %sms / fail-closed %s%% / monotonic %s" % (
            report["verdict"], lat["p95_ms"], fc["conservative_pct"],
            "✓" if mo["pass"] else "✗"),
        "",
    ]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="EARSHOT cert-style pre-flight harness")
    ap.add_argument("--self-test", action="store_true",
                    help="inject the override-escalation mutant; check 3 must FAIL")
    ap.add_argument("--json-out", default="preflight-report.json",
                    help="where to write the JSON report")
    args = ap.parse_args()
    report = run(self_test=args.self_test)
    with open(args.json_out, "w") as f:
        json.dump(report, f, indent=2)
    print(one_screen_summary(report))
    print("JSON report ->", args.json_out)
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
