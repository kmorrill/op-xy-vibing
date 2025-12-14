#!/usr/bin/env python3
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable


AUDIO_EXTS = {".wav", ".flac", ".ogg"}

NOTE_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9])([A-G])([#b])?(-?\d)(?![A-Za-z0-9])")

DRUM_KEYWORDS = (
    "kick",
    "snare",
    "clap",
    "rim",
    "hat",
    "hihat",
    "hi-hat",
    "tom",
    "cymbal",
    "crash",
    "ride",
    "shaker",
    "tamb",
    "conga",
    "bongo",
    "cowbell",
    "perc",
    "percussion",
    "drum",
)

VOCAL_KEYWORDS = (
    "vocal",
    "vox",
    "choir",
    "adlib",
    "ad-lib",
)

AMBIENT_KEYWORDS = (
    "ambience",
    "ambient",
    "atmo",
    "atmos",
    "atmosphere",
    "texture",
    "drone",
    "swell",
    "sweep",
    "field",
    "rain",
    "wind",
    "space",
    "cinematic",
    "noise",
    "fx",
    "sfx",
)


@dataclasses.dataclass(frozen=True)
class StyleSpec:
    slug: str
    name: str
    sources: tuple[str, ...]
    desired_counts: dict[str, int]


STYLE_SPECS: list[StyleSpec] = [
    StyleSpec(
        slug="synthwave_new_wave",
        name="Synthwave / 80s New Wave",
        sources=(
            "80s New Wave Library",
            "Neon Drive Library",
            "Faded Reels Library",
            "Vintage Heat",
            "Nocturnal State Library",  # Massive soundpack previews
            "Spectrum Quake Library",  # Massive soundpack previews
            "Hot Vocals Library",
        ),
        desired_counts={"drums": 24, "loop": 8, "vocal": 8, "ambient": 10, "instrument": 18, "preview": 10},
    ),
    StyleSpec(
        slug="afrobeats_afro_fusion",
        name="Afrobeats / Afro-fusion",
        sources=("Afrobeats Library", "Caribbean Current Library", "Hot Vocals Library", "Ambient Atmospheres Library"),
        desired_counts={"drums": 24, "loop": 10, "vocal": 8, "ambient": 8, "instrument": 18, "preview": 10},
    ),
    StyleSpec(
        slug="disco_funk_boogie",
        name="Disco / Funk / Modern Boogie",
        sources=("Disco and Funk Library", "Soul Gold Library", "Velvet Lounge Library", "Hot Vocals Library"),
        desired_counts={"drums": 24, "loop": 8, "vocal": 8, "ambient": 8, "instrument": 20, "preview": 10},
    ),
    StyleSpec(
        slug="boom_bap_lofi",
        name="Boom-bap / Lo-fi Hip Hop",
        sources=("Drum Breaks Library", "True School Library", "Faded Reels Library", "Lucid Mission Library", "Hot Vocals Library"),
        desired_counts={"drums": 24, "loop": 8, "vocal": 8, "ambient": 10, "instrument": 18, "preview": 10},
    ),
    StyleSpec(
        slug="trap_latin_trap",
        name="Trap / Latin Trap",
        sources=("Latin Trap Library", "Magnate Hustle Library", "Raw Voltage Library", "Hot Vocals Library", "Stadium Flex Library"),
        desired_counts={"drums": 24, "loop": 8, "vocal": 8, "ambient": 8, "instrument": 20, "preview": 10},
    ),
    StyleSpec(
        slug="progressive_trance_melodic_techno",
        name="Progressive Trance / Melodic Techno",
        sources=("Progressive Trance Library", "Raw Voltage Library", "Warped Symmetry Library", "Circuit Halo Library", "Spectrum Quake Library"),
        desired_counts={"drums": 22, "loop": 10, "vocal": 6, "ambient": 10, "instrument": 20, "preview": 12},
    ),
    StyleSpec(
        slug="rnb_neo_soul_pop_rnb",
        name="R&B / Neo-soul / Pop-R&B",
        sources=("RnB Licks Library", "Platinum Pop Library", "Soul Gold Library", "Velvet Lounge Library", "Hot Vocals Library"),
        desired_counts={"drums": 22, "loop": 8, "vocal": 10, "ambient": 8, "instrument": 20, "preview": 12},
    ),
    StyleSpec(
        slug="cinematic_ambient_downtempo",
        name="Cinematic Ambient / Downtempo",
        sources=("Ambient Atmospheres Library", "Fade Library", "Lucid Mission Library", "Halcyon Sky Library", "Deep Matter Library", "Nocturnal State Library"),
        desired_counts={"drums": 10, "loop": 6, "vocal": 6, "ambient": 26, "instrument": 12, "preview": 20},
    ),
]


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def ffprobe_duration_seconds(path: Path) -> float | None:
    try:
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nk=1:nw=1", str(path)],
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception:
        return None
    try:
        return float(proc.stdout.strip())
    except Exception:
        return None


def iter_audio_files(root: Path) -> Iterable[Path]:
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            path = Path(dirpath) / filename
            if path.suffix.lower() in AUDIO_EXTS:
                yield path


def iter_preview_oggs(root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        if Path(dirpath).name != ".previews":
            continue
        for filename in filenames:
            if filename.lower().endswith(".ogg"):
                yield Path(dirpath) / filename


def categorize_audio(path: Path) -> str:
    lower_path = str(path).lower()
    lower_name = path.name.lower()

    if "/.previews/" in lower_path or path.suffix.lower() == ".ogg":
        return "preview"

    if any(k in lower_name for k in VOCAL_KEYWORDS) or "/vocal" in lower_path or "/vocals/" in lower_path:
        return "vocal"

    if "/samples/loops/" in lower_path or "/loops/" in lower_path or " bpm" in lower_name or "bpm" in lower_name or "loop" in lower_name:
        return "loop"

    if any(k in lower_name for k in DRUM_KEYWORDS) or "/samples/drums/" in lower_path or "/drums/" in lower_path:
        return "drums"

    if any(k in lower_name for k in AMBIENT_KEYWORDS) or any(k in lower_path for k in AMBIENT_KEYWORDS):
        return "ambient"

    if "/samples/instruments/" in lower_path or NOTE_TOKEN_RE.search(path.stem):
        return "instrument"

    return "instrument"


def pick_many(rng: random.Random, items: list[Path], count: int) -> list[Path]:
    if count <= 0 or not items:
        return []
    if count >= len(items):
        rng.shuffle(items)
        return items
    return rng.sample(items, count)


def build_lookbook_for_style(
    style: StyleSpec,
    shared_root: Path,
    out_dir: Path,
    seed: int,
    keep_work: bool,
) -> Path:
    rng = random.Random(seed)

    source_dirs: list[Path] = []
    for name in style.sources:
        candidate = shared_root / name
        if candidate.is_dir():
            source_dirs.append(candidate)
        else:
            print(f"[warn] missing source dir: {candidate}", file=sys.stderr)

    samples: list[Path] = []
    previews: list[Path] = []
    for source_dir in source_dirs:
        samples_dir = source_dir / "Samples"
        if samples_dir.is_dir():
            samples.extend(iter_audio_files(samples_dir))
        previews.extend(iter_preview_oggs(source_dir))

    candidates: dict[str, list[Path]] = {k: [] for k in ("drums", "loop", "vocal", "ambient", "instrument", "preview")}
    for path in samples:
        category = categorize_audio(path)
        candidates[category].append(path)
    for path in previews:
        candidates["preview"].append(path)

    # De-duplicate while keeping determinism.
    for category, paths in candidates.items():
        unique_sorted = sorted(set(paths))
        rng.shuffle(unique_sorted)
        candidates[category] = unique_sorted

    desired_total = sum(style.desired_counts.values())
    selected: list[tuple[str, Path]] = []
    used: set[Path] = set()

    for category, desired in style.desired_counts.items():
        available = [p for p in candidates.get(category, []) if p not in used]
        picked = pick_many(rng, available, desired)
        for p in picked:
            selected.append((category, p))
            used.add(p)

    # Fill gaps from whatever is left (prioritize instrument/ambient/preview).
    shortage = desired_total - len(selected)
    if shortage > 0:
        pool_categories = ("instrument", "ambient", "preview", "loop", "drums", "vocal")
        pool: list[Path] = []
        for category in pool_categories:
            pool.extend([p for p in candidates.get(category, []) if p not in used])
        pool = sorted(set(pool))
        rng.shuffle(pool)
        for p in pool[:shortage]:
            selected.append((categorize_audio(p), p))
            used.add(p)

    rng.shuffle(selected)

    work_dir = out_dir / f".work_{style.slug}"
    work_dir.mkdir(parents=True, exist_ok=True)

    # Silence segment to space clips a bit.
    silence_path = work_dir / "silence.wav"
    run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=stereo",
            "-t",
            "0.12",
            "-c:a",
            "pcm_s16le",
            str(silence_path),
        ]
    )

    duration_ranges = {
        "drums": (0.35, 0.90),
        "loop": (1.50, 3.00),
        "vocal": (1.50, 2.80),
        "ambient": (3.00, 6.00),
        "instrument": (1.50, 3.00),
        "preview": (1.50, 2.80),
    }

    manifest_entries: list[dict[str, object]] = []
    clip_paths: list[Path] = []

    for index, (category, src) in enumerate(selected, start=1):
        clip_len = rng.uniform(*duration_ranges.get(category, (1.5, 2.5)))
        clip_len = round(clip_len, 2)

        src_duration = ffprobe_duration_seconds(src)
        if src_duration is None or src_duration <= 0:
            start = 0.0
        else:
            max_start = max(0.0, src_duration - clip_len)
            start = rng.uniform(0.0, max_start) if max_start > 0.25 else 0.0
        start = round(start, 2)

        out_clip = work_dir / f"{index:04d}.wav"

        # Small fade to reduce clicks, but keep it minimal (the content is still just concatenated).
        fade_in = 0.01
        fade_out = 0.03
        fade_out_start = max(0.0, clip_len - fade_out)
        afade = f"afade=t=in:st=0:d={fade_in},afade=t=out:st={fade_out_start}:d={fade_out}"

        try:
            run(
                [
                    "ffmpeg",
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-ss",
                    str(start),
                    "-t",
                    str(clip_len),
                    "-i",
                    str(src),
                    "-af",
                    afade,
                    "-ac",
                    "2",
                    "-ar",
                    "44100",
                    "-c:a",
                    "pcm_s16le",
                    str(out_clip),
                ]
            )
        except subprocess.CalledProcessError:
            print(f"[warn] ffmpeg failed, skipping: {src}", file=sys.stderr)
            continue

        clip_paths.append(out_clip)
        manifest_entries.append(
            {
                "index": index,
                "category": category,
                "src": str(src),
                "start": start,
                "duration": clip_len,
            }
        )

    concat_list = work_dir / "concat.txt"
    with concat_list.open("w", encoding="utf-8") as f:
        for i, clip in enumerate(clip_paths):
            f.write(f"file '{clip.name}'\n")
            if i != len(clip_paths) - 1:
                f.write("file 'silence.wav'\n")

    out_path = out_dir / f"{style.slug}.lookbook.wav"
    run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-c:a",
            "pcm_s16le",
            "-ar",
            "44100",
            "-ac",
            "2",
            str(out_path),
        ]
    )

    manifest_path = out_dir / f"{style.slug}.manifest.json"
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "style": dataclasses.asdict(style),
                "seed": seed,
                "clips": manifest_entries,
            },
            f,
            indent=2,
        )

    if not keep_work:
        shutil.rmtree(work_dir, ignore_errors=True)

    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Create NI sample 'lookbook' WAVs by concatenating short clips.")
    parser.add_argument("--shared-root", default="/Users/Shared", help="Root directory containing NI content.")
    parser.add_argument(
        "--out-dir",
        default=str(Path.home() / "Documents" / "xy-remix" / "lookbooks"),
        help="Output directory for generated WAVs and manifests.",
    )
    parser.add_argument("--seed", type=int, default=20251214, help="Base RNG seed.")
    parser.add_argument("--style", action="append", default=[], help="Style slug(s) to build (repeatable). Default: all.")
    parser.add_argument("--keep-work", action="store_true", help="Keep intermediate per-clip WAVs.")

    args = parser.parse_args()

    shared_root = Path(args.shared_root).expanduser()
    out_dir = Path(args.out_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    selected_styles = STYLE_SPECS
    if args.style:
        wanted = set(args.style)
        selected_styles = [s for s in STYLE_SPECS if s.slug in wanted]
        missing = wanted - {s.slug for s in selected_styles}
        for slug in sorted(missing):
            print(f"[warn] unknown style slug: {slug}", file=sys.stderr)

    for style in selected_styles:
        # Derive a stable per-style seed so reruns are reproducible but distinct.
        derived_seed = (args.seed * 1315423911 + sum(ord(c) for c in style.slug)) & 0xFFFFFFFF
        print(f"Building: {style.slug} -> {style.name}")
        out_path = build_lookbook_for_style(
            style=style,
            shared_root=shared_root,
            out_dir=out_dir,
            seed=int(derived_seed),
            keep_work=bool(args.keep_work),
        )
        print(f"  wrote: {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

