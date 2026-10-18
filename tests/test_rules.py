"""Unit tests for the deterministic NL rule parser (no server needed)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from earshot.server.rules import build_rule, parse_deny_nl


def test_en_deny_pattern():
    topics, persons = parse_deny_nl("never mention the clinic in front of mom")
    assert topics == ["clinic"]
    assert persons == ["mom"]


def test_hinglish_deny_pattern_1():
    topics, persons = parse_deny_nl("mom ke saamne clinic ke baare mein mat batao")
    assert topics == ["clinic"]
    assert persons == ["mom"]


def test_hinglish_deny_pattern_2():
    topics, persons = parse_deny_nl("clinic mat batao mom ke saamne")
    assert topics == ["clinic"]
    assert persons == ["mom"]


def test_unparseable_returns_none():
    assert parse_deny_nl("xyzzy frobnicate the thingamajig") is None


def test_structured_rule_enforces():
    rule, unparsed = build_rule("rule-001", "x", "en", "deny", "r1",
                                ["clinic"], None, ["mom"], "SILENT")
    assert unparsed is None
    assert rule["parsed"] is True
    assert rule["topics"] == ["clinic"] and rule["in_front_of"] == ["mom"]


def test_unparsed_rule_never_enforces():
    rule, unparsed = build_rule("rule-002", "xyzzy frobnicate", "en", "deny",
                                None, None, None, None, "SILENT")
    assert rule is None
    assert unparsed["parsed"] is False
    assert "hint" in unparsed


def test_allow_rule_needs_persons():
    rule, unparsed = build_rule("rule-003", "x", "en", "allow", "r3",
                                ["calendar"], None, None, "FULL")
    assert rule is None and unparsed["parsed"] is False


def test_bad_kind_rejected():
    try:
        build_rule("rule-004", "x", "en", "maybe", None, ["a"], None, ["b"], "SILENT")
    except ValueError:
        return
    raise AssertionError("expected ValueError")
