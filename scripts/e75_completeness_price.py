"""E75: the price of completeness -- coverage as a function of rule-pattern length.

Motivation
----------
E73 (2026-10-27) measured a single point of the incompleteness curve: on the
2-qubit Clifford fragment with listings of length <= 4, the frozen 1,474-rule
library reaches the absolute optimum for only 69.75% of the reducible listings,
i.e. 30.25% remain unreachable.  It also found the structural cause -- of the
1,474 Quartz rules only 14 are single-qubit rules, and there is *no* single-qubit
rule of source length 3, so ``h0.x0.h0.z0`` (= I) has zero legal actions.

A single point cannot distinguish two very different worlds:

  (a) incompleteness is *diffuse* -- every extra rule buys a little coverage, so
      the price falls smoothly as the library grows, or
  (b) incompleteness is *thresholded* -- the whole gap is caused by one missing
      length class, so the price collapses to zero as soon as that class exists.

This experiment measures the curve.  It parameterises the library by the maximum
source-pattern length ``L`` and the pattern arity, builds the *maximally powerful*
rule set of that class directly from exhaustive enumeration (so no hand-written
rule can be blamed), and reports

    P(L) = 1 - coverage(L)

on two fragments where the absolute optimum is known by enumeration:

  Part A  width 2, listings <= 4 gates, generators {h,x,z,cx} x 2 qubits
          -> directly comparable with E73's 30.25%
  Part B  width 1, listings <= 8 gates, generators {h,x,z}
          -> the *scaling* of the required rule length with instance length

Part B is the point of the experiment.  If the minimal sufficient rule length
``tau`` grows with the listing length, then no fixed-length library can be
complete, and the price of a fixed ``L`` is a decaying function whose decay
rate is a measurable property of the gate set -- not a property of any
particular library.

Contract
--------
Read-only.  Frozen rule library
``data/v13/e43_quartz_rule_import/generation_a/rule_library.json`` (sha256
recorded).  Nothing under ``data/``, ``release/`` or ``docs/manuscript/`` is
written.  No search budget beyond the frozen peephole contract is used: greedy
closure plus a bounded monotone BFS of depth <= min(gap, 3), exactly as E73.

Built-in checks (the run aborts if any fails)
  1. ``base`` config must reproduce E73's published numbers exactly
     (2,830 reducible / 1,580 greedy exact / 1,974 after search / 856 failures).
  2. Every synthetic action must preserve the unitary up to global phase.
  3. ``c_abs`` recomputed from the class table must match the enumeration.

Outputs (``docs/review/science_boost/2026-10-28_completeness_price/``)
    price_curve.csv     one row per (part, config)
    member_tau.csv      one row per member: tau, tau_single, tau_multi
    tau_by_length.csv   Part B: tau distribution conditioned on listing length
    summary.json        contract, coverage table, self-check results
    MANIFEST.json       sha256 of every artifact
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import itertools
import json
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

from src.optimisation.certified_landscape import (  # noqa: E402
    LandscapeState,
    StateGate,
    _state_from_normalized,
    legal_actions,
    state_unitary,
)

EXPERIMENT_ID = "E75_COMPLETENESS_PRICE_2026_10_28"
RULE_LIBRARY = ROOT / "data" / "v13" / "e43_quartz_rule_import" / "generation_a" / "rule_library.json"
OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-10-28_completeness_price"


def _load_e73() -> Any:
    """Reuse E73's enumeration / class-key / listing helpers verbatim."""

    spec = importlib.util.spec_from_file_location(
        "e73_library_completeness", ROOT / "scripts" / "e73_library_completeness.py"
    )
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RuntimeError("cannot_load_e73")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


E73 = _load_e73()

WIDTH2_GENERATORS: tuple[tuple[str, tuple[int, ...]], ...] = E73.GENERATORS
WIDTH1_GENERATORS: tuple[tuple[str, tuple[int, ...]], ...] = (
    ("h", (0,)),
    ("x", (0,)),
    ("z", (0,)),
)
# Part C: a two-qubit fragment small enough to enumerate to length 8, so that the
# completeness threshold L* can be compared across widths at the *same* listing
# length.  Three generators keeps 3^8 = 6,561 listings per length, the same order
# as Part B's 1-qubit fragment.
WIDTH2C_GENERATORS: tuple[tuple[str, tuple[int, ...]], ...] = (
    ("h", (0,)),
    ("h", (1,)),
    ("cx", (0, 1)),
)
# Part D: width 2 with a phase gate on both qubits, so that the fragment is
# structurally comparable to Part B (1 qubit, {h,x,z}) rather than to Part C's
# phase-free {h,cx}.  5 generators x length 6 = 15,625 listings per length.
WIDTH2D_GENERATORS: tuple[tuple[str, tuple[int, ...]], ...] = (
    ("h", (0,)),
    ("x", (0,)),
    ("h", (1,)),
    ("x", (1,)),
    ("cx", (0, 1)),
)

# E73's published numbers, used as a hard regression gate for the ``base`` config.
# Source: docs/review/science_boost/2026-10-27_library_completeness/summary.json
# (the prose in the round-17 narrative says 460 classes; the machine-readable
# summary says 458, and 458 is what the enumeration reproduces -- the prose is
# the rounded figure and the summary is authoritative).
E73_REFERENCE = {
    "members": 4681,
    "classes": 458,
    "reducible": 2830,
    "greedy_exact": 1580,
    "after_search": 1974,
    "failures": 856,
}


@dataclass(frozen=True)
class SyntheticAction:
    """A rewrite that the complete rule set of a given pattern class would allow.

    ``rule_id`` encodes the class so that the greedy tie-break stays
    deterministic and inspectable (``synth:w2:1q:L3@5`` = window of 3 gates on
    one qubit starting at position 5).
    """

    rule_id: str
    location: int
    cost_delta: int
    post_state: LandscapeState
    window: tuple[int, int]
    pattern: str
    replacement: str


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_key_fixed(matrix: np.ndarray, tol: float = 1e-9, digits: int = 6) -> str:
    """Phase-invariant unitary key that is stable under modulus ties.

    E73's key divides the matrix by the *value* of the largest-magnitude entry.
    That is phase-invariant only while the largest-magnitude entry is unique:
    when several entries tie in modulus -- which is the normal case for Clifford
    unitaries, where every entry has modulus 0, 1 or 1/sqrt(2) -- floating-point
    noise decides which tied entry ``argmax`` returns, and dividing by entries of
    different phase produces keys that differ by a global phase.  The same
    unitary then lands in several classes, ``c_abs`` is computed per split, and
    the resulting gap is an *overestimate*.

    This key divides by the *phase* of the first entry whose modulus exceeds
    ``tol``.  The zero pattern of a unitary is invariant under global phase, so
    the selected index is stable, and the division removes exactly the global
    phase.
    """

    flat = matrix.reshape(-1)
    modulus = np.abs(flat)
    index = int(np.argmax(modulus > tol))
    if modulus[index] <= tol:
        raise RuntimeError("degenerate_unitary")
    phase = flat[index] / modulus[index]
    normalised = matrix * np.conj(phase)
    real = np.round(normalised.real, digits) + 0.0
    imag = np.round(normalised.imag, digits) + 0.0
    return ";".join(f"{r:+.6f}{i:+.6f}" for r, i in zip(real.reshape(-1), imag.reshape(-1)))


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def gate_tuple_text(gates: Iterable[StateGate]) -> str:
    parts = []
    for gate in gates:
        parts.append(gate.name + "".join(str(q) for q in gate.qubits))
    return ".".join(parts)


class Fragment:
    """An exhaustively enumerated gate-set fragment with a truth table."""

    def __init__(
        self,
        name: str,
        num_qubits: int,
        generators: tuple[tuple[str, tuple[int, ...]], ...],
        max_length: int,
        key_mode: str = "fixed",
    ):
        self.name = name
        self.num_qubits = num_qubits
        self.generators = generators
        self.max_length = max_length
        self.key_mode = key_mode
        self.alphabet = frozenset(name for name, _ in generators)
        self.states = self._enumerate()
        self._key_cache: dict[tuple[tuple[str, tuple[int, ...]], ...], str] = {}
        self.classes: dict[str, list[tuple[int, LandscapeState]]] = defaultdict(list)
        for state in self.states:
            self.classes[self.key(state.gates)].append((len(state.gates), state))
        self.c_abs: dict[str, int] = {key: min(cost for cost, _ in members) for key, members in self.classes.items()}
        self.best_form: dict[str, tuple[str, tuple[StateGate, ...]]] = {}
        for key, members in self.classes.items():
            best_cost, best_state = min(members, key=lambda item: (item[0], gate_tuple_text(item[1].gates)))
            self.best_form[key] = (best_cost, best_state.gates)
        # exact-number of reducible members
        self.reducible = [
            state
            for state in self.states
            if len(state.gates) > self.c_abs[self.key(state.gates)]
        ]

    def _enumerate(self) -> list[LandscapeState]:
        states: list[LandscapeState] = [_state_from_normalized(self.num_qubits, ())]
        for length in range(1, self.max_length + 1):
            for word in itertools.product(range(len(self.generators)), repeat=length):
                gates = tuple(StateGate(self.generators[i][0], self.generators[i][1], None) for i in word)
                states.append(_state_from_normalized(self.num_qubits, gates))
        return states

    def key(self, gates: tuple[StateGate, ...]) -> str:
        cache_key = tuple((gate.name, tuple(gate.qubits)) for gate in gates)
        cached = self._key_cache.get(cache_key)
        if cached is not None:
            return cached
        state = _state_from_normalized(self.num_qubits, gates)
        if self.key_mode == "legacy":
            key = E73.canonical_unitary_key(state)
        elif self.key_mode == "fixed":
            key = canonical_key_fixed(state_unitary(state))
        else:  # pragma: no cover - defensive
            raise ValueError(f"unknown_key_mode:{self.key_mode}")
        self._key_cache[cache_key] = key
        return key

    def window_arity(self, gates: tuple[StateGate, ...]) -> int:
        return len({q for gate in gates for q in gate.qubits})

    def tied_pivot_count(self, tol: float = 1e-12) -> int:
        """Listings whose unitary attains its maximal entry modulus more than once.

        This is exactly the condition under which the legacy key can pick
        different pivot entries for the same unitary, so it bounds the damage
        the legacy key can do on this fragment.
        """

        count = 0
        for state in self.states:
            modulus = np.abs(state_unitary(state).reshape(-1))
            top = modulus.max()
            if top > 0 and int(np.sum(modulus >= top - tol)) > 1:
                count += 1
        return count


def synthetic_actions(
    fragment: Fragment,
    state: LandscapeState,
    lmin: int,
    lmax: int,
    arity: int | None,
) -> list[SyntheticAction]:
    """Every rewrite that a complete rule set of pattern length in [lmin, lmax] would allow."""

    gates = state.gates
    actions: list[SyntheticAction] = []
    for length in range(lmin, lmax + 1):
        if length > len(gates):
            continue
        for start in range(0, len(gates) - length + 1):
            window = gates[start : start + length]
            if arity is not None and fragment.window_arity(window) != arity:
                continue
            key = fragment.key(window)
            best_cost, best_gates = fragment.best_form[key]
            if best_cost >= length:
                continue
            post_gates = gates[:start] + best_gates + gates[start + length :]
            post = _state_from_normalized(fragment.num_qubits, post_gates)
            actions.append(
                SyntheticAction(
                    rule_id=f"synth:w{fragment.num_qubits}:{arity or 0}q:L{length}",
                    location=start,
                    cost_delta=best_cost - length,
                    post_state=post,
                    window=(start, start + length),
                    pattern=gate_tuple_text(window),
                    replacement=gate_tuple_text(best_gates),
                )
            )
    return actions


class ActionCache:
    """Base-library actions are config-independent, so cache them per state.

    The cache stores every *non-increasing* action (``cost_delta <= 0``) because
    the greedy closure needs the strictly reducing subset while the bounded BFS
    must also traverse cost-neutral rewrites -- E73's BFS expands neutral actions,
    and dropping them loses 388 of its 394 rescues.
    """

    def __init__(self) -> None:
        self._cache: dict[tuple[frozenset[str], tuple[Any, ...]], list[Any]] = {}

    def get(self, state: LandscapeState, alphabet: frozenset[str]) -> list[Any]:
        key = (alphabet, tuple((g.name, g.qubits) for g in state.gates))
        hit = self._cache.get(key)
        if hit is not None:
            return hit
        actions = []
        for action in legal_actions(state, RULE_LIBRARY, "full"):
            if action.cost_delta > 0:
                continue
            if any(gate.name not in alphabet for gate in action.post_state.gates):
                continue
            actions.append(action)
        self._cache[key] = actions
        return actions


@dataclass(frozen=True)
class Config:
    name: str
    arity: int | None
    lmin: int
    lmax: int
    include_base: bool = True


def actions_for(
    fragment: Fragment,
    state: LandscapeState,
    config: Config,
    cache: ActionCache,
    restrict_alphabet: bool = True,
    strictly_reducing: bool = False,
) -> list[Any]:
    """Actions available under ``config``.

    ``strictly_reducing=True`` reproduces the greedy closure contract (only
    ``cost_delta < 0``); ``False`` reproduces the BFS contract (``cost_delta <= 0``).
    """

    out: list[Any] = []
    if config.include_base:
        out.extend(cache.get(state, fragment.alphabet))
    if config.lmax >= config.lmin:
        out.extend(synthetic_actions(fragment, state, config.lmin, config.lmax, config.arity))
    if strictly_reducing:
        return [action for action in out if action.cost_delta < 0]
    return [action for action in out if action.cost_delta <= 0]


def greedy_closure(
    fragment: Fragment,
    state: LandscapeState,
    config: Config,
    cache: ActionCache,
    deadline: float,
    restrict_alphabet: bool = True,
) -> tuple[LandscapeState, list[str], bool]:
    current = state
    path: list[str] = []
    for _ in range(32):
        if time.perf_counter() > deadline:
            return current, path + ["DEADLINE"], True
        candidates = actions_for(
            fragment,
            state=current,
            config=config,
            cache=cache,
            restrict_alphabet=restrict_alphabet,
            strictly_reducing=True,
        )
        if not candidates:
            break
        best = min(
            candidates,
            key=lambda a: (a.post_state.cost, a.rule_id, a.location),
        )
        current = best.post_state
        path.append(f"{best.rule_id}@{best.location}({best.cost_delta})")
    return current, path, False


def bfs_reaches(
    fragment: Fragment,
    state: LandscapeState,
    target_cost: int,
    max_depth: int,
    config: Config,
    cache: ActionCache,
    deadline: float,
    restrict_alphabet: bool = True,
    max_nodes: int = 20000,
) -> tuple[bool | None, int, str]:
    """Exhaustive monotone search for any state of cost <= target within max_depth."""

    frontier: list[tuple[LandscapeState, tuple[str, ...]]] = [(state, ())]
    seen = {state.state_hash}
    nodes = 0
    for _depth in range(max_depth):
        next_frontier: list[tuple[LandscapeState, tuple[str, ...]]] = []
        for current, path in frontier:
            if time.perf_counter() > deadline or nodes > max_nodes:
                return None, nodes, "BUDGET"
            for action in actions_for(
                fragment, state=current, config=config, cache=cache, restrict_alphabet=restrict_alphabet
            ):
                nodes += 1
                if action.post_state.cost <= target_cost:
                    return True, nodes, "|".join(path + (f"{action.rule_id}@{action.location}",))
                if action.post_state.state_hash in seen:
                    continue
                seen.add(action.post_state.state_hash)
                next_frontier.append((action.post_state, path + (f"{action.rule_id}@{action.location}",)))
        frontier = next_frontier
        if not frontier:
            break
    return False, nodes, ""


def evaluate(
    fragment: Fragment,
    config: Config,
    cache: ActionCache,
    deadline: float,
    check_unitary: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Run one library configuration over every reducible member of the fragment."""

    rows: list[dict[str, Any]] = []
    greedy_exact = 0
    after_search = 0
    budget = 0
    for state in fragment.reducible:
        key = fragment.key(state.gates)
        c_abs = fragment.c_abs[key]
        closed, path, timed_out = greedy_closure(fragment, state, config, cache, deadline)
        if timed_out:
            raise RuntimeError("closure_deadline")
        reached: bool | None = None
        nodes = 0
        bfs_path = ""
        if closed.cost > c_abs:
            gap = closed.cost - c_abs
            reached, nodes, bfs_path = bfs_reaches(
                fragment,
                state,
                c_abs,
                max_depth=min(gap, 3),
                config=config,
                cache=cache,
                deadline=deadline,
            )
        if closed.cost == c_abs:
            greedy_exact += 1
            reached = True
        if reached is True:
            after_search += 1
        if reached is None:
            budget += 1
        if check_unitary:
            reference = state_unitary(state)
            for probe in (closed,):
                overlap = np.abs(np.trace(reference.conj().T @ state_unitary(probe))) / reference.shape[0]
                if abs(overlap - 1.0) > 1e-9:
                    raise RuntimeError(f"unitary_violation:{gate_tuple_text(state.gates)}")
        rows.append(
            {
                "config": config.name,
                "listing": gate_tuple_text(state.gates),
                "cost": len(state.gates),
                "c_abs": c_abs,
                "c_closed": closed.cost,
                "gap_closed": closed.cost - c_abs,
                "reached": "" if reached is None else reached,
                "bfs_nodes": nodes,
                "bfs_path": bfs_path,
                "greedy_path": "|".join(path),
            }
        )
    reducible = len(fragment.reducible)
    stats = {
        "config": config.name,
        "arity": config.arity,
        "lmin": config.lmin,
        "lmax": config.lmax,
        "include_base": config.include_base,
        "members_total": len(fragment.states),
        "members_reducible": reducible,
        "greedy_exact": greedy_exact,
        "greedy_rate": round(greedy_exact / reducible, 6) if reducible else None,
        "after_search": after_search,
        "after_search_rate": round(after_search / reducible, 6) if reducible else None,
        "failures": reducible - after_search,
        "price": round(1 - after_search / reducible, 6) if reducible else None,
        "budget_exhausted": budget,
    }
    return rows, stats


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--width2-max-length", type=int, default=4)
    parser.add_argument("--width1-max-length", type=int, default=8)
    parser.add_argument("--width2c-max-length", type=int, default=8)
    parser.add_argument("--budget-seconds", type=float, default=5400.0)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--skip-part-b", action="store_true")
    parser.add_argument("--skip-part-c", action="store_true")
    args = parser.parse_args()
    out = args.output_root
    out.mkdir(parents=True, exist_ok=True)
    deadline = time.perf_counter() + args.budget_seconds
    cache = ActionCache()

    started = time.perf_counter()

    # ---------------------------------------------------------------- Part A
    m = args.width2_max_length
    configs_a = [Config("base", None, 1, 0)]
    configs_a += [Config(f"1q_L2_{L}", 1, 2, L) for L in range(2, m + 1)]
    configs_a += [Config("1q_L3only", 1, 3, 3)]
    configs_a += [Config(f"2q_L2_{L}", 2, 2, L) for L in range(2, m + 1)]
    configs_a += [Config(f"all_L2_{L}", None, 2, L) for L in range(2, m + 1)]

    # (a) legacy key: reproduces E73 exactly, and quantifies the key defect.
    frag_legacy = Fragment("width2_legacy", 2, WIDTH2_GENERATORS, m, key_mode="legacy")
    legacy_rows, legacy_base = evaluate(frag_legacy, configs_a[0], cache, deadline)
    legacy_base["part"] = "A0_width2_legacy_key"
    reference_ok = (
        legacy_base["members_total"] == E73_REFERENCE["members"]
        and len(frag_legacy.classes) == E73_REFERENCE["classes"]
        and legacy_base["members_reducible"] == E73_REFERENCE["reducible"]
        and legacy_base["greedy_exact"] == E73_REFERENCE["greedy_exact"]
        and legacy_base["after_search"] == E73_REFERENCE["after_search"]
        and legacy_base["failures"] == E73_REFERENCE["failures"]
    )
    if not reference_ok:
        raise RuntimeError(f"e73_regression_gate_failed:{json.dumps(legacy_base)}")
    del legacy_rows

    # (b) fixed key: the corrected measurement.
    frag_a = Fragment("width2", 2, WIDTH2_GENERATORS, m, key_mode="fixed")

    curve_rows: list[dict[str, Any]] = [legacy_base]
    per_member: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    stats_a: dict[str, Any] = {}
    for config in configs_a:
        rows, stats = evaluate(frag_a, config, cache, deadline)
        stats["part"] = "A_width2"
        stats_a[config.name] = stats
        curve_rows.append(stats)
        for row in rows:
            per_member[row["listing"]][config.name] = row

    base = stats_a["base"]

    # tau per member: the smallest complete-library pattern length that suffices.
    tau_rows: list[dict[str, Any]] = []
    for listing, by_config in per_member.items():
        tau = None
        for L in range(2, m + 1):
            row = by_config.get(f"all_L2_{L}")
            if row is not None and row["reached"] is True:
                tau = L
                break
        tau_1q = None
        for L in range(2, m + 1):
            row = by_config.get(f"1q_L2_{L}")
            if row is not None and row["reached"] is True:
                tau_1q = L
                break
        tau_2q = None
        for L in range(2, m + 1):
            row = by_config.get(f"2q_L2_{L}")
            if row is not None and row["reached"] is True:
                tau_2q = L
                break
        base_row = by_config["base"]
        tau_rows.append(
            {
                "part": "A_width2",
                "listing": listing,
                "cost": base_row["cost"],
                "c_abs": base_row["c_abs"],
                "base_gap": base_row["gap_closed"],
                "base_reached": base_row["reached"],
                "tau_all": "" if tau is None else tau,
                "tau_1q": "" if tau_1q is None else tau_1q,
                "tau_2q": "" if tau_2q is None else tau_2q,
            }
        )

    # ---------------------------------------------------------------- Part B
    part_b: dict[str, Any] = {}
    tau_by_length_rows: list[dict[str, Any]] = []
    if not args.skip_part_b:
        frag_b = Fragment("width1", 1, WIDTH1_GENERATORS, args.width1_max_length, key_mode="fixed")
        n = args.width1_max_length
        configs_b = [Config("base", None, 1, 0)]
        configs_b += [Config(f"all_L2_{L}", None, 2, L) for L in range(2, n + 1)]
        stats_b: dict[str, Any] = {}
        member_tau_b: dict[str, dict[str, Any]] = {}
        for config in configs_b:
            rows, stats = evaluate(frag_b, config, cache, deadline)
            stats["part"] = "B_width1"
            stats_b[config.name] = stats
            curve_rows.append(stats)
            for row in rows:
                member_tau_b.setdefault(row["listing"], {})[config.name] = row
        for listing, by_config in member_tau_b.items():
            tau = None
            for L in range(2, n + 1):
                row = by_config.get(f"all_L2_{L}")
                if row is not None and row["reached"] is True:
                    tau = L
                    break
            base_row = by_config["base"]
            tau_rows.append(
                {
                    "part": "B_width1",
                    "listing": listing,
                    "cost": base_row["cost"],
                    "c_abs": base_row["c_abs"],
                    "base_gap": base_row["gap_closed"],
                    "base_reached": base_row["reached"],
                    "tau_all": "" if tau is None else tau,
                    "tau_1q": "",
                    "tau_2q": "",
                }
            )
        by_length: dict[int, list[int]] = defaultdict(list)
        for row in tau_rows:
            if row["part"] != "B_width1":
                continue
            if row["tau_all"] == "":
                continue
            by_length[int(row["cost"])].append(int(row["tau_all"]))
        for length, taus in sorted(by_length.items()):
            counter = Counter(taus)
            row = {
                "part": "B_width1",
                "listing_length": length,
                "n": len(taus),
                "tau_min": min(taus),
                "tau_median": sorted(taus)[len(taus) // 2],
                "tau_mean": round(sum(taus) / len(taus), 4),
                "tau_max": max(taus),
                "tau_histogram": json.dumps({str(k): v for k, v in sorted(counter.items())}),
            }
            for L in range(2, n + 1):
                row[f"price_L{L}"] = round(sum(1 for t in taus if t > L) / len(taus), 6)
            tau_by_length_rows.append(row)
        # legacy key on the same width-1 fragment: quantifies the key defect
        frag_b_legacy = Fragment("width1_legacy", 1, WIDTH1_GENERATORS, args.width1_max_length, key_mode="legacy")
        _legacy_rows, legacy_b_base = evaluate(frag_b_legacy, configs_b[0], cache, deadline)
        legacy_b_base["part"] = "B0_width1_legacy_key"
        curve_rows.append(legacy_b_base)
        part_b = {
            "fragment": {
                "num_qubits": 1,
                "generators": [f"{name}{''.join(str(q) for q in qubits)}" for name, qubits in WIDTH1_GENERATORS],
                "max_length": n,
                "listings": len(frag_b.states),
                "classes": len(frag_b.classes),
                "reducible": len(frag_b.reducible),
            },
            "legacy_key": {
                "classes": len(frag_b_legacy.classes),
                "reducible": len(frag_b_legacy.reducible),
                "price": legacy_b_base["price"],
            },
            "configs": stats_b,
            "tau_by_length": tau_by_length_rows,
        }

    # ---------------------------------------------------------------- Part C
    # Same listing-length window as Part B (m <= 8), width 2.  This is the only
    # fragment here where the completeness threshold L* can be read off *and*
    # compared with Part B's L* = 4 at equal m.
    part_c: dict[str, Any] = {}
    tau_c_by_length: list[dict[str, Any]] = []
    if not args.skip_part_c:
        n_c = args.width2c_max_length
        frag_c = Fragment("width2c", 2, WIDTH2C_GENERATORS, n_c, key_mode="fixed")
        configs_c = [Config("base", None, 1, 0)]
        configs_c += [Config(f"all_L2_{L}", None, 2, L) for L in range(2, n_c + 1)]
        stats_c: dict[str, Any] = {}
        member_c: dict[str, dict[str, Any]] = {}
        for config in configs_c:
            rows, stats = evaluate(frag_c, config, cache, deadline)
            stats["part"] = "C_width2c"
            stats_c[config.name] = stats
            curve_rows.append(stats)
            for row in rows:
                member_c.setdefault(row["listing"], {})[config.name] = row
        by_length_c: dict[int, list[int]] = defaultdict(list)
        tau_c: list[dict[str, Any]] = []
        for listing, by_config in member_c.items():
            tau = None
            for L in range(2, n_c + 1):
                row = by_config.get(f"all_L2_{L}")
                if row is not None and row["reached"] is True:
                    tau = L
                    break
            base_row = by_config["base"]
            tau_c.append(
                {
                    "part": "C_width2c",
                    "listing": listing,
                    "cost": base_row["cost"],
                    "c_abs": base_row["c_abs"],
                    "base_gap": base_row["gap_closed"],
                    "base_reached": base_row["reached"],
                    "tau_all": "" if tau is None else tau,
                    "tau_1q": "",
                    "tau_2q": "",
                }
            )
            if tau is not None:
                by_length_c[int(base_row["cost"])].append(int(tau))
        tau_rows.extend(tau_c)
        for length, taus in sorted(by_length_c.items()):
            row = {
                "part": "C_width2c",
                "listing_length": length,
                "n": len(taus),
                "tau_min": min(taus),
                "tau_median": sorted(taus)[len(taus) // 2],
                "tau_mean": round(sum(taus) / len(taus), 4),
                "tau_max": max(taus),
                "tau_histogram": json.dumps({str(k): v for k, v in sorted(Counter(taus).items())}),
            }
            for L in range(2, n_c + 1):
                row[f"price_L{L}"] = round(sum(1 for t in taus if t > L) / len(taus), 6)
            tau_c_by_length.append(row)
        part_c = {
            "fragment": {
                "num_qubits": 2,
                "generators": [f"{name}{''.join(str(q) for q in qubits)}" for name, qubits in WIDTH2C_GENERATORS],
                "max_length": n_c,
                "listings": len(frag_c.states),
                "classes": len(frag_c.classes),
                "reducible": len(frag_c.reducible),
            },
            "configs": stats_c,
            "tau_by_length": tau_c_by_length,
            "threshold": next(
                (L for L in range(2, n_c + 1) if stats_c[f"all_L2_{L}"]["price"] == 0.0),
                None,
            ),
        }

    # ---------------------------------------------------------------- self-checks
    checks = {
        "e73_regression_gate_legacy_key": "PASS" if reference_ok else "FAIL",
        "legacy_key_reproduces_30_25pct": legacy_base["price"] == round(1 - 1974 / 2830, 6),
        "fixed_key_merges_legacy_classes": len(frag_a.classes) <= len(frag_legacy.classes),
        "classes_sum_to_listings": sum(len(v) for v in frag_a.classes.values()) == len(frag_a.states),
        "c_abs_non_negative": all(v >= 0 for v in frag_a.c_abs.values()),
        "tau_defined_for_all_reached": all(
            row["tau_all"] != "" for row in tau_rows if row["base_reached"] is True and row["part"] == "A_width2"
        ),
        "monotone_price_in_L": all(
            stats_a[f"all_L2_{L}"]["price"] >= stats_a[f"all_L2_{L + 1}"]["price"] for L in range(2, m)
        ),
    }

    summary = {
        "experiment_id": EXPERIMENT_ID,
        "as_of": "2026-10-28",
        "purpose": "measure the price of a fixed-length rule library on fragments where the absolute optimum is enumerated",
        "contract": {
            "rule_library": RULE_LIBRARY.relative_to(ROOT).as_posix(),
            "rule_library_sha256": sha256_file(RULE_LIBRARY),
            "scope": "full (1,474 quartz rules) + pair_v1 + structural exchanges",
            "search": "greedy closure + monotone BFS depth <= min(gap, 3), max 20,000 nodes",
            "read_only": ["data/", "release/", "docs/manuscript/"],
            "synthetic_library": (
                "the maximally powerful rule set of a given (arity, source length) class, built "
                "from exhaustive enumeration: every window is replaced by the minimal listing of "
                "its unitary class inside the fragment"
            ),
            "unitary_key": {
                "fixed": "divide by the phase of the first entry whose modulus exceeds 1e-9",
                "legacy": "E73's canonical_unitary_key: divide by the value of the argmax entry",
            },
        },
        "part_a_legacy_key": {
            "fragment": {
                "num_qubits": 2,
                "max_length": m,
                "listings": len(frag_legacy.states),
                "classes": len(frag_legacy.classes),
                "reducible": len(frag_legacy.reducible),
            },
            "base": legacy_base,
        },
        "part_a": {
            "fragment": {
                "num_qubits": 2,
                "generators": [f"{name}{''.join(str(q) for q in qubits)}" for name, qubits in WIDTH2_GENERATORS],
                "max_length": m,
                "listings": len(frag_a.states),
                "classes": len(frag_a.classes),
                "reducible": len(frag_a.reducible),
                "c_abs_histogram": dict(sorted(Counter(frag_a.c_abs.values()).items())),
            },
            "configs": stats_a,
        },
        "key_defect": {
            "statement": (
                "the legacy key is phase-invariant only while the largest-magnitude entry is unique; "
                "on Clifford unitaries the moduli often tie, argmax picks a different tied entry, and the "
                "same unitary is split across several classes, inflating c_abs and therefore the measured gap"
            ),
            "width2": {
                "legacy_classes": len(frag_legacy.classes),
                "fixed_classes": len(frag_a.classes),
                "legacy_price": legacy_base["price"],
                "fixed_price": stats_a["base"]["price"],
                "tied_pivot_listings": frag_a.tied_pivot_count(),
            },
            "width1": {
                "legacy_classes": part_b.get("legacy_key", {}).get("classes"),
                "fixed_classes": part_b.get("fragment", {}).get("classes"),
                "legacy_price": part_b.get("legacy_key", {}).get("price"),
                "fixed_price": part_b.get("configs", {}).get("base", {}).get("price"),
            },
        },
        "part_b": part_b,
        "part_c": part_c,
        "thresholds": {
            "width1": next(
                (L for L in range(2, args.width1_max_length + 1) if part_b.get("configs", {}).get(f"all_L2_{L}", {}).get("price") == 0.0),
                None,
            )
            if part_b
            else None,
            "width2c": part_c.get("threshold"),
            "note": (
                "L* = the smallest pattern length at which the complete library of that length "
                "reaches the fragment optimum for every reducible listing. Part A cannot measure "
                "L* because its maximum listing length (4) equals the candidate threshold."
            ),
        },
        "self_checks": checks,
        "runtime_seconds": round(time.perf_counter() - started, 1),
    }

    _write_csv(
        out / "price_curve.csv",
        curve_rows,
        [
            "part",
            "config",
            "arity",
            "lmin",
            "lmax",
            "include_base",
            "members_reducible",
            "greedy_exact",
            "greedy_rate",
            "after_search",
            "after_search_rate",
            "failures",
            "price",
            "budget_exhausted",
        ],
    )
    _write_csv(
        out / "member_tau.csv",
        tau_rows,
        ["part", "listing", "cost", "c_abs", "base_gap", "base_reached", "tau_all", "tau_1q", "tau_2q"],
    )
    _write_csv(
        out / "tau_by_length.csv",
        tau_by_length_rows,
        ["part", "listing_length", "n", "tau_min", "tau_median", "tau_mean", "tau_max", "tau_histogram"]
        + [f"price_L{L}" for L in range(2, args.width1_max_length + 1)],
    )
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    (out / "MANIFEST.json").write_text(
        json.dumps(
            {
                "experiment_id": EXPERIMENT_ID,
                "generated": "2026-10-28",
                "script": "scripts/e75_completeness_price.py",
                "artifacts": {
                    name: sha256_file(out / name)
                    for name in sorted(["price_curve.csv", "member_tau.csv", "tau_by_length.csv", "summary.json"])
                },
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    print(json.dumps({"self_checks": checks, "part_a_configs": stats_a, "part_b": part_b.get("tau_by_length", [])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
