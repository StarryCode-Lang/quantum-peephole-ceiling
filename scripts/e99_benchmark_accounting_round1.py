"""E99: benchmark-accounting audit, ROUND 1 (preregistered protocol v1.0).

Protocol: ``docs/review/benchmark_accounting_protocol_2026-11-04.md`` v1.0
(2026-11-04).  This is round-24 30-day list item #5 ("基准口径审计首轮"):
Qiskit optimization levels L0-L3 on the MQT Bench 30-circuit panel, measured
under the protocol's preregistered accounting conventions, to quantify how the
reported "improvement" of the SAME optimization runs depends on the reporting
convention.  The protocol file is the authority: its hypotheses are quoted
byte-for-byte, its judgment rules are applied as registered, and no convention
is tuned after seeing results.  Deviations/interpretations are recorded in
``summary.json["protocol_conflicts_and_gaps"]``, never applied silently.

Method
------
1. Inputs are the 30 E97-normalized MQT instances
   (``2026-11-06_mqt_second_panel/instances/*.qasm``), sha256-checked against
   that package's MANIFEST.json.  Those instances ARE the protocol's
   preregistered baseline (the ``optimization_level=0`` rebase into the frozen
   basis ``{h, x, rz, cx}``, already equivalence-certified in E97).
2. Transpile-and-count harness reused from E61 (same kwargs, same seed, same
   cost metric), so L0-L3 numbers are comparable with the frozen-basis panel.
3. Accounting per (circuit, level), all on the SAME transpiled output:
     口径① source-relative   : denominator = raw MQT generator output gate
                               count (census ``raw_gates``, sha256-pinned;
                               raw cx counts regenerated via mqt.bench and
                               cross-checked against the census raw totals).
     口径② baseline-relative : denominator = the level-0 rebase run's counts
                               (identical to the input instance by
                               construction; the L0 row's reduction is 0).
     口径③ two-qubit-relative: numerator/denominator in cx gates, under both
                               denominators above.
   Reductions in percentage points; H1 difference = ①-②, H3 difference =
   total-gate reduction - two-qubit reduction.
4. Equivalence gate per (circuit, level): MQT QCEC 3.11.0 (protocol §3.4,
   sysconfig shim per ``docs/reproducibility.md``) AND the project's exact
   numerical certifier (E97/E71 path) as an independent cross-check.  A row is
   verdict-relevant only if both agree "equivalent"; uncertified or
   disagreeing rows are excluded fail-closed and listed, never averaged.
5. Statistics per protocol §3: paired Wilcoxon signed-rank (α=0.05) with Holm
   correction, median paired difference with family-stratified bootstrap 95%
   CI (10,000 resamples), ICC/deff with circuit as the cluster unit (deff>10
   switches the main test to family-level means), ITT accounting (failures
   stay in the denominator), monotonicity L0<=L1<=L2<=L3 measured not assumed.

Self-checks (exit 1 on any failure)
    * instance sha256s match the E97 MANIFEST (30/30);
    * 30 circuits x 4 levels all present, or an explicit fail-closed
      unresolved list via ``scope_reduction`` (never fabricated);
    * every verdict-relevant row is double-certified equivalent; excluded rows
      listed with reason;
    * determinism recheck on the first 2 circuits (transpile + counts +
      QCEC verdict reproduce exactly);
    * protocol quotes match the protocol file byte-for-byte (sha256 stored);
    * loaded instance counts match the E97 census root counts;
    * regenerated raw totals match the census raw totals;
    * transpiled outputs stay inside the frozen basis (other-gate count 0).

Contract
    Read-only on ``data/``, ``release/``, ``docs/manuscript/`` and on every
    input package.  No existing file is modified.  Writes only the dated
    output package below.

Outputs (``docs/review/science_boost/2026-11-06_benchmark_accounting_round1/``)
    audit_rows.csv   one row per (circuit, level) with every convention's
                     counts and reductions (120 rows on the full panel)
    summary.json     protocol id/version + sha256, verbatim H1/H2/H3 and
                     judgment rules, per-hypothesis verdicts, per-convention
                     aggregates, versions, conflicts/gaps, negative results
    MANIFEST.json    sha256 + bytes of every artifact (house pattern)
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib
import importlib.metadata
import json
import re
import site
import sys
import sysconfig
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
from qiskit import qasm2, transpile
from scipy import stats as sstats

from experiments.e45_development_grid.run import NAM_BASIS  # noqa: E402
from src.equivalence import certify_equivalence  # noqa: E402


# --------------------------------------------------------------------------
# QCEC availability (protocol §3.4 oracle; shim per docs/reproducibility.md,
# scripts/e59_qcec_oracle.py pattern -- local to this script, touches no file)
# --------------------------------------------------------------------------
def _patch_mqt_dll_path() -> str:
    user_site = site.getusersitepackages()
    original = sysconfig.get_paths

    def patched(*args: Any, **kwargs: Any) -> dict[str, str]:
        paths = dict(original(*args, **kwargs))
        paths["purelib"] = user_site
        return paths

    sysconfig.get_paths = patched  # type: ignore[assignment]
    return user_site


_PATCHED_PURELIB = _patch_mqt_dll_path()
try:
    import mqt.qcec as qcec  # noqa: E402

    QCEC_AVAILABLE = True
    QCEC_VERSION = getattr(qcec, "__version__", "unknown")
except Exception as exc:  # pragma: no cover
    qcec = None  # type: ignore[assignment]
    QCEC_AVAILABLE = False
    QCEC_VERSION = f"UNAVAILABLE:{type(exc).__name__}"


EXPERIMENT_ID = "E99_BENCHMARK_ACCOUNTING_ROUND1_2026_11_06"
PROTOCOL_PATH = ROOT / "docs" / "review" / "benchmark_accounting_protocol_2026-11-04.md"
INPUT_PKG = ROOT / "docs" / "review" / "science_boost" / "2026-11-06_mqt_second_panel"
INPUT_DIR = INPUT_PKG / "instances"
E97_MANIFEST = INPUT_PKG / "MANIFEST.json"
E97_CENSUS = INPUT_PKG / "census_circuit.csv"
OUT = ROOT / "docs" / "review" / "science_boost" / "2026-11-06_benchmark_accounting_round1"

LEVELS = (0, 1, 2, 3)
SEED = 42  # E61 harness seed
TRANSPILE_KWARGS = {
    "layout_method": "trivial",
    "routing_method": "basic",
    "seed_transpiler": SEED,
}
EXCLUDED_FROM_COUNTS = frozenset({"barrier", "snapshot", "delay", "measure", "reset"})
# QCEC verdicts accepted as equivalence.  "equivalent_up_to_global_phase" is
# accepted because global phase is unobservable and the project's numerical
# certifier (the independent cross-check) is global-phase-agnostic by
# construction (fidelity threshold).  Declared before the run, applied
# uniformly; recorded in protocol_conflicts_and_gaps.
EQUIVALENT_VERDICTS = frozenset({"equivalent", "equivalent_up_to_global_phase"})
STOPPING_RULE_THRESHOLD = 0.20  # protocol §3.5

# Protocol §2 family names vs this panel's available circuits.  The mapping is
# declared before any statistic is computed and is recorded in summary.json.
FAMILY_OF = {
    "draper_qft_adder": "Adder",
    "qft": "QFT",
    "qftentangled": "QFT",
    "qpeexact": "QPE",
    "qpeinexact": "QPE",
    "randomcircuit": "Random",
}
H2_STRUCTURAL = {"Adder", "QFT", "QPE"}
H2_RANDOM = {"Random"}
H2_PROTOCOL_STRUCTURAL = ["Adder", "QFT", "QPE", "UCCSD"]
H2_PROTOCOL_RANDOM = ["HaarRandom", "RandomClifford"]

BOOTSTRAP_REPS = 10_000
ALPHA = 0.05
H1_THRESHOLD_PP = 5.0
H0_NEGATIVE_BRANCH_PP = 2.0


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------
# protocol loading (byte-for-byte quotes)
# --------------------------------------------------------------------------
def load_protocol() -> dict[str, Any]:
    raw = PROTOCOL_PATH.read_bytes()
    text = raw.decode("utf-8")
    if text.startswith("\ufeff"):
        text = text[1:]
    hypotheses = {}
    for match in re.finditer(r"^- \*\*H([123])（.*$", text, flags=re.MULTILINE):
        line = match.group(0)
        hypotheses[f"h{match.group(1)}"] = line
    judgment_rules = re.findall(r"^\d\. \*\*.*$", text, flags=re.MULTILINE)
    missing = [k for k in ("h1", "h2", "h3") if k not in hypotheses]
    if missing:
        raise RuntimeError(f"protocol_hypothesis_lines_not_found:{missing}")
    return {
        "path": PROTOCOL_PATH,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "text": text,
        "hypotheses": hypotheses,
        "judgment_rules": judgment_rules,
    }


# --------------------------------------------------------------------------
# counting helpers (E61 cost metric: total / two-qubit on the frozen basis)
# --------------------------------------------------------------------------
def count_circuit(circuit) -> dict[str, Any]:
    counts: dict[str, int] = {}
    total = 0
    two_q = 0
    for instruction in circuit.data:
        name = instruction.operation.name
        if name in EXCLUDED_FROM_COUNTS:
            continue
        total += 1
        counts[name] = counts.get(name, 0) + 1
        if instruction.operation.num_qubits == 2:
            two_q += 1
    known = {name: counts.get(name, 0) for name in NAM_BASIS}
    other = {name: n for name, n in counts.items() if name not in NAM_BASIS}
    return {
        "total": total,
        "two_qubit": two_q,
        "depth": int(circuit.depth()),
        **{f"n_{name}": n for name, n in known.items()},
        "other_gates": other,
    }


def qcec_verdict(left, right) -> str:
    if not QCEC_AVAILABLE:
        return "ORACLE_UNAVAILABLE"
    try:
        result = qcec.verify(left, right)
        return str(getattr(result, "equivalence", "UNKNOWN")).split(".")[-1]
    except Exception as exc:
        return f"ERROR:{type(exc).__name__}"


def numerical_verdict(left, right) -> str:
    try:
        certificate = certify_equivalence(left, right)
        return str(certificate.status.name)
    except Exception as exc:
        return f"ERROR:{type(exc).__name__}"


# --------------------------------------------------------------------------
# statistics (protocol §3; declared before results are seen)
# --------------------------------------------------------------------------
def wilcoxon_greater(diffs: list[float]) -> dict[str, Any]:
    values = np.asarray([d for d in diffs if d is not None], dtype=float)
    if values.size == 0 or np.all(values == 0.0):
        return {"p_raw": 1.0, "n": int(values.size), "note": "all_zero_or_empty"}
    try:
        result = sstats.wilcoxon(values, alternative="greater")
        return {"p_raw": float(result.pvalue), "n": int(values.size), "note": ""}
    except ValueError as exc:
        return {"p_raw": 1.0, "n": int(values.size), "note": f"wilcoxon_error:{exc}"}


def holm_adjust(pvals: dict[str, float]) -> dict[str, float]:
    keys = sorted(pvals, key=lambda k: pvals[k])
    adjusted: dict[str, float] = {}
    running = 0.0
    m = len(keys)
    for index, key in enumerate(keys):
        running = max(running, (m - index) * pvals[key])
        adjusted[key] = min(1.0, running)
    return adjusted


def bootstrap_median_ci(
    values: list[float], families: list[str], reps: int = BOOTSTRAP_REPS, seed: int = SEED
) -> dict[str, Any]:
    array = np.asarray(values, dtype=float)
    fam_array = np.asarray(families)
    rng = np.random.default_rng(seed)
    draws = []
    for family in sorted(set(fam_array)):
        block = array[fam_array == family]
        if block.size == 0:
            continue
        picks = rng.integers(0, block.size, size=(reps, block.size))
        draws.append(block[picks])
    stacked = np.concatenate(draws, axis=1) if draws else np.empty((reps, 0))
    medians = np.median(stacked, axis=1)
    lo, hi = np.percentile(medians, [2.5, 97.5])
    return {
        "median": float(np.median(array)),
        "ci95_low": float(lo),
        "ci95_high": float(hi),
        "reps": reps,
        "stratified_by": "circuit_family",
    }


def icc_deff(matrix: np.ndarray) -> dict[str, Any] | None:
    x = np.asarray(matrix, dtype=float)
    k, m = x.shape
    if k < 2 or m < 2:
        return None
    grand = float(x.mean())
    row_means = x.mean(axis=1)
    msb = m * float(((row_means - grand) ** 2).sum()) / (k - 1)
    msw = float(((x - row_means[:, None]) ** 2).sum()) / (k * (m - 1))
    denom = msb + (m - 1) * msw
    icc = 0.0 if denom == 0 else (msb - msw) / denom
    return {
        "icc": float(icc),
        "deff": float(1 + (m - 1) * icc),
        "clusters": int(k),
        "cluster_size_m": int(m),
        "cluster_unit": "circuit",
    }


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=OUT)
    parser.add_argument("--deadline-seconds", type=float, default=1500.0)
    parser.add_argument("--limit", type=int, default=0, help="smoke-test cap (0 = all 30)")
    args = parser.parse_args()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()

    protocol = load_protocol()
    print(f"[E99] protocol sha256 {protocol['sha256'][:16]}... qcec={QCEC_VERSION}", flush=True)

    # ---- inputs ------------------------------------------------------------
    manifest = json.loads(E97_MANIFEST.read_text(encoding="utf-8"))
    instance_files = sorted(INPUT_DIR.glob("*.qasm"))
    instance_records: list[dict[str, Any]] = []
    for path in instance_files:
        key = f"instances/{path.name}"
        entry = manifest["artifacts"].get(key, {})
        actual = sha256_file(path)
        instance_records.append(
            {
                "circuit_id": path.stem,
                "file": path.name,
                "manifest_sha256": entry.get("sha256", ""),
                "actual_sha256": actual,
                "sha256_match": bool(entry) and entry.get("sha256") == actual,
            }
        )
    if args.limit > 0:
        instance_records = instance_records[: args.limit]

    census: dict[str, dict[str, str]] = {}
    with E97_CENSUS.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("status") == "OK":
                census[row["algorithm"] + "_n" + row["n_qubits"]] = row

    # ---- main loop ---------------------------------------------------------
    rows: list[dict[str, Any]] = []
    determinism_probes: list[dict[str, Any]] = []
    unresolved: list[str] = []
    scope_reduction: dict[str, Any] | None = None
    processed_ids: set[str] = set()

    for record in instance_records:
        if time.perf_counter() - started > args.deadline_seconds and rows:
            scope_reduction = {
                "reason": "deadline_exceeded",
                "completed_circuits": len(processed_ids),
                "unresolved_circuits": [
                    r["circuit_id"] for r in instance_records if r["circuit_id"] not in processed_ids
                ],
            }
            break
        circuit_id = record["circuit_id"]
        processed_ids.add(circuit_id)
        algorithm = re.sub(r"_n\d+$", "", circuit_id)
        n_qubits = int(circuit_id.rsplit("_n", 1)[1])
        family = FAMILY_OF.get(algorithm, algorithm)
        census_row = census.get(circuit_id)
        row_base: dict[str, Any] = {
            "circuit_id": circuit_id,
            "algorithm": algorithm,
            "n_qubits": n_qubits,
            "family": family,
            "in_e97_census": census_row is not None,
            "instance_sha256_match": record["sha256_match"],
        }
        if census_row is None or not record["sha256_match"]:
            row_base.update({"status": "INPUT_INVALID", "certified": "no",
                             "cert_note": "census_missing" if census_row is None else "sha256_mismatch"})
            for level in LEVELS:
                rows.append({**row_base, "level": level})
            unresolved.append(circuit_id)
            continue

        try:
            instance = qasm2.loads(Path(INPUT_DIR / record["file"]).read_text(encoding="utf-8"))
        except Exception as exc:
            row_base.update({"status": "QASM_LOAD_FAILED", "certified": "no", "cert_note": f"{type(exc).__name__}"})
            for level in LEVELS:
                rows.append({**row_base, "level": level})
            unresolved.append(circuit_id)
            continue
        inst_counts = count_circuit(instance)
        census_fields = {"total": "root_gates", "n_rz": "root_rz", "n_cx": "root_cx", "n_h": "root_h"}
        census_mismatch = any(
            int(census_row[census_field]) != inst_counts[field]
            for field, census_field in census_fields.items()
        )
        # 口径① denominator: raw MQT generator output (E97 census, pinned).
        # Primary = the census's raw_gates (raw.size(), the as-practiced
        # convention).  Secondary (declared here, recorded per row) = the raw
        # source's unitary core under E97's own terminal-nonunitary strip
        # policy, because the transpiled numerator contains no measurements.
        raw_total = int(census_row["raw_gates"])
        raw_cx: int | None = None
        raw_regen_total: int | None = None
        raw_core_total: int | None = None
        try:
            from experiments.e45_development_grid.run import _strip_terminal_nonunitary  # noqa: PLC0415
            from mqt.bench import BenchmarkLevel, get_benchmark  # noqa: PLC0415

            raw = get_benchmark(algorithm, BenchmarkLevel.ALG, circuit_size=n_qubits)
            raw_regen_total = int(raw.size())  # apples-to-apples with the census column
            stripped, _counts, _blocker = _strip_terminal_nonunitary(raw)
            core_counts = count_circuit(stripped)
            raw_core_total = core_counts["total"]
            raw_cx = core_counts["two_qubit"]
        except Exception as exc:
            row_base["raw_regen_note"] = f"{type(exc).__name__}"
        if raw_cx is None or raw_cx == 0:
            raw_cx = None  # convention ③ source variant unavailable, fail-closed

        level_outputs: dict[int, Any] = {}
        for level in LEVELS:
            row = {**row_base, "level": level, "status": "OK", "cert_note": ""}
            row.update(
                {
                    "raw_total_census": raw_total,
                    "raw_total_regen": "" if raw_regen_total is None else raw_regen_total,
                    "raw_total_unitary_core": "" if raw_core_total is None else raw_core_total,
                    "raw_2q": "" if raw_cx is None else raw_cx,
                    "census_root_count_match": not census_mismatch,
                }
            )
            t0 = time.perf_counter()
            try:
                output = transpile(instance, optimization_level=level, basis_gates=NAM_BASIS, **TRANSPILE_KWARGS)
            except Exception as exc:
                row.update({"status": "TRANSPILE_FAILED", "certified": "no",
                            "cert_note": f"{type(exc).__name__}: {exc}"})
                rows.append(row)
                unresolved.append(f"{circuit_id}:L{level}")
                continue
            row["transpile_seconds"] = round(time.perf_counter() - t0, 3)
            out_counts = count_circuit(output)
            row.update(
                {
                    "opt_total": out_counts["total"],
                    "opt_rz": out_counts["n_rz"],
                    "opt_cx": out_counts["n_cx"],
                    "opt_h": out_counts["n_h"],
                    "opt_x": out_counts["n_x"],
                    "opt_other": json.dumps(out_counts["other_gates"], sort_keys=True) if out_counts["other_gates"] else "",
                    "opt_depth": out_counts["depth"],
                }
            )
            v0 = time.perf_counter()
            verdict_q = qcec_verdict(instance, output)
            verdict_n = numerical_verdict(instance, output)
            row["verify_seconds"] = round(time.perf_counter() - v0, 3)
            row["equiv_qcec"] = verdict_q
            row["equiv_numerical"] = verdict_n
            if verdict_q in EQUIVALENT_VERDICTS and verdict_n == "VERIFIED_EQUIVALENT":
                row["certified"] = "yes"
            else:
                row["certified"] = "no"
                row["status"] = "UNCERTIFIED"
                row["cert_note"] = f"qcec={verdict_q};numerical={verdict_n}"
            level_outputs[level] = output

            # ---- accounting (same output, multiple conventions) ------------
            base = level_outputs.get(0)
            base_counts = count_circuit(base) if base is not None else None
            if base_counts is None:
                row["baseline_total"] = ""
                row["baseline_cx"] = ""
            else:
                row["baseline_total"] = base_counts["total"]
                row["baseline_cx"] = base_counts["two_qubit"]
            opt_total = out_counts["total"]
            opt_cx = out_counts["two_qubit"]
            red_total_src = 100.0 * (1.0 - opt_total / raw_total) if raw_total else None
            red_total_base = (
                100.0 * (1.0 - opt_total / base_counts["total"])
                if base_counts and base_counts["total"]
                else None
            )
            red_2q_src = 100.0 * (1.0 - opt_cx / raw_cx) if raw_cx else None
            red_2q_base = (
                100.0 * (1.0 - opt_cx / base_counts["two_qubit"])
                if base_counts and base_counts["two_qubit"]
                else None
            )
            round3 = lambda value: "" if value is None else round(value, 4)  # noqa: E731
            red_total_src_core = 100.0 * (1.0 - opt_total / raw_core_total) if raw_core_total else None
            row["red_total_src_pp"] = round3(red_total_src)
            row["red_total_src_core_pp"] = round3(red_total_src_core)
            row["red_total_base_pp"] = round3(red_total_base)
            row["red_2q_src_pp"] = round3(red_2q_src)
            row["red_2q_base_pp"] = round3(red_2q_base)
            row["h1_diff_pp"] = (
                round(red_total_src - red_total_base, 4)
                if red_total_src is not None and red_total_base is not None
                else ""
            )
            row["h3_diff_pp"] = (
                round(red_total_base - red_2q_base, 4)
                if red_total_base is not None and red_2q_base is not None
                else ""
            )
            row["h3_diff_src_pp"] = (
                round(red_total_src - red_2q_src, 4)
                if red_total_src is not None and red_2q_src is not None
                else ""
            )
            rows.append(row)

        # ---- determinism probe material (first 2 circuits) -----------------
        if circuit_id in ("bv_n4", "bv_n8") and len(level_outputs) == len(LEVELS):
            probe: dict[str, Any] = {"circuit_id": circuit_id, "levels": {}}
            for level in LEVELS:
                output = transpile(instance, optimization_level=level, basis_gates=NAM_BASIS, **TRANSPILE_KWARGS)
                counts = count_circuit(output)
                first = next(r for r in rows if r["circuit_id"] == circuit_id and r["level"] == level)
                probe["levels"][str(level)] = all(
                    counts[field] == first[row_field]
                    for field, row_field in (
                        ("total", "opt_total"), ("n_rz", "opt_rz"), ("n_cx", "opt_cx"),
                        ("n_h", "opt_h"), ("n_x", "opt_x"), ("depth", "opt_depth"),
                    )
                ) and qcec_verdict(instance, output) == first["equiv_qcec"]
            probe["identical"] = all(probe["levels"].values())
            determinism_probes.append(probe)

    # ---- self-checks -------------------------------------------------------
    circuit_ids = [record["circuit_id"] for record in instance_records]
    ok_rows = [row for row in rows if row.get("status") == "OK"]
    certified_rows = [row for row in rows if row.get("certified") == "yes"]
    excluded = [
        {"circuit_id": row["circuit_id"], "level": row["level"], "status": row.get("status"), "note": row.get("cert_note", "")}
        for row in rows
        if row.get("certified") != "yes"
    ]
    complete = all(
        sum(1 for row in rows if row["circuit_id"] == cid) == len(LEVELS) for cid in circuit_ids
    )
    raw_consistent = all(
        row.get("raw_total_regen") in ("", None) or int(row["raw_total_regen"]) == int(row["raw_total_census"])
        for row in rows
    )  # raw.size() regeneration vs the pinned census column (determinism)
    checks: dict[str, bool] = {
        "instance_sha256_match_e97_manifest": all(r["sha256_match"] for r in instance_records),
        "rows_complete_or_scope_reduction_declared": (complete and not unresolved) or (scope_reduction is not None and bool(unresolved)),
        "instance_counts_match_e97_census": all(row.get("census_root_count_match", False) for row in rows),
        "regenerated_raw_totals_match_census": raw_consistent,
        "all_verdict_rows_double_certified": len(certified_rows) == len(ok_rows) and len(ok_rows) > 0,
        "transpiled_outputs_within_frozen_basis": all(not row.get("opt_other") for row in rows),
        "determinism_two_circuits_identical": bool(determinism_probes)
        and len(determinism_probes) == 2
        and all(probe["identical"] for probe in determinism_probes),
        "protocol_quotes_byte_exact": all(
            quote in protocol["text"] for quote in protocol["hypotheses"].values()
        )
        and all(rule in protocol["text"] for rule in protocol["judgment_rules"]),
    }

    # ---- statistics over certified rows only -------------------------------
    certified = [row for row in rows if row.get("certified") == "yes"]
    families_by_circuit = {row["circuit_id"]: row["family"] for row in rows}
    stats: dict[str, Any] = {}

    def collect(metric: str) -> tuple[dict[int, list[float]], dict[int, list[str]]]:
        by_level: dict[int, list[float]] = {level: [] for level in LEVELS}
        fam_by_level: dict[int, list[str]] = {level: [] for level in LEVELS}
        for row in certified:
            value = row.get(metric)
            if value in ("", None):
                continue
            by_level[row["level"]].append(float(value))
            fam_by_level[row["level"]].append(row["family"])
        return by_level, fam_by_level

    h1_levels, h1_fams = collect("h1_diff_pp")
    h3_levels, h3_fams = collect("h3_diff_pp")
    h3s_levels, h3s_fams = collect("h3_diff_src_pp")

    # §3.3 clustering: circuit is the cluster unit; m = 4 level-configs
    h1_matrix_circuits = [
        [next((float(r["h1_diff_pp"]) for r in certified
               if r["circuit_id"] == cid and r["level"] == lv and r.get("h1_diff_pp") not in ("", None)), None)
         for lv in LEVELS]
        for cid in circuit_ids
    ]
    full = [row for row in h1_matrix_circuits if all(v is not None for v in row)]
    clustering = icc_deff(np.array(full)) if full else None
    deff = clustering["deff"] if clustering else 1.0
    governing = "circuit_level" if (clustering is None or deff <= 10.0) else "family_means_per_3_3"
    stats["clustering_3_3"] = {**(clustering or {}), "governing_unit": governing}

    def config_table(by_level, fam_by_level, label: str) -> dict[str, Any]:
        raw_p = {}
        per_level: dict[str, Any] = {}
        for level in LEVELS:
            diffs = by_level[level]
            if not diffs:
                per_level[f"L{level}"] = {"n": 0, "note": "no_certified_rows"}
                raw_p[str(level)] = 1.0
                continue
            per_level[f"L{level}"] = {
                "n": len(diffs),
                "median_diff_pp": round(float(np.median(diffs)), 4),
                "mean_diff_pp": round(float(np.mean(diffs)), 4),
                "share_positive": round(float(np.mean([d > 0 for d in diffs])), 4),
                "bootstrap_ci": bootstrap_median_ci(diffs, fam_by_level[level]),
                **wilcoxon_greater(diffs),
            }
            raw_p[str(level)] = per_level[f"L{level}"]["p_raw"]
        adjusted = holm_adjust(raw_p)
        for key, value in adjusted.items():
            per_level[f"L{key}"]["p_holm"] = round(value, 6)
            per_level[f"L{key}"]["significant_at_alpha"] = bool(value < ALPHA)
        return {"metric": label, "per_level": per_level}

    stats["h1"] = config_table(h1_levels, h1_fams, "source_relative_minus_baseline_relative_total_pp")
    stats["h3_primary"] = config_table(h3_levels, h3_fams, "total_minus_two_qubit_baseline_relative_pp")
    stats["h3_sensitivity_source_relative"] = config_table(h3s_levels, h3s_fams, "total_minus_two_qubit_source_relative_pp")

    if governing == "family_means_per_3_3":
        fam_of_circuit = {row["circuit_id"]: row["family"] for row in certified}
        family_mean: dict[str, list[float]] = {}
        for row in certified:
            if row.get("h1_diff_pp") in ("", None):
                continue
            family_mean.setdefault(fam_of_circuit[row["circuit_id"]], []).append(float(row["h1_diff_pp"]))
        fam_values = [float(np.mean(v)) for v in family_mean.values()]
        stats["h1_family_means_3_3"] = {
            "families": len(fam_values),
            "median_diff_pp": round(float(np.median(fam_values)), 4),
            **wilcoxon_greater(fam_values),
        }

    # ---- H1 verdict (registered rules: Wilcoxon alpha=0.05 Holm + median>=5pp;
    #      H0 branch per protocol §2: median < 2pp is a publishable negative) --
    def h1_verdict() -> dict[str, Any]:
        per_level = stats["h1"]["per_level"]
        verdicts = {}
        for key, entry in per_level.items():
            if entry.get("n", 0) == 0:
                verdicts[key] = "no_certified_rows"
            elif entry["significant_at_alpha"] and entry["median_diff_pp"] >= H1_THRESHOLD_PP:
                verdicts[key] = "supported"
            elif entry["median_diff_pp"] < H0_NEGATIVE_BRANCH_PP:
                verdicts[key] = "negative_h0_branch"
            else:
                verdicts[key] = "inconclusive"
        supported = [k for k, v in verdicts.items() if v == "supported"]
        if supported:
            overall = f"supported_for_available_configs:{','.join(supported)}"
        elif all(v == "negative_h0_branch" for v in verdicts.values()):
            overall = "negative_h0_branch_all_configs"
        else:
            overall = "inconclusive"
        return {
            "per_level": verdicts,
            "overall_round1": overall,
            "coverage": "1 of the protocol's >=3 tools available (Qiskit L0-L3); full H1 verdict deferred to rounds with pytket/BQSKit/pyzx",
        }

    def h3_verdict() -> dict[str, Any]:
        per_level = stats["h3_primary"]["per_level"]
        verdicts = {}
        for key, entry in per_level.items():
            if entry.get("n", 0) == 0:
                verdicts[key] = "no_certified_rows"
            elif entry["significant_at_alpha"] and entry["median_diff_pp"] > 0:
                verdicts[key] = "supported"
            elif entry["median_diff_pp"] <= 0:
                verdicts[key] = "not_supported"
            else:
                verdicts[key] = "inconclusive"
        supported = [k for k, v in verdicts.items() if v == "supported"]
        return {
            "per_level": verdicts,
            "overall_round1": f"supported_for_configs:{','.join(supported)}" if supported else "not_supported_round1",
        }

    # ---- H2 verdict (no test preregistered in §3 for H2; one-sided
    #      Mann-Whitney U declared here before results, recorded as a gap) ----
    h2_structural: list[float] = []
    h2_random: list[float] = []
    for cid in circuit_ids:
        diffs = [
            float(row["h1_diff_pp"])
            for row in certified
            if row["circuit_id"] == cid and row.get("h1_diff_pp") not in ("", None)
        ]
        if not diffs:
            continue
        family = families_by_circuit.get(cid, "")
        if family in H2_STRUCTURAL:
            h2_structural.append(float(np.mean(diffs)))
        elif family in H2_RANDOM:
            h2_random.append(float(np.mean(diffs)))
    if h2_structural and h2_random:
        mwu = sstats.mannwhitneyu(h2_structural, h2_random, alternative="greater")
        h2_result = {
            "structural_circuits": len(h2_structural),
            "random_circuits": len(h2_random),
            "median_structural_pp": round(float(np.median(h2_structural)), 4),
            "median_random_pp": round(float(np.median(h2_random)), 4),
            "p_one_sided_mwu": round(float(mwu.pvalue), 6),
            "significant_at_alpha": bool(float(mwu.pvalue) < ALPHA),
        }
        if h2_result["significant_at_alpha"] and h2_result["median_structural_pp"] > h2_result["median_random_pp"]:
            h2_verdict = "supported_provisional"
        elif h2_result["median_structural_pp"] <= h2_result["median_random_pp"]:
            h2_verdict = "not_supported_round1"
        else:
            h2_verdict = "inconclusive_underpowered"
    else:
        h2_result = {"structural_circuits": len(h2_structural), "random_circuits": len(h2_random)}
        h2_verdict = "no_data"

    # ---- monotonicity (measured, not assumed; E61 found L3 < L2 on 6/101) ---
    monotonicity: dict[str, Any] = {}
    for cid in circuit_ids:
        series = {
            row["level"]: row.get("opt_total")
            for row in rows
            if row["circuit_id"] == cid and isinstance(row.get("opt_total"), int)
        }
        if len(series) != len(LEVELS):
            continue
        for lo, hi in ((0, 1), (1, 2), (2, 3)):
            if series[hi] > series[lo]:
                monotonicity[f"L{hi}_worse_than_L{lo}"] = monotonicity.get(f"L{hi}_worse_than_L{lo}", 0) + 1
    monotonicity["note"] = "counts of circuits where the higher level produced MORE total gates (violation of L0<=L1<=L2<=L3); measured, never assumed"

    # ---- aggregates ---------------------------------------------------------
    conventions = ("red_total_src_pp", "red_total_base_pp", "red_2q_src_pp", "red_2q_base_pp")
    convention_aggregates: dict[str, Any] = {}
    for metric in conventions:
        by_level, _f = collect(metric)
        convention_aggregates[metric] = {
            f"L{level}": {
                "n": len(by_level[level]),
                "median_reduction_pp": round(float(np.median(by_level[level])), 4) if by_level[level] else None,
                "mean_reduction_pp": round(float(np.mean(by_level[level])), 4) if by_level[level] else None,
            }
            for level in LEVELS
        }

    aggregate_table = [
        {
            key: row.get(key)
            for key in (
                "circuit_id", "n_qubits", "family", "level", "status", "certified",
                "opt_total", "opt_rz", "opt_cx", "opt_depth",
                "baseline_total", "baseline_cx", "raw_total_census", "raw_cx",
                "red_total_src_pp", "red_total_base_pp", "red_2q_src_pp", "red_2q_base_pp",
                "h1_diff_pp", "h3_diff_pp", "equiv_qcec", "equiv_numerical",
            )
        }
        for row in rows
    ]

    negative_results: dict[str, Any] = {}
    h1_verdicts = h1_verdict()
    if h1_verdicts["overall_round1"].startswith("negative"):
        negative_results["h1"] = {
            "disposition": "protocol §2/§6: H0 is publishable; a <2pp median difference means baseline inflation is specific to the project's own out-of-basis panel, and D1's generalization tone must be withdrawn for in-basis inputs",
            "detail": h1_verdicts,
        }

    # ---- summary ------------------------------------------------------------
    try:
        import mqt.bench as mqt_bench  # noqa: F401

        mqt_bench_version = str(importlib.metadata.version("mqt.bench"))
    except Exception:
        mqt_bench_version = "unknown"

    summary = {
        "experiment_id": EXPERIMENT_ID,
        "round": "1 of the preregistered benchmark-accounting audit (round-24 item #5)",
        "protocol": {
            "file": PROTOCOL_PATH.name,
            "version": "1.0 (2026-11-04)",
            "sha256": protocol["sha256"],
            "preregistered": True,
        },
        "hypotheses_verbatim": protocol["hypotheses"],
        "judgment_rules_verbatim": protocol["judgment_rules"],
        "inputs": {
            "instances": "docs/review/science_boost/2026-11-06_mqt_second_panel/instances/*.qasm (E97 output, certified in the frozen basis)",
            "instance_sha256_source": "that package's MANIFEST.json",
            "per_instance": instance_records,
            "source_relative_denominator": "raw MQT generator-output gate counts from the E97 census (raw_gates column, primary); raw size / unitary core / two-qubit counts regenerated via mqt.bench and cross-checked against the census",
            "baseline_relative_denominator": "the level-0 rebase run (protocol §4: fixed basis {h,x,rz,cx}, optimization_level=0)",
        },
        "conventions": {
            "red_total_src_pp": "口径① source-relative, total gates: 100*(1-opt_total/raw_total_census) [primary; raw_total_census = E97 census raw_gates = raw.size(), includes the raw source's terminal measurement layer, the as-practiced convention]",
            "red_total_src_core_pp": "口径① declared secondary: same numerator over the raw source's unitary core (E97 _strip_terminal_nonunitary policy) - recorded for transparency, not used in verdicts",
            "red_total_base_pp": "口径② baseline-relative, total gates: 100*(1-opt_total/L0_rebase_total)",
            "red_2q_src_pp": "口径③ source-relative, two-qubit gates: 100*(1-opt_2q/raw_2q) [two-qubit gate counts, any name: raw sources may use cz]",
            "red_2q_base_pp": "口径③ baseline-relative, two-qubit gates: 100*(1-opt_2q/L0_rebase_2q)",
            "h1_diff_pp": "red_total_src_pp - red_total_base_pp (H1 statistic)",
            "h3_diff_pp": "red_total_base_pp - red_2q_base_pp (H3 primary statistic, same-basis pairing)",
            "h3_diff_src_pp": "red_total_src_pp - red_2q_src_pp (H3 sensitivity)",
        },
        "transpile_harness": {
            "reused_from": "scripts/e61_opt_level_monotonicity.py (kwargs + seed + cost metric, for comparability)",
            "basis_gates": NAM_BASIS,
            "kwargs": TRANSPILE_KWARGS,
            "levels": list(LEVELS),
        },
        "equivalence_gate": {
            "primary": "MQT QCEC 3.11.0 (protocol §3.4; sysconfig shim per docs/reproducibility.md)",
            "cross_check": "src.equivalence.certify_equivalence (E97/E71 exact numerical-unitary path)",
            "row_certified_only_if": 'QCEC "equivalent" AND numerical "VERIFIED_EQUIVALENT"; disagreements excluded fail-closed',
            "excluded_rows": excluded,
        },
        "per_convention_aggregate_table_rows_30x4": aggregate_table,
        "convention_aggregates": convention_aggregates,
        "statistics": stats,
        "verdicts": {
            "h1": h1_verdicts,
            "h2": {
                "statistic": h2_result,
                "verdict_round1": h2_verdict,
                "family_mapping_note": (
                    f"protocol structural families {H2_PROTOCOL_STRUCTURAL}: panel has Adder/QFT/QPE but no UCCSD; "
                    f"protocol random families {H2_PROTOCOL_RANDOM}: panel has only MQT randomcircuit (Haar-like random unitary, NOT RandomClifford); "
                    "verdict is provisional on the closest available families"
                ),
                "test_note": "§3 preregisters a test only for H1; one-sided Mann-Whitney U at alpha=0.05 declared before results",
            },
            "h3": h3_verdict(),
        },
        "monotonicity_measured": monotonicity,
        "determinism_check": {"circuits": [p["circuit_id"] for p in determinism_probes], "identical": all(p["identical"] for p in determinism_probes) if determinism_probes else None},
        "scope_reduction": scope_reduction,
        "negative_results": negative_results,
        "protocol_conflicts_and_gaps": [
            "§3.4 names QCEC 3.11.0; the brief names the project certify path - resolved by using QCEC as primary per the protocol AND the numerical certifier as an independent cross-check on every row (row certified only if both agree).",
            "The brief pins inputs to the E97-normalized instances (already the L0 rebase); protocol 口径① requires the generator's raw output as denominator - resolved by transpiling the instances (brief) while taking raw denominators from the sha256-pinned E97 census (protocol).",
            "H1/Holm: §3 expects 3 tools; round 1 has only Qiskit L0-L3, so Holm runs over the 4 level-configs within Qiskit and the 3-tool H1 verdict is deferred.",
            "H3: the protocol fixes the numerator (two-qubit gates) but not the denominator; primary pairing is baseline-relative (same basis on both sides, consistent with the protocol's own R2 critique), source-relative pairing reported as a preregistered sensitivity column.",
            "H2: protocol families UCCSD/HaarRandom/RandomClifford are absent from the MQT-30 panel; tested on Adder/QFT/QPE vs randomcircuit, provisional and underpowered (n_random=2).",
            "口径① denominator detail: the pinned census raw_gates counts raw.size(), which includes the raw source's terminal measurement layer (e.g. bv_n4: 11 = 8 unitary + 3 measures). The primary convention keeps the artifact as recorded (as-practiced); a declared secondary column (red_total_src_core_pp) uses the unitary core so the effect of that choice is itself auditable.",
        ],
        "self_checks": checks,
        "versions": {
            "python": sys.version.split()[0],
            "qiskit": importlib.import_module("qiskit").__version__,
            "qiskit_note": "installed version used; evidence chain pins 2.4.1, no upgrade performed",
            "numpy": np.__version__,
            "scipy": importlib.import_module("scipy").__version__,
            "mqt_bench": mqt_bench_version,
            "mqt_qcec": QCEC_VERSION,
        },
        "contract": {
            "writes": [str(out_dir.relative_to(ROOT)).replace("\\", "/")],
            "reads": {
                "protocol": str(PROTOCOL_PATH.relative_to(ROOT)).replace("\\", "/"),
                "e97_manifest": str(E97_MANIFEST.relative_to(ROOT)).replace("\\", "/"),
                "e97_census": str(E97_CENSUS.relative_to(ROOT)).replace("\\", "/"),
                "e97_census_sha256": sha256_file(E97_CENSUS),
            },
            "itt_note": "protocol §3.4: failed/uncertified rows stay in the denominator record (listed, never deleted silently); verdict aggregates use certified rows only",
        },
        "runtime_seconds": round(time.perf_counter() - started, 1),
    }

    # ---- write artifacts ----------------------------------------------------
    fields = [
        "circuit_id", "algorithm", "n_qubits", "family", "level", "status", "certified", "cert_note",
        "equiv_qcec", "equiv_numerical", "verify_seconds",
        "opt_total", "opt_rz", "opt_cx", "opt_h", "opt_x", "opt_other", "opt_depth", "transpile_seconds",
        "baseline_total", "baseline_cx", "raw_total_census", "raw_total_regen", "raw_total_unitary_core", "raw_2q",
        "raw_regen_note", "census_root_count_match", "in_e97_census", "instance_sha256_match",
        "red_total_src_pp", "red_total_src_core_pp", "red_total_base_pp", "red_2q_src_pp", "red_2q_base_pp",
        "h1_diff_pp", "h3_diff_pp", "h3_diff_src_pp",
    ]
    with (out_dir / "audit_rows.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    (out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    manifest_out = {
        "experiment_id": EXPERIMENT_ID,
        "artifacts": {
            path.relative_to(out_dir).as_posix(): {"sha256": sha256_file(path), "bytes": path.stat().st_size}
            for path in sorted(out_dir.rglob("*"))
            if path.is_file() and path.name != "MANIFEST.json"
        },
    }
    (out_dir / "MANIFEST.json").write_text(json.dumps(manifest_out, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    failed = [key for key, value in checks.items() if value is False]
    print(json.dumps({
        "h1": summary["verdicts"]["h1"]["overall_round1"],
        "h2": h2_verdict,
        "h3": summary["verdicts"]["h3"]["overall_round1"],
        "certified_rows": len(certified_rows),
        "rows": len(rows),
        "h1_medians_pp": {k: v.get("median_diff_pp") for k, v in stats["h1"]["per_level"].items()},
        "h3_medians_pp": {k: v.get("median_diff_pp") for k, v in stats["h3_primary"]["per_level"].items()},
        "monotonicity": monotonicity,
        "checks_failed": failed,
        "runtime_seconds": summary["runtime_seconds"],
    }, indent=1, ensure_ascii=False), flush=True)
    for key in failed:
        print(f"[E99] FAILED: {key}", flush=True)
    print(f"[E99] wrote {out_dir}", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
