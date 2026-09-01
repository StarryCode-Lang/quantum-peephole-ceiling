"""Reconstruct and verify E31's first-party Python import closure statically."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENVIRONMENT = ROOT / "data/v11/e31_factorial_pareto/formal_run/environment.json"
DISCLOSURE_GATE = ROOT / "data/v11/e31_factorial_pareto/transitive_source_provenance_gate.json"
DEFAULT_OUTPUT = ROOT / "release/e31_first_party_import_closure_audit.json"
ENTRYPOINTS = (
    "experiments/e31_formal_orchestrator.py",
    "experiments/e31_shared_rule_worker.py",
)
FIRST_PARTY_ROOTS = {"experiments", "src"}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _module_for_path(path: Path) -> str:
    relative = path.relative_to(ROOT).with_suffix("")
    parts = list(relative.parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _path_for_module(module: str) -> Path | None:
    parts = module.split(".")
    file_path = ROOT.joinpath(*parts).with_suffix(".py")
    package_path = ROOT.joinpath(*parts, "__init__.py")
    if file_path.is_file():
        return file_path
    if package_path.is_file():
        return package_path
    return None


def _package_initializers(module: str) -> set[str]:
    parts = module.split(".")
    initializers: set[str] = set()
    for stop in range(1, len(parts) + 1):
        candidate = ".".join(parts[:stop])
        path = ROOT.joinpath(*parts[:stop], "__init__.py")
        if path.is_file():
            initializers.add(candidate)
    return initializers


def _local_imports(path: Path) -> set[str]:
    module = _module_for_path(path)
    package = module if path.name == "__init__.py" else module.rsplit(".", 1)[0]
    discovered: set[str] = set()
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".", 1)[0] in FIRST_PARTY_ROOTS:
                    discovered.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base_parts = package.split(".")
                if node.level > len(base_parts):
                    raise ValueError(f"relative import escapes first-party root: {path}")
                base_parts = base_parts[: len(base_parts) - (node.level - 1)]
                if node.module:
                    base_parts.extend(node.module.split("."))
                base = ".".join(base_parts)
            else:
                base = str(node.module or "")
            if not base or base.split(".", 1)[0] not in FIRST_PARTY_ROOTS:
                continue
            if _path_for_module(base) is not None:
                discovered.add(base)
            for alias in node.names:
                candidate = f"{base}.{alias.name}"
                if _path_for_module(candidate) is not None:
                    discovered.add(candidate)
    return discovered


def resolve_first_party_closure() -> set[str]:
    pending = [_module_for_path(ROOT / relative) for relative in ENTRYPOINTS]
    resolved: set[str] = set()
    while pending:
        module = pending.pop()
        path = _path_for_module(module)
        if path is None:
            raise ValueError(f"first-party module does not resolve: {module}")
        relative = path.relative_to(ROOT).as_posix()
        if relative in resolved:
            continue
        resolved.add(relative)
        dependencies = _local_imports(path)
        for dependency in tuple(dependencies):
            dependencies.update(_package_initializers(dependency))
        pending.extend(sorted(dependencies))
    return resolved


def build_audit() -> dict:
    environment = json.loads(ENVIRONMENT.read_text(encoding="utf-8"))
    gate = json.loads(DISCLOSURE_GATE.read_text(encoding="utf-8"))
    direct = set(environment.get("source_sha256", {}))
    omitted = set(gate.get("omitted_first_party_import_closure", {}))
    resolved = resolve_first_party_closure()
    if direct & omitted:
        raise RuntimeError("direct and post-hoc E31 source inventories overlap")
    if resolved != direct | omitted:
        raise RuntimeError(
            "E31 import closure differs from the frozen plus disclosed inventories: "
            f"missing={sorted(resolved - direct - omitted)}, "
            f"extraneous={sorted((direct | omitted) - resolved)}"
        )
    for relative, expected in environment["source_sha256"].items():
        if _sha(ROOT / relative) != expected:
            raise RuntimeError(f"direct frozen source hash drift: {relative}")
    for relative, record in gate["omitted_first_party_import_closure"].items():
        if _sha(ROOT / relative) != record["sha256"]:
            raise RuntimeError(f"post-hoc closure source hash drift: {relative}")
    return {
        "status": "PASS_EXACT_STATIC_FIRST_PARTY_IMPORT_CLOSURE_RECONSTRUCTED",
        "entrypoints": list(ENTRYPOINTS),
        "resolved_source_count": len(resolved),
        "direct_prerun_frozen_count": len(direct),
        "posthoc_disclosed_count": len(omitted),
        "complete_cryptographic_prerun_source_closure": False,
        "dynamic_imports_not_proven": True,
        "environment_sha256": _sha(ENVIRONMENT),
        "transitive_source_provenance_gate_sha256": _sha(DISCLOSURE_GATE),
        "resolved_sources": {
            relative: _sha(ROOT / relative) for relative in sorted(resolved)
        },
    }


def verify_audit(path: Path = DEFAULT_OUTPUT) -> dict:
    recorded = json.loads(path.read_text(encoding="utf-8"))
    expected = build_audit()
    if recorded != expected:
        raise RuntimeError("recorded E31 import-closure audit is absent, stale, or inconsistent")
    return recorded


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    payload = build_audit()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
