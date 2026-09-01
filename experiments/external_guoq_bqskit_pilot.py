"""Bounded, resource-instrumented GUOQ+BQSKit pilot (never shared-520)."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd
import psutil
from qiskit import qasm2, transpile
from qiskit.quantum_info import Operator

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.external_guoq_benchmark import (
    JAR_SHA256,
    NAM_RULES,
    NAM_RULES_SHA256,
    NAM_SYMBOLIC_RULES,
    NAM_SYMBOLIC_RULES_SHA256,
    OFFICIAL_ARTIFACT_DOI,
    OFFICIAL_LICENSE,
    OFFICIAL_REPOSITORY,
    OFFICIAL_SOURCE_COMMIT,
)
from experiments.guoq_bqskit_server import OFFICIAL_RESYNTH_SHA256

DEFAULT_ROOT = (
    PROJECT_ROOT / "data" / "v10" / "prepaper" / "external_baselines" /
    "guoq" / "bqskit_pilot"
)
COMMON_BASIS = ["rz", "sx", "x", "cx"]
SCHEMA_VERSION = "1.0.0-pilot"
PINNED_TOP_LEVEL = {"bqskit": "1.2.1", "qiskit": "2.4.1", "requests": "2.32.5"}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def _load_qasm(path: Path):
    return qasm2.loads(
        path.read_text(encoding="utf-8"),
        custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS,
    )


def _metrics(circuit) -> dict[str, int]:
    two_q_count = sum(item.operation.num_qubits == 2 for item in circuit.data)
    two_q_depth = circuit.depth(
        filter_function=lambda instruction: instruction.operation.num_qubits == 2
    )
    return {
        "gate_count": int(circuit.size()),
        "two_qubit_gate_count": int(two_q_count),
        "depth": int(circuit.depth() or 0),
        "two_qubit_depth": int(two_q_depth or 0),
    }


def _package_versions(python: Path) -> dict[str, str]:
    code = (
        "import importlib.metadata,json; "
        "print(json.dumps({n:importlib.metadata.version(n) for n in "
        "['bqskit','qiskit','requests','numpy','scipy','bqskitrs']}))"
    )
    completed = subprocess.run(
        [str(python), "-c", code], capture_output=True, text=True,
        timeout=30, check=True,
    )
    return json.loads(completed.stdout)


def _preflight(
    server_python: Path, java: Path, jar: Path, rules_dir: Path,
    official_resynth: Path, wheelhouse: Path, output_root: Path,
) -> dict:
    expected = {
        jar: JAR_SHA256,
        rules_dir / NAM_RULES: NAM_RULES_SHA256,
        rules_dir / NAM_SYMBOLIC_RULES: NAM_SYMBOLIC_RULES_SHA256,
        official_resynth: OFFICIAL_RESYNTH_SHA256,
    }
    blockers = []
    observed = {}
    for path, expected_hash in expected.items():
        if not path.is_file():
            blockers.append({"code": "missing_artifact", "path": str(path)})
            observed[str(path)] = None
        else:
            actual = _sha256(path)
            observed[str(path)] = actual
            if actual != expected_hash:
                blockers.append({
                    "code": "artifact_hash_mismatch", "path": str(path),
                    "expected": expected_hash, "actual": actual,
                })
    try:
        versions = _package_versions(server_python)
    except Exception as exc:
        versions = {}
        blockers.append({"code": "python_dependency_import_failure", "detail": str(exc)})
    for package, version in PINNED_TOP_LEVEL.items():
        if versions.get(package) != version:
            blockers.append({
                "code": "package_version_mismatch", "package": package,
                "expected": version, "actual": versions.get(package),
            })
    wheels = []
    if wheelhouse.is_dir():
        for wheel in sorted(wheelhouse.glob("*.whl")):
            wheels.append({
                "file": wheel.name, "bytes": wheel.stat().st_size,
                "sha256": _sha256(wheel),
            })
    else:
        blockers.append({"code": "missing_wheelhouse", "path": str(wheelhouse)})
    record = {
        "schema_version": SCHEMA_VERSION,
        "recorded_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "decision": "GO" if not blockers else "NO_GO",
        "blockers": blockers,
        "scope": "3_input_bqskit_pilot_no_shared_520",
        "official_repository": OFFICIAL_REPOSITORY,
        "official_source_commit": OFFICIAL_SOURCE_COMMIT,
        "official_artifact_doi": OFFICIAL_ARTIFACT_DOI,
        "official_license": OFFICIAL_LICENSE,
        "artifact_hashes": observed,
        "server_python": str(server_python.resolve()),
        "package_versions": versions,
        "pinned_top_level": PINNED_TOP_LEVEL,
        "wheelhouse": wheels,
        "host": {
            "platform": platform.platform(), "machine": platform.machine(),
            "logical_cpu_count": os.cpu_count(),
            "total_ram_gib": psutil.virtual_memory().total / 2**30,
        },
        "resource_contract": {
            "bqskit_compiler_workers": 1,
            "blas_threads": 1,
            "logical_cpu_affinity_count": 1,
            "java_heap": "4g",
            "inputs": 3,
            "timeout_seconds_per_input": 120,
        },
        "formal_comparison_eligible": False,
    }
    path = output_root / "preflight" / "preflight.json"
    _atomic_text(path, json.dumps(record, indent=2, sort_keys=True) + "\n")
    _atomic_text(
        output_root / "preflight" / "dependency_lock.json",
        json.dumps({
            "python": str(server_python.resolve()),
            "packages": versions, "wheels": wheels,
        }, indent=2, sort_keys=True) + "\n",
    )
    return record


def _process_tree(root_pid: int) -> list[psutil.Process]:
    try:
        root = psutil.Process(root_pid)
        return [root, *root.children(recursive=True)]
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return []


def _kill_tree(root_pid: int) -> None:
    processes = _process_tree(root_pid)
    for process in reversed(processes):
        try:
            process.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    psutil.wait_procs(processes, timeout=5)


def _wait_server(timeout_seconds: float = 60) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error = ""
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen("http://127.0.0.1:8080", timeout=1) as response:
                payload = json.loads(response.read())
                if response.status == 200 and payload.get("workers") == 1:
                    return
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        time.sleep(0.1)
    raise RuntimeError(f"BQSKit server readiness timeout: {last_error}")


def _read_events(path: Path) -> list[dict]:
    if not path.exists():
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def _summarize_resynthesis(events: list[dict], stopped_unix: float) -> dict:
    starts = {
        event["request_id"]: event for event in events
        if event.get("event") == "request_start"
    }
    completes = {
        event["request_id"]: event for event in events
        if event.get("event") == "request_complete"
    }
    completed_wall = sum(
        float(event.get("wall_seconds", 0.0)) for event in completes.values()
    )
    completed_cpu = sum(
        float(event.get("server_cpu_seconds", 0.0)) for event in completes.values()
    )
    unfinished = [request_id for request_id in starts if request_id not in completes]
    censored_wall = sum(
        max(0.0, stopped_unix - float(starts[request_id]["started_unix"]))
        for request_id in unfinished
    )
    return {
        "resynthesis_requests_started": len(starts),
        "resynthesis_requests_completed": len(completes),
        "resynthesis_requests_failed": sum(
            event.get("status") != "ok" for event in completes.values()
        ),
        "resynthesis_completed_wall_seconds": completed_wall,
        "resynthesis_completed_server_cpu_seconds": completed_cpu,
        "resynthesis_active_censored_wall_seconds": censored_wall,
        "resynthesis_unfinished_at_timeout": len(unfinished),
    }


def _run_optimizer(
    command: list[str], cwd: Path, server_pid: int, timeout_seconds: float,
    stdout_path: Path, stderr_path: Path,
) -> dict:
    child_env = os.environ.copy()
    child_env.update({
        "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1",
        "VECLIB_MAXIMUM_THREADS": "1",
    })
    with stdout_path.open("w", encoding="utf-8") as stdout_handle, \
            stderr_path.open("w", encoding="utf-8") as stderr_handle:
        process = subprocess.Popen(
            command, cwd=cwd, stdout=stdout_handle, stderr=stderr_handle,
            text=True, env=child_env,
        )
        started = time.perf_counter()
        peak_rss = 0
        available_cores = psutil.Process().cpu_affinity()
        affinity_core = min(available_cores) if available_cores else 0
        affinity_set: set[int] = set()
        affinity_failures: dict[int, str] = {}
        cpu_baseline: dict[int, float] = {}
        cpu_latest: dict[int, float] = {}
        timed_out = False
        while process.poll() is None:
            roots = _process_tree(server_pid) + _process_tree(process.pid)
            unique = {item.pid: item for item in roots}
            rss = 0
            for pid, item in unique.items():
                try:
                    if pid not in affinity_set:
                        try:
                            item.cpu_affinity([affinity_core])
                            affinity_set.add(pid)
                        except (psutil.NoSuchProcess, psutil.AccessDenied,
                                OSError) as exc:
                            affinity_failures[pid] = f"{type(exc).__name__}: {exc}"
                    rss += item.memory_info().rss
                    cpu = sum(item.cpu_times()[:2])
                    cpu_baseline.setdefault(pid, cpu)
                    cpu_latest[pid] = cpu
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            peak_rss = max(peak_rss, rss)
            if time.perf_counter() - started >= timeout_seconds:
                timed_out = True
                _kill_tree(process.pid)
                break
            time.sleep(0.05)
        try:
            returncode = process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _kill_tree(process.pid)
            returncode = None
        elapsed = time.perf_counter() - started
    cpu_seconds = sum(
        max(0.0, cpu_latest[pid] - cpu_baseline.get(pid, cpu_latest[pid]))
        for pid in cpu_latest
    )
    return {
        "optimizer_wall_seconds": elapsed, "combined_cpu_seconds": cpu_seconds,
        "combined_peak_rss_bytes": peak_rss, "timed_out": timed_out,
        "returncode": returncode,
        "cpu_affinity_logical_core": affinity_core,
        "single_cpu_affinity_enforced": not affinity_failures,
        "cpu_affinity_processes_pinned": len(affinity_set),
        "cpu_affinity_failures": json.dumps(affinity_failures, sort_keys=True),
    }


def _run_one(
    row: dict, server_python: Path, server_script: Path, java: Path, jar: Path,
    rules_dir: Path, official_resynth: Path, output_root: Path,
    timeout_seconds: float, seed: int,
) -> dict:
    circuit_id = str(row["circuit_id"])
    trial = int(row["trial"])
    run_dir = output_root / "runs" / f"t{trial:02d}_{circuit_id}"
    run_dir.mkdir(parents=True, exist_ok=True)
    server_log = run_dir / "resynthesis_events.jsonl"
    if server_log.exists():
        server_log.unlink()
    server_stdout = run_dir / "server_stdout.log"
    server_stderr = run_dir / "server_stderr.log"
    input_path = PROJECT_ROOT / str(row["quartz_input_qasm_path"])
    source_path = PROJECT_ROOT / str(row["source_common_qasm_path"])
    job = f"bqskit_{circuit_id}_t{trial:02d}"

    parse_wall_start, parse_cpu_start = time.perf_counter(), time.process_time()
    source = _load_qasm(source_path)
    nam_input = _load_qasm(input_path)
    # The frozen source is already the protocol's common-basis logical input.
    # Re-transpiling the Nam adapter input would count decomposition overhead
    # that was not present in the original shared input.
    input_common = source
    parse_wall = time.perf_counter() - parse_wall_start
    parse_cpu = time.process_time() - parse_cpu_start

    server_env = os.environ.copy()
    server_env.update({
        "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1",
    })
    server_started = time.perf_counter()
    with server_stdout.open("w", encoding="utf-8") as stdout_handle, \
            server_stderr.open("w", encoding="utf-8") as stderr_handle:
        server = subprocess.Popen(
            [str(server_python), str(server_script),
             "--official-resynth", str(official_resynth), "--log", str(server_log)],
            cwd=official_resynth.parent, stdout=stdout_handle, stderr=stderr_handle,
            text=True, env=server_env,
        )
    try:
        _wait_server()
        server_start_wall = time.perf_counter() - server_started
        command = [
            str(java), "-Xmx4g", "-cp", str(jar), "qoptimizer.Optimizer",
            "-g", "NAM", "-opt", "TWO_Q", "-resynth", "BQSKIT",
            "-r", str(rules_dir / NAM_RULES),
            "-sr", str(rules_dir / NAM_SYMBOLIC_RULES),
            "-out", str(run_dir), "-job", job, "--seed", str(seed),
            str(input_path),
        ]
        resource = _run_optimizer(
            command, jar.parent, server.pid, timeout_seconds,
            run_dir / "optimizer_stdout.log", run_dir / "optimizer_stderr.log",
        )
        stopped_unix = time.time()
    except Exception as exc:
        server_start_wall = time.perf_counter() - server_started
        stopped_unix = time.time()
        resource = {
            "optimizer_wall_seconds": 0.0, "combined_cpu_seconds": 0.0,
            "combined_peak_rss_bytes": 0, "timed_out": False,
            "returncode": None, "startup_error": f"{type(exc).__name__}: {exc}",
        }
    finally:
        _kill_tree(server.pid)
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass

    events = _read_events(server_log)
    resynth = _summarize_resynthesis(events, stopped_unix)
    candidates = sorted(run_dir.glob(f"latest_sol_{job}_*.qasm"))
    output_path = candidates[-1] if candidates else None
    if resource.get("timed_out") and output_path:
        status, failure = "ok_timeout_incumbent", ""
    elif resource.get("timed_out"):
        status, failure = "timeout_no_incumbent", "timeout_no_incumbent"
    elif resource.get("startup_error"):
        status, failure = "server_startup_error", resource["startup_error"]
    elif resource.get("returncode") not in (0, None):
        status, failure = "invocation_error", "nonzero_exit"
    elif output_path:
        status, failure = "ok_completed", ""
    else:
        status, failure = "missing_output", "completed_without_output"

    verify_wall_start, verify_cpu_start = time.perf_counter(), time.process_time()
    equivalent = False
    output_common_metrics = {
        key: None for key in ("gate_count", "two_qubit_gate_count", "depth", "two_qubit_depth")
    }
    verify_error = ""
    if output_path:
        try:
            optimized = _load_qasm(output_path)
            equivalent = bool(Operator(source).equiv(Operator(optimized)))
            common_output = transpile(
                optimized, basis_gates=COMMON_BASIS, optimization_level=0,
                seed_transpiler=0,
            )
            output_common_metrics = _metrics(common_output)
            if not equivalent:
                status, failure = "equivalence_failure", "exact_operator_inequivalence"
        except Exception as exc:
            status = "output_parse_or_verification_error"
            failure = f"{type(exc).__name__}: {exc}"
            verify_error = failure
    verify_wall = time.perf_counter() - verify_wall_start
    verify_cpu = time.process_time() - verify_cpu_start
    input_common_metrics = _metrics(input_common)
    observed_resynth_wall = (
        resynth["resynthesis_completed_wall_seconds"] +
        resynth["resynthesis_active_censored_wall_seconds"]
    )
    rewrite_residual = max(
        0.0, resource["optimizer_wall_seconds"] - observed_resynth_wall
    )
    result = {
        "schema_version": SCHEMA_VERSION,
        "tool": "guoq_bqskit", "tool_config": "nam_two_q_bqskit_level3",
        "formal_comparison_eligible": False,
        "pilot_only_no_shared_520": True,
        "circuit_id": circuit_id, "trial": trial, "seed": seed,
        "status": status, "failure_class": failure,
        "timeout_incumbent": bool(resource.get("timed_out") and output_path),
        "exact_equivalent": equivalent,
        "valid_equivalent_output": equivalent,
        "adapter_parse_wall_seconds": parse_wall,
        "adapter_parse_cpu_seconds": parse_cpu,
        "server_start_wall_seconds": server_start_wall,
        **resource,
        **resynth,
        "rewrite_orchestration_residual_wall_seconds": rewrite_residual,
        "rewrite_timing_method": (
            "optimizer wall minus completed and active-censored server request occupancy; "
            "includes Java parse, rewrite search, HTTP, serialization, and timeout overhead"
        ),
        "verification_wall_seconds": verify_wall,
        "verification_cpu_seconds": verify_cpu,
        "pipeline_wall_seconds": (
            parse_wall + server_start_wall + resource["optimizer_wall_seconds"] + verify_wall
        ),
        "input_qasm_path": input_path.relative_to(PROJECT_ROOT).as_posix(),
        "input_qasm_sha256": _sha256(input_path),
        "source_common_qasm_path": source_path.relative_to(PROJECT_ROOT).as_posix(),
        "source_common_qasm_sha256": _sha256(source_path),
        "output_qasm_path": (
            output_path.relative_to(PROJECT_ROOT).as_posix() if output_path else ""
        ),
        "output_qasm_sha256": _sha256(output_path) if output_path else "",
        "verification_error": verify_error,
    }
    result.update({f"common_input_{key}": value for key, value in input_common_metrics.items()})
    result.update({f"common_output_{key}": value for key, value in output_common_metrics.items()})
    for key in input_common_metrics:
        before, after = input_common_metrics[key], output_common_metrics[key]
        result[f"common_{key}_reduction_pct"] = (
            100.0 * (1.0 - after / before)
            if before and after is not None else (0.0 if before == 0 and after == 0 else None)
        )
    _atomic_text(run_dir / "result.json", json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def run(arguments) -> Path:
    output_root = arguments.output_root.resolve()
    preflight = _preflight(
        arguments.server_python.resolve(), arguments.java.resolve(),
        arguments.jar.resolve(), arguments.rules_dir.resolve(),
        arguments.official_resynth.resolve(), arguments.wheelhouse.resolve(),
        output_root,
    )
    if preflight["decision"] != "GO":
        raise RuntimeError("GUOQ+BQSKit pilot preflight is NO_GO")
    if not 1 <= len(arguments.circuit_id) <= 10:
        raise ValueError("pilot accepts one to ten pre-registered circuit IDs")
    manifest = pd.read_csv(arguments.manifest)
    selected = []
    for circuit_id in arguments.circuit_id:
        matches = manifest[(manifest["circuit_id"] == circuit_id) & (manifest["trial"] == 0)]
        if len(matches) != 1:
            raise RuntimeError(f"expected one trial-0 row for {circuit_id}; got {len(matches)}")
        selected.append(matches.iloc[0].to_dict())
    preregistration = {
        "created_before_pilot": True,
        "circuit_ids_in_order": arguments.circuit_id,
        "selection_rule": "same three IDs fixed in the preceding rewrite-only smoke",
        "timeout_seconds_per_input": arguments.timeout_seconds,
        "seed": arguments.seed,
        "manifest_sha256": _sha256(arguments.manifest.resolve()),
        "formal_comparison_eligible": False,
    }
    _atomic_text(
        output_root / "preregistration.json",
        json.dumps(preregistration, indent=2, sort_keys=True) + "\n",
    )
    rows = []
    checkpoint = output_root / "guoq_bqskit_pilot_checkpoint.csv"
    for row in selected:
        result = _run_one(
            row, arguments.server_python.resolve(),
            (PROJECT_ROOT / "experiments" / "guoq_bqskit_server.py").resolve(),
            arguments.java.resolve(), arguments.jar.resolve(),
            arguments.rules_dir.resolve(), arguments.official_resynth.resolve(),
            output_root, arguments.timeout_seconds, arguments.seed,
        )
        rows.append(result)
        _atomic_text(checkpoint, pd.DataFrame(rows).to_csv(index=False))
        print(
            f"GUOQ+BQSKit pilot {result['circuit_id']}: {result['status']} "
            f"requests={result['resynthesis_requests_started']}", flush=True,
        )
    output = output_root / "guoq_bqskit_pilot.csv"
    _atomic_text(output, pd.DataFrame(rows).to_csv(index=False))
    checkpoint.unlink(missing_ok=True)
    metadata = {
        "schema_version": SCHEMA_VERSION,
        "status": "complete" if all(row["valid_equivalent_output"] for row in rows) else "failed",
        "n_rows": len(rows), "formal_comparison_eligible": False,
        "formal_gate": "requires successful full-configuration protocol review; not granted by pilot",
        "shared_520": "NOT_RUN",
        "official_artifact_doi": OFFICIAL_ARTIFACT_DOI,
        "official_source_commit": OFFICIAL_SOURCE_COMMIT,
        "result_sha256": _sha256(output),
        "status_counts": pd.Series([row["status"] for row in rows]).value_counts().to_dict(),
    }
    _atomic_text(
        output_root / "metadata.json",
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
    )
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server-python", type=Path, required=True)
    parser.add_argument("--java", type=Path, required=True)
    parser.add_argument("--jar", type=Path, required=True)
    parser.add_argument("--rules-dir", type=Path, required=True)
    parser.add_argument("--official-resynth", type=Path, required=True)
    parser.add_argument("--wheelhouse", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--circuit-id", action="append", required=True)
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_ROOT)
    arguments = parser.parse_args()
    print(run(arguments))


if __name__ == "__main__":
    main()
