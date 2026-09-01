"""Bounded GUOQ preflight and smoke adapter.

This adapter deliberately does not implement the shared-520 confirmatory run.
It establishes whether the official GUOQ artifact can execute on the current
host, records immutable artifact identities, and runs at most three selected
Nam-basis inputs with rewrite rules only.  Smoke rows are diagnostic evidence,
not paper-comparison rows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd
from qiskit import qasm2
from qiskit.quantum_info import Operator

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = (
    PROJECT_ROOT / "data" / "v10" / "prepaper" / "external_baselines" / "guoq"
)

OFFICIAL_REPOSITORY = "https://github.com/qqq-wisc/guoq"
OFFICIAL_SOURCE_COMMIT = "8c4c3a5a6dfc9f7fc375ec16c2180139f0a8cb1a"
OFFICIAL_ARTIFACT_DOI = "10.5281/zenodo.14057840"
OFFICIAL_ARTIFACT_CONCEPT_DOI = "10.5281/zenodo.14055562"
OFFICIAL_LICENSE = "Apache-2.0"
JAR_NAME = "GUOQ-1.0-jar-with-dependencies.jar"
JAR_MD5 = "8fe405b8f0dd61a48e7248d8bd0681b6"
JAR_SHA256 = "df09a32ea7d3df8e6c7877f833531f1f250d58590439cafcfc08d7a9a6ba8895"
RULES_ARCHIVE_MD5 = "dc66b0b1b371374dd14bd85a0cf130e2"
RULES_ARCHIVE_SHA256 = "02345092cc2384d006ec9ced28df68329ced51cbddfade2181480eb96f9ffd76"
NAM_RULES = "rules_q3_s6_nam.txt"
NAM_SYMBOLIC_RULES = "rules_q3_s3_nam_symb.txt"
NAM_RULES_SHA256 = "1e9c436f0261c9052b8b0a1b874095267cabdb60c4ef1b8c02950e8800499ba8"
NAM_SYMBOLIC_RULES_SHA256 = "a5c3923c75975d04a9e59fc93a6233d5bf6d015f365f95bc50a8ac2614470490"
SMOKE_SCHEMA_VERSION = "1.0.0"


def _hash(path: Path, algorithm: str = "sha256") -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def _java_major(java: Path) -> tuple[int | None, str]:
    try:
        completed = subprocess.run(
            [str(java), "-version"], capture_output=True, text=True, timeout=10
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"{type(exc).__name__}: {exc}"
    version_text = (completed.stderr + "\n" + completed.stdout).strip()
    match = re.search(r'version "(\d+)', version_text)
    return (int(match.group(1)) if match else None), version_text


def _preflight(java: Path, jar: Path, rules_dir: Path, output_root: Path) -> Path:
    java = java.resolve()
    jar = jar.resolve()
    rules_dir = rules_dir.resolve()
    blockers: list[dict[str, str]] = []
    major, java_version = _java_major(java)
    if not java.exists():
        blockers.append({"code": "missing_java", "detail": str(java)})
    elif major is None or major < 21:
        blockers.append({
            "code": "incompatible_java",
            "detail": f"GUOQ requires Java 21; detected {java_version}",
        })
    if not jar.exists():
        blockers.append({"code": "missing_jar", "detail": str(jar)})
        jar_sha256 = None
        jar_md5 = None
    else:
        jar_sha256, jar_md5 = _hash(jar), _hash(jar, "md5")
        if jar_sha256 != JAR_SHA256 or jar_md5 != JAR_MD5:
            blockers.append({
                "code": "artifact_hash_mismatch",
                "detail": f"jar md5={jar_md5} sha256={jar_sha256}",
            })
    expected_rule_hashes = {
        rules_dir / NAM_RULES: NAM_RULES_SHA256,
        rules_dir / NAM_SYMBOLIC_RULES: NAM_SYMBOLIC_RULES_SHA256,
    }
    observed_rule_hashes = {}
    for rule, expected_hash in expected_rule_hashes.items():
        if not rule.exists():
            blockers.append({"code": "missing_rule", "detail": str(rule)})
            observed_rule_hashes[rule.name] = None
        else:
            observed_hash = _hash(rule)
            observed_rule_hashes[rule.name] = observed_hash
            if observed_hash != expected_hash:
                blockers.append({
                    "code": "artifact_hash_mismatch",
                    "detail": f"{rule.name} sha256={observed_hash}",
                })

    try:
        import psutil

        memory_gib = psutil.virtual_memory().total / 2**30
    except ImportError:
        memory_gib = None
    docker = shutil.which("docker")
    container_blockers = []
    if docker is None:
        container_blockers.append("docker_not_found")
    if memory_gib is not None and memory_gib < 32:
        container_blockers.append("host_ram_below_official_32_GiB_recommendation")

    record = {
        "schema_version": SMOKE_SCHEMA_VERSION,
        "recorded_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "scope": "go_no_go_only_no_shared_520",
        "official_repository": OFFICIAL_REPOSITORY,
        "official_source_commit": OFFICIAL_SOURCE_COMMIT,
        "official_license": OFFICIAL_LICENSE,
        "official_artifact_doi": OFFICIAL_ARTIFACT_DOI,
        "official_artifact_concept_doi": OFFICIAL_ARTIFACT_CONCEPT_DOI,
        "execution_artifact": {
            "jar_name": JAR_NAME,
            "expected_md5": JAR_MD5,
            "observed_md5": jar_md5,
            "expected_sha256": JAR_SHA256,
            "observed_sha256": jar_sha256,
            "rules_archive_expected_md5": RULES_ARCHIVE_MD5,
            "rules_archive_expected_sha256": RULES_ARCHIVE_SHA256,
            "rule_files_expected_sha256": {
                NAM_RULES: NAM_RULES_SHA256,
                NAM_SYMBOLIC_RULES: NAM_SYMBOLIC_RULES_SHA256,
            },
            "rule_files_observed_sha256": observed_rule_hashes,
        },
        "host": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "logical_cpu_count": os.cpu_count(),
            "total_ram_gib": memory_gib,
            "docker_path": docker,
            "java_path": str(java),
            "java_major": major,
            "java_version": java_version,
            "jre_distribution_used_for_recorded_smoke": {
                "vendor": "Eclipse Temurin",
                "version": "21.0.12+8 LTS",
                "archive": "OpenJDK21U-jre_x64_windows_hotspot_21.0.12_8.zip",
                "archive_sha256": "b8aa18fef5edb69bee8618f99677d66d0873d22cb40d974c15ac9ffcdecf73ba",
            },
        },
        "rewrite_only_smoke": {
            "decision": "GO" if not blockers else "NO_GO",
            "blockers": blockers,
            "configuration": {
                "gate_set": "NAM",
                "objective": "TWO_Q",
                "resynthesis": "NONE",
                "heap_limit": "4g",
                "non_symbolic_rules": NAM_RULES,
                "symbolic_rules": NAM_SYMBOLIC_RULES,
            },
        },
        "official_container": {
            "decision": "GO" if not container_blockers else "NO_GO",
            "blockers": container_blockers,
            "official_platform": "linux/amd64",
            "official_recommended_ram_gib": 32,
        },
        "full_resynthesis": {
            "decision": "NOT_ASSESSED",
            "reason": "rewrite-only smoke does not start the BQSKit/Python server",
        },
        "shared_520": {
            "decision": "NOT_RUN",
            "reason": "parent task authorizes go/no-go evidence only",
        },
    }
    path = output_root / "preflight" / "preflight.json"
    _atomic_text(path, json.dumps(record, indent=2, sort_keys=True) + "\n")
    print(path)
    return path


def _load_qasm(path: Path):
    return qasm2.loads(
        path.read_text(encoding="utf-8"),
        custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS,
    )


def _metrics(circuit) -> dict[str, int]:
    return {
        "gate_count": int(circuit.size()),
        "two_qubit_gate_count": int(sum(
            item.operation.num_qubits == 2 for item in circuit.data
        )),
        "depth": int(circuit.depth() or 0),
    }


def _run_one(
    row: dict, java: Path, jar: Path, rules_dir: Path, output_root: Path,
    timeout_seconds: float, seed: int,
) -> dict:
    circuit_id = str(row["circuit_id"])
    trial = int(row["trial"])
    safe_id = re.sub(r"[^A-Za-z0-9_-]", "_", circuit_id)
    run_dir = output_root / "smoke" / f"t{trial:02d}_{safe_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    input_path = PROJECT_ROOT / str(row["quartz_input_qasm_path"])
    source_path = PROJECT_ROOT / str(row["source_common_qasm_path"])
    job = f"smoke_{safe_id}_t{trial:02d}"
    command = [
        str(java), "-Xmx4g", "-cp", str(jar), "qoptimizer.Optimizer",
        "-g", "NAM", "-opt", "TWO_Q", "-resynth", "NONE",
        "-r", str(rules_dir / NAM_RULES),
        "-sr", str(rules_dir / NAM_SYMBOLIC_RULES),
        "-out", str(run_dir), "-job", job, "--seed", str(seed),
        str(input_path),
    ]
    start = time.perf_counter()
    timed_out = False
    try:
        completed = subprocess.run(
            command, cwd=jar.parent, capture_output=True, text=True,
            timeout=timeout_seconds,
        )
        returncode = completed.returncode
        stdout, stderr = completed.stdout, completed.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        returncode = None
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
    elapsed = time.perf_counter() - start
    candidates = sorted(run_dir.glob(f"latest_sol_{job}_*.qasm"))
    output_path = candidates[-1] if candidates else None
    if timed_out and output_path:
        status, failure = "ok_timeout_incumbent", ""
    elif timed_out:
        status, failure = "timeout_no_incumbent", "timeout_no_incumbent"
    elif returncode != 0:
        status, failure = "invocation_error", "nonzero_exit"
    elif output_path is None:
        status, failure = "missing_output", "completed_without_output"
    else:
        status, failure = "ok_completed", ""

    result: dict[str, object] = {
        "schema_version": SMOKE_SCHEMA_VERSION,
        "tool": "guoq",
        "tool_mode": "rewrite_only_resynth_none",
        "smoke_only_not_formal_comparison": True,
        "circuit_id": circuit_id,
        "trial": trial,
        "seed": seed,
        "status": status,
        "failure_class": failure,
        "timed_out": timed_out,
        "returncode": returncode,
        "runtime_seconds": elapsed,
        "timeout_seconds": timeout_seconds,
        "input_qasm_path": input_path.relative_to(PROJECT_ROOT).as_posix(),
        "input_qasm_sha256": _hash(input_path),
        "source_common_qasm_path": source_path.relative_to(PROJECT_ROOT).as_posix(),
        "source_common_qasm_sha256": _hash(source_path),
        "output_qasm_path": (
            output_path.relative_to(PROJECT_ROOT).as_posix()
            if output_path and PROJECT_ROOT in output_path.parents else str(output_path or "")
        ),
        "output_qasm_sha256": _hash(output_path) if output_path else "",
        "stdout_tail": stdout[-2000:],
        "stderr_tail": stderr[-2000:],
        "exact_equivalent": False,
        "valid_equivalent_output": False,
    }
    try:
        source = _load_qasm(source_path)
        guoq_input = _load_qasm(input_path)
        result.update({f"input_{key}": value for key, value in _metrics(guoq_input).items()})
        if output_path:
            output = _load_qasm(output_path)
            equivalent = bool(Operator(source).equiv(Operator(output)))
            result.update({f"output_{key}": value for key, value in _metrics(output).items()})
            result["exact_equivalent"] = equivalent
            result["valid_equivalent_output"] = equivalent
            if not equivalent:
                result["status"] = "equivalence_failure"
                result["failure_class"] = "exact_operator_inequivalence"
    except Exception as exc:
        result["status"] = "output_parse_or_verification_error"
        result["failure_class"] = f"{type(exc).__name__}: {exc}"
    return result


def _smoke(
    manifest: Path, java: Path, jar: Path, rules_dir: Path, output_root: Path,
    circuit_ids: list[str], timeout_seconds: float, seed: int,
) -> Path:
    if not 1 <= len(circuit_ids) <= 3:
        raise ValueError("smoke requires one to three circuit IDs")
    preflight_path = _preflight(java, jar, rules_dir, output_root)
    preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
    if preflight["rewrite_only_smoke"]["decision"] != "GO":
        raise RuntimeError("rewrite-only smoke preflight is NO_GO")
    frame = pd.read_csv(manifest)
    selected = []
    for circuit_id in circuit_ids:
        matches = frame[(frame["circuit_id"] == circuit_id) & (frame["trial"] == 0)]
        if len(matches) != 1:
            raise RuntimeError(f"expected one trial-0 row for {circuit_id}; got {len(matches)}")
        selected.append(matches.iloc[0].to_dict())
    rows = [
        _run_one(row, java.resolve(), jar.resolve(), rules_dir.resolve(),
                 output_root.resolve(), timeout_seconds, seed)
        for row in selected
    ]
    path = output_root / "smoke" / "guoq_smoke.csv"
    _atomic_text(path, pd.DataFrame(rows).to_csv(index=False))
    metadata = {
        "schema_version": SMOKE_SCHEMA_VERSION,
        "status": "complete" if all(row["valid_equivalent_output"] for row in rows) else "failed",
        "scope": "one_to_three_input_smoke_not_formal_comparison",
        "n_rows": len(rows),
        "formal_comparison_eligible": False,
        "official_repository": OFFICIAL_REPOSITORY,
        "official_source_commit": OFFICIAL_SOURCE_COMMIT,
        "official_artifact_doi": OFFICIAL_ARTIFACT_DOI,
        "official_license": OFFICIAL_LICENSE,
        "jar_sha256": _hash(jar),
        "manifest_path": manifest.resolve().relative_to(PROJECT_ROOT).as_posix(),
        "manifest_sha256": _hash(manifest.resolve()),
        "result_sha256": _hash(path),
        "configuration": {
            "gate_set": "NAM", "objective": "TWO_Q", "resynthesis": "NONE",
            "heap_limit": "4g", "timeout_seconds": timeout_seconds, "seed": seed,
        },
        "status_counts": pd.Series([row["status"] for row in rows]).value_counts().to_dict(),
    }
    _atomic_text(
        output_root / "smoke" / "metadata.json",
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
    )
    print(path)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("preflight", "smoke"):
        sub = subparsers.add_parser(name)
        sub.add_argument("--java", type=Path, required=True)
        sub.add_argument("--jar", type=Path, required=True)
        sub.add_argument("--rules-dir", type=Path, required=True)
        sub.add_argument("--output-root", type=Path, default=DEFAULT_ROOT)
        if name == "smoke":
            sub.add_argument("--manifest", type=Path, required=True)
            sub.add_argument("--circuit-id", action="append", required=True)
            sub.add_argument("--timeout-seconds", type=float, default=8.0)
            sub.add_argument("--seed", type=int, default=0)
    arguments = parser.parse_args()
    if arguments.command == "preflight":
        _preflight(arguments.java, arguments.jar, arguments.rules_dir,
                   arguments.output_root)
    else:
        _smoke(arguments.manifest, arguments.java, arguments.jar,
               arguments.rules_dir, arguments.output_root,
               arguments.circuit_id, arguments.timeout_seconds, arguments.seed)


if __name__ == "__main__":
    main()
