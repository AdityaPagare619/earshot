"""
EARSHOT policy engine — the deterministic disclosure rules.

Faithful port of `worldsim/policy.py` (the sim-tested engine: 42.4% -> 0 leaks
over 3,000 personas). The `decide()` contract is FROZEN: same signature, same
level names, same Decision constructor fields, same FAIL_CLOSED_CONFIDENCE,
deny-first precedence, monotonic-downward override handling.

Production additions (MASTER_PLAN P0s), all backward compatible:
  - P0-1: `decide_after_resample()` — wake word triggers a fresh presence
    re-sample before every disclosure decision (measured: residual leaks -> 0).
  - P0-2: SILENT pairs with a private nudge — `Decision.nudge_required` is True
    exactly when level == SILENT (certification: never a dead end).
  - P0-3: unknown topics default HIGH — an item with missing/invalid
    `sensitivity` is treated as HIGH (fail closed) instead of crashing.

No AI in the hot path; decisions are pure functions of
(speaker, perceived audience, presence confidence, item, user rules, device).
"""
import time

FULL, ABSTRACT, EXISTENCE, SILENT = "FULL", "ABSTRACT", "EXISTENCE", "SILENT"
_LEVEL_RANK = {SILENT: 0, EXISTENCE: 1, ABSTRACT: 2, FULL: 3}

PUBLIC, LOW, MEDIUM, HIGH = "PUBLIC", "LOW", "MEDIUM", "HIGH"
_VALID_TIERS = frozenset({PUBLIC, LOW, MEDIUM, HIGH})

# Below this presence confidence we fail closed: treat the room as untrusted.
FAIL_CLOSED_CONFIDENCE = 0.6


def _cap(a, b):
    return a if _LEVEL_RANK[a] <= _LEVEL_RANK[b] else b


class Decision:
    __slots__ = ("level", "reasons", "latency_ms", "untrusted_seen", "rule_hit")

    def __init__(self, level, reasons, latency_ms, untrusted_seen, rule_hit):
        self.level = level
        self.reasons = reasons
        self.latency_ms = latency_ms
        self.untrusted_seen = untrusted_seen
        self.rule_hit = rule_hit

    @property
    def nudge_required(self):
        """P0-2: SILENT is never a dead end — the speaker channel pairs with a
        private nudge (phone buzz/card) on the second channel."""
        return self.level == SILENT

    def to_dict(self):
        return {
            "level": self.level,
            "reasons": self.reasons,
            "latency_ms": round(self.latency_ms, 4),
            "untrusted_seen": sorted(self.untrusted_seen),
            "rule_hit": self.rule_hit,
            "nudge_required": self.nudge_required,
        }


def decide(speaker, audience_perceived, presence_confidence, item, rules,
           device_kind="echo_show", override_attempt=False):
    """Core EARSHOT decision.

    speaker: persona id asking. audience_perceived: set of persona ids believed present
      (includes speaker). presence_confidence: 0..1. item: dict(sensitivity, topics:set,
      label). rules: list of rule dicts. override_attempt: user tried "just tell everyone".
    """
    t0 = time.perf_counter()
    reasons = []
    topics = set(item["topics"])

    # P0-3: unknown topics default HIGH (fail closed) with a voice-correction path.
    sens = item.get("sensitivity")
    if sens not in _VALID_TIERS:
        reasons.append("unknown/missing sensitivity tier -> default HIGH (fail closed)")
        sens = HIGH

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

    if level == SILENT:
        # P0-2: certification forbids silent failures — pair SILENT on the
        # speaker channel with a private nudge on the second channel.
        reasons.append("SILENT -> private nudge to second channel required")

    if override_attempt:
        # A voice override can never escalate disclosure. It is logged, not obeyed.
        reasons.append("override attempt resisted: voice cannot widen disclosure")

    latency_ms = (time.perf_counter() - t0) * 1000
    return Decision(level, reasons, latency_ms, untrusted, rule_hit)


def decide_after_resample(resample, speaker, item, rules,
                          device_kind="echo_show", override_attempt=False):
    """P0-1 wake-word path: take a FRESH presence snapshot at decision time,
    then decide. `resample` is a zero-arg callable returning
    `(audience_perceived, presence_confidence)`.

    The sim's residual leaks (presence lag on new arrivals) vanished only when
    the decision used a re-sampled snapshot; the engine keeps this purity by
    never caching presence itself — the caller re-samples.
    """
    audience_perceived, presence_confidence = resample()
    return decide(speaker, audience_perceived, presence_confidence, item, rules,
                  device_kind, override_attempt)


def naive_decide(item):
    """The world WITHOUT earshot: a plain assistant reads everything aloud."""
    t0 = time.perf_counter()
    latency_ms = (time.perf_counter() - t0) * 1000
    return Decision(FULL, ["no gateway: everything spoken"], latency_ms, set(), None)
