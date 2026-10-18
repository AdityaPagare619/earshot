"""
undo_last: reverse the last disclosure-affecting action.

The ledger is append-only — undo never rewrites history. It appends an `undo`
entry recording what was reversed:

- phone card still pending  -> card retracted from the second-channel queue.
- voice announcement already spoken -> cannot be un-said; the undo entry logs
  the correction honestly ("spoken disclosure cannot be retracted").
"""
from .ledger import _default_ledger
from .gating import _default_queue_fn


def undo_last(ledger=None, queue=None):
    """MCP tool: undo_last(). Returns {reversed, action, note, ledger_seq}."""
    ledger = ledger or _default_ledger()
    queue = queue or _default_queue_fn()

    target = ledger.last_disclosure_action()
    if target is None:
        return {"reversed": False, "action": None,
                "note": "Nothing disclosure-affecting to undo.", "ledger_seq": None}

    channel = target["channel"]
    item_id = target["item_id"]

    if channel == "phone":
        card_id = f"card-{item_id}"
        card = queue.retract(card_id)
        action = (f"retracted phone card {card_id}"
                  if card else f"phone card {card_id} already delivered — marked withdrawn")
        entry = ledger.append(
            tool="undo_last", item_id=item_id, level=target["level"],
            channel="phone", rule_hit=target["rule_hit"],
            audience=target["audience"], confidence=target["confidence"],
            speaker=target["speaker"],
            action=f"undo of seq {target['seq']}: {action}",
            extra={"undone_seq": target["seq"]},
        )
        return {"reversed": True, "action": action, "note": None,
                "ledger_seq": entry["seq"]}
    else:
        action = f"voice announcement for '{item_id}' was already spoken"
        note = ("Spoken words cannot be retracted. This undo is recorded as a "
                "correction in the ledger; future re-disclosure of this item is "
                "blocked under the current rules.")
        entry = ledger.append(
            tool="undo_last", item_id=item_id, level=target["level"],
            channel="voice", rule_hit=target["rule_hit"],
            audience=target["audience"], confidence=target["confidence"],
            speaker=target["speaker"],
            action=f"undo of seq {target['seq']}: {action} (correction logged)",
            extra={"undone_seq": target["seq"]},
        )
        return {"reversed": False, "action": action, "note": note,
                "ledger_seq": entry["seq"]}
