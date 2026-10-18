"""Unit tests for the EARSHOT policy engine port.

Covers MASTER_PLAN P0-1/2/3, monotonic-downward, deny-beats-allow, fail-closed,
and the FROZEN decide() contract.
"""
import inspect
import statistics

import pytest

from earshot.policy.engine import (
    FULL, ABSTRACT, EXISTENCE, SILENT,
    PUBLIC, LOW, MEDIUM, HIGH,
    FAIL_CLOSED_CONFIDENCE,
    Decision, decide, decide_after_resample, naive_decide,
)

RANK = {SILENT: 0, EXISTENCE: 1, ABSTRACT: 2, FULL: 3}

PRIYA, SPOUSE, MOM = "priya", "spouse", "mom"


def item(sensitivity=None, topics=("health",), label="Lab report: HbA1c 8.1"):
    d = {"topics": set(topics), "label": label}
    if sensitivity is not None:
        d["sensitivity"] = sensitivity
    return d


def deny_rule(name="no-health-mom", topics=("health",), scope=None, cap="EXISTENCE"):
    return {"kind": "deny", "name": name, "topics": set(topics),
            "in_front_of": {MOM} if scope is None else scope, "cap": cap}


def allow_rule(name="spouse-money", topics=("money",), persons=(SPOUSE,)):
    return {"kind": "allow", "name": name, "topics": set(topics),
            "persons": set(persons)}


# ---------------------------------------------------------------- P0-1
def test_p01_wake_word_fresh_resample_closes_presence_lag():
    """P0-1: a visitor arrives after the last snapshot; the stale snapshot
    leaks (FULL), the wake-word fresh re-sample withholds."""
    high = item(HIGH)
    stale = lambda: ({PRIYA}, 0.95)                      # visitor not yet seen
    fresh = lambda: ({PRIYA, MOM}, 0.95)                 # re-sampled at wake word
    d_stale = decide_after_resample(stale, PRIYA, high, [])
    d_fresh = decide_after_resample(fresh, PRIYA, high, [])
    assert d_stale.level == FULL, "stale snapshot leaks HIGH to the room"
    assert RANK[d_fresh.level] < RANK[d_stale.level]
    assert d_fresh.level == EXISTENCE
    assert MOM in d_fresh.untrusted_seen


def test_p01_resample_fn_receives_no_caching_inside_engine():
    """The engine never caches presence: two calls with different snapshots
    decide on their own inputs."""
    calls = iter([({PRIYA}, 0.9), ({PRIYA, MOM}, 0.9)])
    d1 = decide_after_resample(lambda: next(calls), PRIYA, item(HIGH), [])
    d2 = decide_after_resample(lambda: next(calls), PRIYA, item(HIGH), [])
    assert d1.level == FULL and d2.level == EXISTENCE


# ---------------------------------------------------------------- P0-2
def test_p02_silent_pairs_with_private_nudge():
    """P0-2: SILENT is never a dead end — the engine emits a nudge flag."""
    rules = [deny_rule(name="rel-silent", topics=("relationship",),
                       scope="any_untrusted", cap=SILENT)]
    d = decide(PRIYA, {PRIYA, MOM}, 0.95, item(HIGH, topics=("relationship",)),
               rules)
    assert d.level == SILENT
    assert d.nudge_required is True
    assert d.to_dict()["nudge_required"] is True
    assert any("nudge" in r.lower() for r in d.reasons)
    assert d.rule_hit == "rel-silent"


@pytest.mark.parametrize("level,item_kw,rules", [
    (FULL, dict(sensitivity=LOW, topics=("family",)), []),
    (EXISTENCE, dict(sensitivity=HIGH, topics=("health",)), []),
    (ABSTRACT, dict(sensitivity=MEDIUM, topics=("work",)), []),
])
def test_p02_no_nudge_unless_silent(level, item_kw, rules):
    d = decide(PRIYA, {PRIYA, MOM}, 0.95, item(**item_kw), rules)
    assert d.level == level
    assert d.nudge_required is False
    assert d.to_dict()["nudge_required"] is False


# ---------------------------------------------------------------- P0-3
def test_p03_unknown_topics_default_high():
    """P0-3: missing/invalid sensitivity tier fails closed to HIGH."""
    for bad in (None, "CRITICAL", ""):
        it = {"topics": {"schedule"}, "label": "mystery payload"}
        if bad is not None:
            it["sensitivity"] = bad
        d = decide(PRIYA, {PRIYA, MOM}, 0.95, it, [])
        assert d.level == EXISTENCE, f"tier={bad!r} did not fail closed"
        assert any("default HIGH" in r for r in d.reasons)


def test_p03_valid_tiers_unchanged():
    """Well-formed items behave exactly as the sim-tested mapping."""
    assert decide(PRIYA, {PRIYA, MOM}, 0.9, item(LOW, ("family",)), []).level == FULL
    assert decide(PRIYA, {PRIYA, MOM}, 0.9, item(MEDIUM, ("work",)), []).level == ABSTRACT
    assert decide(PRIYA, {PRIYA, MOM}, 0.9, item(HIGH), []).level == EXISTENCE
    assert decide(PRIYA, {PRIYA, MOM}, 0.9, item(PUBLIC, ("news",)), []).level == FULL


# ------------------------------------------------- monotonic-downward
SCENARIOS = [
    (PRIYA, {PRIYA}, 0.95, item(HIGH), []),
    (PRIYA, {PRIYA, MOM}, 0.95, item(HIGH), []),
    (PRIYA, {PRIYA, MOM}, 0.95, item(MEDIUM, ("work",)), []),
    (PRIYA, {PRIYA, SPOUSE, MOM}, 0.95, item(HIGH, ("money",)),
     [allow_rule(), deny_rule(name="no-money-mom", topics=("money",), cap=SILENT)]),
    (PRIYA, {PRIYA}, 0.30, item(HIGH), []),
    (PRIYA, {PRIYA, MOM}, 0.95, item(HIGH, ("relationship",)),
     [deny_rule(name="rel-silent", topics=("relationship",),
                scope="any_untrusted", cap=SILENT)]),
]


@pytest.mark.parametrize("speaker,aud,conf,it,rules", SCENARIOS)
def test_monotonic_downward_override_never_escalates(speaker, aud, conf, it, rules):
    """Voice can narrow disclosure, never widen it (100% resisted in sim)."""
    base = decide(speaker, aud, conf, it, rules, override_attempt=False)
    att = decide(speaker, aud, conf, it, rules, override_attempt=True)
    assert RANK[att.level] <= RANK[base.level], (
        f"override escalated {base.level} -> {att.level}")
    assert any("resist" in r.lower() for r in att.reasons)


# ------------------------------------------------------ deny-beats-allow
def test_deny_beats_allow_presence_beats_identity():
    """Spouse allowlisted for money topics still loses the moment Mom walks in:
    presence beats identity; deny beats allow."""
    rules = [allow_rule(),
             deny_rule(name="no-money-mom", topics=("money",), cap=SILENT)]
    money = item(HIGH, topics=("money",), label="Savings balance")
    with_mom = decide(PRIYA, {PRIYA, SPOUSE, MOM}, 0.95, money, rules)
    without_mom = decide(PRIYA, {PRIYA, SPOUSE}, 0.95, money, rules)
    assert with_mom.level == SILENT and with_mom.rule_hit == "no-money-mom"
    assert without_mom.level == FULL  # spouse allowed, nobody untrusted


def test_deny_any_untrusted_scope():
    rules = [deny_rule(name="work-any", topics=("work",),
                       scope="any_untrusted", cap=ABSTRACT)]
    d = decide(PRIYA, {PRIYA, MOM}, 0.95, item(MEDIUM, ("work",)), rules)
    assert d.level == ABSTRACT and d.rule_hit == "work-any"


# --------------------------------------------------------- fail-closed
def test_fail_closed_low_confidence():
    d = decide(PRIYA, {PRIYA}, 0.30, item(HIGH), [])
    assert "__unknown__" in d.untrusted_seen
    assert d.level == EXISTENCE
    assert any("fail closed" in r for r in d.reasons)


def test_fail_closed_boundary_is_exactly_06():
    """0.6 is trusted; anything below fails closed (FROZEN threshold)."""
    assert FAIL_CLOSED_CONFIDENCE == 0.6
    assert decide(PRIYA, {PRIYA}, 0.6, item(HIGH), []).level == FULL
    assert decide(PRIYA, {PRIYA}, 0.599, item(HIGH), []).level == EXISTENCE


# ---------------------------------------------------- frozen contract
def test_frozen_decide_signature():
    params = list(inspect.signature(decide).parameters)
    assert params == ["speaker", "audience_perceived", "presence_confidence",
                      "item", "rules", "device_kind", "override_attempt"]
    sig = inspect.signature(decide)
    assert sig.parameters["device_kind"].default == "echo_show"
    assert sig.parameters["override_attempt"].default is False


def test_frozen_level_names():
    assert (FULL, ABSTRACT, EXISTENCE, SILENT) == ("FULL", "ABSTRACT", "EXISTENCE", "SILENT")


def test_frozen_decision_fields():
    d = decide(PRIYA, {PRIYA}, 0.9, item(HIGH), [])
    for f in ("level", "reasons", "latency_ms", "untrusted_seen", "rule_hit"):
        assert hasattr(d, f), f"missing Decision field {f}"
    assert set(Decision.__slots__) == {"level", "reasons", "latency_ms",
                                       "untrusted_seen", "rule_hit"}
    dto = d.to_dict()
    assert dto["level"] == FULL and dto["rule_hit"] is None
    assert isinstance(dto["latency_ms"], float)


def test_latency_well_under_alexa_budget():
    """Measured p99 in sim: 0.006ms against a 500ms budget."""
    lat = [decide(PRIYA, {PRIYA, MOM}, 0.9, item(HIGH), []).latency_ms
           for _ in range(1000)]
    assert statistics.median(lat) < 1.0


def test_naive_decide_always_full():
    for sens in (PUBLIC, LOW, MEDIUM, HIGH):
        d = naive_decide(item(sens))
        assert d.level == FULL
