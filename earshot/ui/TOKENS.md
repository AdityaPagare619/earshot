# EARSHOT design-token contract — `earshot/ui/TOKENS.md`

**Version:** 1.0.0 · **Status: FROZEN** (2026-10-18) · **Owner:** lane ui-inspiration
**Consumers:** lanes simulator-shell, room-viz, inspector-ui, phone-channel —
code against these names BLIND. The machine-readable mirror is
`earshot/ui/tokens.css` (`:root` block); names below and in `tokens.css` are
identical by construction (checked by `earshot/ui/check-tokens.py`).

## 0. Philosophy (the 10-second rule)

Every video beat gets ~10s of judge attention. Color is the fastest channel we
have, so **glow is semantic, never decorative**: every glowing element must cite
a lattice level (`FULL/ABSTRACT/EXISTENCE/SILENT`) or a P0 operational state
(arrival, fail-closed, signature approval). If you can't name the rule the glow
cites, remove the glow. AMOLED near-black canvas; dense where the operator needs
density (pipeline, presence), calm everywhere else. Body text is NEVER
monospace — mono is for hashes, trace IDs and micro-labels only; the video path
never shows a terminal.

---

## 1. Neutral scale — canvas → panes → cards, one direction

| Token | Value | Usage |
|---|---|---|
| `--ear-canvas` | `#050507` | Page background. True-near-black for AMOLED |
| `--ear-canvas-2` | `#0A0A10` | Recessed wells (floor-plan pit, lattice-grid cells) |
| `--ear-surface` | `#101015` | Pane backgrounds |
| `--ear-surface-2` | `#17171F` | Cards on panes |
| `--ear-surface-3` | `#1E1E28` | Hover / raised cards only |
| `--ear-line` | `#262633` | Structural hairlines (card borders, dividers) |
| `--ear-line-strong` | `#343444` | Active/hovered structural edges |
| `--ear-text` | `#F4F4F7` | Primary text (~19:1 on canvas) |
| `--ear-text-dim` | `#A8A8B8` | Secondary text (~7:1 on surface) |
| `--ear-text-faint` | `#646472` | Micro-labels only (below body-text contrast floor) |
| `--ear-veil` | `rgba(5,5,7,.72)` | Scrim over floor-plan edges / overlays |

Rule: surfaces only ever get *lighter* toward the viewer. Never put a card
darker than its pane.

---

## 2. Semantic glow palette — the only colors allowed to glow

| Token | Value | Meaning | USE | NEVER |
|---|---|---|---|---|
| `--ear-level-full` | `#34F5A2` | FULL disclosure — open mic, say it all | Full cards, room border when alone/trusted, speaker ring | warnings, anything negative |
| `--ear-level-abstract` | `#FFC24B` | ABSTRACT — summarized, details stripped | Abstract cards, lattice-grid "spouse" cell | fail-closed states (that is orange, not amber) |
| `--ear-level-existence` | `#8B7CFF` | EXISTENCE — "one item exists", content withheld | Existence cards, approval-request accents | body text, idle UI |
| `--ear-level-silent` | `#FF4D6D` | SILENT — withheld, sent to phone | Silent cards, room border when a non-listener is present | the LIVE indicator (see below) |
| `--ear-presence` | `#FFFFFF` | Walk-in arrival pulse; LIVE dot; phone buzz flash | Arrival ring (once, 1.6s), LIVE dot + label | persistent fills — white is a signal, not a theme |
| `--ear-lowconf` | `#FF8A3D` | Fail-closed lockdown — confidence < 0.6 (P0-2) | Lockdown banner, dashed low-confidence presence rings | disclosure-level badges |
| `--ear-approve` | `#4FD8FF` | Plan-hash signature approval (EXISTENCE-with-signature) | Phone approve button, signature hash chip | anywhere else — cyan is *earned* by a signature flow |

Room-state language (§4) is just these four levels + idle + lockdown; the
amber/orange distinction is load-bearing: **amber = ABSTRACT level,
orange = fail-closed lockdown. Never substitute.**

---

## 3. Glow shadows — pre-mixed, blind-codeable

```
--ear-glow-full:      0 0 18px rgba(52,245,162,.32), 0 0 48px rgba(52,245,162,.12)
--ear-glow-abstract:  0 0 18px rgba(255,194,75,.32),  0 0 48px rgba(255,194,75,.12)
--ear-glow-existence: 0 0 18px rgba(139,124,255,.34), 0 0 48px rgba(139,124,255,.13)
--ear-glow-silent:    0 0 18px rgba(255,77,109,.34),  0 0 48px rgba(255,77,109,.13)
--ear-glow-presence:  0 0 14px rgba(255,255,255,.45)
--ear-glow-lowconf:   0 0 18px rgba(255,138,61,.36),  0 0 48px rgba(255,138,61,.14)
--ear-glow-approve:   0 0 18px rgba(79,216,255,.36),  0 0 48px rgba(79,216,255,.14)
```

Rules: **one glow per element, max one breathing element per pane** (breathing =
the `--ear-dur-breathe` pulse, reserved for the *currently decisive* state —
e.g. the live room border). Glowing fills are forbidden; glow lives on borders
and rings, never on backgrounds. The LIVE indicator is a white dot
(`--ear-presence`) + micro label, never red — red is taken by SILENT.

---

## 4. Room border color language — the walk-in is visual

Every room exposes exactly one dynamic variable:

```
--ear-room-state: <one of the level accents>;   /* default: --ear-room-idle */
--ear-room-idle: #3A3A48;                        /* no active disclosure */
```

Behavior (lane room-viz implements; simulator-shell sets):
- Border is 2px, radius `--ear-r-lg`, `box-shadow` = matching `--ear-glow-*`.
- On disclosure-level change: **crossfade the border color over 400ms**
  (`--ear-dur-fast`), then hold. No blinking, no shake — the shift *is* the
  event, and the video's walk-in beat depends on it reading at 10s.
- Arrival (avatar crosses threshold): white pulse ring
  (`--ear-glow-presence`, 1.6s, once) *inside* the room, then border settles to
  the new level color.
- Fail-closed (`--ear-lowconf`): dashed 2px border in `--ear-lowconf` +
  lockdown banner — this OVERRIDES the level border until confidence recovers.
- Never show a room with two state colors at once. `--ear-room-state` is the
  single source of truth; lanes never branch on color directly.

Semantics: mint border = "say it all" · amber = "summarized" ·
violet = "existence only" · rose = "withheld, on your phone" · orange dashed =
"not sure, locked down".

---

## 5. Type

```
--ear-font-sans: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif
--ear-font-mono: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace

--ear-fs-hero:     64px / 1.05 / 700   /* the 42.4% cold-open number, stats only */
--ear-fs-display:  34px / 1.15 / 700   /* pane titles in video framing */
--ear-fs-h1:       24px / 1.2  / 650
--ear-fs-h2:       17px / 1.3  / 600
--ear-fs-body:     14px / 1.5  / 400
--ear-fs-caption:  12px / 1.45 / 400   /* rationale lines, trace metadata */
--ear-fs-micro:    10.5px / 1.3 / 600  /* labels: uppercase, letter-spacing .12em */
```

Mono is allowed ONLY for: plan hashes, ledger hash chains, trace IDs, timestamps,
confidence readouts, and `--ear-fs-micro` labels. Body/prose is always sans.

---

## 6. Spacing & radius

```
--ear-s1: 4px  --ear-s2: 8px  --ear-s3: 12px  --ear-s4: 16px
--ear-s5: 20px --ear-s6: 24px --ear-s8: 32px  --ear-s12: 48px
--ear-gap: 16px                               /* pane-to-pane gutter */

--ear-r-sm: 6px   /* chips, tiny badges */
--ear-r-md: 10px  /* cards, buttons */
--ear-r-lg: 16px  /* panes, room outlines */
--ear-r-xl: 24px  /* hero cards, phone frame */
--ear-r-pill: 999px /* avatar chips, presence pills, LIVE badge */
```

---

## 7. Motion — how things move (the crafted part)

```
--ear-dur-instant: 120ms
--ear-dur-fast:    240ms   /* hovers, border crossfades (room border = 400ms, see §4) */
--ear-dur-glide:   480ms   /* avatars, card collapse */
--ear-dur-breathe: 2400ms  /* the single breathing glow per pane */
--ear-ease-glide:  cubic-bezier(.22,.8,.24,1)
--ear-ease-snap:   cubic-bezier(.16,1,.3,1)
```

Per-element rules (video legibility):
- **Avatars glide** — `transform: translate()` over `--ear-dur-glide` with
  `--ear-ease-glide`. People move through space; they never fade-pop in place.
- **Walk-in** — arrival pulse (1.6s, once) → border crossfades (400ms) →
  disclosure card collapses.
- **Pipeline cards** (inspector) — stagger-in: 80ms stagger, 300ms slide+fade
  with `--ear-ease-snap`, wake-word → snapshot → policy → level, in causal order.
- **Withheld cards** (center pane) — collapse to the phone card over 420ms
  (height + opacity, `--ear-ease-glide`): the *narrowing* is visible, never a cut.
- **Lattice narrowing** (voice re-query) — level badges step DOWN the ladder
  (mint→amber→violet→rose); a voice answer never widens (P1 monotonic-downward).
- **Breathing** — reserved for the decisive live state only, one per pane.
- Honor `prefers-reduced-motion`: reduce to opacity crossfades, no travel.

---

## 8. Avatar & presence semantics (lanes 4/5)

- **Avatar chip:** 36px circle, `--ear-r-pill`, initials or glyph, surface-2 fill,
  name in `--ear-fs-caption` below/beside.
- **Speaker** (who Alexa answers): double ring in current `--ear-room-state` +
  "SPEAKING" micro label. Exactly one speaker at a time.
- **Present:** neutral `--ear-line-strong` ring.
- **Low-confidence presence** (< 0.6): dashed `--ear-lowconf` ring + "?" badge —
  pairs with the lockdown banner (P0-2), never shown as confidently present.
- **Arriving:** white pulse ring, once; then settles to present ring.
- **Leaving:** glides to the room edge over `--ear-dur-glide`, then removed.
- Confidence readout (mono, micro): `0.93` style, beside the name.

---

## 9. Lattice-grid card rules (lane 6 — the 0:45 lattice beat)

Four cells (alone / spouse / mother-in-law / kids' friends), one per level.
Each cell: 2px border in its level accent + matching `--ear-glow-*` (static, not
breathing — four breathers would be noise), big level word (`--ear-fs-h1`) in the
accent, one rationale line (`--ear-fs-caption`, `--ear-text-dim`), mono trace chip
(`decide_disclosure · 0.006ms`). Grid on `--ear-canvas-2`. The *same payload*
heads all four cells — that sameness is the class-limiter made visible.

---

## 10. Layout

```
--ear-layout-pane-left:   360px   /* room floor-plan */
--ear-layout-pane-center: 1fr     /* conversation: speaker vs phone */
--ear-layout-pane-right:  400px   /* lattice inspector */
--ear-maxw: 1560px
```

Center pane is split: LEFT "what the room hears", RIGHT "what your phone got"
(labeled `SIMULATED SECOND CHANNEL`). The asymmetry — room card collapsing while
the phone card holds — is the product's thesis in one glance.

---

## 11. Contract stability

- Names are frozen at v1.0.0. New tokens get added; existing names/values don't
  change without a minor-version bump and a note here. Downstream lanes pin
  behavior to *names*, never hex.
- Reserved namespace: `--ear-*`. Lanes must not invent parallel palettes; a new
  semantic color needs a usage-rule row in §2, approved by the lane owner.
- `tokens.css` is generated from this file's tables — `check-tokens.py` fails
  the lane if a mockup or lane file uses an `--ear-*` name not defined there.
- Changelog: v1.0.0 (2026-10-18) — initial frozen contract.

---

## 12. Provenance

Inspiration sprint: `inspiration/REFERENCES.md`. Kept: Lumio floor-plan (room
outline as state border, floating avatar badges). Rejected: neon multi-hue
dashboard clutter (glow without meaning — the documented failure mode),
editorial dark (too sparse for operator density), 3D floor renders (video clutter
+ implies real person-ID). Design rationale: `../../DESIGN.md`.
