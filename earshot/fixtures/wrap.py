"""
Wrapped fixture upstreams for EARSHOT.

These are HONESTLY LABELED SIMULATIONS of upstream data sources
(calendar, bank, messages, health) for the Priya-household demo. Nothing here
is real user data; names, amounts, and OTPs are invented. Every accessor
returns an envelope carrying ``fixture: true``, and every item carries it too,
so no consumer can mistake a fixture for live data.
"""
from __future__ import annotations

import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parent

SENSITIVITIES = {"PUBLIC", "LOW", "MEDIUM", "HIGH"}

# Topic vocabulary mirrors worldsim/world.py REQUEST_BANK topics (2026-10-18).
# P0-3 (unknown topics default HIGH) is enforced by failing loudly on load.
TOPIC_VOCABULARY = {
    "schedule", "health", "work", "money", "family",
    "relationship", "errand", "legal", "home", "security",
}

REQUIRED_KEYS = {"id", "label", "domain", "sensitivity", "topics", "fixture"}

SCHEMA = "earshot-fixture/1"


def _validate_item(item: dict, domain: str) -> None:
    missing = REQUIRED_KEYS - item.keys()
    if missing:
        raise ValueError(f"item {item.get('id')!r} missing keys: {sorted(missing)}")
    if item["sensitivity"] not in SENSITIVITIES:
        raise ValueError(
            f"item {item['id']!r} bad sensitivity {item['sensitivity']!r}")
    if item["fixture"] is not True:
        raise ValueError(
            f"item {item['id']!r} must carry fixture:true (honest-sim boundary)")
    unknown = set(item["topics"]) - TOPIC_VOCABULARY
    if unknown:
        # Fail loudly rather than letting policy.py treat them as unknown->HIGH
        # silently, which would hide a vocabulary drift from the video beats.
        raise ValueError(
            f"item {item['id']!r} topics outside vocabulary: {sorted(unknown)}")
    if item["domain"] != domain:
        raise ValueError(
            f"item {item['id']!r} domain {item['domain']!r} != file {domain!r}")


def _load(domain: str) -> dict:
    """Load and validate a fixture domain. Every response carries fixture:true."""
    doc = json.loads((FIXTURES_DIR / f"{domain}.json").read_text(encoding="utf-8"))
    if doc.get("schema") != SCHEMA:
        raise ValueError(f"{domain}.json schema {doc.get('schema')!r} != {SCHEMA!r}")
    items = doc["items"]
    for item in items:
        _validate_item(item, domain)
    ids = [i["id"] for i in items]
    if len(set(ids)) != len(ids):
        raise ValueError(f"{domain}.json has duplicate item ids")
    return {"fixture": True, "domain": domain, "items": items}


def get_calendar() -> dict:
    return _load("calendar")


def get_bank() -> dict:
    return _load("bank")


def get_messages() -> dict:
    return _load("messages")


def get_health() -> dict:
    return _load("health")


def get_all() -> dict:
    """All fixture domains in one envelope (fixture:true included)."""
    return {
        "fixture": True,
        "domains": ["calendar", "bank", "messages", "health"],
        "data": {
            "calendar": get_calendar()["items"],
            "bank": get_bank()["items"],
            "messages": get_messages()["items"],
            "health": get_health()["items"],
        },
    }


def get_item(item_id: str) -> dict:
    """Single item by id, fixture:true labeled. Raises KeyError if missing."""
    for domain in ("calendar", "bank", "messages", "health"):
        for item in _load(domain)["items"]:
            if item["id"] == item_id:
                return item
    raise KeyError(f"no fixture item {item_id!r}")


def beat_items(beat: str) -> list[dict]:
    """All fixture items tagged for a given video beat (metadata only —
    the disclosure lattice must never key on ``beat``)."""
    return [i for d in get_all()["data"].values() for i in d if i.get("beat") == beat]
