#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DrumSlot:
    note: int
    label: str
    rel_source: str
    playmode: str = "oneshot"


DRUM_SLOTS: tuple[DrumSlot, ...] = (
    DrumSlot(
        note=53,
        label="kick_hot_salsa_ds_1",
        rel_source="Magnate Hustle Library/Samples/Drums/Kick/Kick Hot Salsa DS 1.wav",
    ),
    DrumSlot(
        note=54,
        label="kick_hotsauce_1",
        rel_source="Caribbean Current Library/Samples/Drums/Kick/Kick HotSauce 1.wav",
    ),
    DrumSlot(
        note=55,
        label="snare_loveaddict_1",
        rel_source="Magnate Hustle Library/Samples/Drums/Snare/Snare LoveAddict 1.wav",
    ),
    DrumSlot(
        note=56,
        label="snare_hotsauce_1",
        rel_source="Caribbean Current Library/Samples/Drums/Snare/Snare HotSauce 1.wav",
    ),
    DrumSlot(
        note=57,
        label="rim_lavega",
        rel_source="Caribbean Current Library/Samples/Drums/Snare/Rim LaVega.wav",
    ),
    DrumSlot(
        note=58,
        label="clap_midnight",
        rel_source="Magnate Hustle Library/Samples/Drums/Clap/Clap Midnight.wav",
    ),
    DrumSlot(
        note=59,
        label="tamb_avocado",
        rel_source="Caribbean Current Library/Samples/Drums/Percussion/Tamb Avocado.wav",
    ),
    DrumSlot(
        note=60,
        label="shaker_carnival",
        rel_source="Caribbean Current Library/Samples/Drums/Shaker/Shaker Carnival.wav",
    ),
    DrumSlot(
        note=61,
        label="closedhh_hot_salsa_ds",
        rel_source="Magnate Hustle Library/Samples/Drums/Hihat/ClosedHH Hot Salsa DS.wav",
        playmode="group",
    ),
    DrumSlot(
        note=62,
        label="openhh_percussionista",
        rel_source="Caribbean Current Library/Samples/Drums/Hihat/OpenHH Percussionista.wav",
        playmode="group",
    ),
    DrumSlot(
        note=63,
        label="closedhh_clean2hiss_1",
        rel_source="Magnate Hustle Library/Samples/Drums/Hihat/ClosedHH Clean2Hiss 1.wav",
        playmode="group",
    ),
    DrumSlot(
        note=64,
        label="clave_avocado",
        rel_source="Caribbean Current Library/Samples/Drums/Percussion/Clave Avocado.wav",
    ),
    DrumSlot(
        note=65,
        label="tom_uptobat_1",
        rel_source="Magnate Hustle Library/Samples/Drums/Tom/Tom UpToBat 1.wav",
    ),
    DrumSlot(
        note=66,
        label="crash_darkred",
        rel_source="Magnate Hustle Library/Samples/Drums/Cymbal/Crash DarkRed.wav",
    ),
    DrumSlot(
        note=67,
        label="tom_uptobat_2",
        rel_source="Magnate Hustle Library/Samples/Drums/Tom/Tom UpToBat 2.wav",
    ),
    DrumSlot(
        note=68,
        label="ride_wildout",
        rel_source="Magnate Hustle Library/Samples/Drums/Cymbal/Ride WildOut.wav",
    ),
    DrumSlot(
        note=69,
        label="tom_uptobat_3",
        rel_source="Magnate Hustle Library/Samples/Drums/Tom/Tom UpToBat 3.wav",
    ),
    DrumSlot(
        note=70,
        label="timbale_karnaval",
        rel_source="Caribbean Current Library/Samples/Drums/Percussion/Timbale Karnaval.wav",
    ),
    DrumSlot(
        note=71,
        label="conga_bazouka_1",
        rel_source="Caribbean Current Library/Samples/Drums/Percussion/Conga Bazouka 1.wav",
    ),
    DrumSlot(
        note=72,
        label="conga_bazouka_2",
        rel_source="Caribbean Current Library/Samples/Drums/Percussion/Conga Bazouka 2.wav",
    ),
    DrumSlot(
        note=73,
        label="cowbell_hotsauce_1",
        rel_source="Caribbean Current Library/Samples/Drums/Percussion/Cowbell HotSauce 1.wav",
    ),
    DrumSlot(
        note=74,
        label="guiro_avo_1",
        rel_source="Caribbean Current Library/Samples/Drums/Percussion/Guiro Avo 1.wav",
    ),
    DrumSlot(
        note=75,
        label="bell_atsteppa",
        rel_source="Caribbean Current Library/Samples/Drums/Percussion/Bell AtSteppa.wav",
    ),
    DrumSlot(
        note=76,
        label="castanets_avocado",
        rel_source="Caribbean Current Library/Samples/Drums/Percussion/Castanets Avocado.wav",
    ),
)


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def safe_slug(text: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_").lower()
    return slug or "sample"


def wav_framecount(path: Path) -> int:
    with wave.open(str(path), "rb") as w:
        return int(w.getnframes())


def ensure_empty_dir(path: Path, overwrite: bool) -> None:
    if path.exists():
        if not overwrite:
            raise FileExistsError(f"Refusing to overwrite existing directory: {path}")
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=False)


def convert_to_opxy_wav(src: Path, dst: Path) -> None:
    run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(src),
            "-ac",
            "2",
            "-ar",
            "44100",
            "-c:a",
            "pcm_s16le",
            str(dst),
        ]
    )


def build_drum_preset(preset_dir: Path, shared_root: Path) -> dict:
    regions: list[dict] = []
    for slot in sorted(DRUM_SLOTS, key=lambda s: s.note):
        src = shared_root / slot.rel_source
        if not src.is_file():
            raise FileNotFoundError(f"Missing source sample: {src}")

        out_name = f"{slot.note:02d}_{safe_slug(slot.label)}.wav"
        out_path = preset_dir / out_name
        convert_to_opxy_wav(src, out_path)
        frames = wav_framecount(out_path)

        regions.append(
            {
                "fade.in": 0,
                "fade.out": 0,
                "framecount": frames,
                "hikey": slot.note,
                "lokey": slot.note,
                "gain": 0,
                "pan": 0,
                "pitch.keycenter": 60,
                "playmode": slot.playmode,
                "reverse": False,
                "sample": out_name,
                "sample.end": frames,
                "transpose": 0,
                "tune": 0,
            }
        )

    # Template based on community tools and teopxy converter output.
    return {
        "version": 4,
        "platform": "OP-XY",
        "type": "drum",
        "octave": 0,
        "engine": {
            "bendrange": 8191,
            "highpass": 0,
            "modulation": {
                "aftertouch": {"amount": 16383, "target": 0},
                "modwheel": {"amount": 16383, "target": 0},
                "pitchbend": {"amount": 16383, "target": 0},
                "velocity": {"amount": 16383, "target": 0},
            },
            "params": [16384] * 8,
            "playmode": "poly",
            "portamento.amount": 0,
            "portamento.type": 32767,
            "transpose": 0,
            "tuning.root": 0,
            "tuning.scale": 0,
            "velocity.sensitivity": 19660,
            "volume": 18348,
            "width": 0,
        },
        "envelope": {
            "amp": {"attack": 0, "decay": 0, "release": 1000, "sustain": 32767},
            "filter": {"attack": 0, "decay": 14581, "release": 0, "sustain": 0},
        },
        "fx": {"active": False, "params": [22014, 0, 30285, 11880, 0, 32767, 0, 0], "type": "ladder"},
        "lfo": {"active": False, "params": [6212, 16865, 18344, 16000, 0, 0, 0, 0], "type": "tremolo"},
        "regions": regions,
    }


def build_808_sampler_preset(preset_dir: Path, shared_root: Path) -> dict:
    src = shared_root / "Magnate Hustle Library/Samples/One Shots/Synth Note/Bass LoveAddict E1.wav"
    if not src.is_file():
        raise FileNotFoundError(f"Missing source sample: {src}")

    out_name = "bass_loveaddict_e1.wav"
    out_path = preset_dir / out_name
    convert_to_opxy_wav(src, out_path)
    frames = wav_framecount(out_path)

    # Match the common factory-style default loop points (~20%/80% of the sample).
    loop_start = max(0, int(frames * 0.2))
    loop_end = max(loop_start + 1, int(frames * 0.8))

    region = {
        "framecount": frames,
        "gain": 0,
        "hikey": 96,
        "lokey": 0,
        "loop.crossfade": 3,
        "loop.enabled": True,
        "loop.end": loop_end,
        "loop.onrelease": True,
        "loop.start": loop_start,
        "pitch.keycenter": 28,  # E1
        "reverse": False,
        "sample": out_name,
        "sample.end": frames,
        "sample.start": 0,
        "tune": 0,
    }

    # Template based on observed sampler presets, with conservative defaults.
    return {
        "version": 4,
        "platform": "OP-XY",
        "type": "sampler",
        "octave": 0,
        "engine": {
            "bendrange": 23919,
            "highpass": 0,
            "modulation": {
                "aftertouch": {"amount": 16384, "target": 0},
                "modwheel": {"amount": 16384, "target": 0},
                "pitchbend": {"amount": 16384, "target": 0},
                "velocity": {"amount": 16384, "target": 0},
            },
            "params": [16384] * 8,
            "playmode": "mono",
            "portamento.amount": 0,
            "portamento.type": 0,
            "transpose": 0,
            "tuning.root": 0,
            "tuning.scale": 0,
            "velocity.sensitivity": 24903,
            "volume": 20642,
            "width": 0,
        },
        "envelope": {
            "amp": {"attack": 0, "decay": 32767, "release": 12000, "sustain": 32767},
            "filter": {"attack": 0, "decay": 32767, "release": 0, "sustain": 32767},
        },
        "fx": {"active": False, "params": [0, 0, 0, 0, 0, 0, 0, 0], "type": "svf"},
        "lfo": {"active": False, "params": [0, 0, 0, 0, 0, 0, 0, 0], "type": "tremolo"},
        "regions": [region],
    }


def write_patch_json(preset_dir: Path, payload: dict) -> None:
    patch_path = preset_dir / "patch.json"
    with patch_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Latin Trap OP-XY presets from NI content in /Users/Shared.")
    parser.add_argument("--shared-root", default="/Users/Shared", help="Root directory containing NI content.")
    parser.add_argument(
        "--out-dir",
        default=str(Path.home() / "Documents" / "xy-remix" / "generated-presets" / "latin_trap"),
        help="Output directory for generated .preset folders.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing preset output directories.")
    args = parser.parse_args()

    shared_root = Path(args.shared_root).expanduser()
    out_dir = Path(args.out_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    drum_dir = out_dir / "LatinTrap_DrumKit.preset"
    ensure_empty_dir(drum_dir, overwrite=bool(args.overwrite))
    drum_patch = build_drum_preset(drum_dir, shared_root=shared_root)
    write_patch_json(drum_dir, drum_patch)

    bass_dir = out_dir / "LatinTrap_808Sub.preset"
    ensure_empty_dir(bass_dir, overwrite=bool(args.overwrite))
    bass_patch = build_808_sampler_preset(bass_dir, shared_root=shared_root)
    write_patch_json(bass_dir, bass_patch)

    print(f"Wrote: {drum_dir}")
    print(f"Wrote: {bass_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
