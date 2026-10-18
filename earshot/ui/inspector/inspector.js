/* EARSHOT inspector — RIGHT pane module (lane inspector-ui).
 * Pluggable web component <earshot-inspector>. No framework, no build step.
 *
 * Event bus (window.EarshotBus):
 *   'wake'      {trace_id}                              — wake-word detected
 *   'toolcall'  {trace_id, stage, tool, args, result}   — an MCP tool call
 *     stage: 'wake' | 'snapshot' | 'policy' | 'level'
 *     result: {level?, latency_ms, confidence?, rule_hit?, rule_nl?}
 *   'decision'  {trace_id, item_label, audience, confidence,
 *                decision:{level, reasons, latency_ms, untrusted_seen, rule_hit},
 *                rule_nl}                              — final lattice decision
 *   'grid'      [{audience_label, who, level, rule_hit?}] — four-room view
 *   'room'      {present:[], room_state}                — binds --ear-room-state
 *
 * Until mcp-server merges, mock-payloads.js emits exactly these shapes.
 * Token contract: --ear-* names per ui-inspiration; local fallbacks so this
 * file renders standalone before TOKENS.md merges.
 */
(function () {
"use strict";

var listeners = {};
window.EarshotBus = {
  on: function (ev, fn) { (listeners[ev] = listeners[ev] || []).push(fn); },
  emit: function (ev, payload) {
    (listeners[ev] || []).forEach(function (fn) {
      try { fn(payload); } catch (e) { /* never break the bus */ }
    });
  }
};

var STAGES = [
  { id: "wake",     label: "WAKE-WORD", desc: "fresh presence re-sample" },
  { id: "snapshot", label: "SNAPSHOT",  desc: "who is listening" },
  { id: "policy",   label: "POLICY",    desc: "deterministic lattice" },
  { id: "level",    label: "LEVEL",     desc: "what the room hears" }
];
var LEVEL_VERB = {
  FULL: "spoken in full", ABSTRACT: "summary only",
  EXISTENCE: "title only", SILENT: "withheld"
};

function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
  });
}
function accent(level) { return "var(--ear-level-" + String(level).toLowerCase() + ")"; }

var CSS = [
":host{",
"--ear-canvas:#050607;--ear-surface:#0b0e11;--ear-surface-2:#11161b;",
"--ear-line:rgba(255,255,255,.09);--ear-text:#e9eff3;--ear-text-dim:#8b98a3;",
"--ear-level-full:#2ee6a8;--ear-level-abstract:#ffb224;",
"--ear-level-existence:#a78bfa;--ear-level-silent:#fb5e7e;",
"--ear-presence:#ffffff;--ear-lowconf:#ff7a1a;--ear-approve:#38e1ff;",
"--ear-radius:10px;--ear-font:'Inter',system-ui,-apple-system,sans-serif;",
"--ear-mono:ui-monospace,'SF Mono',Menlo,Consolas,monospace;",
"--ear-room-state:var(--ear-level-full);",
"}",
":host{display:block;background:var(--ear-canvas);color:var(--ear-text);",
"font-family:var(--ear-font);height:100%;}",
".wrap{height:100%;display:flex;flex-direction:column;overflow:hidden;}",
".tabs{display:flex;gap:6px;padding:12px 14px 0;}",
".tab{font:600 11px/1 var(--ear-font);letter-spacing:.14em;color:var(--ear-text-dim);",
"background:none;border:1px solid var(--ear-line);border-radius:999px;padding:8px 14px;cursor:pointer;}",
".tab.on{color:var(--ear-canvas);background:var(--ear-text);border-color:var(--ear-text);}",
".view{flex:1;overflow-y:auto;padding:14px;display:none;}",
".view.on{display:block;}",
".rail{display:flex;align-items:center;margin:2px 0 16px;}",
".stage{flex:1;text-align:center;position:relative;}",
".stage .dot{width:12px;height:12px;border-radius:50%;margin:0 auto 8px;",
"background:var(--ear-surface-2);border:1px solid var(--ear-line);transition:all .4s;}",
".stage .sl{font:600 10px/1.4 var(--ear-mono);letter-spacing:.18em;color:var(--ear-text-dim);}",
".stage .sd{font:400 10px/1.4 var(--ear-font);color:var(--ear-text-dim);opacity:.7;}",
".stage:not(:last-child)::after{content:'';position:absolute;top:6px;left:calc(50% + 10px);",
"right:calc(-50% + 10px);height:1px;background:var(--ear-line);}",
".stage.live .dot{background:var(--stage-accent,var(--ear-presence));",
"box-shadow:0 0 14px 2px var(--stage-accent,var(--ear-presence));border-color:transparent;}",
".stage.live .sl{color:var(--ear-text);}",
".stage.done .dot{background:var(--stage-accent,var(--ear-line));border-color:transparent;}",
".flow{display:flex;flex-direction:column;gap:10px;}",
".tcard{background:var(--ear-surface);border:1px solid var(--ear-line);",
"border-left:3px solid var(--card-accent);border-radius:var(--ear-radius);padding:12px 14px;",
"box-shadow:0 0 22px -8px var(--card-accent);",
"animation:slidein .5s cubic-bezier(.2,.9,.25,1) both;}",
"@keyframes slidein{from{opacity:0;transform:translateX(26px);}to{opacity:1;transform:none;}}",
".tcard header{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px;}",
".tool{font:600 13px/1.3 var(--ear-font);color:var(--ear-text);}",
".trace{font:400 10px/1 var(--ear-mono);color:var(--ear-text-dim);}",
".args{font:400 12px/1.5 var(--ear-font);color:var(--ear-text-dim);}",
".conf{display:flex;align-items:center;gap:8px;margin-top:8px;}",
".conf-bar{flex:1;height:4px;background:var(--ear-surface-2);border-radius:2px;overflow:hidden;}",
".conf-bar i{display:block;height:100%;background:var(--ear-presence);border-radius:2px;}",
".conf-num{font:500 11px/1 var(--ear-mono);color:var(--ear-text-dim);}",
".res{display:flex;align-items:center;gap:10px;margin-top:10px;}",
".lvl{font:700 12px/1 var(--ear-font);letter-spacing:.12em;color:var(--lv);",
"border:1px solid var(--lv);border-radius:6px;padding:6px 10px;box-shadow:0 0 12px -4px var(--lv);}",
".verb{font:400 12px/1 var(--ear-font);color:var(--ear-text-dim);}",
".lat{margin-left:auto;font:400 11px/1 var(--ear-mono);color:var(--ear-text-dim);}",
".rule-hit{margin-top:10px;border-top:1px dashed var(--ear-line);padding-top:10px;}",
".rule-tag{font:700 9px/1 var(--ear-mono);letter-spacing:.16em;color:var(--ear-canvas);",
"background:var(--ear-lowconf);border-radius:4px;padding:4px 7px;margin-right:8px;}",
".rule-hit strong{font:600 13px/1.4 var(--ear-font);color:var(--ear-text);}",
".rule-nl{font:400 12px/1.5 var(--ear-font);color:var(--ear-text-dim);margin-top:4px;font-style:italic;}",
".rule-cap{font:500 11px/1.5 var(--ear-font);color:var(--ear-text-dim);margin-top:2px;}",
".decision{margin-top:14px;background:var(--ear-surface-2);border:1px solid var(--ear-line);",
"border-top:3px solid var(--card-accent);border-radius:var(--ear-radius);padding:16px;",
"box-shadow:0 0 30px -10px var(--card-accent);animation:slidein .5s .1s cubic-bezier(.2,.9,.25,1) both;}",
".dec-top{display:flex;justify-content:space-between;margin-bottom:8px;}",
".dec-label{font:600 10px/1 var(--ear-mono);letter-spacing:.2em;color:var(--ear-text-dim);}",
".dec-lat{font:400 11px/1 var(--ear-mono);color:var(--ear-text-dim);}",
".dec-level{font:800 30px/1.1 var(--ear-font);letter-spacing:.06em;color:var(--lv);",
"text-shadow:0 0 24px var(--lv);}",
".dec-item{font:500 13px/1.4 var(--ear-font);margin:6px 0 8px;}",
".reasons{margin:0;padding:0;list-style:none;}",
".reasons li{font:400 12px/1.6 var(--ear-font);color:var(--ear-text-dim);padding-left:14px;position:relative;}",
".reasons li::before{content:'\\203A';position:absolute;left:0;color:var(--card-accent);}",
".phone-nudge{margin-top:10px;font:600 12px/1.4 var(--ear-font);color:var(--ear-approve);",
"border:1px solid var(--ear-approve);border-radius:8px;padding:8px 12px;display:inline-block;",
"box-shadow:0 0 14px -6px var(--ear-approve);}",
".ghead{font:600 10px/1.6 var(--ear-mono);letter-spacing:.18em;color:var(--ear-text-dim);margin:2px 0 4px;}",
".gitem{font:500 13px/1.5 var(--ear-font);margin-bottom:14px;padding:10px 12px;",
"background:var(--ear-surface);border:1px solid var(--ear-line);border-radius:var(--ear-radius);}",
".garrow{font:600 10px/1 var(--ear-mono);letter-spacing:.2em;color:var(--ear-text-dim);",
"text-align:center;margin-bottom:12px;}",
".grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;}",
".gcol{background:var(--ear-surface);border:1px solid var(--ear-line);",
"border-top:3px solid var(--card-accent);border-radius:var(--ear-radius);padding:12px;",
"box-shadow:0 0 20px -10px var(--card-accent);animation:slidein .5s cubic-bezier(.2,.9,.25,1) both;}",
".g-aud{font:700 11px/1.3 var(--ear-font);letter-spacing:.1em;}",
".g-who{font:400 11px/1.4 var(--ear-font);color:var(--ear-text-dim);margin:2px 0 10px;}",
".g-level{font:800 17px/1.2 var(--ear-font);letter-spacing:.05em;color:var(--lv);",
"text-shadow:0 0 16px var(--lv);margin-bottom:10px;}",
".g-detail{font:400 12px/1.55 var(--ear-font);}",
".g-detail strong{display:block;font-size:12.5px;margin-bottom:2px;}",
".g-detail .dim{color:var(--ear-text-dim);}",
".g-detail.silent strong{color:var(--ear-text-dim);}",
".approve-chip{display:inline-block;margin-top:6px;font:600 11px/1 var(--ear-font);",
"color:var(--ear-approve);border:1px solid var(--ear-approve);border-radius:6px;padding:6px 9px;}",
".g-rule{margin-top:10px;border-top:1px dashed var(--ear-line);padding-top:8px;}",
".g-rule strong{font-size:11.5px;}",
"@media (prefers-reduced-motion:reduce){.tcard,.gcol,.decision{animation:none;}}"
].join("\n");

var HTML =
'<div class="wrap">' +
'<nav class="tabs"><button class="tab on" data-view="pipe">LIVE PIPELINE</button>' +
'<button class="tab" data-view="grid">LATTICE GRID</button></nav>' +
'<div class="view on" data-view="pipe"><div class="rail"></div><div class="flow"></div></div>' +
'<div class="view" data-view="grid">' +
'<div class="ghead">SAME PAYLOAD · FOUR ROOMS · THE CLASS-LIMITER</div>' +
'<div class="gitem">Prenatal visit — Tue 10:30 · City Clinic, Ring Road</div>' +
'<div class="garrow">DISCLOSURE NARROWS →</div>' +
'<div class="grid"></div></div>' +
"</div>";

function toolCard(ev) {
  var lvl = ev.result && ev.result.level;
  var ruleHtml = "";
  if (ev.result && ev.result.rule_hit) {
    ruleHtml =
      '<div class="rule-hit"><span class="rule-tag">deny rule</span>' +
      "<strong>" + esc(ev.result.rule_hit) + "</strong>" +
      (ev.result.rule_nl ? '<div class="rule-nl">&ldquo;' + esc(ev.result.rule_nl) + "&rdquo;</div>" : "") +
      '<div class="rule-cap">caps disclosure at ' + esc(lvl || "") + "</div></div>";
  }
  var confHtml = "";
  if (ev.result && typeof ev.result.confidence === "number") {
    var c = ev.result.confidence, low = c < 0.6;
    confHtml = '<div class="conf"><span class="conf-bar"><i style="width:' +
      Math.round(c * 100) + "%;" + (low ? "background:var(--ear-lowconf);" : "") + '"></i></span>' +
      '<span class="conf-num">' + c.toFixed(2) + (low ? " · fail closed" : "") + "</span></div>";
  }
  return (
    '<article class="tcard" style="--card-accent:' + accent(lvl || "FULL") + '">' +
    '<header><span class="tool">' + esc(ev.tool) + "</span>" +
    '<span class="trace">' + esc(ev.trace_id || "") + "</span></header>" +
    '<div class="args">' + esc(ev.args || "") + "</div>" + confHtml +
    (lvl ?
      '<div class="res"><span class="lvl" style="--lv:' + accent(lvl) + '">' + esc(lvl) + "</span>" +
      '<span class="verb">' + esc(LEVEL_VERB[lvl] || "") + "</span>" +
      '<span class="lat">' + esc(String(ev.result.latency_ms != null ? ev.result.latency_ms : "")) + " ms</span></div>"
      : "") +
    ruleHtml +
    "</article>"
  );
}

function decisionBanner(d) {
  var dec = d.decision, lvl = dec.level;
  var phone = (lvl === "SILENT" || lvl === "EXISTENCE")
    ? '<div class="phone-nudge">sent to your phone — detail never spoken</div>' : "";
  var reasons = (dec.reasons || []).map(function (r) {
    return "<li>" + esc(r) + "</li>";
  }).join("");
  return (
    '<section class="decision" style="--card-accent:' + accent(lvl) + '">' +
    '<div class="dec-top"><span class="dec-label">decision</span>' +
    '<span class="dec-lat">' + esc(String(dec.latency_ms)) + " ms</span></div>" +
    '<div class="dec-level" style="--lv:' + accent(lvl) + '">' + esc(lvl) + "</div>" +
    '<div class="dec-item">' + esc(d.item_label || "") + "</div>" +
    '<ul class="reasons">' + reasons + "</ul>" + phone +
    "</section>"
  );
}

function gridCard(col) {
  var lvl = col.level, body = "";
  if (lvl === "FULL") {
    body = '<div class="g-detail"><strong>Prenatal visit — Tue 10:30</strong>' +
      "<span>City Clinic, Ring Road · bring insurance card</span></div>";
  } else if (lvl === "ABSTRACT") {
    body = '<div class="g-detail"><strong>Health appointment tomorrow morning</strong>' +
      '<span class="dim">details withheld · full card on your phone</span></div>';
  } else if (lvl === "EXISTENCE") {
    body = '<div class="g-detail"><strong>One calendar event</strong>' +
      '<span class="approve-chip">approve on phone to hear more</span></div>';
  } else {
    body = '<div class="g-detail silent"><strong>—</strong>' +
      '<span class="phone-nudge">withheld · sent to your phone</span></div>';
  }
  var rule = col.rule_hit
    ? '<div class="g-rule"><span class="rule-tag">deny rule</span><strong>' +
      esc(col.rule_hit) + "</strong></div>" : "";
  return (
    '<div class="gcol" style="--card-accent:' + accent(lvl) + ';animation-delay:' + (col._i * 110) + 'ms">' +
    '<div class="g-aud">' + esc(col.audience_label) + "</div>" +
    '<div class="g-who">' + esc(col.who) + "</div>" +
    '<div class="g-level" style="--lv:' + accent(lvl) + '">' + esc(lvl) + "</div>" +
    body + rule +
    "</div>"
  );
}

class Inspector extends HTMLElement {
  connectedCallback() {
    if (this._ready) return;
    this._ready = true;
    const root = this.attachShadow({ mode: "open" });
    const style = document.createElement("style");
    style.textContent = CSS;
    root.appendChild(style);
    const holder = document.createElement("div");
    holder.innerHTML = HTML;
    root.appendChild(holder);
    this._rail = root.querySelector(".rail");
    this._flow = root.querySelector(".flow");
    this._grid = root.querySelector(".grid");
    this._renderRail();
    root.querySelectorAll(".tab").forEach((t) => {
      t.addEventListener("click", () => {
        root.querySelectorAll(".tab").forEach((x) => x.classList.remove("on"));
        t.classList.add("on");
        root.querySelectorAll(".view").forEach((v) => {
          v.classList.toggle("on", v.dataset.view === t.dataset.view);
        });
      });
    });
    const bus = window.EarshotBus;
    bus.on("wake", (ev) => this._onWake(ev));
    bus.on("toolcall", (ev) => this._onToolcall(ev));
    bus.on("decision", (ev) => this._onDecision(ev));
    bus.on("grid", (cols) => this._renderGrid(cols));
    bus.on("room", (ev) => {
      if (ev && ev.room_state) this.style.setProperty("--ear-room-state", accent(ev.room_state));
    });
  }

  _renderRail() {
    this._rail.innerHTML = STAGES.map(function (s) {
      return '<div class="stage" data-stage="' + s.id + '">' +
        '<div class="dot"></div><div class="sl">' + s.label + "</div>" +
        '<div class="sd">' + s.desc + "</div></div>";
    }).join("");
  }

  _markStage(stageId, accentVar) {
    const st = this._rail.querySelector('[data-stage="' + stageId + '"]');
    if (!st) return;
    st.classList.add("live");
    if (accentVar) st.style.setProperty("--stage-accent", accentVar);
  }

  _settle(stageId, delay) {
    setTimeout(() => {
      const st = this._rail && this._rail.querySelector('[data-stage="' + stageId + '"]');
      if (st) { st.classList.remove("live"); st.classList.add("done"); }
    }, delay);
  }

  _onWake(ev) {
    this._rail.querySelectorAll(".stage").forEach((s) => s.classList.remove("live", "done"));
    this._flow.querySelectorAll(".tcard, .decision").forEach((c) => { c.style.opacity = ".4"; });
    this._markStage("wake", "var(--ear-presence)");
    this._settle("wake", 700);
  }

  _onToolcall(ev) {
    const lvl = ev.result && ev.result.level;
    this._markStage(ev.stage, lvl ? accent(lvl) : "var(--ear-presence)");
    const div = document.createElement("div");
    div.innerHTML = toolCard(ev);
    const card = div.firstChild;
    card.style.animationDelay = (this._flow.querySelectorAll(".tcard").length * 90) + "ms";
    this._flow.appendChild(card);
    this._settle(ev.stage, 900);
  }

  _onDecision(ev) {
    this._markStage("level", accent(ev.decision.level));
    const div = document.createElement("div");
    div.innerHTML = decisionBanner(ev);
    this._flow.appendChild(div.firstChild);
    setTimeout(() => {
      this._rail.querySelectorAll(".stage").forEach((s) => {
        s.classList.remove("live"); s.classList.add("done");
      });
    }, 1200);
  }

  _renderGrid(cols) {
    this._grid.innerHTML = cols.map(function (c, i) {
      c._i = i;
      return gridCard(c);
    }).join("");
  }
}

if (window.customElements && !window.customElements.get("earshot-inspector")) {
  window.customElements.define("earshot-inspector", Inspector);
}

window.EarshotInspector = { levels: ["FULL", "ABSTRACT", "EXISTENCE", "SILENT"] };
})();
