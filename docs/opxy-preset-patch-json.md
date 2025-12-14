# OP‑XY preset `patch.json` format (observed)

This is a first‑pass reverse‑engineering note based on:

- Preset exports found at `~/Documents/xy-remix/source-presets/**.preset/patch.json`.
- Open‑source “preset builders” that generate `.preset/patch.json` for OP‑XY.

Teenage Engineering has not published an official public schema (as of writing), so treat this as **observed behavior** + **community conventions**.

Each preset is a directory ending in `.preset/` containing:

- `patch.json` (the patch/engine settings)
- Optional audio assets (`.wav`, `.aif`) referenced by `regions[*].sample`

## 0) Open‑source tooling references (patch generators/editors)

These repos are useful because they **emit working `patch.json`** and encode a lot of implicit rules (key mapping, region fields, resampling expectations, etc.).

### Must‑read repos (OP‑XY focused)

| Repo | What it is | Key files to read | Notes |
|---|---|---|---|
| `https://github.com/joseph-holland/op-patchstudio` | Full UI for drum + multisample OP‑XY presets | `src/utils/patchGeneration.ts`, `src/components/drum/baseDrumJson.ts`, `src/components/multisample/baseMultisampleJson.ts` | Most complete reference: framecount validation, resampling, trimming, loop metadata, per‑slot settings. |
| `https://github.com/buba447/opxy-drum-tool` | Classic web drum + multisample patch generator | `index.html`, `multisample-tool.html`, `lib/audio_tools.js` | Widely referenced; demonstrates the minimal patch JSON needed for drum and multisampler. |
| `https://github.com/YYUUGGOO/OP-XY-Drum-Utility` | Web/React “drum kit” builder/exporter | `src/App.tsx`, `patch.json`, `opxy json doc.md` | Includes a patch template + region generator; **note** `opxy json doc.md` contains some speculative statements that conflict with observed dot‑keys (see §1 notes). |

### Additional repos (useful patterns / cross‑checks)

| Repo | Focus | Key files | Notes |
|---|---|---|---|
| `https://github.com/buba447/OPXY-Multisample-Tool` | Python multisample recording/packing | `preset.json`, `PackSamples.py`, `Helpers.py` | Good baseline `multisampler` template + “regions” writer; expects `.preset/patch.json`. |
| `https://github.com/paul-sneddon/teopxy` | Python OP‑1 drum → OP‑XY drum preset converter | `teopxy.py` | Useful for “drum” region fields (`gain`, `transpose`, `playmode`) and key mapping. |
| `https://github.com/inrainbws/logic_pro_drums_for_opxy` | Python: bounce+splice+export drum kits | `splice_and_export.py` | Clean framecount + `sample.start/end` handling; explicit 53–76 key mapping table. |
| `https://github.com/foxxyz/op-xy-patch-generator` | Node CLI + web generator | `template.json`, `cli/generate.js` | Minimal “drum” patch generator; framecount calculation is simplistic (byte math), so treat as a template only. |
| `https://github.com/sixthlaw/opxy-multisampler-preset-builder` | Web multisampler builder | `src/main.js` | Shows an alternate multisampler region mapping pattern (see §6.2). |
| `https://github.com/DimaDake/maschine-multisample-to-op-xy-converter` | Web NI Maschine → OP‑XY multisampler | `src/main.js` | Implements the “last `hikey = 127`” convention and region sorting. |
| `https://github.com/aliosa27/op-xy-slicer` | Python slicer → drum presets | `xy.py` | Generates the right shape, but uses placeholder `framecount`/`sample.end` in the published code; not reliable as a reference for numeric correctness. |
| `https://github.com/discepoli/op-xy-drum-preset-builder` | Python folder → drum preset | `generate_drum_preset.py` | Generates the right shape, but uses placeholder `framecount`; author notes loop/frame issues. |

## 1) Top‑level object

All observed `patch.json` files share the same top‑level shape:

```json
{
  "version": 4,
  "platform": "OP-XY",
  "type": "<engine>",
  "octave": 0,
  "engine": { "...": "..." },
  "envelope": { "...": "..." },
  "fx": { "...": "..." },
  "lfo": { "...": "..." },
  "regions": []
}
```

Notes:

- Keys like `"portamento.amount"` and `"loop.end"` are literal JSON keys (not nested objects).
- Many community tools also use dot‑keys (e.g. `"loop.enabled"`, `"sample.end"`) and the OP‑XY appears to accept them as‑is.
- Most continuous parameters are stored as integers in `[0, 32767]` (`16384` ≈ “center”).
  - Open‑source tools frequently treat these as **normalized** values (e.g. UI percent) and convert to OP‑XY’s internal integer space.

### 1.1 Observed enums

From 229 presets:

- `type` (engine): `axis`, `dissolve`, `epiano`, `hardsync`, `multisampler`, `organ`, `prism`, `sampler`, `simple`, `wavetable`
  - Community tools also emit `type: "drum"` for drum kits (not present in this export set).
- `engine.playmode`: `poly`, `mono`, `legato`
- `fx.type`: `ladder`, `svf`, `z lowpass`, `z hipass`
- `lfo.type`: `tremolo`, `random`, `value`, `element`

### 1.2 Number formats & units (observed)

The file mixes a few different “number spaces”:

- **Normalized internal params**: many continuous controls are stored as **integers** in `[0, 32767]` (with `16384` ≈ center).
  - Examples: `engine.params[*]`, `engine.volume`, `engine.width`, `engine.highpass`, `engine.bendrange`, `engine.velocity.sensitivity`, `envelope.*.*`, `fx.params[*]`, `lfo.params[*]`, modulation `*.amount`.
  - These appear to be device‑internal encodings (often derived from UI percent/knobs by generators).
- **MIDI notes**: `lokey`, `hikey`, and `pitch.keycenter` are **integers** in MIDI note space (`0..127`).
- **Audio frame indices**: `framecount`, `sample.start`, `sample.end`, and `loop.*` are **integers** expressed in audio **frames** (sample “timestamps”) at the sample’s playback rate.
  - Seconds ≈ `frames / sampleRate` (most presets use `44100` Hz audio).
  - Many tools *choose* loop points in percent of duration but always *store* them as frames.
- **Semitone-ish ints**: `engine.transpose` and drum `regions[*].transpose` are **integers** (semitones). `tune` is an **integer** but its exact unit (cents vs internal) is unclear in exports (almost always `0`).
- **Floats**: `engine.tuning` (when present) is an array of **12 floats** (likely per‑semitone cents offsets).

## 2) `engine` object

Observed keys (always present unless noted):

- `params`: array of **8** integers in `[0, 32767]`
  - For synth engines, `params[0..3]` appear to map to the OP‑XY’s engine parameters **P1–P4**.
  - Many engines leave `params[4..7]` at `0` (Axis uses them sometimes).
  - For `sampler`/`multisampler`, `params[*]` are usually `16384` (default/centered), with occasional variance.
  - For musical meaning of P1–P4 per engine, see `docs/opxy-synth-engines.md`.
- `volume`: int `[0, 32767]`
- `width`: int `[0, 32767]` (likely stereo width)
- `highpass`: int `[0, 32767]` (values observed are typically small)
  - Hardware/UI note (from a deep‑dive video transcript): this appears to be the preset‑level **High Pass** setting (shift + instrument). It’s separate from the main filter block, and “scramble” may not randomize it—so it can be the reason a sound still feels filtered even when the main filter looks open.
- `bendrange`: int `[0, 32767]` (likely an encoded pitch‑bend range)
- `playmode`: string enum (see above)
- `transpose`: int (observed `0..12`)
- `velocity.sensitivity`: int `[0, 32767]`
- `portamento.amount`: int `[0, 32767]`
- `portamento.type`: int `[0, 32767]` (often `0` or `32767`)
- `tuning.root`: int (few discrete values observed)
- `tuning.scale`: int (few discrete values observed)
- `tuning` (optional): array of **12** floats (observed range about `-15..+12`)
  - Likely per‑semitone cents offsets for microtuning.
- `modulation`: mapping for performance modulation sources:
  - `aftertouch`, `modwheel`, `pitchbend`, `velocity`
  - each is an object: `{ "target": <int>, "amount": <int> }`
  - `target` looks like an encoded destination ID; `0` appears to mean “none”.

## 3) `envelope` object

Always:

- `amp`: `{ attack, decay, sustain, release }` ints `[0, 32767]`
- `filter`: `{ attack, decay, sustain, release }` ints `[0, 32767]`

Hardware/UI notes (from a deep‑dive video transcript; mapping to JSON is partly unconfirmed):

- On melodic synth tracks this behaves like a standard ADSR: `attack` → peak, `decay` → `sustain`, and `release` after key‑up. Short `decay/release` reads as “plucky”; longer `attack/release` reads as “pad”.
- The filter envelope shapes the filter cutoff over time; how audible it is depends heavily on the filter’s envelope amount (see `fx` below).
- On `type: "drum"` the OP‑XY’s envelope UI is *not* ADSR (it’s described as `start/attack/hold/decay` plus a per‑pad fade‑in/out). Community tools still emit ADSR‑shaped `envelope.*` objects for drum presets, but the exact correspondence needs confirmation via export diffs.

## 4) `fx` object

- `active`: boolean
- `type`: enum (see §1.1)
- `params`: array of **8** ints in `[0, 32767]`

Interpretation is still unknown, but given `fx.type` values like `ladder` and `svf`, this appears to represent a per‑track filter/effect block with a fixed 8‑slot parameter vector.

Update based on hardware/UI behavior (transcript): this object very likely *is* the main **filter** block (M3) on the OP‑XY, despite the name `fx` in `patch.json`:

- The on‑device filter types cycle through values that match `fx.type`: `svf`, `ladder`, `z lowpass`, `z hipass`.
- The UI exposes 4 “primary” filter controls: cutoff, resonance, filter‑envelope amount, and key tracking.
  - Key tracking ties cutoff to note pitch; on drum kits it’s useful for keeping higher‑pitched sounds (hats/percs) bright even if the cutoff is tuned for the kick/snare.
- Subjectively, the biggest audible difference between filter models is the character of the resonance peak.
- `engine.highpass` (preset settings) is a separate high‑pass stage without resonance; `fx.type: "z hipass"` is useful when you want a resonant high‑pass.
- A very short, resonant filter envelope sweep can add a transient “pop” at note‑on.

Hypothesis for `fx.params` mapping (needs export validation):

- `fx.params[0]`: cutoff
- `fx.params[1]`: resonance
- `fx.params[2]`: filter‑envelope amount
- `fx.params[3]`: key tracking
- `fx.params[4..7]`: unknown / model‑specific

## 5) `lfo` object

- `active`: boolean
- `type`: enum (see §1.1)
- `params`: array of **8** ints in `[0, 32767]`

Interpretation is still unknown (likely rate/depth/shape + routing).

Hardware/UI notes:

- A “random” LFO applied to envelope attack can add subtle per‑hit variation (useful for rolls/fills).
- Modulating sample start tends to get chaotic quickly and can introduce pops/clicks; modulating attack is usually cleaner.

## 6) `regions` array (sample mapping)

`regions` is:

- `[]` (empty) for all non‑sampler synth engines in this dataset
- Non‑empty for `type: "sampler"` (always 1 region here) and `type: "multisampler"` (multiple regions)

### 6.1 Region object keys

Common keys:

- `sample`: string (filename, relative to the `.preset/` directory)
- `framecount`: int (total sample length; when present it matches `sample.end` unless trimmed)
- `sample.start` (optional): int (trim start point)
- `sample.end`: int (trim end point; often equals `framecount`)
- `reverse`: bool
- `gain` (optional): small int (observed `-2..20`)
- `tune`: int (almost always `0`; one observed value `90`)

Pitch mapping keys:

- `lokey`: int (observed always `0` in this dataset)
- `hikey`: int (MIDI note number)
- `pitch.keycenter`: int (MIDI note number; “root key” for the sample)
  - In `multisampler`, `hikey == pitch.keycenter` for every region and regions are sorted ascending by `hikey`.

Loop keys:

- `loop.start`: int
- `loop.end`: int
- `loop.crossfade`: int
- `loop.onrelease`: bool
- `loop.enabled` (optional): bool (exports rarely include `true`, but open‑source generators write it as the master “loop on/off” switch)

Practical note: in exported `multisampler` presets, `loop.enabled` is often present and set to `false` (typical for piano/one‑shot multisamples). Sustain‑looped instruments usually have non‑zero `loop.start`/`loop.end`, and often omit `loop.enabled` in exports.

### 6.2 Notes on region semantics (tentative)

- All sample frame indices (`sample.start`, `sample.end`, `loop.*`) appear to be expressed in the sample’s frame units (same scale as `framecount`).
  - Think “timestamp in samples”: seconds ≈ `frames / sampleRate` (typically `44100`).
- `loop.enabled` may be a newer explicit “disable looping” flag; in this dataset it only appears as `false`.
- `lokey` being always `0` suggests the OP‑XY may be using `hikey` as a region boundary rather than a conventional `[lokey, hikey]` range.
- Hardware/UI note: very short loop regions can produce audible popping/clicking; increasing loop length and/or using `loop.crossfade` helps.

### 6.3 `type: "sampler"` observations (single‑region tonal sampler)

From `../xy-remix/source-presets/**.preset/patch.json` (115 presets):

- `regions` always has exactly **1** entry.
- `regions[0].lokey` is always `0`.
- `regions[0].hikey` ranges `24..99` (never `127` in this dataset).
- `regions[0]["pitch.keycenter"]` ranges `45..74`.
- `regions[0]` always includes `loop.start`, `loop.end`, `loop.crossfade`, and `loop.onrelease` (`loop.onrelease` is `true` in 110/115 presets).
- `regions[0]["loop.enabled"]` is usually absent; when present it is `false` (4/115 presets).
- `regions[0]["sample.start"]` is optional (present in 29/115).
- `regions[0]["sample.end"] == regions[0].framecount` in 88/115 (others trim the end).
- `regions[0].gain` is present in 83/115 (observed range `-2..20`); `regions[0].reverse` is uncommon (9/115).

Practical takeaway: the tonal sampler `patch.json` looks like the multisample region schema, but with a single region; `hikey` is consistently set below `127`, suggesting presets often constrain the playable mapping range (possibly to avoid pitching up too far).

#### 6.3.1 Sustain looping (“repeat points”) pattern

Nearly every tonal sampler preset in this set appears to be configured as a **sustain-looped instrument** (i.e. you can hold a key and the note keeps playing):

- `loop.start` and `loop.end` are non‑zero and sit *inside* the playable sample span.
- `sample.end` is usually **greater** than `loop.end`, leaving a “tail” segment after the loop.
  - Median tail (`sample.end - loop.end`) is ~`52920` frames ≈ `1.2s @ 44.1kHz`.
- `loop.start` tends to be around the first ~10–25% of the sample and `loop.end` around ~75–90%.
  - Median loop length (`loop.end - loop.start`) is ~`158757` frames ≈ `3.6s @ 44.1kHz`.
  - In exported `multisampler` presets, the most common default is exactly **20% / 80%** of the region’s `sample.end`:
    - `loop.start == floor(sample.end * 0.2)`
    - `loop.end == floor(sample.end * 0.8)`
    - This pattern shows up in **128/152** multisampler regions in the source preset set.

This strongly suggests the common intended behavior is:

- While the key is held: play attack → loop `loop.start..loop.end`
- On key release: exit the loop and play the remaining tail up to `sample.end`

`loop.onrelease` is `true` in most sampler presets; community generators disagree on its exact meaning, but this “exit loop on release to play tail” behavior matches the dominant structure of the exported presets.

Hardware/UI cross‑check (transcript): the sampler UI appears to expose three loop behaviors while holding notes:

- Loop off (no repeating between loop points)
- Loop between points until key‑up, then play the remainder of the sample
- Loop continuously even during release (∞)

The on‑device “∞” toggle suggests there’s an explicit representation for “keep looping during release”; determining how that maps onto `loop.onrelease` / `loop.enabled` is still an open reverse‑engineering task.

#### 6.3.2 What generators do

Open‑source patch generators typically implement sustain looping by:

- Treating `loop.start`/`loop.end` as **frame indices** at the sample’s playback rate (after resampling).
- Defaulting loop points to a **percent of sample duration** when no explicit loop is provided (the common defaults vary by tool; factory exports often resemble `20%/80%`).
- Writing `loop.enabled` explicitly for multisamples; for single‑sample presets it’s often omitted in exports.
- Setting `loop.crossfade` to `0` (many tools), or leaving it at a small constant in factory presets; its exact semantics remain unclear, but looping works without it.

In other words: loop points may be *chosen* in percent, but they’re *stored* in `patch.json` as integer frame indices.

### 6.4 Community generator conventions (drum + multisampler)

These conventions show up repeatedly across the open‑source tools listed in §0:

- **Drum key mapping:** regions are typically mapped to MIDI notes `53..76` (24 slots), with `lokey == hikey == note`.
  - This is used by `opxy-drum-tool`, `op-patchstudio`, `OP-XY-Drum-Utility`, and `logic_pro_drums_for_opxy`.
- **Multisampler key ranges:** generators typically sort samples by `pitch.keycenter` (root MIDI note), then assign key ranges with monotonically increasing `lokey`/`hikey` and force the last region’s `hikey` to `127`.
  - Example pattern (high‑level):
    - `lokey` starts at `0`
    - each region uses `hikey = rootNote` (or `nextRootNote - 1`, depending on the generator)
    - next region’s `lokey = prevRootNote + 1`
    - last region: `hikey = 127`
  - This is implemented in `opxy-drum-tool` (`multisample-tool.html`), `op-patchstudio`, and `maschine-multisample-to-op-xy-converter`.
- **Framecount correctness:** the most reliable tools compute `framecount` from decoded audio buffer length *after* resampling, and set `sample.end == framecount` unless trimmed.
  - See `op-patchstudio`’s validation logic in `src/utils/patchGeneration.ts`.

### 6.5 `type: "drum"` notes (drum kit presets)

The drum‑kit preset format is **similar to** the sampler region schema, but commonly uses `type: "drum"` and includes additional per‑slot keys.

Observed via community tools (e.g. `teopxy`) and working generators:

- `type` is `"drum"`.
- `regions` usually contains **24** regions mapped to MIDI notes `53..76`.
- Each region typically sets `lokey == hikey == note`.
- Region objects often include:
  - `fade.in`, `fade.out`: int
  - `pan`: int
  - `transpose`: int (semitones)
  - `playmode`: `"gate" | "oneshot" | "group" | "loop"` (often used to choke hi‑hats with `"group"`)
  - `pitch.keycenter`: often `60` (not per‑slot)

Practical reference: `tools/generate_latin_trap_presets.py` emits a working example at `~/Documents/xy-remix/generated-presets/latin_trap/LatinTrap_DrumKit.preset/patch.json`.

Hardware/UI note (transcript): drum tracks appear to have a **global** envelope (applies to all pads) plus **per‑pad** envelope tweaks. The per‑pad attack/release edits are likely represented by `fade.in`/`fade.out` (and/or related per‑region fields), but the global “start/attack/hold/decay” mapping to JSON is still unconfirmed.

### 6.6 Practical sampling constraints (hardware workflow notes)

These points don’t introduce new JSON keys, but they matter when **generating** `.preset/patch.json` and choosing defaults:

- **Per‑track filter, not per‑pad:** on the OP‑XY drum sampler, all pads share the same filter settings (cutoff/resonance/envelope amount/key tracking). In JSON terms, the filter block (`fx`) is preset‑global; don’t expect per‑region filter control.
  - Sound‑design implication: if you need different filter treatments for different drum sounds, split sounds across multiple tracks/presets, or lean on key tracking and per‑pad envelope/trim instead of filtering per slot.
- **Pad count + zone count:** drum kits are practically **24 slots** (notes `53..76`), and the multisampler UI appears to support up to **24** sampled zones.
  - Generation implication: keep `regions` ≤ 24 for `type: "drum"` and for “auto‑sampled” multisamples unless you’ve confirmed larger sets work.
- **No auto‑chop on device (vs OP‑Z):** the OP‑XY does not appear to automatically slice a recording across 24 drum pads.
  - Generation implication: if you want “break slicing”, do it offline and emit either (a) one audio file per pad, or (b) multiple regions referencing the same file with different trim points (if the drum engine respects `sample.start`/`sample.end` for `type: "drum"` in your tests).
- **On‑device recording duration:** sampling is described as “up to ~20 seconds” per recording on the hardware.
  - Generation implication: long samples will still load from disk as long as the OP‑XY accepts them, but if you’re trying to match on‑device behavior, keep one‑shot samples comfortably under ~20 seconds (~`882000` frames @ 44.1kHz).
- **Stereo sampling:** sampling is described as **stereo** on OP‑XY.
  - Generation implication: `patch.json` doesn’t declare sample format, so external tools should normalize audio to a known‑good format (common convention: WAV PCM16, 44.1kHz, stereo), and set `framecount`/`sample.end` based on the decoded frame length after conversion.

## 7) Open questions / next reverse‑engineering steps

- Confirm the exact mapping of:
  - `engine.params[4..7]` (when used)
  - `fx.params[*]` per `fx.type`
  - `lfo.params[*]` per `lfo.type`
  - `engine.modulation.*.target` destination IDs
- Clarify region mapping rules (especially `lokey`/`hikey`) and loop crossfade semantics; exported presets and community generators don’t always match.
- Derive a permissive JSON Schema once defaults and ranges are confirmed.

## 8) Sample source sweep: `/Users/Shared` (Native Instruments content)

This section is about **finding raw audio** suitable for creating new OP‑XY sample presets (especially `type: "sampler"` and `type: "multisampler"`).

### 8.1 Broad counts (entire tree)

Observed file counts under `/Users/Shared`:

- Audio: `110187` `*.wav`, `142703` `*.ogg`, `1160` `*.flac`, `0` `*.aif/*.aiff`
- MIDI/loops: `11157` `*.mid`, `321` `*.rx2`
- Kontakt packaging: `3120` `*.nki`, `474` `*.nkx`, `611` `*.nkc`, `138` `*.nkr`

Top-level structure:

- `212` top-level directories
- `150` directories matching `* Library`

### 8.2 High‑value “direct audio” libraries (easy sources)

These have lots of raw `*.wav` on disk (so they’re straightforward to turn into OP‑XY `.preset/` folders):

- `/Users/Shared/Maschine 2 Library/Samples` (~`21190` WAV) — well organized into `Drums/`, `Instruments/`, `Loops/`, `One Shots/`
- `/Users/Shared/Battery 4 Factory Library/Samples` (~`12434` WAV) — mostly drums/one‑shots
- Examples of expansion libraries with ~1–3k WAV each (not exhaustive): `Vintage Heat`, `Marble Rims Library`, `True School Library`, `Street Swarm Library`, `Sierra Grove Library`, `Raw Voltage Library`, `Circuit Halo Library`, `Liquid Energy Library`, `Deep Matter Library`, `Elastic Thump Library`

### 8.3 Note‑named multisample sets (best candidates for `multisampler`)

Many expansions include note-labeled filenames like `Something F#3.wav`, which can be grouped into multisample sets by basename + folder.

Broad scan result:

- `637` multisample-ish groups with ≥8 distinct root notes detected across `/Users/Shared`.
- Top dirs by number of such groups: `Maschine 2 Library (134)`, `True School Library (67)`, `Plugin Boutique (49)`, `Marble Rims Library (38)`, `Vintage Heat (30)`.
- Largest single-group note coverage observed: `Lucid Mission Library (67 notes)`, `Elastic Thump Library (64)`, `Marble Rims Library (61)`, `DJ Khalil Library (61)`, `Vintage Heat (56)`, `Maschine 2 Library (53)`.

Example groups (paths show the naming pattern):

- `/Users/Shared/Lucid Mission Library/Samples/Instruments/Keys/Compressed Piano Samples/Compressed Piano C3.wav`
- `/Users/Shared/Elastic Thump Library/Samples/Instruments/Bass/SwampBass E2.wav`
- `/Users/Shared/Plugin Boutique/Scaler2/Sounds/RetroBass/RetroBass-C2.flac` (FLAC → convert to WAV for OP‑XY)

### 8.4 “Container” Kontakt libraries (often require resampling)

Many Kontakt libraries store their audio in `.nkx/.nkc/.nkr` containers (with `.nki` instruments) and do not expose raw WAV on disk (e.g., orchestral/session/string libraries).

Practical implication: to build OP‑XY sampled instruments from these, plan on **auditioning in Kontakt and recording/bouncing** the notes you want as WAV, rather than copying samples directly.

### 8.5 `NBPL` previews

`/Users/Shared/NBPL` is dominated by `.ogg` preview files (in `Samples/<uuid>/.previews/*.nksf.ogg`), so it’s more useful for browsing than as a direct source for OP‑XY sampling.
