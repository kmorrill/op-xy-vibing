# OP‑XY Synth Engines: Parameter Behaviors and Sound‑Design Notes

This guide summarizes how each of the OP‑XY’s synth engines responds as you move its four engine parameters (P1–P4) from low to high. It blends observations from the official guide with oscilloscope‑driven analysis to highlight spectrum changes, modulation behavior, and useful interactions. Use this as a creative companion when proposing CC/parameter edits in loops.

## Simple (virtual‑analogue)

- P1 – shape: Morphs from sawtooth toward square. Low = bright saw; mid rounds off; high ≈ square (hollow, thinner).
- P2 – pulse width: Adjusts square duty/PWM. Higher values narrow the pulse, emphasizing odd harmonics and nasal tone.
- P3 – noise: Adds white noise. Low = clean; high = hissy/gritty with more HF content.
- P4 – stereo phaser: Stereo width via phase‑shifting. Low = centered; high = wider, animated image.

## Prism (dual‑oscillator)

- P1 – shape: Both oscillators from saw→square; near max introduces asymmetric PW, emphasizing 2nd harmonic (extra color).
- P2 – ratio: Steps through musical intervals (fifths/fourths). Higher = more complex/dissonant spectra.
- P3 – detune: Limited detune of osc2. Low = subtle chorus; high = audible beating/fatness.
- P4 – stereo phaser: Like Simple; increases width and motion at higher settings.

## Wavetable (wavetable/FM hybrid)

- P1 – table: Chooses 1 of 9 wavetables with distinct harmonic sets.
- P2 – position: Scans within the selected table. Small moves = gentle morph; long sweeps = drastic timbre shifts.
- P3 – warp / FM amount: PW/warping with FM‑like sidebands. Higher = more inharmonic partials/instability.
- P4 – detune / FM depth: Detunes osc2 to drive FM. Higher = clanging/bell‑like metallic overtones.

## Axis (two‑operator FM with filter)

- P1 – low‑pass filter: Dark→bright with notable resonance. Higher opens filter, revealing more harmonics.
- P2 – operator tuning: From −1 octave to +1 at mid, then up to +5 octaves via fifth/fourth leaps; shifts FM relationship and tension.
- P3 – wave shape: Operators morph saw↔triangle. Low = rich/buzzy; high = smoother/rounder.
- P4 – tremolo: Volume modulation. Low = slow/subtle; high = fast/pronounced, string‑like.

## Epiano (electric piano emulation)

- P1 – modulation amount & shape: Sine carrier modulated by saw/square. Higher = richer harmonics; modulator shape morphs.
- P2 – carrier shape: Sine→triangle‑like. Higher = stronger low‑order partials and brightness.
- P3 – attack enhancer: Adds fast‑decaying higher‑pitched attack. Higher = more “tine”/bite.
- P4 – decay time: Length of modulation decay to pure carrier. Higher = shorter decay for pluckier EP response.

## Organ (organ/FM hybrid)

- P1 – type/registration: Chooses organ model/registration and FM algo; sets base harmonic mix.
- P2 – bass/harmonic mix: Adds sub in some modes or mixes higher partials in others. Higher = thicker/detuned variants.
- P3 – tremolo depth & P4 – tremolo rate: Depth sets modulation amount; rate sets speed. Slow/shallow = gentle; fast/deep = rotary‑like.

## Hardsync (synced saw leads)

- P1 – detune: Detunes two hard‑synced saws over ~3 octaves. Higher = wider spread and harsher bite.
- P2 – sub: Adds a sub at fundamental; when sync jumps octaves, behaves like true sub‑bass anchor.
- P3 – noise: White noise mix. Higher = more grit/digital edge.
- P4 – high‑pass filter: Removes lows. Higher = thinner/edgier, noise accentuated.

## Dissolve (noise‑modulated AM/FM)

- P1 – noise & pitch modulation: Sets noise mix and random pitch mod rate/intensity. Higher = more wobble/instability.
- P2 – AM: Noise‑driven amplitude modulation. Higher = deeper tremolo and added sidebands.
- P3 – FM: Noise‑driven frequency modulation. Higher = metallic/bell‑like inharmonic overtones.
- P4 – detune: Detunes two sines up to ~minor second. Higher = stronger beating; interacts with P1 for evolving base tone.

---

## Using These Insights

- Low vs high: Lower values favor fundamental‑heavy, smoother timbres; higher values add harmonics, modulation, and stereo motion.
- Spectrum dependence: Filters (Axis P1, Hardsync P4) shape frequency emphasis; modulation controls (Dissolve P2–P3, Wavetable P3–P4) introduce inharmonics/randomness as they rise.
- Interplay: Axis P1+P2 together set FM color; Dissolve P1+P4 establish base beating/noise envelope with P2/P3 for fine modulation.
- Creative starting points: Begin around mid settings, then push extremes to explore. Use low settings for clean tones; high to add grit, motion, or density.

