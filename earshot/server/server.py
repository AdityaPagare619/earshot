"""EARSHOT MCP server — Streamable HTTP, MCP spec 2025-11-25.

Implements the MASTER_PLAN §3 tool inventory against the real policy engine
(`earshot.policy.engine`, contract FROZEN by the policy-port lane) with the
merged `earshot.notify_ledger` tool implementations underneath.

Run (Streamable HTTP — the Inspector / browser-simulator route):
    cd ~/workspace/earshot-trees/mcp-server
    .venv/bin/python -m earshot.server.server --port 8000
Then point MCP Inspector at http://127.0.0.1:8000/mcp (Streamable HTTP).

Run (stdio — the elicitation-capable route):
    .venv/bin/python -m earshot.server.server --transport stdio
Note: on the 2026-07-28 Streamable HTTP route the SDK closes the back-channel
by design (NoBackChannelError), so request_approval degrades to the pending
token flow and the phone page becomes the elicitation surface; over stdio
(or a 2025-11-25-negotiated client) ctx.elicit works and the approval
completes inside the tool call.

No AI in the hot path. Every disclosure decision is a pure function of
(speaker, perceived audience, presence confidence, item, user rules, device).
Presence perception is SIMULATED (the simulator shell re-samples on wake word
and passes the fresh snapshot in); the server never pretends otherwise.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import uuid
from types import SimpleNamespace

from pydantic import BaseModel, Field

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.context import Context
from mcp.shared.exceptions import MCPError, NoBackChannelError

from earshot.policy import engine as policy_engine
from earshot.policy.engine import (
    FULL, ABSTRACT, EXISTENCE, SILENT, FAIL_CLOSED_CONFIDENCE,
)
from earshot.notify_ledger import (
    gate_notification as _nl_gate_notification,
    rescope_context as _nl_rescope_context,
    get_ledger as _nl_get_ledger,
    explain_withholding as _nl_explain_withholding,
    undo_last as _nl_undo_last,
    new_ledger,
    new_context_store,
    new_second_channel_queue,
)

from .rules import build_rule

SERVER_NAME = "earshot"
SIMULATED_NOTE = ("presence is simulated: the simulator shell re-samples on "
                  "wake word and passes the fresh snapshot in; no real "
                  "camera, no real Alexa device")


def _canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def _plan_hash(plan):
    return hashlib.sha256(_canonical(plan).encode("utf-8")).hexdigest()


def _norm_item(item):
    item = dict(item or {})
    label = str(item.get("label") or item.get("id") or "item")
    item.setdefault("label", label)
    item.setdefault(
        "id",
        re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-") or "item",
    )
    topics = item.get("topics", [])
    item["topics"] = [topics] if isinstance(topics, str) else list(topics)
    # Missing/invalid sensitivity -> engine defaults HIGH (P0-3, fail closed).
    return item


class ServerState:
    """Per-server mutable state. One instance per process."""

    def __init__(self):
        self.rules = []
        self.unparsed_rules = []
        self._rule_seq = 0
        self.speaker = "speaker"
        self.audience = {"speaker"}
        self.confidence = 1.0
        self.ledger = new_ledger()
        self.context = new_context_store()
        self.queue = new_second_channel_queue()
        self.approvals = {}

    def next_rule_id(self):
        self._rule_seq += 1
        return f"rule-{self._rule_seq:03d}"

    def note_room(self, audience, confidence):
        if audience is not None:
            self.audience = set(audience)
        if confidence is not None:
            self.confidence = float(confidence)


# ---------------------------------------------------------------------------
# Elicitation schemas (spec primitives only)
# ---------------------------------------------------------------------------

class ApprovalElicitation(BaseModel):
    approve: bool = Field(description="Approve this disclosure plan?")
    note: str = Field(default="", description="Optional note for the ledger")


class SpeakerConfirm(BaseModel):
    confirmed: bool = Field(description="Confirm this speaker identity?")
    name: str = Field(default="", description="Echo of the declared name")


# ---------------------------------------------------------------------------
# Server factory
# ---------------------------------------------------------------------------

def create_server(state=None):
    state = state or ServerState()
    mcp = MCPServer(
        name=SERVER_NAME,
        title="EARSHOT — room-aware disclosure gateway",
        description=(
            "Deterministic disclosure lattice for voice AI: FULL / ABSTRACT / "
            "EXISTENCE / SILENT. " + SIMULATED_NOTE
        ),
        instructions=(
            "Call decide_disclosure before voicing anything. Audience and "
            "confidence are perceived room state (simulated). Rules are "
            "language-blind; write them in any language."
        ),
    )

    def _decision_ns(decision_dict):
        return SimpleNamespace(
            level=decision_dict["level"],
            rule_hit=decision_dict.get("rule_hit"),
        )

    # -- 1. decide_disclosure ------------------------------------------------
    @mcp.tool(name="decide_disclosure",
              description="Decide the disclosure level for an item in the current "
                          "room. P0-1: goes through decide_after_resample — the "
                          "snapshot passed in is re-read at decision time.")
    async def decide_disclosure(item: dict, audience: list, confidence: float,
                                override_attempt: bool = False) -> dict:
        item = _norm_item(item)
        state.note_room(audience, confidence)
        decision = policy_engine.decide_after_resample(
            lambda: (set(audience), float(confidence)),
            speaker=state.speaker,
            item=item,
            rules=state.rules,
            override_attempt=override_attempt,
        )
        # Cross-lane contract: record the VOICE-channel decision turn.
        state.context.add_turn(item, set(audience), float(confidence),
                               state.speaker, decision)
        entry = state.ledger.append(
            tool="decide_disclosure", item_id=item["id"], level=decision.level,
            channel="voice", rule_hit=decision.rule_hit,
            audience=set(audience), confidence=float(confidence),
            speaker=state.speaker,
            action=(f"voice decision for '{item['label']}': {decision.level}"),
            extra={"reasons": decision.reasons},
        )
        result = {"item_id": item["id"], "level": decision.level,
                  "decision": decision.to_dict(), "ledger_seq": entry["seq"]}
        if decision.nudge_required:
            # P0-2: SILENT is never a dead end — pair with a phone nudge.
            card = {"card_id": f"card-{item['id']}-nudge",
                    "item_id": item["id"], "label": item["label"],
                    "detail": "A private detail was withheld from voice — "
                              "check your phone.",
                    "level": SILENT, "rule_hit": decision.rule_hit,
                    "nudge": True}
            state.queue.enqueue(card)
            nudge_entry = state.ledger.append(
                tool="decide_disclosure", item_id=item["id"], level=SILENT,
                channel="phone", rule_hit=decision.rule_hit,
                audience=set(audience), confidence=float(confidence),
                speaker=state.speaker,
                action=f"P0-2 nudge: phone card {card['card_id']} queued",
                extra={"reasons": decision.reasons, "card_id": card["card_id"]},
            )
            result["nudge"] = {"card_id": card["card_id"],
                               "ledger_seq": nudge_entry["seq"]}
        return result

    # -- 2/3/4. rule config --------------------------------------------------
    @mcp.tool(name="set_rule",
              description="Add a disclosure rule. Structured fields are the real "
                          "contract; rule_nl is stored verbatim (any language, "
                          "lattice is language-blind) and parsed best-effort. "
                          "Unparsed rules never enforce.")
    async def set_rule(rule_nl: str, lang: str = "en", kind: str = "deny",
                       name: str | None = None, topics: list | None = None,
                       persons: list | None = None,
                       in_front_of: list | None = None,
                       cap: str = "SILENT") -> dict:
        rule_id = state.next_rule_id()
        rule, unparsed = build_rule(rule_id, rule_nl, lang, kind, name,
                                   topics, persons, in_front_of, cap)
        if rule is None:
            state.unparsed_rules.append(unparsed)
            state.ledger.append(tool="set_rule", rule_hit=None,
                                speaker=state.speaker,
                                action=f"rule {rule_id} NOT enforced: "
                                       f"{unparsed['hint']}",
                                extra={"rule_nl": rule_nl, "lang": lang})
            return {"status": "needs_structure", "id": rule_id,
                    "parsed": False, "hint": unparsed["hint"]}
        state.rules.append(rule)
        state.ledger.append(tool="set_rule", rule_hit=None,
                            speaker=state.speaker,
                            action=f"rule '{rule['name']}' ({rule_id}) enforced",
                            extra={"rule": rule})
        return {"status": "enforced", "id": rule_id, "parsed": True,
                "rule": rule}

    @mcp.tool(name="list_rules",
              description="List enforced rules (plus unparsed ones, flagged).")
    async def list_rules() -> dict:
        return {"rules": copy.deepcopy(state.rules),
                "unparsed": copy.deepcopy(state.unparsed_rules)}

    @mcp.tool(name="delete_rule",
              description="Delete a rule by id.")
    async def delete_rule(id: str) -> dict:
        before = len(state.rules)
        state.rules = [r for r in state.rules if r["id"] != id]
        state.unparsed_rules = [r for r in state.unparsed_rules if r["id"] != id]
        removed = before - len(state.rules)
        state.ledger.append(tool="delete_rule", speaker=state.speaker,
                            action=f"rule {id}: "
                            f"{'removed' if removed else 'not found'}")
        return {"id": id, "removed": bool(removed)}

    # -- 5. declare_speaker --------------------------------------------------
    @mcp.tool(name="declare_speaker",
              description="Declare who is speaking. Asks for confirmation via "
                          "elicitation; pass confirmed=true to skip.")
    async def declare_speaker(name: str, confirmed: bool = False,
                              ctx: Context = None) -> dict:
        async def _set():
            old = state.speaker
            state.speaker = name
            state.audience.add(name)
            state.ledger.append(tool="declare_speaker", speaker=name,
                                action=f"speaker {old} -> {name}")
            return {"status": "declared", "speaker": name, "previous": old}

        if confirmed:
            return await _set()
        if ctx is not None:
            try:
                result = await ctx.elicit(
                    message=f"Confirm speaker identity: {name}?",
                    schema=SpeakerConfirm,
                )
                elicited = True
            except (MCPError, NoBackChannelError):
                result, elicited = None, False
            if elicited and result is not None and result.action == "accept" \
                    and result.data.confirmed:
                return await _set()
            if elicited and result is not None \
                    and result.action in ("decline", "cancel"):
                return {"status": "not_confirmed",
                        "message": "Speaker declaration declined."}
        return {"status": "confirmation_required", "speaker": name,
                "hint": "Re-call with confirmed=true, or answer the "
                        "elicitation prompt."}

    # -- 6. get_audience -----------------------------------------------------
    @mcp.tool(name="get_audience",
              description="Perceived room state: who is present and with what "
                          "confidence. Simulated — honestly labeled.")
    async def get_audience() -> dict:
        return {"audience": sorted(state.audience),
                "confidence": state.confidence,
                "speaker": state.speaker,
                "source": "simulated", "note": SIMULATED_NOTE}

    # -- 7. explain_withholding ----------------------------------------------
    @mcp.tool(name="explain_withholding",
              description="Why wasn't I told? Deterministic ledger lookup; "
                          "cites the winning rule by name.")
    async def explain_withholding(item_id: str) -> dict:
        return _nl_explain_withholding(item_id, ledger=state.ledger)

    # -- 8. get_ledger -------------------------------------------------------
    @mcp.tool(name="get_ledger",
              description="Hash-chained decision log. since: seq int or ISO ts. "
                          "Chain re-verified on every read.")
    async def get_ledger(since: str | int | None = None) -> dict:
        return _nl_get_ledger(since, ledger=state.ledger)

    # -- 9. send_to_second_channel -------------------------------------------
    @mcp.tool(name="send_to_second_channel",
              description="Send a private card to the phone (second channel). "
                          "Records the PHONE-channel decision turn so rescope "
                          "can re-disclose it later.")
    async def send_to_second_channel(payload: dict) -> dict:
        payload = dict(payload or {})
        item = _norm_item({
            "id": payload.get("item_id"),
            "label": payload.get("label", "phone card"),
            "sensitivity": payload.get("sensitivity", "HIGH"),
            "topics": payload.get("topics", []),
        })
        audience = payload.get("audience") or sorted(state.audience)
        confidence = float(payload.get("confidence", state.confidence))
        decision = policy_engine.decide(
            speaker=state.speaker, audience_perceived=set(audience),
            presence_confidence=confidence, item=item, rules=state.rules)
        state.context.add_turn(item, set(audience), confidence,
                               state.speaker, decision)
        card = {"card_id": f"card-{item['id']}",
                "item_id": item["id"], "label": item["label"],
                "detail": payload.get("detail", item["label"]),
                "level": decision.level, "rule_hit": decision.rule_hit}
        state.queue.enqueue(card)
        entry = state.ledger.append(
            tool="send_to_second_channel", item_id=item["id"],
            level=decision.level, channel="phone",
            rule_hit=decision.rule_hit, audience=set(audience),
            confidence=confidence, speaker=state.speaker,
            action=f"phone card {card['card_id']} queued",
            extra={"reasons": decision.reasons, "card_id": card["card_id"]})
        return {"card_id": card["card_id"], "level": decision.level,
                "decision": decision.to_dict(), "ledger_seq": entry["seq"]}

    # -- 10/11. approval flow -------------------------------------------------
    # Modern-protocol reality (verified against the SDK): server-initiated
    # JSON-RPC requests are forbidden by construction (NoBackChannelError) on
    # every transport, so ctx.elicit is attempted but the REAL elicitation
    # surface is the phone: request_approval queues an approval-request card
    # to the second channel, and the human completes it out-of-band via
    # approve(token, plan_hash) — exactly the spec's URL-mode pattern, with
    # the phone page as the out-of-band surface.
    @mcp.tool(name="request_approval",
              description="EXISTENCE with a signature: propose a disclosure "
                          "plan, get a plan-hash-bound token. Tries MCP "
                          "elicitation when the transport allows it; the "
                          "phone channel is the out-of-band approval surface "
                          "(an approval card is queued there).")
    async def request_approval(plan: dict, ctx: Context = None) -> dict:
        plan = dict(plan or {})
        phash = _plan_hash(plan)
        token = f"appr-{uuid.uuid4().hex[:8]}"
        record = {"token": token, "plan": plan, "plan_hash": phash,
                  "status": "pending"}
        state.approvals[token] = record
        elicited = False
        if ctx is not None:
            try:
                result = await ctx.elicit(
                    message=("Approve disclosure plan "
                             f"(hash {phash[:12]}…)?"),
                    schema=ApprovalElicitation,
                )
                elicited = True
            except (MCPError, NoBackChannelError):
                result = None
            if elicited and result is not None and result.action == "accept":
                record["status"] = ("approved" if result.data.approve
                                    else "declined")
                record["note"] = result.data.note
                state.ledger.append(
                    tool="request_approval", item_id=plan.get("item_id"),
                    level=EXISTENCE, channel="phone",
                    speaker=state.speaker,
                    action=(f"plan {token} {record['status']} via elicitation "
                            f"(hash {phash[:12]}…)"),
                    extra={"plan_hash": phash})
                if result.data.approve:
                    _sign_card(state, plan, phash, token)
                return {"token": token, "plan_hash": phash,
                        "status": record["status"]}
            if elicited and result is not None \
                    and result.action in ("decline", "cancel"):
                record["status"] = "declined"
                state.ledger.append(
                    tool="request_approval", item_id=plan.get("item_id"),
                    speaker=state.speaker,
                    action=f"plan {token} declined via elicitation")
                return {"token": token, "plan_hash": phash,
                        "status": "declined"}
        # Out-of-band path (the normal modern-protocol case): queue an
        # approval-request card on the second channel; the phone page is the
        # elicitation surface.
        req_card = {"card_id": f"card-{token}-request", "kind": "approval_request",
                    "token": token, "plan_hash": phash,
                    "item_id": plan.get("item_id"),
                    "label": plan.get("label", "Approval requested"),
                    "detail": plan.get("detail", ""),
                    "level": EXISTENCE, "rule_hit": None}
        state.queue.enqueue(req_card)
        state.ledger.append(
            tool="request_approval", item_id=plan.get("item_id"),
            level=EXISTENCE, channel="phone", speaker=state.speaker,
            action=(f"plan {token} pending: approval card "
                    f"{req_card['card_id']} queued to second channel "
                    f"(hash {phash[:12]}…)"),
            extra={"plan_hash": phash, "card_id": req_card["card_id"]})
        return {"token": token, "plan_hash": phash, "status": "pending",
                "approval_card_id": req_card["card_id"],
                "next": "approve on the phone/second channel via "
                        "approve(token, plan_hash)"}

    @mcp.tool(name="approve",
              description="Approve a pending plan. The plan_hash must match "
                          "the hash issued by request_approval (plan-hash "
                          "binding); a modified plan cannot be approved.")
    async def approve(token: str, plan_hash: str) -> dict:
        record = state.approvals.get(token)
        if record is None:
            return {"approved": False, "error": "unknown token"}
        if record["plan_hash"] != plan_hash:
            state.ledger.append(
                tool="approve", speaker=state.speaker,
                action=(f"plan {token} REJECTED: plan_hash mismatch "
                        f"(plan was modified)"),
                extra={"expected": record["plan_hash"][:12],
                       "got": str(plan_hash)[:12]})
            return {"approved": False,
                    "error": "plan_hash mismatch — the plan was modified "
                             "after request_approval; approval refused"}
        if record["status"] != "pending":
            return {"approved": record["status"] == "approved",
                    "plan_hash": plan_hash, "status": record["status"]}
        record["status"] = "approved"
        # The approval-request card has been actioned; retract it so the
        # phone page stops showing it.
        state.queue.retract(f"card-{token}-request")
        entry = state.ledger.append(
            tool="approve", item_id=record["plan"].get("item_id"),
            level=EXISTENCE, channel="phone", speaker=state.speaker,
            action=f"plan {token} approved (hash {plan_hash[:12]}…)",
            extra={"plan_hash": plan_hash})
        card = _sign_card(state, record["plan"], plan_hash, token)
        return {"approved": True, "plan_hash": plan_hash,
                "card_id": card["card_id"], "ledger_seq": entry["seq"]}

    # -- 12. rescope_context --------------------------------------------------
    @mcp.tool(name="rescope_context",
              description="Room changed: re-decide every recorded turn "
                          "(voice AND phone) against the new audience. Items "
                          "newly voice-safe go to redisclosures_queued.")
    async def rescope_context(new_audience: list | None = None,
                              confidence: float | None = None) -> dict:
        new_audience = (list(new_audience) if new_audience is not None
                        else sorted(state.audience))
        confidence = (float(confidence) if confidence is not None
                      else state.confidence)
        state.note_room(new_audience, confidence)
        return _nl_rescope_context(
            new_audience, confidence, state.speaker, state.context,
            state.rules, policy=policy_engine, ledger=state.ledger)

    # -- 13. undo_last --------------------------------------------------------
    @mcp.tool(name="undo_last",
              description="Undo the last disclosure-affecting action. Phone "
                          "cards retract; spoken words get an honest correction "
                          "entry (history is never rewritten).")
    async def undo_last() -> dict:
        base = _nl_undo_last(ledger=state.ledger, queue=state.queue)
        if base.get("ledger_seq") is not None:
            return base
        # Lane-local extension: the merged undo only sees gate_notification
        # entries; cover this server's own voice/phone entries the same way.
        # Card ids come from the ledger extra (approval cards are keyed by
        # token, not item_id).
        target = None
        for e in reversed(state.ledger.entries_since()):
            if e.get("tool") in ("decide_disclosure", "send_to_second_channel",
                                 "approve", "request_approval") \
                    and e.get("channel"):
                target = e
                break
        if target is None:
            return base
        item_id, channel = target["item_id"], target["channel"]
        card_id = (target.get("extra") or {}).get("card_id") or f"card-{item_id}"
        if channel == "phone":
            card = state.queue.retract(card_id)
            action = (f"retracted phone card {card_id}" if card
                      else f"phone card {card_id} already delivered — "
                           f"marked withdrawn")
        else:
            action = (f"voice announcement for '{item_id}' was already "
                      f"spoken — correction logged, history not rewritten")
        entry = state.ledger.append(
            tool="undo_last", item_id=item_id, level=target["level"],
            channel=channel, rule_hit=target["rule_hit"],
            audience=target["audience"], confidence=target["confidence"],
            speaker=target["speaker"],
            action=f"undo of seq {target['seq']}: {action}",
            extra={"undone_seq": target["seq"]})
        return {"reversed": channel == "phone", "action": action,
                "note": None, "ledger_seq": entry["seq"]}

    # -- 14. gate_notification -------------------------------------------------
    @mcp.tool(name="gate_notification",
              description="Unprompted speech: announce vs phone-only. "
                          "FULL/ABSTRACT -> voice; EXISTENCE/SILENT -> phone "
                          "card (P0-2: SILENT always pairs with a nudge).")
    async def gate_notification(notif: dict, audience: list,
                                confidence: float | None = None) -> dict:
        confidence = (float(confidence) if confidence is not None
                      else state.confidence)
        state.note_room(audience, confidence)
        result = _nl_gate_notification(
            notif, audience, confidence, state.speaker, state.rules,
            policy=policy_engine, ledger=state.ledger, queue=state.queue)
        # Cross-lane contract: record the turn for BOTH voice and phone
        # channel outcomes — rescope must see phone-sent items.
        item = _norm_item({
            "id": notif.get("id"), "label": notif.get("label", "notification"),
            "sensitivity": notif.get("sensitivity", "HIGH"),
            "topics": notif.get("topics", []),
        })
        state.context.add_turn(item, set(audience), confidence,
                               state.speaker,
                               _decision_ns(result["decision"]))
        return result

    # -- Resource: ui://earshot/inspector ------------------------------------
    @mcp.resource("ui://earshot/inspector",
                  name="earshot-inspector",
                  description="Live lattice state for the MCP Apps inspector card.",
                  mime_type="application/json")
    async def inspector() -> str:
        recent = state.ledger.entries_since()[-8:]
        return json.dumps({
            "server": SERVER_NAME,
            "transport": "streamable-http",
            "spec": "2025-11-25",
            "speaker": state.speaker,
            "audience": sorted(state.audience),
            "confidence": state.confidence,
            "presence_source": "simulated",
            "fail_closed_threshold": FAIL_CLOSED_CONFIDENCE,
            "levels": [FULL, ABSTRACT, EXISTENCE, SILENT],
            "rules": state.rules,
            "context_turns": len(state.context.turns()),
            "pending_phone_cards": len(state.queue.pending()),
            "second_channel_cards": state.queue.pending(),
            "pending_approvals": sum(
                1 for a in state.approvals.values()
                if a["status"] == "pending"),
            "ledger_head": state.ledger.head(),
            "recent_decisions": [
                {"seq": e["seq"], "tool": e["tool"],
                 "item_id": e["item_id"], "level": e["level"],
                 "channel": e["channel"], "rule_hit": e["rule_hit"],
                 "audience": e["audience"]} for e in recent
            ],
        })

    return mcp


def _sign_card(state, plan, plan_hash, token):
    """EXISTENCE with a signature: approved plan -> signed phone card."""
    card = {"card_id": f"card-{token}",
            "item_id": plan.get("item_id", "approval"),
            "label": plan.get("label", "Approved disclosure"),
            "detail": plan.get("detail", ""),
            "level": EXISTENCE, "rule_hit": None,
            "signature": plan_hash, "token": token}
    state.queue.enqueue(card)
    state.ledger.append(
        tool="approve", item_id=card["item_id"], level=EXISTENCE,
        channel="phone", speaker=state.speaker,
        action=f"signed card {card['card_id']} queued (hash {plan_hash[:12]}…)",
        extra={"plan_hash": plan_hash, "card_id": card["card_id"]})
    return card


def main():
    import argparse
    parser = argparse.ArgumentParser(description="EARSHOT MCP server")
    parser.add_argument("--transport", default="streamable-http",
                        choices=["stdio", "streamable-http"],
                        help="stdio supports server-initiated elicitation; "
                             "streamable-http is the Inspector/browser route "
                             "(2026-07-28 modern route has no back-channel: "
                             "request_approval degrades to the phone token flow)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    server = create_server()
    if args.transport == "stdio":
        server.run(transport="stdio")
    else:
        server.run(transport="streamable-http", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
