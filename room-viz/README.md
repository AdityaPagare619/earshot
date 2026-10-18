# room-viz — LEFT pane: live floor-plan

The demo's walk-in beat, made visual: avatars glide in/out as presence changes;
each room's border glows with the current disclosure level (FULL / ABSTRACT /
EXISTENCE / SILENT). Dark, glowing, AMOLED. No build step — plain HTML/CSS/JS.

## Layout

```
room-viz/
  DESIGN.md          # ≤1-page written decision (governance gate) + pre-mortem
  README.md          # this file
  src/room-viz.js    # the module — exposes window.RoomViz
  src/room-viz.css   # tokens + styles
  demo/index.html    # standalone harness: mock bus + scripted walk-in + manual controls
  demo/mock-bus.js   # mock event bus (same shape as the real contract)
  demo/scenario.js   # the 0:15–0:45 walk-in timeline
```

## Embedding (simulator-shell)

```html
<link rel="stylesheet" href="../room-viz/src/room-viz.css">
<div id="left-pane"></div>
<script src="../room-viz/src/room-viz.js"></script>
<script>
  var viz = new RoomViz({ el: document.getElementById('left-pane'), bus: yourEventBus });
  // or drive it directly:
  viz.handleEvent({ type: 'earshot:presence', detail: { person: 'MIL', room: 'kitchen', confidence: 0.93 } });
</script>
```

## Event contract (frozen)

| Event | detail | Meaning |
|---|---|---|
| `earshot:presence` | `{ person, room\|null, confidence }` | `room` ∈ kitchen/living/bedroom/hall; `null` = left. Avatar glides along the door→room path; `confidence < 0.6` renders a dashed amber ring (fail-closed cue). |
| `earshot:disclosure` | `{ room, level, itemId?, reasons?[] }` | `level` ∈ FULL/ABSTRACT/EXISTENCE/SILENT. Border shifts color over 400ms; chip updates. |
| `earshot:wakeword` | `{ ts }` | P0-1: violet re-sample pulse from the Echo Show; kitchen border briefly shows the fail-closed state, then resolves. |

`RoomViz#levelOf(room)` / `#presenceOf(name)` for read-back. All colors behind the
`:root` token block in `room-viz.css`.

## Disclosure color semantics

- FULL → emerald `#2fe8a4` · ABSTRACT → gold `#ffb03a` · EXISTENCE → ember `#ff5f3c`
- SILENT → crimson `#ff2e63` + animated double-stroke · UNKNOWN → violet `#8b7bff`

## Token adoption (ui-inspiration TOKENS.md)

Placeholder vars now; when TOKENS.md merges, rename in the single `:root` block:

| placeholder | → adopt |
|---|---|
| `--esh-bg` | ui-inspiration `surface-0` / near-black |
| `--esh-wall`, `--esh-label` | hairline + label tokens |
| `--esh-level-full/abstract/existence/silent/unknown` | glow accent tokens (keep the 5 semantic slots — the mapping is hue-for-hue) |

## Demo

Open `demo/index.html` in a browser (or `?autoplay=1` for the scripted walk-in).
The right panel logs every bus event live — if the shell's wiring ever goes quiet,
this panel shows it. Presence is **simulated** (labeled); the module itself is
bus-agnostic and will take the real presence feed unchanged.
