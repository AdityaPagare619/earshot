# EARSHOT — Master Planning Document

**Status: FROZEN** (2026-10-18, ~15:05 IST). Under Aditya's think-backward ideology lock.
Changes after this point only by his word. Execution from here is agent-management.

**Competition:** Build, Ship, Shape: Amazon Developer Hackathon — Alexa+ track.
**Deadline:** Sat Oct 24, 00:30 IST (real cutoff: Fri Oct 23 night).
**Founder interview:** 8/8 takes approved by Aditya 15:01 IST (public MIT repo; Kiro
attempt only if <2h else cut; simulated presence + real phone buzz; dark mission
control; triage order confirmed; video+repo only; AI voiceover; pregnancy scenario kept).

---

## 0. The governing ideology (Aditya's law)

**The Limitation Principle:** never solve problems instance-by-instance. Design
mechanisms that *limit entire problem classes*. EARSHOT does not solve "privacy for
Hindi speakers," then "for Spanish speakers," then "for guests" — it implements one
disclosure lattice keyed on *topics and audience*, which limits the whole class of
broadcast-leak problems at once. Every feature below must be justifiable as a
class-limiter, not an instance-fix.

**Language-blind by architecture:** this is a global competition. The lattice never
keys on tongue — only on topic sensitivity and who's listening. Users write rules in
their own language; enforcement is language-independent. No per-language anything.

**Use what's available; make things work for each other:** the phone is the private
screen the speaker lacks; the ledger built for audit becomes the explanation engine;
the cert pre-flight built for us becomes the video's proof beat. Nothing single-use.

---

## 1. The win state — 3-minute video, shot by shot

| Time | Beat | What the judge sees |
|---|---|---|
| 0:00–0:15 | **Cold open** | Black screen. "Alexa, what's my day?" → cheerfully reads the prenatal visit → record scratch, freeze: *"There were four people in that room."* Measured number: **42.4% of sensitive disclosures leak without a gateway.** |
| 0:15–0:45 | **The walk-in** | Priya (named in first 20s). "Alexa, what's my day?" → FULL card. Mother-in-law's avatar crosses the room threshold → room border shifts → card collapses live → "one private item, sent to your phone" → **phone buzzes on camera.** |
| 0:45–1:05 | **Lattice grid** | Same calendar payload, four rooms: alone / spouse / mother-in-law / kids' friends → FULL / ABSTRACT / EXISTENCE / SILENT. The class-limiter, visible in 10s. |
| 1:05–1:20 | **Notification gating** | Package notification arrives with guests present → **phone buzz instead of announcement**. The Instax scenario, live. (Most-evidenced branch; nobody demos it.) |
| 1:20–1:30 | **Rules in your language** | Deny-rule card in Hinglish + English gloss, captioned *"your language, your rules — the lattice is language-blind."* |
| 1:30–1:50 | **Explain-your-silence (mic-drop)** | "Alexa, why didn't you tell me about the appointment?" → *"At 3:42, two people were in the room, so the detail was withheld under your rule — 'never mention the clinic in front of Mom.'"* Rule cited by name. |
| 1:50–2:15 | **The architecture** | Gateway BEFORE the model: "Alexa can't leak what it was never told." Decision p99 = **0.006ms** measured (80,000x under the 500ms budget). No AI in the hot path. *"When EARSHOT doesn't know who's listening, it assumes everyone is."* Apple HomeView line: *"Apple just validated the trunk with face-scoped disclosure. We handle the people the camera doesn't know."* |
| 2:15–2:45 | **Proof it works** | World-sim: 3,000 personas, 777 households → 42.4% → **0 leaks** after the wake-word fix. Pre-flight-lite grades the repo live — our own cert harness, final 15s. |
| 2:45–3:00 | **The one-liner** | *"Alexa answers the person, but it speaks to the room."* |

**Triage (founder-approved cut order):** shrink re-disclosure → shrink language beat →
protect walk-in, lattice grid, notification gating, explain-silence. Never cut the
walk-in, the phone buzz, or the 42.4% number.

---

## 2. Problem tree — X and its branches (achievability per branch)

**Trunk X:** voice AI speaks to the room, not the person. All disclosure is broadcast.

| # | Branch | Verdict |
|---|---|---|
| 1 | Who's listening (presence, speaker, guests, kids) | ACHIEVABLE (simulated presence + manual toggle, honestly labeled; wake-word re-sample) |
| 2 | What may be said (lattice, sensitivity, rules) | ACHIEVABLE (full lattice, shipped) |
| 3 | Uncertainty (fail-closed at 0.6 confidence) | ACHIEVABLE (measured: 1.35% over-withhold) |
| 4 | Second channel (phone as private screen) | ACHIEVABLE (browser-tab phone, real buzz) |
| 5 | Memory scope (re-scope on room change; re-disclosure) | ACHIEVABLE (simulated context manager) |
| 6 | Audit & explanation (ledger, "why didn't you tell me?") | ACHIEVABLE (hash-chained ledger) |
| 7 | Multi-user identity (voice-declared + confirmation) | ACHIEVABLE |
| 8 | Unprompted speech (notification gating) | ACHIEVABLE — elevated to full demo beat (10 real incidents) |
| 9 | Cross-device consistency (Show vs Dot vs phone) | PARTIAL (device-kind aware rules; no real multi-device) |
| 10 | Recovery (undo disclosure, voice rule correction) | ACHIEVABLE |

**Honestly simulated:** real camera person-ID, real Alexa device hooks, Amazon voice
profiles. **Out of scope (stated in README):** content moderation, general smart-home
control, real purchases.

---

## 3. Tool-call inventory — 12 tools, each demanded by a branch

`decide_disclosure(item, audience, confidence)` → lattice level + reasons [2,3] ·
`set_rule(rule_nl, lang)` / `list_rules()` / `delete_rule(id)` — NL rule config, any
language [2] · `declare_speaker(name)` + confirmation [7] · `get_audience()` —
perceived room state [1] · `explain_withholding(item_id)` — ledger-backed [6] ·
`get_ledger(since)` — hash-chained [6] · `send_to_second_channel(payload)` [4] ·
`request_approval(plan)` + `approve(token)` — EXISTENCE *with a signature*; plan-hash
bound [4] · `rescope_context()` — on room change [5] · `undo_last()` [10] ·
`gate_notification(notif, audience)` — announce vs phone-only [8].

Resources: `ui://earshot/inspector` (MCP Apps lattice card). Elicitation for approvals.
Every tool emits a trace the visualizer animates — never raw terminal in the video.

---

## 4. Components (exact, nothing more)

**A. earshot-policy** — port `worldsim/policy.py`: audience-risk, allow/deny
deny-first precedence, fail-closed 0.6, lattice. The sim-tested code ships.
**B. MCP server** — Streamable HTTP, MCP spec 2025-11-25: the 12 tools above +
`ui://earshot/inspector` + wrapped fixture upstreams (calendar, bank, messages —
honestly labeled).
**C. Simulator web client** — the visual mission control (see §5). Labeled simulated.
**D. Phone second channel** — web page; receives withheld cards + approvals; real buzz.
**E. Pre-flight-lite** — cert-style harness grading EARSHOT itself (p95, fail-closed
coverage, monotonic-downward). Video's last 15s.
**F. Regression rig** — `worldsim/` in CI: every policy change re-runs the 3,000-person
gauntlet before merge.

---

## 5. Visual system spec — dark mission control, never terminal

Three panes, near-black AMOLED canvas, glowing accents:
**LEFT — the room:** live floor-plan; avatars glide in/out; room border shifts color
with disclosure state. The walk-in is *visual*.
**CENTER — the conversation:** what the speaker hears vs what the phone receives,
side by side.
**RIGHT — the inspector:** the lattice decision as a glowing pipeline
(wake-word → fresh snapshot → policy → level); tool calls as animated cards.
Inspiration sprint: Dribbble/Awwwards dark dashboards, war-room UIs, network-ops
visualizations. Terminal stays in the repo; the video never shows it.

---

## 6. Sim-driven hard requirements (P0 — non-negotiable)

Source: `worldsim/FINDINGS.md` (8,918 decisions, 5,866 sensitive).
**P0-1:** wake-word triggers fresh presence re-sample before every disclosure
(measured: residual leaks → 0). **P0-2:** SILENT pairs with a private nudge —
never a dead end (certification). **P0-3:** unknown topics default HIGH.
**P1:** explain-silence cites the winning rule by name (reasons piped from engine).
**P1:** disclosure monotonic-downward by voice (voice narrows, never widens).
**P2:** keep fail-closed threshold 0.6 (1.35% annoyance, measured).

---

## 7. Community evidence → plan consequences

Source: `research/COMMUNITY_EVIDENCE.md`. Branch 8 elevated (Instax anchor — README
"real incidents" section: Instax 2019, Portland 2018, cross-hear deliveries).
Pitch carries the Apple HomeView line (§1, 1:50–2:15). Demo-time: branches 8+2
heaviest; 5+6 keep beats; kids in README threat model only (thin evidence, sensitive).

---

## 8. Advanced/bonus stacking (Devpost-verified 18 Oct)

Track core: MCP Apps inspector card ✓, elicitation for approvals ✓, Streamable HTTP
✓. AWS Builder: **Kiro attempt only** — hard box of 2 hours, cut on smell of creep
(Bedrock/AgentCore would be theater against our deterministic architecture — refused
on principle). Open Source: public MIT repo = the contribution. Product feedback per
tool; friction log from minute one (sim-driven entries already banked: presence-lag
class, "can't script what Alexa says" → gateway architecture).

---

## 9. Hard-rules checklist

Deadline Oct 24 00:30 IST (real cutoff Fri night) · MCP 2025-11-25+ Streamable HTTP ·
repo CALLS the tech in code · video <3:00, public YouTube, English · friction log
(+10%) · one track prize + one mini prize stackable · feedback per tool · public repo
+ MIT license · office hours #2 Mon Oct 19 9:30pm IST (ask: 2026-07-28 acceptability;
MCP App rendering in sim host).

---

## 10. Day-by-day (Sun Oct 18 → Fri Oct 23)

**Sun:** repo + worktrees + agent wave launch; UI inspiration sprint; policy port.
**Mon:** MCP server + 12 tools; simulator shell; office hours 9:30pm IST.
**Tue:** mission-control UI (room viz, inspector pipeline); phone channel + buzz.
**Wed:** notification gating + memory re-scope + ledger/explain; pre-flight-lite.
**Thu:** full run-throughs; worldsim regression green; video shoot (AI voiceover).
**Fri:** video edit <3:00; README (real incidents, Apple line, architecture);
friction log; product feedback; Kiro attempt (2h box); SUBMIT.

## 11. Scope lock

Components A–F + 12 tools + 3-pane UI. Anything else needs Aditya's word.
Cut order if late: re-disclosure, language beat, phone-approval detail —
never the walk-in, lattice grid, notification gating, explain-silence, 42.4%.

## 12. Open risks

Presence is simulated (honestly labeled; toggle fallback) · no real Alexa device ·
rule language as text, not voice-recognized · Kiro may not land in 2h (cut cleanly).
