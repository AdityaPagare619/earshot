"""Founder drill cases — 18 Oct directive, 1.5-day wave.

The rule language must genuinely express these five cases with RULES ALONE.
No engine code changes. Each test = one drill case, end to end through the
real policy engine (earshot.policy.engine) and the real notify-ledger tools.

A test that fails = a design failure (needs code, not rules) -> REPORT, don't patch.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from earshot.policy import engine
from earshot.policy.engine import (
    decide, FULL, ABSTRACT, EXISTENCE, SILENT, HIGH, MEDIUM, LOW,
)
from earshot.notify_ledger import (
    gate_notification, rescope_context, undo_last,
    new_ledger, new_context_store, new_second_channel_queue,
)

# The engine's topic vocabulary (worldsim parity). "Any topic" in the rule
# language is expressed by enumerating the vocabulary — there is no wildcard.
ALL_TOPICS = {
    "schedule", "health", "work", "money", "family",
    "relationship", "errand", "legal", "home", "security",
}
_RANK = {SILENT: 0, EXISTENCE: 1, ABSTRACT: 2, FULL: 3}


def at_or_below(level, cap):
    return _RANK[level] <= _RANK[cap]


def test_a_kid_safe_mode():
    """(a) Kid-safe: any topic capped at ABSTRACT when a child is in the audience."""
    kid = "aarav_kid"
    rules = [{
        "kind": "deny", "name": "kid-safe-mode",
        "topics": set(ALL_TOPICS),          # "any topic", enumerated
        "in_front_of": {kid}, "cap": ABSTRACT,
    }]
    item = {"id": "t1", "sensitivity": MEDIUM, "topics": {"money"},
            "label": "rent discussion"}
    d = decide(speaker="me", audience_perceived={"me", kid},
               presence_confidence=1.0, item=item, rules=rules)
    assert at_or_below(d.level, ABSTRACT), f"kid present: got {d.level}"
    assert d.rule_hit == "kid-safe-mode", f"rule_hit={d.rule_hit}"

    d2 = decide(speaker="me", audience_perceived={"me"},
                presence_confidence=1.0, item=item, rules=rules)
    assert d2.level == FULL, f"kid absent: got {d2.level}"

    # HIGH items stay at-or-below ABSTRACT too (sensitivity floor is stricter).
    hi = {"id": "t2", "sensitivity": HIGH, "topics": {"health"}, "label": "x"}
    d3 = decide(speaker="me", audience_perceived={"me", kid},
                presence_confidence=1.0, item=hi, rules=rules)
    assert at_or_below(d3.level, ABSTRACT), f"HIGH + kid: got {d3.level}"
    print("PASS (a) kid-safe mode")


def test_b_wfh_confidentiality():
    """(b) WFH: deny work topics in front of anyone outside the household."""
    rules = [
        {"kind": "allow", "name": "household-work",
         "topics": {"work"}, "persons": {"me", "spouse"}},
        {"kind": "deny", "name": "wfh-confidential",
         "topics": {"work"}, "in_front_of": "any_untrusted", "cap": SILENT},
    ]
    item = {"id": "t3", "sensitivity": HIGH, "topics": {"work"},
            "label": "layoff planning"}
    # Spouse only: household -> FULL.
    d = decide(speaker="me", audience_perceived={"me", "spouse"},
               presence_confidence=1.0, item=item, rules=rules)
    assert d.level == FULL, f"household only: got {d.level}"
    # Colleague walks in: outside household -> SILENT.
    d2 = decide(speaker="me", audience_perceived={"me", "spouse", "colleague"},
                presence_confidence=1.0, item=item, rules=rules)
    assert d2.level == SILENT, f"colleague present: got {d2.level}"
    assert d2.rule_hit == "wfh-confidential"
    print("PASS (b) work-from-home confidentiality")


def test_c_roommate_therapy():
    """(c) Roommate + therapy: deny health in front of a named person, cap SILENT."""
    rules = [{
        "kind": "deny", "name": "therapy-private",
        "topics": {"health"}, "in_front_of": {"rohan_roommate"}, "cap": SILENT,
    }]
    item = {"id": "t4", "sensitivity": HIGH, "topics": {"health"},
            "label": "therapy appointment"}
    d = decide(speaker="me", audience_perceived={"me", "rohan_roommate"},
               presence_confidence=1.0, item=item, rules=rules)
    assert d.level == SILENT, f"roommate present: got {d.level}"
    assert d.rule_hit == "therapy-private"
    d2 = decide(speaker="me", audience_perceived={"me"},
                presence_confidence=1.0, item=item, rules=rules)
    assert d2.level == FULL, f"alone: got {d2.level}"
    print("PASS (c) roommate + therapy")


def test_d_announce_to_me_only():
    """(d) Announce-to-me-only: gate_notification goes phone-only
    whenever the audience isn't just self."""
    rules = [{
        "kind": "deny", "name": "me-only",
        "topics": set(ALL_TOPICS), "in_front_of": "any_untrusted",
        "cap": EXISTENCE,
    }]
    notif = {"id": "n1", "label": "Dinner plans Friday", "kind": "reminder",
             "sensitivity": LOW, "topics": {"schedule"},
             "announce_text": "Dinner with Priya Friday 8pm"}
    ledger, queue = new_ledger(), new_second_channel_queue()

    # Guest present -> phone-only, even for a LOW item.
    r = gate_notification(notif, audience={"me", "guest"}, confidence=1.0,
                          speaker="me", rules=rules,
                          policy=engine, ledger=ledger, queue=queue)
    assert r["channel"] == "phone", f"guest present: channel={r['channel']}"
    assert r["level"] == EXISTENCE, f"guest present: level={r['level']}"

    # Just self -> voice.
    r2 = gate_notification(notif, audience={"me"}, confidence=1.0,
                           speaker="me", rules=rules,
                           policy=engine, ledger=ledger, queue=queue)
    assert r2["channel"] == "voice", f"alone: channel={r2['channel']}"
    print("PASS (d) announce-to-me-only")


def test_e_forget_what_you_heard():
    """(e) 'Forget what you heard': undo_last + rescope_context clears it.

    Strong reading (the honest one): after forgetting, the item must be GONE —
    no phone card remains AND it must not resurface via re-disclosure when the
    room becomes safe. A forgotten item that re-discloses is worse than no
    forget at all.
    """
    rules = [{
        "kind": "deny", "name": "health-private",
        "topics": {"health"}, "in_front_of": "any_untrusted", "cap": EXISTENCE,
    }]
    ledger, queue, ctx = new_ledger(), new_second_channel_queue(), new_context_store()
    item = {"id": "n2", "sensitivity": HIGH, "topics": {"health"},
            "label": "lab results"}

    # Disclose to phone while a guest is present; record the context turn
    # the way decide_disclosure does.
    notif = dict(item, kind="alert", announce_text="lab results are in")
    g = gate_notification(notif, audience={"me", "guest"}, confidence=1.0,
                          speaker="me", rules=rules,
                          policy=engine, ledger=ledger, queue=queue)
    assert g["channel"] == "phone"
    d = decide(speaker="me", audience_perceived={"me", "guest"},
               presence_confidence=1.0, item=item, rules=rules)
    ctx.add_turn(item, audience={"me", "guest"}, confidence=1.0,
                 speaker="me", decision=d)

    # "Forget what you heard."
    u = undo_last(ledger=ledger, queue=queue)
    assert u["reversed"] is True, f"undo: {u}"
    assert queue.retract("card-n2") is None, "phone card must stay retracted"

    # Room becomes safe. The forgotten item must NOT resurface.
    r = rescope_context(new_audience={"me"}, confidence=1.0, speaker="me",
                        ctx=ctx, rules=rules, policy=engine, ledger=ledger)
    assert "n2" not in r["redisclosures_queued"], (
        "DESIGN FAILURE: forgotten item re-disclosed on rescope — "
        f"redisclosures_queued={r['redisclosures_queued']}"
    )
    print("PASS (e) forget-what-you-heard")


if __name__ == "__main__":
    test_a_kid_safe_mode()
    test_b_wfh_confidentiality()
    test_c_roommate_therapy()
    test_d_announce_to_me_only()
    try:
        test_e_forget_what_you_heard()
    except AssertionError as ex:
        print(f"FAIL (e) {ex}")
        sys.exit(1)
