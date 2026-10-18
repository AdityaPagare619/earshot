/* ════════════════════════════════════════════════════════════════════
   EARSHOT simulator shell — app.js
   Owns: PresenceStore (SSOT), EarshotBus (frozen topics), EarshotClient
   (mock ⇢ MCP Streamable HTTP), CENTER chat UI, presence panel, wake-word.
   Lanes 5/6 attach to #mount-room / #mount-inspector and subscribe to
   window.EarshotBus — they never touch the store internals.
   ════════════════════════════════════════════════════════════════════ */
(function () {
"use strict";

/* ── 1. Event bus (frozen contract — see DESIGN.md) ─────────────── */
const EarshotBus = {
  _t: {},
  on(topic, fn) { (this._t[topic] = this._t[topic] || []).push(fn); },
  once(topic, fn) {
    const w = (p) => { this.off(topic, w); fn(p); };
    this.on(topic, w);
  },
  off(topic, fn) { this._t[topic] = (this._t[topic] || []).filter((f) => f !== fn); },
  emit(topic, payload) {
    const p = Object.assign({ ts: new Date().toISOString() }, payload);
    (this._t[topic] || []).forEach((fn) => { try { fn(p); } catch (e) { console.error(e); } });
    ticker(`<span class="ev">${topic}</span>`);
  },
};
window.EarshotBus = EarshotBus;

/* ── 2. Config ──────────────────────────────────────────────────── */
const qs = new URLSearchParams(location.search);
const EARSHOT_SERVER_BASE = qs.get("server") || "http://127.0.0.1:8765"; // documented base URL
const MCP_ROUTE = "/mcp";                                                // Streamable HTTP endpoint
const FAIL_CLOSED = 0.6;                 // P0 gate (MASTER_PLAN §6)

/* ── 3. PresenceStore — the SSOT for who's in the room ──────────── */
const people = [
  { id: "priya", name: "Priya",   role: "self",     present: true,  confidence: 1.0 },
  { id: "rohan", name: "Rohan",   role: "spouse",   present: false, confidence: 0 },
  { id: "mil",   name: "Meera",   role: "guest",    note: "mother-in-law", present: false, confidence: 0 },
  { id: "kids",  name: "Kids' friends", role: "outsider", present: false, confidence: 0 },
];
const store = {
  people,
  get(id) { return people.find((p) => p.id === id); },
  setPresence(id, present, conf) {
    const p = this.get(id);
    if (!p) return;
    const was = p.present;
    p.present = present;
    p.confidence = conf !== undefined ? conf : (present ? 0.95 : 0);
    renderPresence();
    EarshotBus.emit("presence.changed", { personId: id, present, confidence: p.confidence });
    if (present && !was) EarshotBus.emit("walkin", { personId: id }); // walk-in beat hook
    EarshotBus.emit("presence.snapshot", { people: snapshot() });
  },
  // P0-1: fresh presence re-sample — simulated sensor sweep, honestly labeled
  resample(reason) {
    const jitter = () => (Math.random() * 0.06 - 0.03);
    people.forEach((p) => {
      if (!p.present) { p.confidence = 0; return; }
      const base = p.id === "priya" ? 1.0 : p.id === "rohan" ? 0.97 : p.id === "mil" ? 0.92 : 0.88;
      p.confidence = Math.min(1, Math.max(0, base + jitter()));
    });
    const stamp = new Date().toLocaleTimeString();
    document.getElementById("resample-stamp").textContent = "re-sample: " + stamp + " (simulated)";
    renderPresence();
    EarshotBus.emit("wakeword.resample", { reason: reason || "manual", people: snapshot() });
    EarshotBus.emit("presence.snapshot", { people: snapshot() });
    latticeFlash("snap");
  },
};
function snapshot() {
  return people.map((p) => ({ id: p.id, name: p.name, role: p.role, present: p.present, confidence: +p.confidence.toFixed(2) }));
}
// Effective audience: fail-closed — confidence in (0, 0.6) counts as PRESENT
function effectiveAudience() {
  return people
    .filter((p) => p.present || (p.confidence > 0 && p.confidence < FAIL_CLOSED))
    .map((p) => ({ id: p.id, name: p.name, role: p.role, confidence: +p.confidence.toFixed(2),
                   failClosed: p.confidence > 0 && p.confidence < FAIL_CLOSED }));
}

/* ── 4. Fixtures (shape matches fixture-upstreams lane; labeled mock) ─ */
const rules = [
  { id: "rule-1", name: "never mention the clinic in front of Mom", kind: "deny",
    topic: "clinic", audience: ["guest", "outsider"], lang: "hinglish",
    gloss: "Mom ke saamne clinic ka zikr mat karo" },
];
const calendar = [
  { id: "evt-1", title: "Dental checkup",  detail: "Dental checkup, City Dental, 10:00 AM",   topic: "health-routine", sensitivity: "LOW" },
  { id: "evt-2", title: "Lunch with Rohan", detail: "Lunch with Rohan, 1:00 PM",               topic: "social",         sensitivity: "LOW" },
  { id: "evt-3", title: "Prenatal visit",  detail: "Prenatal visit, St. Mary's Clinic, 4:30 PM", topic: "clinic",       sensitivity: "HIGH" },
];
const LATTICE = ["SILENT", "EXISTENCE", "ABSTRACT", "FULL"]; // index = openness
const stricter = (a, b) => (LATTICE.indexOf(a) <= LATTICE.indexOf(b) ? a : b);
const sessionFloor = {}; // monotonic-downward: item can only narrow within a session

/* ── 5. Transports: mock now, MCP Streamable HTTP on merge ─────── */
const MockTransport = {
  name: "mock",
  async call(tool, args) {
    await new Promise((r) => setTimeout(r, 30 + Math.random() * 60)); // visible latency, simulated
    switch (tool) {
      case "get_audience": return { audience: effectiveAudience() };
      case "list_rules":   return { rules };
      case "decide_disclosure": return mockDecide(args.item, args.audience);
      case "send_to_second_channel":
        return { delivered: true, channel: "phone (browser stand-in, simulated)", payload: args.payload };
      case "explain_withholding":
        return { item_id: args.item_id, reasons: ["see disclosure.decision event"] };
      default: return { mock: true, tool, note: "not yet wired to mock" };
    }
  },
};
// P0-1/2/3 + fail-closed + monotonic-downward, deterministic. Shapes mirror
// MASTER_PLAN §3 so swapping to the real server is mechanical.
function mockDecide(item, audience) {
  const sens = item.sensitivity || "HIGH";               // P0-3: unknown topic → HIGH
  const others = audience.filter((p) => p.role !== "self");
  const guests = others.filter((p) => p.role === "guest" || p.role === "outsider");
  const reasons = [];
  if (!item.sensitivity) reasons.push("P0-3: unknown topic defaulted to HIGH");
  const fc = audience.filter((p) => p.failClosed);
  if (fc.length) reasons.push(`P0 fail-closed: low-confidence presence treated as present (${fc.map((p) => p.name).join(", ")})`);
  let level = "FULL";
  if (others.length === 0) {
    level = "FULL"; reasons.push("audience: speaker only");
  } else if (sens === "HIGH" && guests.length) {
    const hit = rules.find((r) => r.kind === "deny" && r.topic === item.topic &&
      r.audience.some((a) => guests.some((g) => g.role === a)));
    level = "EXISTENCE";
    reasons.push(hit ? `deny rule: "${hit.name}"` : "HIGH topic + outsider present (fail-safe)");
  } else if (sens === "HIGH") {
    level = "ABSTRACT"; reasons.push("HIGH topic + non-speaker present (no deny rule)");
  } else if (sens === "MEDIUM" && guests.length) {
    level = "ABSTRACT"; reasons.push("MEDIUM topic + outsider present");
  } else {
    reasons.push("LOW topic — speakable to this audience");
  }
  // monotonic-downward within session
  if (sessionFloor[item.id]) level = stricter(level, sessionFloor[item.id]);
  sessionFloor[item.id] = level;
  return { level, reasons, confidence: 0.97, policy: "mock (pending mcp-server lane)" };
}

const EarshotClient = {
  mode: "mock",
  transport: MockTransport,
  async call(tool, args) {
    const t0 = performance.now();
    let result, via = this.mode;
    try {
      result = this.mode === "mcp"
        ? await mcpCall(tool, args)          // may throw → fall back
        : await MockTransport.call(tool, args);
    } catch (e) {
      via = "mock (fallback)";
      result = await MockTransport.call(tool, args);
    }
    const ms = +(performance.now() - t0).toFixed(1);
    EarshotBus.emit("tool.call", { tool, args: summarizeArgs(args), result: summarizeResult(result), ms, via });
    return result;
  },
  async probe() {
    // Provisional Streamable HTTP probe: JSON-RPC tools/list. The mcp-server
    // lane owns the exact route; this flips MOCK MODE → LIVE on any 2xx JSON.
    try {
      const ctl = new AbortController();
      const to = setTimeout(() => ctl.abort(), 1500);
      const res = await fetch(EARSHOT_SERVER_BASE + MCP_ROUTE, {
        method: "POST", signal: ctl.signal,
        headers: { "Content-Type": "application/json", "Accept": "application/json, text/event-stream" },
        body: JSON.stringify({ jsonrpc: "2.0", id: "probe", method: "tools/list", params: {} }),
      });
      clearTimeout(to);
      if (res.ok) {
        this.mode = "mcp"; this.transport = { name: "mcp" };
        setBadge(true);
        document.getElementById("transport-name").textContent = "mcp (live)";
        return true;
      }
    } catch (e) { /* stay on mock — server lane not merged yet */ }
    setBadge(false);
    return false;
  },
};
async function mcpCall(tool, args) {
  const res = await fetch(EARSHOT_SERVER_BASE + MCP_ROUTE, {
    method: "POST",
    headers: { "Content-Type": "application/json", "Accept": "application/json, text/event-stream" },
    body: JSON.stringify({ jsonrpc: "2.0", id: "c" + Date.now(), method: "tools/call",
                           params: { name: tool, arguments: args } }),
  });
  if (!res.ok) throw new Error("mcp http " + res.status);
  const text = await res.text();
  const line = text.split("\n").find((l) => l.startsWith("data:"));
  const payload = JSON.parse((line ? line.slice(5) : text).trim());
  if (payload.error) throw new Error(payload.error.message);
  return payload.result;
}
function setBadge(live) {
  const b = document.getElementById("server-badge");
  b.textContent = live ? "LIVE" : "MOCK MODE";
  b.className = "badge " + (live ? "badge-live" : "badge-mock");
  b.title = live ? "Connected to the MCP server" : "mcp-server lane not merged — mock transport (simulated)";
}
function summarizeArgs(a) {
  if (!a) return {};
  const o = {};
  if (a.item) o.item = a.item.id || a.item.title || "?";
  if (a.audience) o.audience = a.audience.map((p) => p.name).join("+");
  if (a.payload) o.payload = a.payload.id || "?";
  return o;
}
function summarizeResult(r) {
  if (!r) return r;
  if (r.level) return { level: r.level };
  if (r.audience) return { n: r.audience.length };
  if (r.delivered !== undefined) return { delivered: r.delivered };
  return { ok: true };
}
window.Earshot = { bus: EarshotBus, store, client: EarshotClient, rules, calendar };

/* ── 6. UI: presence panel ──────────────────────────────────────── */
function esc(s) { return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
function renderPresence() {
  const el = document.getElementById("presence-list");
  el.innerHTML = "";
  people.forEach((p) => {
    const row = document.createElement("div");
    row.className = "person-row";
    const pct = Math.round(p.confidence * 100);
    row.innerHTML =
      `<div><div class="person-name">${esc(p.name)}${p.note ? ` <span class="person-role">${esc(p.note)}</span>` : ""}</div>` +
      `<div class="person-role">${esc(p.role)}</div></div>` +
      `<label class="toggle" title="Simulated presence toggle for ${esc(p.name)}">` +
      `<input type="checkbox" ${p.present ? "checked" : ""} ${p.id === "priya" ? "disabled" : ""}>` +
      `<span class="track"></span></label>` +
      `<div class="conf-bar"><div class="conf-fill ${p.confidence < FAIL_CLOSED && p.confidence > 0 ? "low" : ""}" style="width:${pct}%"></div></div>` +
      `<div class="conf-val">confidence ${p.confidence.toFixed(2)}${p.confidence > 0 && p.confidence < FAIL_CLOSED ? " — FAIL-CLOSED → treated as present" : ""}</div>`;
    const box = row.querySelector("input");
    box.addEventListener("change", () => store.setPresence(p.id, box.checked));
    el.appendChild(row);
  });
}

/* ── 7. UI: tool trace + ticker + lattice strip ─────────────────── */
function addTrace({ tool, args, result, ms, via }) {
  const list = document.getElementById("tool-trace-list");
  const empty = list.querySelector(".trace-empty");
  if (empty) empty.remove();
  const d = document.createElement("div");
  d.className = "trace-card";
  d.innerHTML = `<span class="t-tool">${esc(tool)}</span><span class="t-ms">${ms}ms · ${esc(via)}</span><br>` +
    `<span class="t-res">${esc(JSON.stringify(args))} → ${esc(JSON.stringify(result))}</span>`;
  list.prepend(d);
  while (list.children.length > 30) list.lastChild.remove();
}
EarshotBus.on("tool.call", addTrace);
function ticker(html) {
  const t = document.getElementById("bus-ticker");
  t.innerHTML = "bus: " + html;
}
function latticeFlash(step) {
  document.querySelectorAll(".lattice-step").forEach((s) => s.classList.remove("hot", "level-set"));
  const el = document.querySelector(`.lattice-step[data-step="${step}"]`);
  if (el) el.classList.add("hot");
}
function latticeSetLevel(level) {
  document.querySelectorAll(".lattice-step").forEach((s) => s.classList.remove("hot"));
  const el = document.getElementById("lattice-level");
  el.textContent = "LEVEL: " + level;
  el.classList.add("level-set");
  el.style.color = ""; // color via class
  el.className = "lattice-step level-set level-" + level;
}
EarshotBus.on("wakeword.resample", () => {
  latticeFlash("wake");
  setTimeout(() => latticeFlash("snap"), 220);
});
EarshotBus.on("disclosure.decision", (p) => {
  latticeFlash("policy");
  setTimeout(() => latticeSetLevel(p.level), 260);
});

/* ── 8. The disclosure turn ─────────────────────────────────────── */
function matchIntent(utterance) {
  const u = utterance.toLowerCase();
  if (/day|schedule|calendar|appointment|events|plan/.test(u)) return calendar.slice();
  // anything else: unknown topic → P0-3 defaults HIGH
  return [{ id: "utt-" + Date.now(), title: "voice query", detail: utterance, topic: "unknown", sensitivity: null }];
}
function composeSpeech(worst, decisions) {
  const priv = decisions.filter((d) => d.level === "EXISTENCE" || d.level === "SILENT");
  if (worst === "FULL") {
    const items = decisions.map((d) => d.item.detail).join("; ");
    return `You have ${decisions.length} events today: ${items}.`;
  }
  if (worst === "ABSTRACT") {
    return `You have ${decisions.length} events today — morning, midday, and afternoon. Details depend on who's listening.`;
  }
  if (worst === "EXISTENCE") {
    return `<span class="withheld">You have ${decisions.length} events today. ` +
      `${priv.length} private item${priv.length > 1 ? "s" : ""} ha${priv.length > 1 ? "ve" : "s"} been sent to your phone.</span>`;
  }
  return `<span class="withheld">(stays silent — a private nudge was sent to your phone)</span>`;
}
function phoneCardsFor(decisions) {
  return decisions.map((d) => {
    const it = d.item;
    if (d.level === "FULL") {
      return `<div class="phone-card"><div class="pc-head">FULL · same as spoken</div>` +
        `<div class="pc-title">${esc(it.title)}</div><div class="pc-detail">${esc(it.detail)}</div>` +
        `<div class="pc-meta">sensitivity ${esc(it.sensitivity || "HIGH (P0-3)")}</div></div>`;
    }
    if (d.level === "ABSTRACT") {
      return `<div class="phone-card"><div class="pc-head">ABSTRACT · scrubbed for the room</div>` +
        `<div class="pc-title">${esc(it.title)}</div><div class="pc-detail">Timing only — details withheld from voice.</div>` +
        `<div class="pc-meta">sensitivity ${esc(it.sensitivity || "HIGH (P0-3)")}</div></div>`;
    }
    return `<div class="phone-card"><div class="pc-head">🔒 PRIVATE · sent to phone only</div>` +
      `<div class="pc-title">${esc(it.title)}</div><div class="pc-detail">${esc(it.detail)}</div>` +
      `<div class="pc-meta">${esc(d.reasons.join(" · "))}</div></div>`;
  }).join("");
}
function reasonsHtml(decisions) {
  const rs = [];
  decisions.forEach((d) => d.reasons.forEach((r) => {
    const named = r.match(/deny rule: "(.+)"/);
    rs.push(named ? `rule cited by name: <span class="rule-name">"${esc(named[1])}"</span>` : esc(r));
  }));
  return rs.length ? `<div class="reasons">⊕ ${[...new Set(rs)].join("<br>⊕ ")}</div>` : "";
}
function renderTurn(utterance, ts, audience, decisions, worst) {
  const log = document.getElementById("chat-log");
  const empty = log.querySelector(".chat-empty");
  if (empty) empty.remove();
  const t = document.createElement("div");
  t.className = "turn";
  const audNames = audience.map((p) => esc(p.name) + (p.failClosed ? " (fail-closed)" : "")).join(", ");
  t.innerHTML =
    `<div class="turn-head"><span class="level-pill level-${worst}">${worst}</span>` +
    `<span class="q">"${esc(utterance)}"</span>` +
    `<span class="ts">${ts.toLocaleTimeString()} · room: ${audNames}</span></div>` +
    `<div class="turn-cols">` +
    `<div class="col"><div class="col-label">🔊 SPEAKER HEARS</div>` +
    `<div class="speech">${composeSpeech(worst, decisions)}</div>${reasonsHtml(decisions)}</div>` +
    `<div class="col"><div class="col-label">📱 PHONE RECEIVES <span class="sim-tag">simulated</span></div>` +
    `${phoneCardsFor(decisions)}</div>` +
    `</div>`;
  log.appendChild(t);
  t.scrollIntoView({ behavior: "smooth", block: "end" });
}

async function ask(utterance) {
  utterance = (utterance || "").trim();
  if (!utterance) return;
  const ts = new Date();
  // P0-1: wake-word triggers a FRESH presence re-sample BEFORE the disclosure.
  store.resample("utterance");
  const audience = effectiveAudience();
  await EarshotClient.call("get_audience", {});
  const items = matchIntent(utterance);
  const decisions = [];
  let worst = "FULL";
  for (const item of items) {
    const d = await EarshotClient.call("decide_disclosure", { item, audience });
    const dec = { item, level: d.level, reasons: d.reasons };
    decisions.push(dec);
    worst = stricter(worst, d.level);
    EarshotBus.emit("disclosure.decision", {
      itemId: item.id, level: d.level, reasons: d.reasons,
      audience: audience.map((p) => p.id),
    });
  }
  // P0-2: withheld content pairs with a private nudge — never a dead end.
  for (const d of decisions) {
    if (d.level === "EXISTENCE" || d.level === "SILENT") {
      const card = await EarshotClient.call("send_to_second_channel", { payload: d.item });
      EarshotBus.emit("channel.card", { card });
    }
  }
  renderTurn(utterance, ts, audience, decisions, worst);
  document.getElementById("pane-left").dataset.disclosure = worst.toLowerCase();
}

/* ── 9. Wake-word button + input + scripted scenario ────────────── */
document.getElementById("btn-wakeword").addEventListener("click", (e) => {
  const b = e.currentTarget;
  b.classList.remove("pulsing"); void b.offsetWidth; b.classList.add("pulsing");
  store.resample("manual wake-word button");
});
document.getElementById("btn-ask").addEventListener("click", () => {
  const inp = document.getElementById("utterance");
  ask(inp.value); inp.value = ""; inp.focus();
});
document.getElementById("utterance").addEventListener("keydown", (e) => {
  if (e.key === "Enter") { ask(e.target.value); e.target.value = ""; }
});

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
// The DONE turn: FULL → walk-in → wake-word re-sample → EXISTENCE.
async function playScenario() {
  const btn = document.getElementById("btn-scenario");
  btn.disabled = true;
  try {
    document.getElementById("chat-log").innerHTML = "";
    ["rohan", "mil", "kids"].forEach((id) => store.setPresence(id, false));
    Object.keys(sessionFloor).forEach((k) => delete sessionFloor[k]);
    await sleep(500);
    await ask("Alexa, what's my day?");          // Priya alone → FULL
    await sleep(1400);
    store.setPresence("mil", true);             // ← the walk-in (Meera crosses the threshold)
    await sleep(1100);
    await ask("Alexa, what's my day?");          // wake-word re-sample → EXISTENCE
  } finally {
    btn.disabled = false;
  }
}
document.getElementById("btn-scenario").addEventListener("click", playScenario);

/* ── 10. Boot ───────────────────────────────────────────────────── */
renderPresence();
ticker("ready — probing MCP server…");
EarshotClient.probe().then(() => ticker("ready"));
EarshotBus.emit("presence.snapshot", { people: snapshot() });

})();
