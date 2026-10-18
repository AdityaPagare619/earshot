"""Rule configuration for the EARSHOT MCP server.

Structured fields (kind/topics/persons/in_front_of/cap) are the REAL contract.
`rule_nl` is stored verbatim (language-blind: the lattice never keys on tongue)
and parsed best-effort with deterministic regexes for the canonical deny
patterns in English and Hinglish. A rule that cannot be parsed is flagged
parsed:false and NEVER enforces — silent non-enforcement is worse than no rule.

Rule dict shape (worldsim/policy contract):
    deny:  {kind:"deny", name, topics:[...], in_front_of:[...], cap}
    allow: {kind:"allow", name, topics:[...], persons:[...]}
"""
from __future__ import annotations

import re

VALID_KINDS = ("deny", "allow")
VALID_CAPS = ("FULL", "ABSTRACT", "EXISTENCE", "SILENT")

_EN_DENY = re.compile(
    r"never\s+(?:mention|talk\s+about|tell(?:\s+anyone)?(?:\s+about)?|"
    r"speak\s+of|bring\s+up)\s+(.+?)\s+in\s+front\s+of\s+(.+)",
    re.IGNORECASE,
)
# "mom ke saamne clinic ke baare mein mat batao" -> (mom, clinic ke baare mein)
_HI_DENY_1 = re.compile(
    r"(.+?)\s+ke\s+saamne\s+(.+?)\s+mat\s+(?:batao|bolo|batana|bolna|kaho)",
    re.IGNORECASE,
)
# "clinic mat batao mom ke saamne" -> (clinic, mom)
_HI_DENY_2 = re.compile(
    r"(.+?)\s+mat\s+(?:batao|bolo|batana|bolna|kaho)\s+(.+?)\s+ke\s+saamne",
    re.IGNORECASE,
)


def _split_names(text):
    parts = re.split(r"\s+and\s+|,|;|\s+aur\s+", text.strip(), flags=re.IGNORECASE)
    return [p.strip().lower() for p in parts if p.strip()]


def _clean_topic(text):
    t = text.strip().lower()
    t = re.sub(r"\s+ke\s+baare\s+mein\s*$", "", t)  # "clinic ke baare mein" -> "clinic"
    t = re.sub(r"^the\s+", "", t)
    return t.strip()


def parse_deny_nl(rule_nl):
    """Best-effort parse of a deny rule in EN/Hinglish. Returns
    (topics, in_front_of) or None."""
    m = _EN_DENY.search(rule_nl or "")
    if m:
        return [_clean_topic(m.group(1))], _split_names(m.group(2))
    m = _HI_DENY_1.search(rule_nl or "")
    if m:
        return [_clean_topic(m.group(2))], _split_names(m.group(1))
    m = _HI_DENY_2.search(rule_nl or "")
    if m:
        return [_clean_topic(m.group(1))], _split_names(m.group(2))
    return None


def build_rule(rule_id, rule_nl, lang, kind, name, topics, persons,
               in_front_of, cap):
    """Returns (rule_dict_or_None, unparsed_record_or_None)."""
    kind = (kind or "deny").lower()
    if kind not in VALID_KINDS:
        raise ValueError(f"kind must be one of {VALID_KINDS}")
    cap = (cap or "SILENT").upper()
    if kind == "deny" and cap not in VALID_CAPS:
        raise ValueError(f"cap must be one of {VALID_CAPS}")

    rule_name = name or (rule_nl or rule_id)[:60]

    if kind == "allow":
        if not topics or not persons:
            return None, {"id": rule_id, "rule_nl": rule_nl, "lang": lang,
                          "kind": kind, "parsed": False,
                          "hint": "allow rules need explicit topics=[...] and persons=[...]"}
        return {"id": rule_id, "kind": "allow", "name": rule_name,
                "topics": list(topics), "persons": list(persons),
                "rule_nl": rule_nl, "lang": lang, "parsed": True}, None

    # deny
    if not topics or not in_front_of:
        parsed = parse_deny_nl(rule_nl)
        if parsed is None:
            return None, {"id": rule_id, "rule_nl": rule_nl, "lang": lang,
                          "kind": kind, "parsed": False,
                          "hint": ("could not parse deny pattern; pass explicit "
                                   "topics=[...] and in_front_of=[...], e.g. "
                                   "topics=['clinic'], in_front_of=['mom']")}
        ptopics, pin_front = parsed
        topics = topics or ptopics
        in_front_of = in_front_of or pin_front
    return {"id": rule_id, "kind": "deny", "name": rule_name,
            "topics": list(topics), "in_front_of": list(in_front_of),
            "cap": cap, "rule_nl": rule_nl, "lang": lang,
            "parsed": True}, None
