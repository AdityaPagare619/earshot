#!/usr/bin/env python3
"""
Instax scenario, end to end (the video's 1:05–1:20 beat + 1:30–1:50 beat).

Setup: Priya is alone. A package notification arrives -> announced (FULL).
Then the kid walks in (room change). The same package notification arrives
again -> phone buzz instead of announcement (EXISTENCE, deny rule wins).
Then: ledger integrity, explain-your-silence citing the rule by name,
room change back to alone -> re-disclosure queued, undo_last retracts.

Run: python3 -m earshot.notify_ledger.test_instax
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from earshot.notify_ledger import (
    gate_notification, rescope_context, get_ledger, explain_withholding,
    undo_last, new_ledger, new_context_store, new_second_channel_queue,
)
from earshot.notify_ledger.policy_iface import MockPolicy, FULL, EXISTENCE
from earshot.notify_ledger.context import ContextStore

SPEAKER = "priya"

RULES = [
    {"kind": "deny", "name": "never spoil surprises in front of the kids",
     "topics": ["gift", "package"], "cap": "EXISTENCE",
     "in_front_of": ["kid"]},
    {"kind": "deny", "name": "never mention the clinic in front of Mom",
     "topics": ["appointment", "health"], "cap": "EXISTENCE",
     "in_front_of": ["mom"]},
]

INSTAX = {
    "id": "notif-instax-1",
    "label": "Parcel arriving — Instax Mini camera",
    "kind": "package",
    "sensitivity": "HIGH",
    "topics": ["gift", "package"],
    "announce_text": "Parcel arriving — Instax Mini camera.",
}

CLINIC = {
    "id": "appt-clinic-1",
    "label": "Prenatal visit, 3:42pm",
    "kind": "appointment",
    "sensitivity": "HIGH",
    "topics": ["appointment", "health"],
    "announce_text": "Your prenatal visit is at 3:42pm.",
}


def main():
    policy = MockPolicy()
    ledger = new_ledger()
    queue = new_second_channel_queue()
    ctx = ContextStore()

    print("== 1. Priya alone, package arrives -> voice announcement ==")
    r1 = gate_notification(INSTAX, audience={"priya"}, confidence=0.95,
                           speaker=SPEAKER, rules=RULES,
                           policy=policy, ledger=ledger, queue=queue)
    print(f"   channel={r1['channel']} level={r1['level']} text={r1['text']!r}")
    assert r1["channel"] == "voice" and r1["level"] == FULL
    ctx.add_turn(INSTAX, {"priya"}, 0.95, SPEAKER, policy.decide(
        SPEAKER, {"priya"}, 0.95,
        {"sensitivity": INSTAX["sensitivity"], "topics": set(INSTAX["topics"]),
         "label": INSTAX["label"]}, RULES))

    print("== 2. Kid walks in; package notification arrives -> PHONE BUZZ ==")
    r2 = gate_notification(INSTAX, audience={"priya", "kid"}, confidence=0.92,
                           speaker=SPEAKER, rules=RULES,
                           policy=policy, ledger=ledger, queue=queue)
    print(f"   channel={r2['channel']} level={r2['level']} text={r2['text']!r}")
    print(f"   winning rule: {r2['decision']['rule_hit']!r}")
    assert r2["channel"] == "phone" and r2["level"] == EXISTENCE
    assert r2["decision"]["rule_hit"] == "never spoil surprises in front of the kids"
    pending = queue.pending()
    assert len(pending) == 1 and pending[0]["card_id"] == "card-notif-instax-1"
    print(f"   phone queue: {pending[0]['label']!r} (this is the buzz)")
    ctx.add_turn(INSTAX, {"priya", "kid"}, 0.92, SPEAKER, policy.decide(
        SPEAKER, {"priya", "kid"}, 0.92,
        {"sensitivity": INSTAX["sensitivity"], "topics": set(INSTAX["topics"]),
         "label": INSTAX["label"]}, RULES))

    print("== 3. Ledger is hash-chained and verifies ==")
    snap = get_ledger(ledger=ledger)
    print(f"   entries={len(snap['entries'])} valid={snap['valid']} "
          f"head={snap['head']['hash'][:12]}...")
    assert snap["valid"] and len(snap["entries"]) == 2

    print("== 4. 'Why didn't you tell me?' -> cites the rule by name ==")
    exp = explain_withholding("notif-instax-1", ledger=ledger)
    print(f"   {exp['sentence']}")
    assert exp["rule_hit"] == "never spoil surprises in front of the kids"
    assert exp["audience_after"] == ["kid", "priya"]

    print("== 5. Kid leaves; room safe again -> re-disclosure queued ==")
    rs = rescope_context({"priya"}, 0.95, SPEAKER, ctx, RULES,
                         policy=policy, ledger=ledger)
    print(f"   rescoped={len(rs['rescoped'])} redisclosures={rs['redisclosures_queued']}")
    assert rs["redisclosures_queued"] == ["notif-instax-1"]

    print("== 6. undo_last retracts the phone card ==")
    # Most recent disclosure action is rescope (no channel); last gated one is r2.
    # Add one more phone-bound notification, then undo it.
    r3 = gate_notification(CLINIC, audience={"priya", "mom"}, confidence=0.9,
                           speaker=SPEAKER, rules=RULES,
                           policy=policy, ledger=ledger, queue=queue)
    assert r3["channel"] == "phone"
    assert r3["decision"]["rule_hit"] == "never mention the clinic in front of Mom"
    u = undo_last(ledger=ledger, queue=queue)
    print(f"   reversed={u['reversed']} action={u['action']!r}")
    assert u["reversed"] is True
    assert queue.retract("card-appt-clinic-1") is None  # already retracted

    print("== 7. Full chain still verifies after undo (append-only) ==")
    snap2 = get_ledger(ledger=ledger)
    assert snap2["valid"]
    tools = [e["tool"] for e in snap2["entries"]]
    print(f"   tools in chain: {tools}")
    assert "undo_last" in tools

    print("== 8. Explain silence for the clinic appointment (P1) ==")
    exp2 = explain_withholding("appt-clinic-1", ledger=ledger)
    print(f"   {exp2['sentence']}")
    assert exp2["rule_hit"] == "never mention the clinic in front of Mom"

    print("\nINSTAX SCENARIO GREEN: voice->phone->explain->rescope->undo all work.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
