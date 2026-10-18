"""
EARSHOT notify-ledger lane: policy decision contract + a faithful mock.

The real engine lives in worldsim/policy.py (ported by the policy-port lane).
This mock mirrors its semantics exactly — deny-first precedence, presence beats
identity, fail-closed at 0.6 confidence, sensitivity -> level mapping — so the
five tools behave identically when mcp-server swaps in the real engine.
"""
import time

FULL, ABSTRACT, EXISTENCE, SILENT = "FULL", "ABSTRACT", "EXISTENCE", "SILENT"
_LEVEL_RANK = {SILENT: 0, EXISTENCE: 1, ABSTRACT: 2, FULL: 3}
PUBLIC, LOW, MEDIUM, HIGH = "PUBLIC", "LOW", "MEDIUM", "HIGH"

# Shared with worldsim/policy.py. Divergence here = Instax replays.
FAIL_CLOSED_CONFIDENCE = 0.6


def _cap(a, b):
    return a if _LEVEL_RANK[a] <= _LEVEL_RANK[b] else b


class Decision:
    """Decision contract: {level, reasons, latency_ms, untrusted_seen, rule_hit}."""

    __slots__ = ("level", "reasons", "latency_ms", "untrusted_seen", "rule_hit")

    def __init__(self, level, reasons, latency_ms, untrusted_seen, rule_hit):
        self.level = level
        self.reasons = reasons
        self.latency_ms = latency_ms
        self.untrusted_seen = untrusted_seen
        self.rule_hit = rule_hit

    def to_dict(self):
        return {
            "level": self.level,
            "reasons": list(self.reasons),
            "latency_ms": round(self.latency_ms, 4),
            "untrusted_seen": sorted(self.untrusted_seen),
            "rule_hit": self.rule_hit,
        }


class MockPolicy:
    """Drop-in stand-in for the policy-port engine. Same call shape: decide()."""

    def decide(self, speaker, audience_perceived, presence_confidence, item,
               rules, device_kind="echo_show", override_attempt=False):
        t0 = time.perf_counter()
        reasons = []
        topics = set(item["topics"])
        sens = item["sensitivity"]

        allow_persons = set()
        for r in rules:
            if r["kind"] == "allow" and topics & set(r["topics"]):
                allow_persons |= set(r["persons"])

        uncertain = presence_confidence < FAIL_CLOSED_CONFIDENCE
        audience = set(audience_perceived)
        untrusted = {p for p in audience if p != speaker and p not in allow_persons}
        if uncertain:
            untrusted.add("__unknown__")
            reasons.append("presence uncertain -> fail closed")

        # Deny rules: presence always beats identity.
        cap = FULL
        rule_hit = None
        for r in rules:
            if r["kind"] != "deny" or not (topics & set(r["topics"])):
                continue
            scope = r["in_front_of"]
            hit = (scope == "any_untrusted" and bool(untrusted)) or bool(audience & set(scope))
            if hit:
                cap = _cap(cap, r["cap"])
                rule_hit = r["name"]
                reasons.append(f"deny rule '{r['name']}' caps at {r['cap']}")

        if not untrusted:
            level = FULL
            reasons.append("audience fully trusted")
        else:
            if sens == HIGH:
                level = EXISTENCE
            elif sens == MEDIUM:
                level = ABSTRACT
            else:
                level = FULL
            reasons.append(f"untrusted present {sorted(untrusted)}; {sens} -> {level}")

        level = _cap(level, cap)

        if override_attempt:
            reasons.append("override attempt resisted: voice cannot widen disclosure")

        latency_ms = (time.perf_counter() - t0) * 1000
        return Decision(level, reasons, latency_ms, untrusted, rule_hit)
