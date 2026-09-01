"""Fail-closed structural verifier for the checked-in CycloneDX SBOM."""

from __future__ import annotations

import hashlib
import json
import re
import tomllib
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SBOM = PROJECT_ROOT / "release" / "sbom.cdx.json"
DIRECT_REQUIREMENTS = PROJECT_ROOT / "requirements.txt"
PYPROJECT = PROJECT_ROOT / "pyproject.toml"


def _normalise(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _direct_requirement_names(path: Path) -> set[str]:
    names = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = re.match(r"([A-Za-z0-9_.-]+)", stripped)
        if match:
            names.add(_normalise(match.group(1)))
    return names


def verify_sbom(path: Path = SBOM) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("bomFormat") != "CycloneDX" or payload.get("specVersion") != "1.6":
        raise ValueError("SBOM must be CycloneDX JSON specification 1.6")
    if "serialNumber" in payload or "timestamp" in payload.get("metadata", {}):
        raise ValueError("SBOM is not reproducible: volatile serial/timestamp present")

    project = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))["project"]
    root = payload.get("metadata", {}).get("component", {})
    if root.get("name") != project["name"] or root.get("version") != project["version"]:
        raise ValueError("SBOM root component does not match pyproject name/version")

    components = payload.get("components", [])
    refs = [component.get("bom-ref") for component in components]
    if any(not ref for ref in refs) or len(refs) != len(set(refs)):
        raise ValueError("SBOM component bom-ref values must be present and unique")
    if any(not component.get("name") or not component.get("version") for component in components):
        raise ValueError("every SBOM component must have a name and version")
    component_names = {_normalise(component["name"]) for component in components}
    direct_names = _direct_requirement_names(DIRECT_REQUIREMENTS)
    missing_direct = sorted(direct_names - component_names)
    if missing_direct:
        raise ValueError(f"SBOM omits direct requirements: {missing_direct}")
    direct_refs = {
        component["bom-ref"]
        for component in components
        if _normalise(component["name"]) in direct_names
    }
    root_ref = root.get("bom-ref")
    root_dependency = next(
        (
            dependency
            for dependency in payload.get("dependencies", [])
            if dependency.get("ref") == root_ref
        ),
        None,
    )
    if root_dependency is None or not direct_refs.issubset(
        set(root_dependency.get("dependsOn", []))
    ):
        raise ValueError("SBOM root dependency graph omits direct requirements")

    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "status": "verified",
        "spec_version": payload["specVersion"],
        "root_component": f"{root['name']}=={root['version']}",
        "components": len(components),
        "direct_requirements_covered": len(direct_names),
        "sha256": digest,
    }


def main() -> int:
    print(json.dumps(verify_sbom(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
