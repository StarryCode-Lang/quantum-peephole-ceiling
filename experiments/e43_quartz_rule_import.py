"""Generate and verify the v13 Quartz-derived rule library."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.optimisation.quartz_rule_import import write_outputs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ecc", type=Path, required=True)
    parser.add_argument("--source-metadata", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    receipt = write_outputs(args.ecc, args.source_metadata, args.output_root)
    print(receipt)
    return 0 if receipt["status"] == "PASS_STAGE_S2_E43" else 2


if __name__ == "__main__":
    raise SystemExit(main())
