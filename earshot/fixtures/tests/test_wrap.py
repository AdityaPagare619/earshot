"""Loader test for the EARSHOT fixture upstreams.

Every fixture item must carry sensitivity + topics, and every accessor
response must include fixture:true. Beat-critical facts for the video are
pinned by id so an edit to a JSON file cannot silently drift the demo.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from fixtures import wrap  # noqa: E402


def test_all_accessors_label_fixture_true():
    for acc in (wrap.get_calendar, wrap.get_bank, wrap.get_messages, wrap.get_health):
        resp = acc()
        assert resp["fixture"] is True, f"{acc.__name__} envelope missing fixture:true"
    assert wrap.get_all()["fixture"] is True


def test_every_item_tagged():
    data = wrap.get_all()["data"]
    assert sum(len(v) for v in data.values()) == 20
    for domain, items in data.items():
        for item in items:
            assert item["fixture"] is True
            assert set(item["topics"]), f"{item['id']} has no topics"
            assert item["sensitivity"] in wrap.SENSITIVITIES, item["id"]
            assert item["domain"] == domain, item["id"]
            assert item["label"], item["id"]


def test_beat_anchors_pinned():
    # Walk-in: prenatal at 3:40pm with Dr. Shah; MIL staying over; OTP exists.
    cal = {i["id"]: i for i in wrap.get_calendar()["items"]}
    assert cal["cal-001"]["label"] == "Prenatal visit, Dr. Shah, 3:40pm"
    assert cal["cal-001"]["sensitivity"] == "HIGH"
    assert "health" in cal["cal-001"]["topics"]
    assert cal["cal-003"]["label"].startswith("Mother-in-law")
    msg = {i["id"]: i for i in wrap.get_messages()["items"]}
    assert msg["msg-006"]["label"] == "Delivery update: Instax Mini arriving today"
    assert msg["msg-006"].get("beat") == "instax"
    assert wrap.get_item("bank-001")["label"] == "Savings balance Rs. 4,82,300"
    assert wrap.get_item("health-001")["sensitivity"] == "HIGH"


def test_vocabulary_covers_worldsim():
    # The policy lane matches on worldsim's topic vocabulary; drift = silent
    # unknown->HIGH. Keep the constant pinned to the worldsim set.
    expected = {"schedule", "health", "work", "money", "family",
                "relationship", "errand", "legal", "home", "security"}
    assert wrap.TOPIC_VOCABULARY == expected


def test_lookup_and_beats():
    assert wrap.get_item("cal-001")["label"].startswith("Prenatal")
    assert {i["id"] for i in wrap.beat_items("lattice-grid")} >= {
        "cal-002", "cal-004", "cal-005", "bank-001", "bank-004", "msg-002"}
    try:
        wrap.get_item("nope-000")
    except KeyError:
        pass
    else:
        raise AssertionError("get_item must raise KeyError on unknown id")
