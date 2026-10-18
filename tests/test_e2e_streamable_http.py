"""End-to-end verification of the EARSHOT MCP server over Streamable HTTP.

Starts nothing itself — expects the server running at URL (arg 1).
Covers: tool listing (all 14 names), every tool callable with sane results,
ui://earshot/inspector resource, elicitation-fallback approval flow,
both-channel context turns + rescope re-disclosure, ledger hash-chain validity,
undo, SILENT nudge (P0-2), fail-closed (P0-1/0.6), deny-rule cap.
"""
import asyncio
import json
import os
import sys

# Friction: httpx2 (the SDK's httpx fork) crashes parsing bracketed IPv6
# entries like [::1] in NO_PROXY (InvalidURL: Invalid port: ':1]') at client
# creation. Sanitize before any mcp import touches env.
for _k in ("no_proxy", "NO_PROXY"):
    _v = os.environ.get(_k, "")
    os.environ[_k] = ",".join(
        p for p in _v.split(",") if p and not p.startswith("["))
os.environ.pop("ALL_PROXY", None)
os.environ.pop("all_proxy", None)

from mcp.client.streamable_http import streamable_http_client
from mcp.client.client import Client

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000/mcp"

EXPECTED_TOOLS = [
    "decide_disclosure", "set_rule", "list_rules", "delete_rule",
    "declare_speaker", "get_audience", "explain_withholding", "get_ledger",
    "send_to_second_channel", "request_approval", "approve",
    "rescope_context", "undo_last", "gate_notification",
]

passed, failed = [], []


def check(name, cond, detail=""):
    (passed if cond else failed).append(name)
    print(("PASS " if cond else "FAIL ") + name + (f" — {detail}" if detail and not cond else ""))


async def call(client, name, args):
    res = await client.call_tool(name, args)
    out = res.content[0].text if res.content else ""
    try:
        return json.loads(out)
    except Exception:
        return {"_raw": out}


async def main():
    async with Client(streamable_http_client(URL)) as client:

        tools = await client.list_tools()
        names = [t.name for t in tools.tools]
        check("tools_listed", all(n in names for n in EXPECTED_TOOLS),
              f"got {sorted(names)}")
        check("tool_count>=14", len(names) >= 14, str(len(names)))

        # resource
        rres = await client.read_resource("ui://earshot/inspector")
        rdata = json.loads(rres.contents[0].text)
        check("inspector_resource", rdata["server"] == "earshot"
              and rdata["spec"] == "2025-11-25", str(rdata)[:120])

        # speaker + rules
        r = await call(client, "declare_speaker", {"name": "priya", "confirmed": True})
        check("declare_speaker", r.get("speaker") == "priya", str(r))
        r = await call(client, "set_rule", {
            "rule_nl": "mom ke saamne clinic ke baare mein mat batao",
            "lang": "hi", "kind": "deny",
            "topics": ["clinic"], "in_front_of": ["mom"], "cap": "EXISTENCE"})
        check("set_rule_hinglish", r.get("status") == "enforced", str(r))
        r = await call(client, "set_rule", {
            "rule_nl": "never mention the clinic in front of mom"})
        check("set_rule_nl_parse", r.get("parsed") is True, str(r)[:200])
        r = await call(client, "set_rule", {"rule_nl": "xyzzy frobnicate"})
        check("set_rule_unparsed_never_enforces",
              r.get("status") == "needs_structure" and r.get("parsed") is False)
        r = await call(client, "list_rules", {})
        check("list_rules", len(r["rules"]) == 2, str(len(r["rules"])))

        # voice disclosure with MIL present -> EXISTENCE (HIGH sensitivity)
        item = {"id": "appt-1", "label": "Prenatal visit 3:42pm",
                "sensitivity": "HIGH", "topics": ["clinic"]}
        # Two overlapping deny rules: rule-001 caps clinic@mom at EXISTENCE,
        # rule-002 (NL-parsed, default cap SILENT) caps at SILENT.
        # Tightest cap wins -> SILENT (+ P0-2 nudge).
        r = await call(client, "decide_disclosure",
                       {"item": item, "audience": ["priya", "mom"], "confidence": 0.9})
        check("decide_with_mil_tightest_cap_SILENT", r.get("level") == "SILENT",
              str(r.get("level")))
        check("silent_decision_nudged", r.get("nudge", {}).get("card_id"),
              str(r)[:160])
        check("deny_rule_cited", r["decision"].get("rule_hit") is not None,
              str(r["decision"].get("rule_hit")))

        # alone -> FULL
        r = await call(client, "decide_disclosure",
                       {"item": item, "audience": ["priya"], "confidence": 0.95})
        check("decide_alone_FULL", r.get("level") == "FULL", str(r.get("level")))

        # fail-closed: low confidence -> untrusted
        r = await call(client, "decide_disclosure",
                       {"item": item, "audience": ["priya"], "confidence": 0.3})
        check("fail_closed_low_conf", r.get("level") == "EXISTENCE",
              str(r.get("level")))

        # override resisted, monotonic-downward
        r = await call(client, "decide_disclosure",
                       {"item": item, "audience": ["priya", "mom"],
                        "confidence": 0.9, "override_attempt": True})
        check("override_resisted", r.get("level") != "FULL"
              and any("override" in x for x in r["decision"]["reasons"]))

        # phone channel: gate_notification phone-only with MIL present
        notif = {"id": "pkg-1", "label": "Instax package",
                 "kind": "package", "sensitivity": "HIGH",
                 "topics": ["clinic"],
                 "announce_text": "Your Instax Mini from the clinic arrived"}
        r = await call(client, "gate_notification",
                       {"notif": notif, "audience": ["priya", "mom"], "confidence": 0.9})
        check("gate_phone_only", r.get("channel") == "phone", str(r.get("channel")))

        # direct phone send
        r = await call(client, "send_to_second_channel",
                       {"payload": {"item_id": "note-1", "label": "Lab results",
                                    "detail": "results are in", "sensitivity": "HIGH",
                                    "topics": ["clinic"]}})
        check("send_to_phone", r.get("card_id", "").startswith("card-"))

        # SILENT nudge (P0-2): deny cap SILENT on medium item -> phone nudge
        r = await call(client, "set_rule", {
            "rule_nl": "x", "kind": "deny", "name": "silent-rule",
            "topics": ["sealed"], "in_front_of": ["mom"], "cap": "SILENT"})
        r = await call(client, "decide_disclosure",
                       {"item": {"id": "s-1", "label": "Sealed doc",
                                 "sensitivity": "MEDIUM", "topics": ["sealed"]},
                        "audience": ["priya", "mom"], "confidence": 0.9})
        check("silent_nudge_paired", r.get("level") == "SILENT"
              and r.get("nudge", {}).get("card_id"), str(r)[:200])

        # audience / explain / ledger
        r = await call(client, "get_audience", {})
        check("get_audience", "mom" in r.get("audience", []), str(r.get("audience")))
        r = await call(client, "explain_withholding", {"item_id": "appt-1"})
        check("explain_cites_rule", r.get("rule_hit") is not None, str(r)[:200])
        r = await call(client, "get_ledger", {})
        check("ledger_valid", r.get("valid") is True and len(r["entries"]) > 5,
              f"{len(r.get('entries', []))} entries")

        # RESCOPE: mom leaves -> phone-sent pkg-1 becomes voice-safe
        r = await call(client, "rescope_context",
                       {"new_audience": ["priya"], "confidence": 0.95})
        queued = r.get("redisclosures_queued", [])
        check("rescope_sees_phone_turns", "pkg-1" in queued,
              f"queued={queued}")

        # approval flow via elicitation fallback (client has no elicitation)
        plan = {"item_id": "appt-1", "label": "Read appointment aloud",
                "detail": "Prenatal visit 3:42pm", "audience": ["priya"]}
        r = await call(client, "request_approval", {"plan": plan})
        check("approval_pending", r.get("status") == "pending"
              and r.get("token", "").startswith("appr-"), str(r)[:160])
        check("approval_card_queued", r.get("approval_card_id", "").startswith("card-"))
        token, phash = r["token"], r["plan_hash"]
        # the phone page sees the approval-request card via the inspector resource
        rres = await client.read_resource("ui://earshot/inspector")
        cards = json.loads(rres.contents[0].text)["second_channel_cards"]
        check("inspector_shows_approval_card",
              any(c.get("kind") == "approval_request" and c.get("token") == token
                  for c in cards), str(len(cards)))
        r = await call(client, "approve", {"token": token, "plan_hash": "tampered"})
        check("approve_hash_binding", r.get("approved") is False
              and "mismatch" in r.get("error", ""), str(r)[:160])
        r = await call(client, "approve", {"token": token, "plan_hash": phash})
        check("approve_ok", r.get("approved") is True
              and r.get("card_id", "").startswith("card-"), str(r)[:160])

        # undo: retracts the signed approval card
        r = await call(client, "undo_last", {})
        check("undo_retracts_phone_card",
              r.get("reversed") is True and "retracted" in r.get("action", ""),
              str(r)[:160])

        # delete rule
        r = await call(client, "delete_rule", {"id": "rule-001"})
        check("delete_rule", r.get("removed") is True)

    print(f"\n{len(passed)} passed, {len(failed)} failed")
    if failed:
        print("FAILED:", failed)
        sys.exit(1)


asyncio.run(main())
