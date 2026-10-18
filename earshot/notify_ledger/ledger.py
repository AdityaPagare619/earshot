"""
Hash-chained, tamper-evident decision log.

Each entry hashes the previous entry's hash; entries are frozen dicts at write.
get_ledger() re-verifies the chain on every read and reports `valid`.
"""
import copy
import hashlib
import json
import time
from datetime import datetime, timezone

GENESIS_HASH = "0" * 64


def _canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def _entry_hash(entry_body, prev_hash):
    return hashlib.sha256((_canonical(entry_body) + prev_hash).encode("utf-8")).hexdigest()


class Ledger:
    def __init__(self):
        self._entries = []

    def append(self, tool, item_id=None, level=None, channel=None, rule_hit=None,
               audience=None, confidence=None, speaker=None, action=None, extra=None):
        entry_body = {
            "seq": len(self._entries),
            "ts": datetime.now(timezone.utc).isoformat(),
            "tool": tool,
            "item_id": item_id,
            "level": level,
            "channel": channel,
            "rule_hit": rule_hit,
            "audience": sorted(audience) if audience is not None else None,
            "confidence": confidence,
            "speaker": speaker,
            "action": action,
            "extra": extra or {},
        }
        prev_hash = self._entries[-1]["hash"] if self._entries else GENESIS_HASH
        entry = dict(entry_body)
        entry["prev_hash"] = prev_hash
        entry["hash"] = _entry_hash(entry_body, prev_hash)
        self._entries.append(entry)
        return copy.deepcopy(entry)

    def verify(self):
        prev = GENESIS_HASH
        for e in self._entries:
            body = {k: v for k, v in e.items() if k not in ("hash", "prev_hash")}
            if e["prev_hash"] != prev:
                return False
            if e["hash"] != _entry_hash(body, prev):
                return False
            prev = e["hash"]
        return True

    def entries_since(self, since=None):
        if since is None:
            return [copy.deepcopy(e) for e in self._entries]
        if isinstance(since, int):
            return [copy.deepcopy(e) for e in self._entries if e["seq"] > since]
        return [copy.deepcopy(e) for e in self._entries if e["ts"] > since]

    def latest_for_item(self, item_id):
        for e in reversed(self._entries):
            if e["item_id"] == item_id:
                return copy.deepcopy(e)
        return None

    def last_disclosure_action(self):
        """Most recent entry that disclosed (or attempted to disclose) something."""
        for e in reversed(self._entries):
            if e["tool"] in ("gate_notification", "rescope_context") and e["channel"]:
                return copy.deepcopy(e)
        return None

    def head(self):
        if not self._entries:
            return {"seq": -1, "hash": GENESIS_HASH, "valid": True}
        return {"seq": self._entries[-1]["seq"], "hash": self._entries[-1]["hash"],
                "valid": self.verify()}


def get_ledger(since=None, ledger=None):
    """MCP tool: get_ledger(since) — returns entries after `since` (seq or ISO ts)
    plus chain validity and the head hash."""
    ledger = ledger or _default_ledger()
    entries = ledger.entries_since(since)
    return {"entries": entries, "valid": ledger.verify(), "head": ledger.head()}


_default = None


def _default_ledger():
    global _default
    if _default is None:
        _default = Ledger()
    return _default


def new_ledger():
    return Ledger()
