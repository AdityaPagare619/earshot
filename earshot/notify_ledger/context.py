"""
rescope_context: audience-scoped memory on room change + re-disclosure.

ContextStore holds conversation turns annotated with the audience present when
each turn happened. On a room change, every withheld turn is re-decided against
the new audience. Items that newly qualify for voice disclosure go onto the
re-disclosure queue (voice re-prompt — the "safe again" moment). Nothing is
ever re-disclosed without a fresh decision; voice never widens on stale context.
"""
import copy

from .ledger import _default_ledger
from .policy_iface import MockPolicy, FULL


class ContextStore:
    def __init__(self):
        self._turns = []

    def add_turn(self, item, audience, confidence, speaker, decision):
        """Record a decided turn with its audience annotation."""
        self._turns.append({
            "item_id": item["id"],
            "item": copy.deepcopy(item),
            "audience": sorted(audience),
            "confidence": confidence,
            "speaker": speaker,
            "level": decision.level,
            "rule_hit": decision.rule_hit,
        })

    def turns(self):
        return copy.deepcopy(self._turns)


def rescope_context(new_audience, confidence, speaker, ctx, rules,
                    policy=None, ledger=None):
    """MCP tool: rescope_context() — re-scope history on room change.

    Returns {rescoped: [per-turn re-decisions], redisclosures_queued: [item_ids
    newly voice-safe]}. Every re-decision is ledgered.
    """
    policy = policy or MockPolicy()
    ledger = ledger or _default_ledger()

    rescoped = []
    redisclosures_queued = []

    for turn in ctx.turns():
        decision = policy.decide(
            speaker=speaker,
            audience_perceived=set(new_audience),
            presence_confidence=confidence,
            item={"sensitivity": turn["item"]["sensitivity"],
                  "topics": set(turn["item"]["topics"]),
                  "label": turn["item"]["label"]},
            rules=rules,
        )
        old_level, new_level = turn["level"], decision.level
        entry = ledger.append(
            tool="rescope_context", item_id=turn["item_id"], level=new_level,
            channel=None, rule_hit=decision.rule_hit,
            audience=set(new_audience), confidence=confidence, speaker=speaker,
            action=(f"re-decided after room change {turn['audience']} -> "
                    f"{sorted(new_audience)}: {old_level} -> {new_level}"),
            extra={"reasons": decision.reasons},
        )
        rescoped.append({
            "item_id": turn["item_id"],
            "audience_before": turn["audience"],
            "audience_after": sorted(new_audience),
            "level_before": old_level,
            "level_after": new_level,
            "rule_hit": decision.rule_hit,
            "ledger_seq": entry["seq"],
        })
        # Re-disclosure: previously phone-only/abstracted, now voice-safe.
        if old_level != FULL and new_level == FULL:
            redisclosures_queued.append(turn["item_id"])

    return {"rescoped": rescoped, "redisclosures_queued": redisclosures_queued}
