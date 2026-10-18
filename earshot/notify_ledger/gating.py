"""
gate_notification: the Instax scenario — announce vs phone-only for unprompted speech.

Channel mapping (deterministic, from the policy decision level):
  FULL     -> voice announcement, full text
  ABSTRACT -> voice announcement, abstracted text (no detail)
  EXISTENCE -> PHONE-ONLY card ("something arrived — details on your phone")
  SILENT    -> PHONE-ONLY minimal nudge (P0-2: never a dead end)

Phone-bound payloads queue in `second_channel_queue`, which the phone-channel
lane drains (real buzz happens there). Every gating decision is ledgered with
the audience snapshot and confidence that produced it.
"""
import copy

from .ledger import new_ledger, _default_ledger
from .policy_iface import MockPolicy, FULL, ABSTRACT, EXISTENCE, SILENT

PHONE_LEVELS = {EXISTENCE, SILENT}

# Templates for the phone card per level.
_PHONE_TEMPLATES = {
    EXISTENCE: "A private notification arrived — details on your phone.",
    SILENT: "Alexa has a private note for you — check your phone.",
}

_ABSTRACT_TEXT = {
    # Abstracted voice text keyed by a coarse notification kind.
    "package": "You have a package arriving.",
    "appointment": "You have an appointment coming up.",
    "message": "You have a new message.",
}


def _voice_text(notif, level):
    if level == FULL:
        return notif.get("announce_text") or notif["label"]
    kind = notif.get("kind", "package")
    return _ABSTRACT_TEXT.get(kind, "You have a new notification.")


class SecondChannelQueue:
    """In-memory outbox for phone-bound cards. Drained by the phone-channel lane."""

    def __init__(self):
        self._cards = []

    def enqueue(self, card):
        self._cards.append(copy.deepcopy(card))
        return card["card_id"]

    def retract(self, card_id):
        for i, c in enumerate(self._cards):
            if c["card_id"] == card_id:
                return self._cards.pop(i)
        return None

    def pending(self):
        return copy.deepcopy(self._cards)


_default_queue = None


def _default_queue_fn():
    global _default_queue
    if _default_queue is None:
        _default_queue = SecondChannelQueue()
    return _default_queue


def new_second_channel_queue():
    return SecondChannelQueue()


def gate_notification(notif, audience, confidence, speaker, rules,
                      policy=None, ledger=None, queue=None):
    """MCP tool: gate_notification(notif, audience).

    notif: {id, label, kind, sensitivity, topics, announce_text?}
    audience: iterable of persona ids believed present (incl. speaker).
    Returns {channel, level, text, decision, ledger_seq, card_id?}.
    """
    policy = policy or MockPolicy()
    ledger = ledger or _default_ledger()
    queue = queue or _default_queue_fn()

    decision = policy.decide(
        speaker=speaker,
        audience_perceived=set(audience),
        presence_confidence=confidence,
        item={"sensitivity": notif["sensitivity"], "topics": set(notif["topics"]),
              "label": notif["label"]},
        rules=rules,
    )

    level = decision.level
    result = {"level": level, "decision": decision.to_dict()}

    if level in PHONE_LEVELS:
        # Phone-only: the Instax branch. Voice stays silent.
        card = {
            "card_id": f"card-{notif['id']}",
            "item_id": notif["id"],
            "label": notif["label"],
            "detail": notif.get("announce_text") or notif["label"],
            "level": level,
            "rule_hit": decision.rule_hit,
        }
        queue.enqueue(card)
        entry = ledger.append(
            tool="gate_notification", item_id=notif["id"], level=level,
            channel="phone", rule_hit=decision.rule_hit,
            audience=set(audience), confidence=confidence, speaker=speaker,
            action=f"withheld from voice; phone card {card['card_id']} queued",
            extra={"reasons": decision.reasons,
                   "card_text": _PHONE_TEMPLATES[level]},
        )
        result.update({
            "channel": "phone",
            "text": _PHONE_TEMPLATES[level],
            "card_id": card["card_id"],
            "ledger_seq": entry["seq"],
        })
    else:
        voice_text = _voice_text(notif, level)
        entry = ledger.append(
            tool="gate_notification", item_id=notif["id"], level=level,
            channel="voice", rule_hit=decision.rule_hit,
            audience=set(audience), confidence=confidence, speaker=speaker,
            action=f"announced by voice: {voice_text!r}",
            extra={"reasons": decision.reasons},
        )
        result.update({"channel": "voice", "text": voice_text,
                       "ledger_seq": entry["seq"]})
    return result
