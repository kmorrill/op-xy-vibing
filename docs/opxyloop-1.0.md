# OP‑XY Loop JSON Specification (opxyloop‑1.0)

## Preamble

**What this is.** A compact, JSON‑based loop format for **vibe‑coding** musical ideas with large language models (LLMs), quick human edits, and reliable MIDI playback on the OP‑XY. One file = one loop. You can regenerate, tweak, and audition rapidly without wrestling DAW projects or opaque binary formats.

**What you can do with it.**  
- **Generate with an LLM:** Keys are stable, field names are explicit, and defaults are predictable—so models can create and modify patterns safely.  
- **Edit by hand or UI:** The structure maps cleanly to a step grid, plus lanes for CC and LFO modulation.  
- **Play it back:** A lightweight runtime reads the JSON and schedules notes/automation to the OP‑XY over MIDI.

**End goals.**  
- **Fast idea‑to‑sound loop** for composition and prototyping.  
- **Deterministic playback** with minimal hidden state—easy to diff, version, and share.  
- **Musical context aware:** Optional key/mode for degree‑based notes and Roman‑numeral chords.  
- **Device‑friendly:** Keep OP‑XY specifics (fixed CC mapping, engines) out of the data where possible.

**Scope.** This specification covers a **single looping pattern** per document. Scenes/arrangements and file‑level time‑signature changes are intentionally out of scope. The OP‑XY owns its internal meter; this format doesn’t try to change it.

---

## 1. Top‑level object

A valid **opxyloop‑1.0** document is a JSON object with these keys:

| Key | Required | Description |
| :---- | :---- | :---- |
| **version** | Yes | Must equal `"opxyloop-1.0"` (schema identifier). |
| **meta** | Yes | Global timing and optional tonal context (see §2). |
| **deviceProfile** | No | Device defaults for MIDI port and drum note mappings (see §3). |
| **tracks** | Yes | Array of track objects (see §4). |

---

## 2. `meta` object

Defines the global timebase for the loop and, optionally, its tonal context for degree/chord resolution.

| Key | Type | Required | Description |
| :---- | :---- | :---- | :---- |
| **tempo** | number | Yes | Beats per minute used by the playback engine to drive MIDI clock. |
| **ppq** | integer | Yes | Pulses per quarter note (e.g., 96, 480) for internal tick math. |
| **stepsPerBar** | integer | Yes | Step grid per bar (e.g., 16 for a 1/16th grid). |
| **swing** | number 0–1 | No | Swing amount applied to every second grid subdivision. |
| **key** | string | No | Root key for resolving degrees/chord numerals (e.g., `"C"`, `"F#"`). |
| **mode** | string | No | Scale mode: `"major"`, `"minor"`, or modal names (`"ionian"`, `"dorian"`, etc.). |

> If `key`/`mode` are omitted, use absolute pitches or absolute chord symbols instead of relative numerals.

---

## 3. `deviceProfile` object

Provides per‑project settings specific to the connected OP‑XY device.

| Key | Type | Required | Description |
| :---- | :---- | :---- | :---- |
| **portName** | string | No | MIDI port name to send messages to (e.g., `"OP-XY"`). |
| **drumMap** | object | No | Friendly drum names mapped to MIDI note numbers (e.g., `"kick": 36`). |

### 3.1 `drumMap` example

```json
{
  "portName": "OP-XY",
  "drumMap": { "kick": 36, "snare": 38, "ch": 42, "oh": 46, "clap": 39 }
}
```

---

## 4. `tracks` array

Each track loops independently over its pattern length and targets a single MIDI channel/engine.

| Key | Type | Required | Description |
| :---- | :---- | :---- | :---- |
| **id** | string | Yes | Unique identifier (e.g., `"t-drum"`). |
| **name** | string | Yes | Human‑readable name (e.g., `"Drums"`). |
| **type** | string | Yes | OP‑XY synth engine (e.g., `"sampler"`, `"multiSampler"`, `"axis"`, `"dissolve"`). |
| **midiChannel** | integer 0–15 | Yes | MIDI channel for this track. |
| **role** | string | No | High‑level musical role label (annotation only; no playback effect). Recommended values: `"drums"`, `"bass"`, `"pad"`, `"pluck"`, `"lead"`, `"keys"`, `"piano"`, `"guitar"`, `"fx"`, `"vox"`. |
| **pattern** | object | Yes | Loop definition (see §5). |
| **ccLanes** | array | No | Continuous‑controller automation (see §6). |
| **lfos** | array | No | Runtime LFO modulators (see §7). |

> *Note:* There is no `programChange` or `muted` field in this schema; omit a track to silence it.

### 4.1 Track role label (optional)

- `role` is **pure metadata** for editors/generators (e.g., grouping, color, suggested register/density).  
- Players/readers **must not** change MIDI/audio behavior based on `role`.  
- The `"drums"` role **covers both drum kit and auxiliary percussion**.  
- The underlying structure remains `tracks → pattern → steps → events`.

---

## 5. `pattern` object

Defines the looping note content for a track.

| Key | Type | Required | Description |
| :---- | :---- | :---- | :---- |
| **lengthBars** | integer ≥ 1 | Yes | Number of bars in the loop before it restarts. |
| **steps** | array of **Step** | Yes | Sparse array of steps; omit silent indices. |

### 5.1 Step object

Describes notes (or rests) beginning at a grid position.

| Key | Type | Required | Description |
| :---- | :---- | :---- | :---- |
| **idx** | integer ≥ 0 | Yes | Absolute step index: `bar * stepsPerBar + step` (zero‑based). |
| **events** | array of **NoteEvent** | No | One or more note events at this step; empty/omitted = rest. |
| **tuplet** | "triplet" \| "quintuplet" \| "septuplet" | No | Non‑standard subdivision across the step. |
| **mute** | boolean | No | If `true`, ignore all events at this step. |

### 5.1.1 NoteEvent object

A NoteEvent can represent a **single pitch/degree** *or* an **entire chord**. All common timing/dynamics fields apply in either case.

| Field | Type / range | Required | Description |
| :---- | :---- | :---- | :---- |
| **pitch** | integer 0–127 | Yes\* | Absolute MIDI note number. Use for fixed‑pitch tracks (drums or specific notes). |
| **degree** | integer 1–7 | Yes\* | Scale degree relative to the track’s key/scale; typically used with `octaveOffset`. |
| **octaveOffset** | integer | No | Octave shift applied with `degree` to place the note in register. |
| **chord** | string | Yes\* | Shorthand for a chord (relative or absolute), e.g., `Imaj7`, `V7`, `vi7`, `IVadd9`, `Cmaj7`, `Am7`, `G7(b9)`, `Vsus2`, `Imaj7/3`. When provided, this single NoteEvent requests the full chord. |
| **lengthSteps** | integer ≥ 1 | Yes | Number of grid steps to hold the note/chord. |
| **velocity** | integer 1–127 | Yes | Velocity for the note or for all chord tones (unless `velocities` provided). |
| **prob** | number 0–1 | No | Probability of playing (applies to the whole event or chord). |
| **gate** | number 0–1 | No | Percentage of nominal duration to hold (staccato/legato). |
| **microshiftMs** | integer | No | Shift in milliseconds relative to the step boundary (humanize). |
| **ratchet** | integer ≥ 2 | No | Evenly spaced retriggers within the step; probability applies to the group. |
| **meta** | object | No | Freeform metadata for UI/articulation hints. |

\* A NoteEvent must include **one of**: `pitch`, `degree`, or `chord`. When `degree` is used, include `octaveOffset`. When `chord` is used, timing/dynamics fields apply to the chord as a whole.

#### Optional chord rendering hints

These hints control how a chord is voiced/realized when `chord` is present.

| Field | Type | Description |
| :---- | :---- | :---- |
| **invert** | integer ≥ 0 | Inversion index (`0`=root position, `1`=first inversion, …). |
| **register** | `[string, string]` | Clamp realized pitches to a range (e.g., `["C3","B4"]`). |
| **voicing** | string | Voicing hint, e.g., `"close"`, `"open-4"`, `"spread-5"`. |
| **omit** | array of strings | Omit chord degrees by symbol: `"3"`, `"5"`, `"7"`, etc. |
| **velocities** | array of ints | Per‑tone velocities (low→high). |
| **rollMs** | integer | Arpeggiated “strum” delay between adjacent tones (ms). |

#### Chord symbol grammar

- **Relative (uses `meta.key`/`mode`):** `I`, `ii`, `iii`, `IV`, `V`, `vi`, `vii°` with optional quality: `maj`, `min`, `dim`, `aug`, `7`, `maj7`, `min7`, `ø7`, `sus2`, `sus4`, `add9`, `9`, `11`, `13`. Examples: `Imaj7`, `Vsus2`, `ii7`, `V7(b9)`, `IVadd9`.  
- **Absolute:** `Cmaj7`, `Am7`, `Fadd9`, `G7(b9)`.  
- **Slash bass:** `Imaj7/3`, `G7/B`.  
- **Defaults:** Unspecified qualities resolve diatonically for the given mode.

**Implementation notes for `chord` expansion**  
- Expand a chord NoteEvent into multiple per‑pitch events internally, sharing timing and probability unless overridden.  
- Tools lacking chord support may pre‑expand chords into ordinary NoteEvents.  
- If no inversion/voicing hints are provided, use close position within a practical register (default `["C3","B4"]`).

### 5.1.2 DrumKit — single‑track drum authoring helper



Author all drum parts in **one track** using compact pattern strings. The **playback engine reads `drumKit` directly** and schedules hits at runtime—**no pre‑conversion to `steps → events` is required**. Placed here because it maps cleanly to the **Step/NoteEvent timing model**. Tools that don’t implement `drumKit` can ignore it, or optionally convert it into `steps` themselves if needed for editing workflows.

**Location:** Optional field on a *drum track object* (typically `type: "sampler"`).  
**Effect:** Schedules hits at specific `Step.idx` values based on per‑bar pattern strings.

#### Fields

Within a drum track, add a `drumKit` object with these fields:

- **patterns** (array of **DrumPatternSpec**) — **required**.
- **repeatBars** (integer ≥ 1) — optional. Repeat all listed patterns forward from each `bar` for this many bars; clamped to the track’s `pattern.lengthBars`. Default: `1`.
- **lengthSteps** (integer ≥ 1) — optional. Default note length for emitted hits. Default: `1`.

**DrumPatternSpec** (elements of `drumKit.patterns`):

- **bar** (integer ≥ 1) — the starting bar where this pattern applies.
- **key** (string) — **must** be a key in `deviceProfile.drumMap` (e.g., `"kick"`, `"snare"`, `"clap"`, `"ch"`, `"oh"`).
- **pattern** (string) — exactly **`meta.stepsPerBar`** characters; allowed chars: `x` (hit), `.` or `-` (rest). No whitespace.
- **vel** (integer 1–127, optional) — velocity for all hits produced by this spec; if omitted, use a reasonable default (e.g., 100).
- **lengthSteps** (integer ≥ 1, optional) — per‑spec override; falls back to `drumKit.lengthSteps` if not set.

> **First‑class helper.** `drumKit` is valid at playback time. Implementations MAY convert it into `pattern.steps[].events[]` internally for editing or export, but this is **not required** for playback.

#### Runtime scheduling semantics → Steps & NoteEvents

Let `S = meta.stepsPerBar`, `B = pattern.lengthBars` on the same track.

For each **DrumPatternSpec** `{bar = b0, key = k, pattern = P, vel, lengthSteps}`:

1. Resolve `pitch` as `deviceProfile.drumMap[k]` (required).
2. For each bar offset `t` in `[0 .. repeatBars-1]` while `b = b0 + t ≤ B`:
   - For each index `s` in `[0 .. S-1]`:
     - If `P[s] == 'x'`, **schedule a hit** at absolute `Step.idx = (b-1)*S + s` with:
       - `pitch`: resolved from `drumMap`.
       - `velocity`: from `vel` (or default if omitted).
       - `lengthSteps`: from spec’s `lengthSteps` → else `drumKit.lengthSteps` → else `1`.

If multiple specs produce hits at the same `idx` (e.g., kick and clap together), **schedule both hits** at that step. No hits are scheduled for `.`/`-` positions.

#### Constraints & defaults

- The track MUST define `pattern.lengthBars`.
- Each `pattern` string MUST be exactly `meta.stepsPerBar` chars.
- `key` MUST exist in `deviceProfile.drumMap`.
- Default velocity if unspecified MAY be `100`.
- Default `lengthSteps` if unspecified is `1`.

#### Example — authoring (compact; engine reads `drumKit` directly)

**Authoring (compact, single track)**
```json
{
  "version": "opxyloop-1.0",
  "meta": { "tempo": 112, "ppq": 96, "stepsPerBar": 16, "swing": 0.10 },
  "deviceProfile": {
    "portName": "OP-XY",
    "drumMap": { "kick": 36, "snare": 38, "clap": 39, "ch": 42, "oh": 46 }
  },
  "tracks": [
    {
      "id": "t-drums",
      "name": "Drums (one-track)",
      "type": "sampler",
      "midiChannel": 0,
      "role": "drums",
      "drumKit": {
        "patterns": [
          { "bar": 1, "key": "kick", "pattern": "x...x...x...x...", "vel": 120 },
          { "bar": 1, "key": "clap", "pattern": "..x...x...x...x.", "vel": 102 },
          { "bar": 1, "key": "ch",   "pattern": ".x.x.x.x.x.x.x.x", "vel": 80  },
          { "bar": 1, "key": "oh",   "pattern": "................", "vel": 95  }
        ],
        "repeatBars": 8,
        "lengthSteps": 1
      },
      "pattern": { "lengthBars": 8, "steps": [] }
    }
  ]
}
```


## 6. Continuous Controller (CC) lanes

Use **ccLanes** to schedule CC automation over time (e.g., filter cutoff, resonance, sends). Destination names must match the OP‑XY’s fixed CC mapping known by the runtime.

### 6.2 OP‑XY CC Name Map (canonical)

For `dest: "name:<identifier>"`, the runtime resolves names to these controller numbers:

- name: `track_volume` → CC 7
- name: `track_mute` → CC 9
- name: `track_pan` → CC 10
- name: `param1` → CC 12; `param2` → 13; `param3` → 14; `param4` → 15
- name: `amp_attack` → CC 20; `amp_decay` → 21; `amp_sustain` → 22; `amp_release` → 23
- name: `filter_attack` → CC 24; `filter_decay` → 25; `filter_sustain` → 26; `filter_release` → 27
- name: `voice_mode` → CC 28 (poly/mono/legato)
- name: `portamento` → CC 29
- name: `pitchbend_amount` → CC 30
- name: `engine_volume` → CC 31
- name: `cutoff` → CC 32; name: `resonance` → CC 33; name: `env_amount` → CC 34; name: `key_tracking` → CC 35
- name: `send_ext` → CC 36; name: `send_tape` → 37; name: `send_fx1` → 38; name: `send_fx2` → 39
- name: `lfo_dest` → CC 40; name: `lfo_param` → CC 41

If you prefer explicit controller numbers in JSON, use `dest: "cc:<number>"` or an integer.

### 6.1 CCLane object

| Key | Type | Required | Description |
| :---- | :---- | :---- | :---- |
| **id** | string | Yes | Lane identifier (e.g., `"cutoff-sweep"`). |
| **dest** | string \| integer | Yes | Destination CC: `cc:<number>` or `name:<identifier>` resolved by the runtime. |
| **channel** | integer 0–15 | No | Overrides the track’s channel for this lane. |
| **mode** | "points" \| "hold" \| "ramp" | Yes | Interpolation/emit behavior. |
| **points** | array of **CCPoint** | Yes | Defines the curve; points are sorted by time. |
| **range** | `[number, number]` | No | Clamp CC values (default `[0,127]`). |

**CCPoint** (time/value pair):  
`{ "t": { "ticks": number } | { "bar": number, "step": number }, "v": 0–127, "curve": "linear"|"exp"|"log"|"s-curve" }`.

---

## 7. Low‑Frequency Oscillators (LFOs)

Runtime‑generated periodic modulation (distinct from explicit CC points).

### 7.1 LFO object

| Key | Type | Required | Description |
| :---- | :---- | :---- | :---- |
| **id** | string | Yes | LFO identifier (e.g., `"cutoff-wobble"`). |
| **dest** | string \| integer | Yes | Destination controller (same formats as CC lanes). |
| **channel** | integer 0–15 | No | Defaults to the track’s channel. |
| **depth** | integer 0–127 | Yes | Peak‑to‑peak amplitude. |
| **rate** | object | Yes | `{"sync": "1/4"|"1/8"|"1/16"|...}` or `{"hz": number}`. Triplets use `"T"` suffix. |
| **phase** | number 0–1 | No | Initial phase offset. |
| **offset** | integer 0–127 | No | Baseline value around which the LFO oscillates. |
| **shape** | "sine" \| "triangle" \| "saw" \| "ramp" \| "square" \| "samplehold" | Yes | Waveform. |
| **fadeMs** | integer ≥ 0 | No | Fade‑in time (ms). |
| **on** | array of windows | No | Active windows: `{ "from": TickRef, "to": TickRef }`. |
| **stereoSpread** | number 0–1 | No | Phase offset for L/R automation when applicable. |

---

## 8. Additional notes & guidance

- **Engine enumeration:** Track `type` must match an OP‑XY engine (`"sampler"`, `"multiSampler"`, `"axis"`, `"dissolve"`, etc.).  
- **Sparse steps:** Omit silent indices in `steps`; the array is intentionally sparse.  
- **Probability & ratchets:** If both are present, probability applies to the entire ratcheted group.  
- **Tonal context:** When using degrees or relative chord numerals, set `meta.key` and `meta.mode` so the runtime can resolve to MIDI pitches. Absolute pitches/symbols require no tonal context.  
- **Fixed CC mapping:** Destination names (e.g., `name:cutoff`) are resolved by the runtime against the OP‑XY’s fixed CC map (see §6.2); do **not** embed a `ccMap` in JSON.  
- **No time‑signature changes:** This schema doesn’t encode time‑signature changes; the OP‑XY handles its own meter.

---

## 9. Quick‑start examples

### 9.1 Minimal drum loop

```json
{
  "version": "opxyloop-1.0",
  "meta": { "tempo": 120, "ppq": 480, "stepsPerBar": 16 },
  "deviceProfile": {
    "portName": "OP-XY",
    "drumMap": { "kick": 36, "snare": 38, "ch": 42, "oh": 46 }
  },
  "tracks": [
    {
      "id": "t-drum",
      "name": "Drums",
      "type": "sampler",
      "midiChannel": 9,
      "role": "drums",
      "pattern": {
        "lengthBars": 1,
        "steps": [
          { "idx": 0,  "events": [{ "pitch": 36, "lengthSteps": 2, "velocity": 112 }] },
          { "idx": 4,  "events": [{ "pitch": 38, "lengthSteps": 2, "velocity": 104 }] },
          { "idx": 8,  "events": [{ "pitch": 36, "lengthSteps": 2, "velocity": 112, "ratchet": 2 }] },
          { "idx": 12, "events": [{ "pitch": 38, "lengthSteps": 2, "velocity": 104, "prob": 0.8 }] }
        ]
      }
    }
  ]
}
```

### 9.2 Degree‑based bass in C Dorian

```json
{
  "version": "opxyloop-1.0",
  "meta": { "tempo": 100, "ppq": 480, "stepsPerBar": 16, "key": "C", "mode": "dorian" },
  "tracks": [
    {
      "id": "t-bass",
      "name": "Bass",
      "type": "axis",
      "midiChannel": 1,
      "role": "bass",
      "pattern": {
        "lengthBars": 2,
        "steps": [
          { "idx": 0,  "events": [{ "degree": 1, "octaveOffset": -2, "lengthSteps": 4, "velocity": 108 }] },
          { "idx": 4,  "events": [{ "degree": 5, "octaveOffset": -2, "lengthSteps": 4, "velocity": 108 }] },
          { "idx": 8,  "events": [{ "degree": 6, "octaveOffset": -2, "lengthSteps": 4, "velocity": 108 }] },
          { "idx": 12, "events": [{ "degree": 4, "octaveOffset": -2, "lengthSteps": 4, "velocity": 108 }] }
        ]
      }
    }
  ]
}
```

### 9.3 Pad using chord symbols with automation

```json
{
  "version": "opxyloop-1.0",
  "meta": { "tempo": 96, "ppq": 480, "stepsPerBar": 16, "swing": 0.08, "key": "C", "mode": "ionian" },
  "deviceProfile": { "portName": "OP-XY" },
  "tracks": [
    {
      "id": "t-chords",
      "name": "Pad",
      "type": "dissolve",
      "midiChannel": 0,
      "role": "pad",
      "pattern": {
        "lengthBars": 2,
        "steps": [
          { "idx": 0,  "events": [{ "chord": "Imaj7", "lengthSteps": 8, "velocity": 96, "invert": 1, "register": ["C3","B4"] }] },
          { "idx": 8,  "events": [{ "chord": "V7",    "lengthSteps": 8, "velocity": 96, "rollMs": 12 }] }
        ]
      },
      "ccLanes": [
        {
          "id": "cutoff-sweep",
          "dest": "name:cutoff",
          "mode": "ramp",
          "points": [
            { "t": { "bar": 0, "step": 0 },  "v": 40 },
            { "t": { "bar": 1, "step": 15 }, "v": 100 }
          ]
        }
      ],
      "lfos": [
        {
          "id": "pad-wobble",
          "dest": "name:resonance",
          "depth": 18,
          "rate": { "sync": "1/8T" },
          "shape": "triangle",
          "offset": 64
        }
      ]
    }
  ]
}
```

### 9.4 Single‑track drums via `drumKit` helper

See §5.1.2 for schema and semantics. Here’s a minimal one‑bar example that the playback engine reads directly (no pre‑conversion of `drumKit` to `steps` is required):

```json
{
  "version": "opxyloop-1.0",
  "meta": { "tempo": 120, "ppq": 480, "stepsPerBar": 16 },
  "deviceProfile": { "portName": "OP-XY", "drumMap": { "kick": 36, "snare": 38 } },
  "tracks": [
    {
      "id": "t-drums",
      "name": "Kit",
      "type": "sampler",
      "midiChannel": 9,
      "role": "drums",
      "drumKit": {
        "patterns": [
          { "bar": 1, "key": "kick",  "pattern": "x...x...x...x...", "vel": 112 },
          { "bar": 1, "key": "snare", "pattern": "....x.......x...", "vel": 104 }
        ],
        "repeatBars": 1,
        "lengthSteps": 1
      },
      "pattern": { "lengthBars": 1, "steps": [] }
    }
  ]
}
```

### 9.5 Minimal role labels example

```json
{
  "version": "opxyloop-1.0",
  "meta": { "tempo": 112, "ppq": 96, "stepsPerBar": 16, "swing": 0.10 },
  "deviceProfile": {
    "portName": "OP-XY",
    "drumMap": { "kick": 36, "snare": 38, "clap": 39, "ch": 42, "oh": 46 }
  },
  "tracks": [
    {
      "id": "t-drums",
      "name": "Kit + Aux Perc",
      "type": "sampler",
      "midiChannel": 0,
      "role": "drums",
      "pattern": {
        "lengthBars": 4,
        "steps": [
          { "idx": 0,  "events": [{ "pitch": 36, "velocity": 120, "lengthSteps": 1 }] },
          { "idx": 6,  "events": [{ "pitch": 39, "velocity": 102, "lengthSteps": 1 }] },
          { "idx": 2,  "events": [{ "pitch": 42, "velocity": 80,  "lengthSteps": 1 }] }
        ]
      }
    },
    {
      "id": "t-bass",
      "name": "Sub Bass",
      "type": "axis",
      "midiChannel": 1,
      "role": "bass",
      "pattern": {
        "lengthBars": 4,
        "steps": [
          { "idx": 0,  "events": [{ "degree": 1, "octaveOffset": -2, "velocity": 110, "lengthSteps": 4 }] },
          { "idx": 8,  "events": [{ "degree": 5, "octaveOffset": -2, "velocity": 112, "lengthSteps": 4 }] }
        ]
      }
    },
    {
      "id": "t-pluck",
      "name": "Glimmer Pluck",
      "type": "multiSampler",
      "midiChannel": 3,
      "role": "pluck",
      "pattern": {
        "lengthBars": 4,
        "steps": [
          { "idx": 1,  "events": [{ "degree": 6, "octaveOffset": 1, "velocity": 105, "lengthSteps": 2 }] },
          { "idx": 5,  "events": [{ "degree": 7, "octaveOffset": 1, "velocity": 103, "lengthSteps": 2 }] }
        ]
      }
    }
  ]
}
```

---

## 10. Validation checklist

- `version` is exactly `"opxyloop-1.0"`.  
- `meta` includes `tempo`, `ppq`, `stepsPerBar` (and optional `swing`, `key`, `mode`).  
- Each `track` defines `id`, `name`, `type`, `midiChannel`, and a `pattern`.  
- Each `Step` provides `idx` and optional `events`/`tuplet`/`mute`.  
- Each `NoteEvent` has **one of** `pitch` | `degree` | `chord`, plus `lengthSteps` and `velocity`.  
- If `degree` is used, include `octaveOffset`; if `chord` is used, optional hints may guide voicing/inversion/strum.  
- Optional `ccLanes`/`lfos` follow their schemas and reference valid destinations.  
- If a track includes `drumKit`: `patterns[].key` must exist in `deviceProfile.drumMap`; each `patterns[].pattern` length equals `meta.stepsPerBar`; scheduling respects `pattern.lengthBars` and the runtime semantics in §5.1.2.  
- If a track includes `role`: treat it as **annotation only** (no playback effect). Recommended values include `"drums"`, `"bass"`, `"pad"`, `"pluck"`, `"lead"`, `"keys"`, `"piano"`, `"guitar"`, `"fx"`, `"vox"`; `"drums"` covers both kit and auxiliary percussion.

---

*This spec is intended to be small, explicit, and implementation‑friendly. If you need scenes or arrangements, store each as its own `opxyloop-1.0` document and sequence them in your application logic.*
