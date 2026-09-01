"""Generate the reproducible CycloneDX dependency inventory for Q-research."""

from __future__ import annotations

import os
import json
import re
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOL_VERSION = "7.3.1"
OUTPUT = PROJECT_ROOT / "release" / "sbom.cdx.json"


def _normalise(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _direct_requirement_names() -> set[str]:
    names = set()
    for line in (PROJECT_ROOT / "requirements.txt").read_text(
        encoding="utf-8"
    ).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = re.match(r"([A-Za-z0-9_.-]+)", stripped)
        if match:
            names.add(_normalise(match.group(1)))
    return names


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".json.tmp")
    command = [
        "uv", "tool", "run", "--from", f"cyclonedx-bom=={TOOL_VERSION}",
        "cyclonedx-py", "requirements", "requirements-lock.txt",
        "--pyproject", "pyproject.toml", "--mc-type", "application",
        "--sv", "1.6", "--output-reproducible", "--of", "JSON",
        "-o", str(temporary),
    ]
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)
    payload = json.loads(temporary.read_text(encoding="utf-8"))
    direct_names = _direct_requirement_names()
    direct_refs = sorted(
        component["bom-ref"]
        for component in payload.get("components", [])
        if _normalise(component.get("name", "")) in direct_names
    )
    root_ref = payload["metadata"]["component"]["bom-ref"]
    dependencies = payload.setdefault("dependencies", [])
    root_dependency = next(
        (dependency for dependency in dependencies if dependency.get("ref") == root_ref),
        None,
    )
    if root_dependency is None:
        root_dependency = {"ref": root_ref}
        dependencies.append(root_dependency)
    root_dependency["dependsOn"] = direct_refs
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temporary, OUTPUT)
    print(f"CycloneDX SBOM generated with cyclonedx-bom {TOOL_VERSION}: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
