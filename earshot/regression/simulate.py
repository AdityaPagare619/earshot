"""
Run the world: every request event goes through BOTH policies —
naive (no gateway) and EARSHOT — against ground-truth room occupancy.
Metrics: leaks, over-withholding, override resistance, latency, rule conflicts.
"""
import json
import random
import statistics
import sys

from earshot.policy.engine import (  # regression wire: tests the SHIPPED engine
    decide, naive_decide, FULL, ABSTRACT, EXISTENCE, SILENT)
from earshot.regression.world import (  # regression wire
    generate_personas, compose_households, default_rules_for, generate_day)


def _fmt_time(t):
    return "%02d:%02d" % (t // 60, t % 60)


def run(n_personas=1200, seed=99, fresh_wake_snapshot=False):
    rng = random.Random(seed)
    personas = generate_personas(n_personas, seed=seed)
    households = compose_households(personas, seed=seed + 1)

    stats = {
        "households": len(households), "personas": n_personas,
        "decisions": 0, "visitor_scenarios": 0,
        "leak_high_naive": 0, "leak_med_naive": 0,
        "leak_high_earshot": 0, "leak_med_earshot": 0,
        "overwithhold": 0, "overwithhold_opportunities": 0,
        "overrides": 0, "overrides_resisted": 0,
        "rule_conflicts": 0, "deny_hits": 0, "allow_hits": 0,
        "lat_naive": [], "lat_earshot": [],
        "sensitive_requests": 0,
    }
    leak_examples, good_catches, conflict_examples = [], [], []

    for hh in households:
        rules = default_rules_for(hh, rng)
        # count conflicting rule pairs (allow+deny on same topic)
        allow_topics, deny_topics = set(), set()
        for r in rules:
            (allow_topics if r["kind"] == "allow" else deny_topics).update(r["topics"])
        if allow_topics & deny_topics:
            stats["rule_conflicts"] += 1
            if len(conflict_examples) < 8:
                conflict_examples.append(
                    {"household": hh["id"],
                     "topics": sorted(allow_topics & deny_topics)})

        for ev in generate_day(hh, rng, fresh_wake_snapshot):
            if ev["type"] == "visitor_arrives":
                stats["visitor_scenarios"] += 1
                continue
            if ev["type"] != "request":
                continue
            item, gt = ev["item"], ev["audience_gt"]
            stats["decisions"] += 1
            sens = item["sensitivity"]
            if sens in ("MEDIUM", "HIGH"):
                stats["sensitive_requests"] += 1

            # ground-truth untrusted: anyone present who is not the speaker
            # and not covered by an allow-rule for these topics
            allowed = set()
            for r in rules:
                if r["kind"] == "allow" and set(item["topics"]) & set(r["topics"]):
                    allowed |= set(r["persons"])
                    stats["allow_hits"] += 1
            untrusted_gt = {p for p in gt if p != ev["speaker"] and p not in allowed}

            d_naive = naive_decide(item)
            d_ear = decide(ev["speaker"], ev["audience_perceived"],
                           ev["confidence"], item, rules, ev["device"],
                           ev["override_attempt"])
            stats["lat_naive"].append(d_naive.latency_ms)
            stats["lat_earshot"].append(d_ear.latency_ms)
            if d_ear.rule_hit:
                stats["deny_hits"] += 1

            # --- leaks: sensitive content spoken while untrusted truly present
            if untrusted_gt:
                if sens == "HIGH" and d_naive.level in (FULL, ABSTRACT):
                    stats["leak_high_naive"] += 1
                if sens == "MEDIUM" and d_naive.level == FULL:
                    stats["leak_med_naive"] += 1
                if sens == "HIGH" and d_ear.level in (FULL, ABSTRACT):
                    stats["leak_high_earshot"] += 1
                    if len(leak_examples) < 10:
                        leak_examples.append({
                            "t": _fmt_time(ev["t"]), "household": hh["id"],
                            "speaker": ev["speaker_name"], "item": item["label"],
                            "level": d_ear.level,
                            "reasons": d_ear.reasons,
                            "visitor": bool(ev.get("visitor_present")),
                        })
                if sens == "MEDIUM" and d_ear.level == FULL:
                    stats["leak_med_earshot"] += 1
                # good catch: earshot withheld what naive would have leaked
                if sens == "HIGH" and d_ear.level in (EXISTENCE, SILENT) \
                        and len(good_catches) < 10 and rng.random() < 0.05:
                    good_catches.append({
                        "t": _fmt_time(ev["t"]), "household": hh["id"],
                        "speaker": ev["speaker_name"], "item": item["label"],
                        "level": d_ear.level,
                        "reasons": d_ear.reasons,
                        "visitor": bool(ev.get("visitor_present")),
                    })

            # --- over-withholding: trusted room, low-stakes item, yet withheld
            if not untrusted_gt and sens in ("PUBLIC", "LOW"):
                stats["overwithhold_opportunities"] += 1
                if d_ear.level != FULL:
                    stats["overwithhold"] += 1

            # --- override resistance
            if ev["override_attempt"]:
                stats["overrides"] += 1
                # resisted if level did not escalate past audience-risk baseline
                base = decide(ev["speaker"], ev["audience_perceived"],
                              ev["confidence"], item, rules, ev["device"], False)
                rank = {SILENT: 0, EXISTENCE: 1, ABSTRACT: 2, FULL: 3}
                if rank[d_ear.level] <= rank[base.level]:
                    stats["overrides_resisted"] += 1

    return stats, leak_examples, good_catches, conflict_examples


def summarize(stats):
    s = stats
    sens = max(s["sensitive_requests"], 1)
    out = []
    out.append("households=%d personas=%d decisions=%d sensitive=%d visitor_scenarios=%d"
               % (s["households"], s["personas"], s["decisions"],
                  s["sensitive_requests"], s["visitor_scenarios"]))
    out.append("NAIVE  high-leaks=%d (%.2f%% of sensitive)  med-leaks=%d"
               % (s["leak_high_naive"], 100.0 * s["leak_high_naive"] / sens,
                  s["leak_med_naive"]))
    out.append("EARSHOT high-leaks=%d (%.2f%%)  med-leaks=%d"
               % (s["leak_high_earshot"], 100.0 * s["leak_high_earshot"] / sens,
                  s["leak_med_earshot"]))
    opp = max(s["overwithhold_opportunities"], 1)
    out.append("over-withhold: %d/%d (%.2f%% of safe low-stakes moments)"
               % (s["overwithhold"], s["overwithhold_opportunities"],
                  100.0 * s["overwithhold"] / opp))
    if s["overrides"]:
        out.append("override attempts: %d resisted=%d (%.1f%%)"
                   % (s["overrides"], s["overrides_resisted"],
                      100.0 * s["overrides_resisted"] / s["overrides"]))
    out.append("rule conflicts (allow+deny same topic): %d households; "
               "deny hits=%d allow hits=%d"
               % (s["rule_conflicts"], s["deny_hits"], s["allow_hits"]))
    out.append("decision latency ms: naive p50=%.4f p99=%.4f | earshot p50=%.4f p99=%.4f"
               % (statistics.median(s["lat_naive"]),
                  sorted(s["lat_naive"])[int(0.99 * (len(s["lat_naive"]) - 1))],
                  statistics.median(s["lat_earshot"]),
                  sorted(s["lat_earshot"])[int(0.99 * (len(s["lat_earshot"]) - 1))]))
    return "\n".join(out)


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 1200
    stats, leaks, catches, conflicts = run(n_personas=n,
                                           fresh_wake_snapshot="--fresh" in sys.argv)
    print(summarize(stats))
    with open("results.json", "w") as f:
        json.dump({"stats": {k: v for k, v in stats.items()
                             if not k.startswith("lat")},
                   "leak_examples": leaks,
                   "good_catches": catches,
                   "rule_conflicts": conflicts}, f, indent=1,
                  default=str)
    print("wrote results.json")
