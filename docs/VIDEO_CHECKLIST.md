# EARSHOT — video shoot checklist (MASTER_PLAN §1, shot by shot)

Target: <3:00, public YouTube, English. AI voiceover. Dark mission control —
**no terminal in the video path** (terminal stays in the repo).

Shoot order follows the §1 sequence. Triage cuts (founder-approved) are marked per
beat; when time bleeds, cut in triage order and protect the uncuttable.

**Never cut:** the walk-in, the phone buzz, the 42.4% number, the lattice grid,
notification gating, explain-silence.

---

## Shot 1 — Cold open (0:00–0:15) [NEVER CUT]
- [ ] Black screen. "Alexa, what's my day?" → cheerfully reads the prenatal visit.
- [ ] Record scratch, freeze frame: *"There were four people in that room."*
- [ ] On-screen number: **42.4% of sensitive disclosures leak without a gateway.**
- Props: black slate, scratch SFX, freeze-frame graphic.

## Shot 2 — The walk-in (0:15–0:45) [NEVER CUT — shoot first]
- [ ] Priya named in the first 20s. "Alexa, what's my day?" → FULL card.
- [ ] Mother-in-law's avatar crosses the room threshold → room border shifts color.
- [ ] Card collapses live → "one private item, sent to your phone."
- [ ] **Phone buzzes on camera** (real buzz — vibration API / audio).
- Depends on: room-viz lane, simulator lane, phone-channel lane. Rehearse the walk-in
  moment until the avatar-glide timing feels physical.

## Shot 3 — Lattice grid (0:45–1:05) [NEVER CUT]
- [ ] Same calendar payload, four rooms side by side:
  alone → FULL / spouse → ABSTRACT / mother-in-law → EXISTENCE / kids' friends →
  SILENT.
- [ ] The class-limiter visible in 10 seconds. Four-room grid graphic ready as a
  static fallback.
- Depends on: inspector-ui lane (four-room lattice grid view).

## Shot 4 — Notification gating (1:05–1:20) [NEVER CUT]
- [ ] Package notification arrives with guests present → **phone buzz instead of
  announcement.**
- [ ] The Instax scenario, live — caption the 2019 incident as the anchor
  ("the most-evidenced branch; nobody demos it").
- Depends on: notify-ledger lane, phone-channel lane.

## Shot 5 — Rules in your language (1:20–1:30) [CUT ORDER: 2nd]
- [ ] Deny-rule card in Hinglish + English gloss.
- [ ] Caption: *"your language, your rules — the lattice is language-blind."*
- Shrink first if the edit runs long (triage order: re-disclosure → language →
  protect the rest).

## Shot 6 — Explain-your-silence (1:30–1:50) [NEVER CUT — mic-drop]
- [ ] "Alexa, why didn't you tell me about the appointment?"
- [ ] Answer cites the rule by name: *"At 3:42, two people were in the room, so the
  detail was withheld under your rule — 'never mention the clinic in front of
  Mom.'"*
- Depends on: notify-ledger lane (explain_withholding pipes reasons through).

## Shot 7 — Architecture (1:50–2:00) [NEVER CUT]
- [ ] Gateway BEFORE the model diagram: "Alexa can't leak what it was never told."
- [ ] Measured number on screen: decision p99 = **0.006 ms** (80,000× under the
  500 ms budget). No AI in the hot path.
- [ ] Line delivered: *"When EARSHOT doesn't know who's listening, it assumes
  everyone is."*
- [ ] Apple HomeView line: *"Apple just validated the trunk with face-scoped
  disclosure. We handle the people the camera doesn't know."*

## Shot 8 — Proof it works (2:00–2:30) [NEVER CUT]
- [ ] World-sim numbers: 3,000 personas, 777 households → 42.4% → **0 leaks**
  after the wake-word fix.
- [ ] Pre-flight-lite grades the repo live — our own cert harness.
- Depends on: preflight lane (video-ready 15s run). If preflight slips, substitute
  the static results graphic — do NOT drop the beat.

## Shot 8b — The unanticipated case (2:30–2:45) [NEVER CUT — founder directive 18 Oct]
- [ ] On camera, an unrehearsed broadcast-privacy problem is named
  (e.g. "my roommate can't hear about my therapy").
- [ ] A rule is written LIVE in plain language via the existing `set_rule` tool —
  no new components, no rehearsal. `decide_disclosure` handles it immediately.
- [ ] Surface: MCP Inspector against the live server
  (`python -m earshot.server.server --port 8000`, Inspector → Streamable HTTP →
  `http://127.0.0.1:8000/mcp`). Verified 18 Oct: the verbatim phrasing
  "my roommate Rohan can't hear about my therapy" parses → enforced →
  therapy item goes SILENT with Rohan present, FULL alone.
- [ ] Lattice visibly re-resolves; the point lands: the system expresses
  unanticipated cases, not just rehearsed ones. Answers the judge's "what about X?"
- [ ] 15 seconds max. If the live call stumbles, the fallback is the same beat
  with the rule pre-typed but still executed live — never a mock.

## Shot 9 — The one-liner (2:45–3:00) [NEVER CUT]
- [ ] *"Alexa answers the person, but it speaks to the room."*
- [ ] End card: repo URL + MIT.

## Triage / cut order (founder-approved, 18 Oct directive)
1. Shrink re-disclosure (memory re-scope detail).
2. Shrink the language beat (Shot 5).
3. Cut phone-approval detail if time presses.
4. Protect in this order: walk-in → lattice grid → notification gating →
   explain-silence → phone buzz → 42.4% number → unanticipated-case beat.

## General shoot rules
- Re-shoot beats in sequence 2→4→6→7→8 (the dependency-heavy beats) before
  polishing 1, 5, 9.
- Every animated beat must exist as a static graphic fallback (lattice grid,
  architecture diagram, sim numbers).
- AI voiceover recorded last, against the locked edit — never before.
- No raw terminal on screen, ever. Tool calls appear as animated cards.
