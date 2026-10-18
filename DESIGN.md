# DESIGN.md — lane video-readme (2026-10-18)

Owner: video-readme lane (single-threaded). Committee: none — docs lane.

## Problem
The submission's written surface (README + friction log + product feedback + video
checklist) must make a judge believe two things in <3 min of reading: (1) trunk X is a
real wound with a body count (community incidents, 42.4% measured leak rate), and (2)
EARSHOT is an honest, deterministic, user-ruled answer — no simulated-toy claims.

## What goes where
- **README.md** — one-liner, problem (trunk X + real incidents, cited), architecture
  (gateway BEFORE the model), disclosure lattice table, Apple HomeView line, honest
  simulation boundaries, 12-tool inventory, repo layout, run instructions. TODO slots
  where build lanes will fill numbers/screenshots; every claim about measured numbers
  points at worldsim/FINDINGS.md or preflight JSON.
- **FRICTION_LOG.md** — the three banked sim-driven entries (presence-lag → wake-word
  fix; "can't script what Alexa says" → gateway architecture; partner-gated toolkit →
  honest simulator) in the required format. Lanes append.
- **PRODUCT_FEEDBACK.md** — per-tool feedback drafts: MCP python-sdk (Streamable HTTP
  server module), MCP Inspector, elicitation. Plus the headline: the
  "audience-scoped context" API proposal for Amazon (the ask Amazon must hear).
- **VIDEO_CHECKLIST.md** — MASTER_PLAN §1 shot list as a shoot checklist, in order,
  with the founder-approved triage/cut order so the shoot protects the uncuttable
  beats (walk-in, phone buzz, 42.4%, lattice grid, notification gating,
  explain-silence) first.

## What I will NOT claim
- No "tested on a real Echo/Alexa+ device." Simulation is labeled in every doc.
- No prevalence claims about incidents (COMMUNITY_EVIDENCE says no prevalence
  claims; several items are second-hand/paraphrase — never presented as proof).
- No real-person-ID (camera presence is simulated + manual toggle, honestly labeled).
- No "we ship X" — it's a skeleton with TODO slots; build lanes fill in.
- No kids anecdotes in the video path; kids stay in the README threat model only
  (thin evidence, sensitive).
- Bedrock/AgentCore are refused on principle, not "planned later."

## Rejected framings
- **"AI that protects your privacy."** Rejected: there is no AI in the hot path.
  The pitch is the determinism — rules, not vibes. Anything claiming AI
  understanding of privacy invites exactly the scrutiny we can't survive.
- **"Enterprise/compliance-first pitch."** Rejected: this is a household wound;
  the Incidents section (Instax Christmas surprise) is the hook, not a SOC-2
  checkbox.
- **"We beat Apple HomeView."** Rejected: we validate alongside it — Apple proved
  the trunk; EARSHOT handles the people the camera doesn't know. Rival framing
  loses the point (fail-closed for unrecognized presence is our differentiator).
- **"Anti-Alexa."** Rejected: we're a gateway plugin for Alexa+, not a rival
  assistant. The architecture is additive to the ecosystem, which is what the
  Alexa+ track rewards.

## Pre-mortem (assume the README lost us the prize)
1. The judge read "42.4% → 0 leaks" as LLM-hallucinated claims because the README
   didn't pin every number to a repo path — FIX: every measured number cites
   worldsim/FINDINGS.md or preflight JSON directly.
2. The "honest simulation" boundaries were a footnote and the judge felt sold a
   real device — FIX: boundaries get their own ## section above the tool inventory,
   labeled in CAPS where they matter.
3. FRICTION_LOG became a complaint dump that made us look stuck — FIX: every entry
   closes with the workaround that already shipped (this log shows we move).
