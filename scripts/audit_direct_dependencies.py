"""Fail when release-critical Python imports rely on undeclared dependencies."""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REQUIREMENTS = ROOT / "requirements.txt"
SCAN_DIRS = ("src", "analysis", "experiments", "scripts")
IMPORT_TO_DISTRIBUTION = {
    "PIL": "pillow",
    "cirq": "cirq-core",
    "qiskit_aer": "qiskit-aer",
    "qiskit_ibm_runtime": "qiskit-ibm-runtime",
    "sklearn": "scikit-learn",
}
# These adapters are deliberately capability-detected and have explicit
# fallback/UNAVAILABLE semantics. They are not part of the core release path.
OPTIONAL_IMPORTS = {
    "mqt": "optional MQT Bench loader falls back to the recorded proxy suite",
    "pyvoqc": "optional VOQC adapter reports unavailable when the binding is absent",
}


def _normalise(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _requirements(path: Path) -> set[str]:
    result = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"([A-Za-z0-9_.-]+)", line.strip())
        if match:
            result.add(_normalise(match.group(1)))
    return result


def _local_roots(root: Path) -> set[str]:
    roots = set(SCAN_DIRS)
    roots.update(path.stem for path in root.glob("*.py"))
    for directory in SCAN_DIRS:
        source_root = root / directory
        roots.update(path.name for path in source_root.rglob("*") if path.is_dir())
        roots.update(path.stem for path in source_root.rglob("*.py"))
    return roots


def audit(requirements: Path = DEFAULT_REQUIREMENTS, root: Path = ROOT) -> dict:
    imports: dict[str, set[str]] = defaultdict(set)
    for directory in SCAN_DIRS:
        for path in (root / directory).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
            relative = path.relative_to(root).as_posix()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports[alias.name.split(".")[0]].add(relative)
                elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                    imports[node.module.split(".")[0]].add(relative)

    declared = _requirements(requirements)
    local = _local_roots(root)
    third_party: dict[str, dict[str, object]] = {}
    undeclared: dict[str, dict[str, object]] = {}
    for import_name, paths in sorted(imports.items()):
        if import_name in sys.stdlib_module_names or import_name in local:
            continue
        distribution = _normalise(IMPORT_TO_DISTRIBUTION.get(import_name, import_name))
        record = {
            "distribution": distribution,
            "declared": distribution in declared,
            "files": sorted(paths),
        }
        if import_name in OPTIONAL_IMPORTS:
            record["optional_reason"] = OPTIONAL_IMPORTS[import_name]
        elif distribution not in declared:
            undeclared[import_name] = record
        third_party[import_name] = record
    if undeclared:
        raise RuntimeError(
            "release-critical imports lack direct requirements: "
            + ", ".join(f"{name}->{item['distribution']}" for name, item in undeclared.items())
        )
    return {
        "status": "VERIFIED",
        "scanned_python_files": sum(1 for directory in SCAN_DIRS for _ in (root / directory).rglob("*.py")),
        "declared_distributions": sorted(declared),
        "third_party_imports": third_party,
        "optional_imports": OPTIONAL_IMPORTS,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requirements", type=Path, default=DEFAULT_REQUIREMENTS)
    args = parser.parse_args()
    print(json.dumps(audit(args.requirements.resolve()), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
