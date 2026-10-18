"""
explain_withholding: "Alexa, why didn't you tell me about the appointment?"

Deterministic lookup against the ledger — no LLM generation. Answers by citing
the WINNING RULE BY NAME (rule_hit from the decision) plus the audience change
that triggered the withholding (P1 requirement).
"""
from datetime import datetime

from .ledger import _default_ledger


def _fmt_audience(aud):
    aud = [p for p in (aud or []) if p != "__unknown__"]
    return ", ".join(aud) if aud else "an uncertain room"


def explain_withholding(item_id, ledger=None):
    """MCP tool: explain_withholding(item_id).

    Returns {rule_hit, audience_before, audience_after, sentence}. The sentence
    is the video's mic-drop line; it names the rule.
    """
    ledger = ledger or _default_ledger()
    entry = ledger.latest_for_item(item_id)
    if entry is None:
        return {"rule_hit": None, "audience_before": None, "audience_after": None,
                "sentence": "I have no record of that item."}

    rule_hit = entry.get("rule_hit")
    audience_after = entry.get("audience")
    confidence = entry.get("confidence")
    ts = entry.get("ts")

    # Find the audience before the change: the most recent prior entry for any
    # item with a different audience (the room-change moment).
    audience_before = None
    for e in reversed([e for e in ledger.entries_since() if e["seq"] < entry["seq"]]):
        if e.get("audience") and e["audience"] != audience_after:
            audience_before = e["audience"]
            break

    if rule_hit:
        sentence = (
            f"At {ts}, {_fmt_audience(audience_after)} "
            f"{'was' if audience_after and len(audience_after) == 1 else 'were'} in the room, "
            f"so the detail was withheld under your rule — '{rule_hit}'."
        )
    elif confidence is not None and confidence < 0.6:
        sentence = (
            f"At {ts}, I wasn't sure who was listening, so I stayed silent — "
            f"that's the fail-closed rule. Check your phone for the detail."
        )
        rule_hit = "fail-closed (presence uncertain)"
    else:
        sentence = f"At {ts}, the room wasn't safe for that detail. It's on your phone."

    return {
        "rule_hit": rule_hit,
        "audience_before": audience_before,
        "audience_after": audience_after,
        "sentence": sentence,
        "ledger_seq": entry["seq"],
    }
