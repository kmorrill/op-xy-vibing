#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from generate_latin_trap_presets import (
    build_808_sampler_preset,
    build_drum_preset,
    ensure_empty_dir,
    safe_slug,
    write_patch_json,
)


TRACK_PRESETS: dict[int, tuple[str, str]] = {
    1: ("LatinTrap_DrumKit", "drums"),
    2: ("LatinTrap_808Sub", "bass"),
}


def browser_path(drop_name: str, preset_name: str) -> str:
    """Return the preset-browser path the OP-XY project should store.

    The matching on-disk folder is:
      presets/<drop_name>/<preset_name>.preset

    The project/browser-facing value should therefore be:
      <drop_name>/<preset_name>
    """
    return f"{drop_name}/{preset_name}"


def open_finder(path: Path) -> None:
    subprocess.run(["open", str(path)], check=False)


def write_manifest(package_root: Path, drop_name: str, preset_root: Path, project_root: Path) -> Path:
    track_mappings = {
        str(track_no): {
            "role": role,
            "preset": browser_path(drop_name, preset_name),
            "preset_folder": f"presets/{drop_name}/{preset_name}.preset",
        }
        for track_no, (preset_name, role) in TRACK_PRESETS.items()
    }

    payload = {
        "opxy_package_layout": "drop-root-presets-v1",
        "copy_to_opxy_root": {
            "presets_folder": str(preset_root),
            "projects_folder": str(project_root),
        },
        "drop_name": drop_name,
        "track_mappings": track_mappings,
        "invariant": "Every track preset path is rewritten to <drop-name>/<preset-name>; do not preserve template track mappings.",
    }

    manifest_path = package_root / "manifest.json"
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return manifest_path


def validate_layout(package_root: Path, drop_name: str) -> None:
    for track_no, (preset_name, _role) in TRACK_PRESETS.items():
        expected = package_root / "presets" / drop_name / f"{preset_name}.preset"
        patch_json = expected / "patch.json"
        if not expected.is_dir() or not patch_json.is_file():
            raise FileNotFoundError(f"Track {track_no} maps to missing preset folder: {expected}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate an OP-XY drop package with presets nested under presets/<drop-name>/."
    )
    parser.add_argument("--shared-root", default="/Users/Shared", help="Root directory containing NI content.")
    parser.add_argument(
        "--out-dir",
        default=str(Path.home() / "Documents" / "xy-remix" / "opxy-copy"),
        help="Package root containing presets/ and projects/ folders to copy to the OP-XY root.",
    )
    parser.add_argument(
        "--drop-name",
        default="latin_trap",
        help="Folder name created directly under presets/. Keep this stable because project mappings use it.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Overwrite the existing presets/<drop-name> folder.")
    parser.add_argument("--open", action="store_true", help="Open Finder windows for the package root and drop preset folder.")
    args = parser.parse_args()

    shared_root = Path(args.shared_root).expanduser()
    package_root = Path(args.out_dir).expanduser()
    drop_name = safe_slug(args.drop_name)

    preset_root = package_root / "presets"
    project_root = package_root / "projects"
    drop_root = preset_root / drop_name
    project_root.mkdir(parents=True, exist_ok=True)
    ensure_empty_dir(drop_root, overwrite=bool(args.overwrite))

    drum_dir = drop_root / "LatinTrap_DrumKit.preset"
    drum_dir.mkdir(parents=True, exist_ok=False)
    drum_patch = build_drum_preset(drum_dir, shared_root=shared_root)
    write_patch_json(drum_dir, drum_patch)

    bass_dir = drop_root / "LatinTrap_808Sub.preset"
    bass_dir.mkdir(parents=True, exist_ok=False)
    bass_patch = build_808_sampler_preset(bass_dir, shared_root=shared_root)
    write_patch_json(bass_dir, bass_patch)

    validate_layout(package_root, drop_name)
    manifest_path = write_manifest(package_root, drop_name, preset_root, project_root)

    print(f"Wrote drop preset folder: {drop_root}")
    print(f"Wrote project folder: {project_root}")
    print(f"Wrote manifest: {manifest_path}")
    print("Project preset mappings:")
    for track_no, (preset_name, role) in TRACK_PRESETS.items():
        print(f"  track {track_no} ({role}): {browser_path(drop_name, preset_name)}")

    if args.open:
        open_finder(package_root)
        open_finder(drop_root)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
