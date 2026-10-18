# EARSHOT — product feedback

Written by the builders, for the tool vendors and for Amazon. One entry per tool
used, per the competition's feedback criterion. DRAFT — lanes refine with real
experience as they build.

---

## 1. MCP python-sdk — Streamable HTTP server module

- **What we used:** `src/mcp/server/_streamable_http_modern.py` (MCP spec
  2025-11-25) to serve all 12 EARSHOT tools over Streamable HTTP.
- **What worked:** spec-compliant server scaffold got us serving tools fast; the
  transport matched the hackathon's required baseline without custom plumbing.
- **Friction (DRAFT — server lane to confirm):** <!-- TODO(mcp-server lane): fill
  real friction here — e.g. session handling, SSE edge cases, auth-shaped holes.
  No invented complaints. -->
- **Ask:** keep the modern module's API stable across spec bumps; a migration note
  per spec version would save every builder a day.

## 2. MCP Inspector

- **What we used:** connecting to the EARSHOT server, invoking all 12 tools,
  inspecting the `ui://earshot/inspector` resource.
- **What worked:** instant visibility into tool schemas and call/response shapes —
  the fastest loop in our wave for verifying the server before the UI existed.
- **Friction (DRAFT — server lane to confirm):** <!-- TODO(mcp-server lane): fill
  real friction here — e.g. elicitation UX, session persistence, notification
  rendering. No invented complaints. -->
- **Ask:** first-class elicitation previews (see below) — approvals are the
  highest-trust interaction in the protocol and they're the least visual.

## 3. MCP elicitation (for approvals)

- **What we used:** elicitation for the `request_approval(plan)` /
  `approve(token)` flow — EXISTENCE *with a signature*, plan-hash bound.
- **What worked:** the protocol's native human-in-the-loop primitive matched our
  need exactly: a pending disclosure plan the user signs or refuses.
- **Friction (DRAFT — phone-channel lane to confirm):** <!-- TODO(phone-channel
  lane): fill real friction here — e.g. timeout semantics, cancellation paths,
  what the client actually renders. No invented complaints. -->
- **Ask:** standardize an "approval card" UI contract so hosts render approval
  requests consistently — right now every host invents its own, and users learn
  to approve blindly, which is how approval UX becomes a phishing surface.

## 4. The big one — an "audience-scoped context" API proposal for Amazon

**The problem this submission can't solve alone:** our worldsim found that the
*only* leak class in 8,918 decisions was presence lag — a visitor enters, presence
hasn't registered, the request lands in the gap. We worked around it (wake-word
triggers a fresh presence re-sample, measured to 0 leaks), but the root cause is
platform-shaped: builders get presence by polling, not by event.

**The proposal:** an Alexa+ API that scopes tool context by audience —

- `getAudience()` returning the current perceived room (members, confidence,
  arrival/departure *events*, not just snapshots);
- a context primitive where the platform itself withholds or redacts tool data
  below a requested disclosure level before the model prompt is assembled;
- a rule-registration surface so user-authored, language-blind disclosure rules
  (EARSHOT's deny-first lattice) run in the platform, not in a plugin.

**Why it belongs to Amazon, not us:** only the platform sits between the sensor
layer (presence/camera) and the model prompt — a plugin can only ever be a second
best. Apple's HomeView (Oct 2026) just proved the trunk is real with face-scoped
disclosure; the open ecosystem needs the audience-scoped equivalent, and it needs
it to fail closed on the people the camera *doesn't* recognize.

**What we'd build on it:** EARSHOT's policy engine drops in unchanged — the sim
already proved the lattice; the API just removes the polling gap and the manual
toggle, honestly.
