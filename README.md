# EARSHOT — a room-aware disclosure gateway for Alexa+

**Alexa answers the person, but it speaks to the room.**

Every other AI whispers to a private screen. An Echo is a loudspeaker in a shared
room. EARSHOT is a self-hosted MCP server (spec 2025-11-25+, Streamable HTTP) that
sits in front of your calendar, bank, messages and health tools and grades every
disclosure by *who's listening* — FULL / ABSTRACT / EXISTENCE / SILENT — through a
deterministic rules engine with no AI in the hot path.

Because Alexa writes its own sentences from tool data, privacy is enforced *before*
the model ever sees the data. **Alexa can't leak what it was never told.**

Built for the **Build, Ship, Shape: Amazon Developer Hackathon** (Alexa+ track).

---

## The problem — trunk X: voice AI speaks to the room, not the person

All disclosure from a voice assistant is broadcast. The person who asked is not
necessarily the only person in the room. Everything else is a branch off that trunk:

- **Who's listening** — presence, speakers, guests, kids.
- **What may be said** — sensitivity lattice, your rules.
- **Uncertainty** — what happens when the gateway isn't sure who's there.
- **Second channel** — the phone is the private screen the speaker lacks.
- **Memory scope** — re-scoping when the room changes.
- **Audit & explanation** — "why didn't you tell me?"
- **Multi-user identity** — voice-declared, confirmed.
- **Unprompted speech** — notifications that announce themselves.
- **Cross-device consistency** — Show vs Dot vs phone.
- **Recovery** — undo a disclosure, correct a rule by voice.

Without a gateway, our household simulation measured **42.4% of sensitive
disclosures leaking to untrusted ears** (2,487 HIGH leaks out of 5,866 sensitive
requests — see [Honest numbers](#honest-numbers)). "There were four people in that
room" happens nearly half the time.

## Real incidents

Judges trust a problem with a body count. All incidents from our community-evidence
sweep (`~/workspace/amazon-hackathon/research/COMMUNITY_EVIDENCE.md`); no prevalence
claims are made — these are documented cases, not statistics.

- **Instax Christmas surprise spoiled (UK, Dec 2019).** Lizzy Nuttall ordered a £130
  Instax camera; a child was in the kitchen when the Echo announced "Parcel arriving
  — Instax." The daughter covered her ears; the surprise was ruined *despite
  Amazon's own policy of withholding gift item names*. Our demo's notification-gating
  beat is built on this incident. (via phonearena.com)
- **Portland family (May 2018).** An Echo recorded a private conversation and *sent
  the audio* to the husband's employee — a wake-word false positive followed by a
  misheard "send message." The extreme trunk case. (wcmu.org, gizmodo.com)
- **Cross-hear deliveries (UK Amazon forum).** A poster asked how to stop his
  daughter's delivery announcements playing on his devices and vice versa; Amazon
  staff answered that in an Amazon Household there is *no way to unlink* —
  announcements are shared by design. (uk.amazonforum.com)
- **Incoming calls announced house-wide (Apr 2024).** "The entire house knows I have
  a call coming in AND who is calling." (amazonforum.com)
- **Bedroom Dot announcing appointments despite opt-out (Apr 2020).** Verbal
  reminders were disabled in the app; the Dot kept announcing appointments and
  orders aloud. Staff answer: use Do Not Disturb. (amazonforum.com)
- **Other adult's packages can't be silenced (2021–2025).** Spoken notifications
  for the *other* adult's packages despite voice profiles; per-person silencing is
  impossible — only all-or-nothing. Dec 2025: "Package delivered" leaking from a
  son's Echo Show 5. (amazonforum.com)
- **Voice purchase confirmations can't be muted.** Disabling shopping notifications
  stops ship/deliver announcements, but Alexa *still verbally confirms every voice
  purchase at order time*. (aeanet.org)
- **Spoken purchase code.** The 4-digit voice-purchase code "will be spoken aloud,
  so you still won't want to say it in front of anyone you don't trust."
  (wukihow.com)

And the industry just moved: **Apple's HomeView (Oct 2026)** recognizes up to six
household members by face and keeps messages, calendar and reminders separate, with
personal content gated on the paired, recently-unlocked iPhone. **Apple just
validated the trunk with face-scoped disclosure. We handle the people the camera
doesn't know.** EARSHOT is the open, user-ruled answer — and the only one that
fail-closes on guests and strangers, the audience Apple's model has no answer for.

## The architecture — the gateway sits BEFORE the model

```
                ┌─────────────────────────────────────────┐
  "Alexa,       │            EARSHOT gateway               │
  what's my      │  wake word → fresh presence re-sample    │
  day?" ──────► │      → policy engine (deterministic)     │ ──► only approved data
                │      → FULL / ABSTRACT / EXISTENCE / SILENT
                └─────────────────────────────────────────┘
                                  │
                          phone second channel
                      (withheld cards + approvals)
```

Amazon's design rules forbid scripting Alexa's speech — you can only influence what
she says through the data your tools return. So EARSHOT doesn't try to control her
words. It controls her **information**. The MCP server intercepts every tool call
between Alexa+ and your upstreams (calendar, bank, messages, health), grades it
against the current room audience, and returns only what the lattice allows.
**Alexa can't leak what it was never told.**

There is **no AI in the hot path** — the decision is a deterministic rules engine
(deny-first precedence, fail-closed at 0.6 presence confidence). Measured decision
p99: **0.006 ms** — roughly 80,000× under the 500 ms Alexa budget. When EARSHOT
doesn't know who's listening, it assumes everyone is.

Three principles govern everything:
1. **Language-blind by architecture.** The lattice keys on topic sensitivity and
   who's listening — never on tongue. Users write rules in their own language;
   enforcement is language-independent.
2. **Monotonic downward by voice.** Voice commands can only *narrow* disclosure,
   never widen it. (Widening requires the phone/second channel.)
3. **Unknowns fail closed.** Unknown topics default HIGH; low presence confidence
   (< 0.6) whitens disclosure. Conservative is cheap — measured at 1.35% of
   low-stakes moments.

## The disclosure lattice

The same payload, four rooms:

| Audience | Level | Example — "prenatal checkup, 3:42pm, Dr. Rao" |
|---|---|---|
| Alone | FULL | Full calendar detail on the speaker. |
| Spouse (trusted) | ABSTRACT | "You have a medical appointment at 3:42pm." |
| Mother-in-law (untrusted) | EXISTENCE | "One private item — sent to your phone." → phone buzzes. |
| Kids' friends | SILENT | Nothing spoken. A private nudge goes to the phone. |

Deny-rules cap by topic regardless of trust (e.g. *"never mention the clinic in
front of Mom"* → SILENT whenever that audience is present). SILENT always pairs
with a phone nudge — never a dead end.

## Honest simulation boundaries

We built honestly, and we say so plainly:

- **Presence is simulated** — a room-state model plus a manual presence toggle,
  honestly labeled in the UI. There is no real camera person-ID in this build.
- **No real Alexa device** — the MCP Toolkit and Category SDK are select-partners
  only; as hackathon participants we had no access path, so we demo through an
  honest web simulator acting as a real MCP client (a permitted path).
- **All fixture upstreams** (calendar, bank, messages) return data labeled
  `fixture:true` — nothing here is a real inbox or a real bank account.
- **Rules are entered as text**, not voice-recognized (the language layer is the
  demo host's; our lattice is language-blind anyway).
- Sim numbers below come from a **behavioral simulation** — 3,000 parameterized
  personas through the real deterministic policy engine — not an LLM society
  (deliberately: you don't need emergent behavior to test a rules engine, you need
  coverage). See `~/workspace/amazon-hackathon/worldsim/FINDINGS.md`.

Out of scope for this build: content moderation, general smart-home control, real
purchases. Kids appear in the README threat model only (evidence too thin and too
sensitive for the demo path).

## Honest numbers

From `worldsim/FINDINGS.md` (8,918 decisions, 5,866 sensitive, 777 households):

| Metric | Without gateway | With EARSHOT |
|---|---|---|
| Sensitive-disclosure leak rate | **42.4%** | **0%** (after wake-word fix; 0.09% before) |
| Over-withholding (fail-closed cost) | — | 1.35% of low-stakes moments |
| Voice override attempts ("just tell everyone") | — | 100% resisted (1,117 attempts) |
| Decision p99 | — | 0.006 ms |

The sim also found the failure mode that mattered: **presence lag on new
arrivals** — a visitor enters, presence hasn't registered, the request lands in
the gap. The fix: the wake word triggers a **fresh presence re-sample before
every disclosure**. Measured: residual leaks → 0.

<!-- TODO(build-lanes): paste preflight-lite JSON summary here after Wed run. -->
<!-- TODO(build-lanes): add simulator screenshot (3-pane mission control) after Tue. -->
<!-- TODO(build-lanes): add video URL here after Fri edit. -->

## The 12 tools

Every tool exists because a branch of the problem tree demanded it:

| Tool | Does | Branch |
|---|---|---|
| `decide_disclosure(item, audience, confidence)` | lattice level + reasons | what's said, uncertainty |
| `set_rule(rule_nl, lang)` | natural-language rule, any language | what's said |
| `list_rules()` / `delete_rule(id)` | rule management | what's said |
| `declare_speaker(name)` + confirmation | voice-declared identity | multi-user |
| `get_audience()` | perceived room state | who's listening |
| `explain_withholding(item_id)` | ledger-backed, cites winning rule by name | audit |
| `get_ledger(since)` | hash-chained audit trail | audit |
| `send_to_second_channel(payload)` | withheld card to the phone | second channel |
| `request_approval(plan)` + `approve(token)` | EXISTENCE *with a signature*; plan-hash bound | second channel |
| `rescope_context()` | re-scope memory on room change | memory scope |
| `undo_last()` | take back the last disclosure | recovery |
| `gate_notification(notif, audience)` | announce vs phone-only | unprompted speech |

Resources: `ui://earshot/inspector` (MCP Apps lattice card). Elicitation for approvals.
Every tool emits a trace the visualizer animates — no terminal in the video.

## Repo layout

```
earshot/
├── policy/        # the deterministic rules engine (sim-tested, ships)
├── server/        # MCP server, Streamable HTTP, 12 tools + inspector resource
├── fixtures/      # Priya-household datasets, every response labeled fixture:true
├── simulator/     # web mission control: room state, manual presence toggle,
                   # wake-word re-sample button — all labeled simulated
├── phone/         # second-channel web page: withheld cards + approvals, real buzz
├── preflight/     # cert-style harness grading the repo itself
└── ui/            # visual tokens (AMOLED dark, glow accents)
docs/
├── MASTER_PLAN.md     # frozen build plan (reference copy)
├── FRICTION_LOG.md    # every real friction, task/expected/actual/workaround
├── PRODUCT_FEEDBACK.md# per-tool feedback + the audience-scoped-context API ask
└── VIDEO_CHECKLIST.md # the 3-minute shot list as a shoot checklist
```

## How to run

<!-- TODO(build-lanes): fill exact commands after lanes land (policy tests, server
     boot, simulator URL, preflight run). Keep to copy-paste form. -->

```bash
# placeholder — replaced by exact commands as lanes merge
pytest policy/                     # sim-tested engine regression
python -m earshot.server          # MCP server (streamable-http)
open http://localhost:PORT/       # simulator mission control
```

## Friction & feedback

- [`FRICTION_LOG.md`](docs/FRICTION_LOG.md) — everything that fought us, with the
  workaround that shipped. (+10% competition criterion, seeded from minute one.)
- [`PRODUCT_FEEDBACK.md`](docs/PRODUCT_FEEDBACK.md) — what we'd tell the tool
  vendors, and the one API Amazon should build: **audience-scoped context**.

## License

MIT. See [LICENSE](LICENSE).
