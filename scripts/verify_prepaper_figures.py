"""Verify the mechanical publication requirements for pre-paper figures."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STEMS = (
    "fig01_rq1_listing_forest", "fig02_heldout_generator_rates",
    "fig03_tool_summary", "fig04_external_baselines",
)
SOURCE_FILES = (
    "fig01_rq1_listing_forest.csv", "fig02_heldout_generator_rates.csv",
    "fig03_tool_summary.csv", "fig04_external_baselines.csv",
)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--figure-dir", type=Path,
                        default=PROJECT_ROOT / "data" / "v10" / "prepaper" / "figures")
    args = parser.parse_args()
    root = args.figure_dir.resolve()
    records = []
    for stem in STEMS:
        paths = {suffix: root / f"{stem}.{suffix}" for suffix in ("pdf", "svg", "png")}
        if not all(path.is_file() and path.stat().st_size > 0 for path in paths.values()):
            raise RuntimeError(f"missing PDF/SVG/PNG set for {stem}")
        svg = paths["svg"].read_text(encoding="utf-8")
        if "<svg" not in svg or "<image" in svg:
            raise RuntimeError(f"{stem}: SVG missing or contains embedded raster image")
        with Image.open(paths["png"]) as image:
            dpi = image.info.get("dpi", (0.0, 0.0))
            if min(float(dpi[0]), float(dpi[1])) < 590.0:
                raise RuntimeError(f"{stem}: PNG DPI below 600-dpi tolerance: {dpi}")
            width, height = image.size
            if min(width, height) < 1200:
                raise RuntimeError(f"{stem}: PNG dimensions unexpectedly small: {image.size}")
        records.append({
            "stem": stem, "png_width": width, "png_height": height,
            "png_dpi_x": float(dpi[0]), "png_dpi_y": float(dpi[1]),
            **{f"{suffix}_sha256": _hash(path) for suffix, path in paths.items()},
        })
    source_records = []
    for name in SOURCE_FILES:
        path = root / "source_data" / name
        frame = pd.read_csv(path)
        if frame.empty:
            raise RuntimeError(f"empty figure source data: {name}")
        source_records.append({"file": name, "rows": len(frame),
                               "columns": list(frame.columns), "sha256": _hash(path)})
    audit = {"status": "mechanically_verified", "figures": records,
             "source_data": source_records,
             "manual_gate_remaining": "visual inspection for clipping, legibility, and interpretation"}
    output = root / "figure_audit.json"
    temporary = output.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(output)
    print(json.dumps({"status": audit["status"], "figures": len(records)}, sort_keys=True))


if __name__ == "__main__":
    main()
