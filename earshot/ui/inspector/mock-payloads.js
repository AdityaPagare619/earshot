/* EARSHOT inspector — mock decision payloads (lane inspector-ui).
 * Shapes mirror worldsim/policy.py exactly: decision objects carry
 * {level, reasons, latency_ms, untrusted_seen, rule_hit}. Tool-call events
 * mirror the MCP server's trace format until mcp-server merges and posts real
 * ones on window.EarshotBus. All data is simulated and labeled as such.
 */
(function () {
"use strict";

var ITEM = "Prenatal visit — Tue 10:30 · City Clinic, Ring Road";

var RULE_MOM = {
  name: "never-mention-clinic-in-front-of-mom",
  nl: "Mom ke saamne clinic ka zikr mat karo",
  kind: "deny", topics: ["clinic", "prenatal"], in_front_of: ["mom"], cap: "EXISTENCE"
};
var RULE_SPOUSE = {
  name: "clinic-summaries-for-spouse",
  kind: "deny", topics: ["clinic", "prenatal"], in_front_of: ["spouse"], cap: "ABSTRACT"
};
var RULE_KIDS = {
  name: "no-health-talk-around-kids",
  kind: "deny", topics: ["clinic", "prenatal"], in_front_of: ["friend1", "friend2"], cap: "SILENT"
};

function dec(level, reasons, untrusted, rule_hit, ms) {
  return {
    level: level, reasons: reasons,
    latency_ms: ms != null ? ms : 0.006,
    untrusted_seen: untrusted || [],
    rule_hit: rule_hit || null
  };
}

/* Full pipeline scenario: MIL walks in during "what's my day?" */
function walkInScenario() {
  var steps = [];
  steps.push({ ev: "wake", at: 0, payload: { trace_id: "tr-3f2a" } });
  steps.push({ ev: "toolcall", at: 500, payload: {
    trace_id: "tr-3f2a", stage: "snapshot", tool: "get_audience",
    args: "re-sample on wake-word · presence confidence",
    result: { level: "FULL", latency_ms: 0.004, confidence: 0.92 }
  }});
  steps.push({ ev: "toolcall", at: 1100, payload: {
    trace_id: "tr-3f2a", stage: "policy", tool: "decide_disclosure",
    args: "item: prenatal visit (HIGH) · audience: priya",
    result: { level: "FULL", latency_ms: 0.006 }
  }});
  steps.push({ ev: "decision", at: 1700, payload: {
    trace_id: "tr-3f2a", item_label: ITEM, audience: ["priya"], confidence: 0.92,
    decision: dec("FULL", ["audience fully trusted"], [], null)
  }});
  /* mother-in-law crosses the threshold — wake-word re-sample (P0-1) */
  steps.push({ ev: "room", at: 2600, payload: { present: ["priya", "mom"], room_state: "EXISTENCE" } });
  steps.push({ ev: "wake", at: 2900, payload: { trace_id: "tr-3f31" } });
  steps.push({ ev: "toolcall", at: 3400, payload: {
    trace_id: "tr-3f31", stage: "snapshot", tool: "get_audience",
    args: "fresh snapshot · audience: priya, mom",
    result: { level: "FULL", latency_ms: 0.004, confidence: 0.88 }
  }});
  steps.push({ ev: "toolcall", at: 4000, payload: {
    trace_id: "tr-3f31", stage: "policy", tool: "decide_disclosure",
    args: "item: prenatal visit (HIGH) · audience: priya, mom · 1 deny rule",
    result: { level: "EXISTENCE", latency_ms: 0.006,
              rule_hit: RULE_MOM.name, rule_nl: RULE_MOM.nl }
  }});
  steps.push({ ev: "toolcall", at: 4700, payload: {
    trace_id: "tr-3f31", stage: "level", tool: "send_to_second_channel",
    args: "full card → phone · title only stays in room",
    result: { level: "EXISTENCE", latency_ms: 0.009 }
  }});
  steps.push({ ev: "decision", at: 5300, payload: {
    trace_id: "tr-3f31", item_label: ITEM, audience: ["priya", "mom"], confidence: 0.88,
    rule_nl: RULE_MOM.nl,
    decision: dec("EXISTENCE",
      ["deny rule '" + RULE_MOM.name + "' caps at EXISTENCE",
       "untrusted present ['mom']; HIGH -> EXISTENCE"],
      ["mom"], RULE_MOM.name, 0.006)
  }});
  /* user tries to override by voice — resisted (monotonic-downward) */
  steps.push({ ev: "wake", at: 6600, payload: { trace_id: "tr-3f38" } });
  steps.push({ ev: "toolcall", at: 7000, payload: {
    trace_id: "tr-3f38", stage: "policy", tool: "decide_disclosure",
    args: "override attempt: “just tell everyone”",
    result: { level: "EXISTENCE", latency_ms: 0.006,
              rule_hit: RULE_MOM.name, rule_nl: RULE_MOM.nl }
  }});
  steps.push({ ev: "decision", at: 7600, payload: {
    trace_id: "tr-3f38", item_label: ITEM, audience: ["priya", "mom"], confidence: 0.88,
    rule_nl: RULE_MOM.nl,
    decision: dec("EXISTENCE",
      ["deny rule '" + RULE_MOM.name + "' caps at EXISTENCE",
       "override attempt resisted: voice cannot widen disclosure"],
      ["mom"], RULE_MOM.name, 0.007)
  }});
  return steps;
}

/* Four-room lattice grid — the class-limiter in one glance */
function latticeGrid() {
  return [
    { audience_label: "ALONE", who: "priya only · conf 0.94", level: "FULL", rule_hit: null },
    { audience_label: "SPOUSE", who: "priya, spouse · conf 0.91", level: "ABSTRACT",
      rule_hit: RULE_SPOUSE.name },
    { audience_label: "MOTHER-IN-LAW", who: "priya, mom · conf 0.88", level: "EXISTENCE",
      rule_hit: RULE_MOM.name },
    { audience_label: "KIDS' FRIENDS", who: "priya, friend1, friend2 · conf 0.81", level: "SILENT",
      rule_hit: RULE_KIDS.name }
  ];
}

window.EarshotMock = {
  item: ITEM,
  rules: [RULE_MOM, RULE_SPOUSE, RULE_KIDS],
  walkInScenario: walkInScenario,
  latticeGrid: latticeGrid,
  /* plays a scenario on the bus with the given step timing */
  play: function (steps, done) {
    var bus = window.EarshotBus;
    steps.forEach(function (s) {
      setTimeout(function () { bus.emit(s.ev, s.payload); }, s.at);
    });
    var last = steps.reduce(function (m, s) { return Math.max(m, s.at); }, 0);
    setTimeout(function () { done && done(); }, last + 1500);
  }
};
})();
