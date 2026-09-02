"""E44 exhaustive oracle validation for the v13 certified landscape core.

The formal search is imported from ``src.optimisation``.  The oracle below
reimplements rule matching and finite-horizon enumeration from the serialized
rule snapshot so that the comparison does not call the formal search helpers.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any, Mapping
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.optimisation.certified_landscape import (
    LandscapeState,
    StateGate,
    legal_actions,
    normalize_angle,
    replay_actions,
    search_landscape,
    search_landscape_horizons,
    state_from_spec,
)


PROTOCOL_ID = "E44_CERTIFIED_LANDSCAPE_ORACLE_V1"
RULE_SCOPE = "e44_core_v1"
HORIZONS = (0, 1, 2, 3, 4)
CASE_COUNTS = {"neutral_exposure": 256, "zero_barrier_escape": 256, "positive_barrier_escape": 256, "no_escape_or_cycle": 256}


def _op(name: str, qubits: tuple[int, ...], angle: float | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {"name": name, "qubits": list(qubits)}
    if angle is not None:
        value["params"] = [angle]
    return value


def generate_panel() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for ordinal in range(256):
        n = 3 + (ordinal % 2)
        extra = 1 + (ordinal % 5)
        operations = [_op("h", (0,)), _op("x", (1,)), _op("h", (0,)), _op("x", (1,))]
        for index in range(extra):
            q = 2 + (index % (n - 2))
            operations.append(_op("rz", (q,), 0.173 + 0.011 * ordinal + 0.007 * index))
        cases.append({"case_id": f"neutral_exposure_{ordinal:03d}", "stratum": "neutral_exposure", "num_qubits": n, "operations": operations})
    for ordinal in range(256):
        n = 3 + (ordinal % 2)
        extra = ordinal % 6
        operations = [_op("h", (0,)), _op("x", (1,)), _op("z", (2,)), _op("h", (0,))]
        for index in range(extra):
            q = 2 + (index % (n - 2))
            operations.append(_op("rz", (q,), 0.231 + 0.013 * ordinal + 0.009 * index))
        cases.append({"case_id": f"zero_barrier_escape_{ordinal:03d}", "stratum": "zero_barrier_escape", "num_qubits": n, "operations": operations})
    for ordinal in range(256):
        operations = [
            _op("cx", (0, 1)), _op("rz", (1,), 1.2 + 0.0017 * ordinal),
            _op("x", (0,)), _op("rz", (0,), -0.4 - 0.0013 * ordinal),
            _op("cx", (0, 1)), _op("h", (0,)), _op("x", (1,)),
        ]
        cases.append({"case_id": f"positive_barrier_escape_{ordinal:03d}", "stratum": "positive_barrier_escape", "num_qubits": 2, "operations": operations})
    for ordinal in range(256):
        operations = [_op("h", (0,)), _op("x", (1,)), _op("rz", (0,), 0.29 + 0.0021 * ordinal), _op("z", (1,))]
        cases.append({"case_id": f"no_escape_or_cycle_{ordinal:03d}", "stratum": "no_escape_or_cycle", "num_qubits": 2, "operations": operations})
    return cases


def _load_rules(path: Path) -> list[dict[str, Any]]:
    library = json.loads(path.read_text(encoding="utf-8"))
    rules = []
    for rule in library["rules"]:
        if rule.get("rule_family") != "quartz_v1":
            continue
        if RULE_SCOPE == "e44_core_v1":
            if int(rule["source"]["num_qubits"]) > 2:
                continue
            if len(rule["source"]["operations"]) > 4 or len(rule["target"]["operations"]) > 6:
                continue
        rules.append(rule)
    return rules


def _ref_replace(state: LandscapeState, location: int, source_len: int, replacement: list[StateGate]) -> LandscapeState:
    return LandscapeState(
        state.num_qubits,
        state.gates[:location] + tuple(replacement) + state.gates[location + source_len:],
    ).normalized()


def _ref_quartz_actions(state: LandscapeState, rules: list[dict[str, Any]]) -> list[tuple[str, int, str, str, LandscapeState]]:
    actions = []
    for location in range(len(state.gates)):
        for rule in rules:
            source = rule["source"]
            source_ops = source["operations"]
            if location + len(source_ops) > len(state.gates) or int(source["num_qubits"]) > state.num_qubits:
                continue
            if tuple(op["name"] for op in source_ops) != tuple(g.name for g in state.gates[location:location + len(source_ops)]):
                continue
            for mapped in itertools.permutations(range(state.num_qubits), int(source["num_qubits"])):
                qmap = dict(enumerate(mapped))
                source_values: dict[str, float] = {}
                valid = True
                for template, actual in zip(source_ops, state.gates[location:location + len(source_ops)]):
                    if actual.qubits != tuple(qmap[int(q)] for q in template["qubits"]):
                        valid = False
                        break
                    for label in template.get("params", []):
                        if actual.angle is None:
                            valid = False
                            break
                        angle = normalize_angle(actual.angle)
                        if label in source_values and abs(normalize_angle(source_values[label] - angle)) > 1e-10:
                            valid = False
                            break
                        source_values[label] = angle
                    if not valid:
                        break
                if not valid:
                    continue
                target_values = {
                    label: normalize_angle(sum(int(coefficient) * source_values[source_label] for source_label, coefficient in expression.items()))
                    for label, expression in rule.get("parameter_binding", {}).items()
                }
                replacement = [
                    StateGate(
                        op["name"],
                        tuple(qmap[int(q)] for q in op["qubits"]),
                        None if not op.get("params") else target_values[op["params"][0]],
                    )
                    for op in rule["target"]["operations"]
                ]
                post = _ref_replace(state, location, len(source_ops), replacement)
                if post.state_hash == state.state_hash:
                    continue
                binding = json.dumps(
                    {"qubits": [[f"Q{q}", qmap[q]] for q in sorted(qmap)],
                     "parameters": [[label, format(value, ".17g")] for label, value in sorted(target_values.items())],
                     "source_parameters": [[label, format(value, ".17g")] for label, value in sorted(source_values.items())]},
                    sort_keys=True, separators=(",", ":"),
                )
                actions.append((rule["rule_id"], location, binding, post.state_hash, post))
    return actions


def _ref_pair_actions(state: LandscapeState) -> list[tuple[str, int, str, str, LandscapeState]]:
    inverse = {"h", "x", "y", "z", "cx", "cz", "swap"}
    actions = []
    for location, (left, right) in enumerate(zip(state.gates, state.gates[1:])):
        replacement: list[StateGate] | None = None
        rule = ""
        if left.qubits == right.qubits and left.name == right.name and left.name in inverse:
            rule, replacement = "pair_v1.self_inverse", []
        elif left.qubits == right.qubits and {left.name, right.name} == {"t", "tdg"}:
            rule, replacement = "pair_v1.t_tdg", []
        elif left.qubits == right.qubits and {left.name, right.name} == {"s", "sdg"}:
            rule, replacement = "pair_v1.s_sdg", []
        elif left.qubits == right.qubits and left.name == right.name and left.name in {"rx", "ry", "rz"}:
            angle = normalize_angle((left.angle or 0.0) + (right.angle or 0.0))
            rule, replacement = ("pair_v1.rotation_zero", []) if abs(angle) <= 1e-10 else ("pair_v1.rotation_merge", [StateGate(left.name, left.qubits, angle)])
        if replacement is not None:
            post = _ref_replace(state, location, 2, replacement)
            actions.append((rule, location, "{}", post.state_hash, post))
    return actions


def _ref_exchange_actions(state: LandscapeState) -> list[tuple[str, int, str, str, LandscapeState]]:
    z_family = {"z", "rz", "s", "sdg", "t", "tdg"}
    x_family = {"x", "rx"}
    actions = []
    for location, (left, right) in enumerate(zip(state.gates, state.gates[1:])):
        left_set, right_set = set(left.qubits), set(right.qubits)
        rule = None
        if left_set.isdisjoint(right_set): rule = "exchange.disjoint"
        elif left.name == right.name and left.qubits == right.qubits and len(left.qubits) == 1: rule = "exchange.same_single"
        elif left.name == right.name and left.qubits == right.qubits and left.name in {"rx", "ry", "rz"}: rule = "exchange.same_axis_rotation"
        elif left.name in z_family and right.name in z_family and left.qubits == right.qubits: rule = "exchange.z_family"
        elif left.name == "cx" and right.name in z_family and len(right.qubits) == 1 and right.qubits[0] == left.qubits[0]: rule = "exchange.cx_control_z"
        elif right.name == "cx" and left.name in z_family and len(left.qubits) == 1 and left.qubits[0] == right.qubits[0]: rule = "exchange.cx_control_z"
        elif left.name == "cx" and right.name in x_family and len(right.qubits) == 1 and right.qubits[0] == left.qubits[1]: rule = "exchange.cx_target_x"
        elif right.name == "cx" and left.name in x_family and len(left.qubits) == 1 and left.qubits[0] == right.qubits[1]: rule = "exchange.cx_target_x"
        elif left.name == "cz" and right.name in z_family and len(right.qubits) == 1 and right.qubits[0] in left_set: rule = "exchange.cz_z"
        elif right.name == "cz" and left.name in z_family and len(left.qubits) == 1 and left.qubits[0] in right_set: rule = "exchange.cz_z"
        elif left.name == right.name == "swap" and left_set == right_set: rule = "exchange.same_swap"
        elif left.name == right.name == "cz" and left_set == right_set: rule = "exchange.same_cz"
        if rule is None:
            continue
        post = LandscapeState(state.num_qubits, state.gates[:location] + (right, left) + state.gates[location + 2:]).normalized()
        if post.state_hash != state.state_hash:
            actions.append((rule, location, "{}", post.state_hash, post))
    return actions


def _ref_actions(state: LandscapeState, rules: list[dict[str, Any]]) -> list[tuple[str, int, str, str, LandscapeState]]:
    actions = _ref_quartz_actions(state, rules) + _ref_pair_actions(state) + _ref_exchange_actions(state)
    return sorted({(a[0], a[1], a[2], a[3]): a for a in actions}.values(), key=lambda item: (item[0], item[1], item[2], item[3]))


def _ref_path(state_hash: str, parents: Mapping[str, tuple[str, tuple[str, int, str, str, LandscapeState]]]) -> list[tuple[str, int, str, str, LandscapeState]]:
    path = []
    current = state_hash
    while current in parents:
        previous, action = parents[current]
        path.append(action)
        current = previous
    return list(reversed(path))


def _ref_peak(initial: LandscapeState, path: list[tuple[str, int, str, str, LandscapeState]]) -> int:
    return max([initial.cost] + [action[4].cost for action in path])


def _ref_threshold(initial: LandscapeState, states: Mapping[str, LandscapeState], adjacency: Mapping[str, list[tuple[str, int, str, str, LandscapeState]]], horizon: int, threshold: int):
    queue = deque([(initial.state_hash, 0)])
    parents = {}
    seen = {(initial.state_hash, 0)}
    while queue:
        current, depth = queue.popleft()
        if depth > 0 and states[current].cost < initial.cost:
            return current, _ref_path_key((current, depth), parents)
        if depth >= horizon: continue
        for action in adjacency.get(current, []):
            if action[4].cost > initial.cost + threshold: continue
            child = (action[3], depth + 1)
            if child in seen: continue
            seen.add(child); parents[child] = ((current, depth), action); queue.append(child)
    return None


def _ref_path_key(key, parents):
    path=[]
    while key in parents:
        previous, action = parents[key]
        path.append(action)
        key=previous
    return list(reversed(path))


def reference_search_horizons(initial: LandscapeState, rules: list[dict[str, Any]], horizons=HORIZONS) -> dict[str, dict[str, Any]]:
    requested=tuple(sorted(set(int(horizon) for horizon in horizons))); max_horizon=max(requested)
    states={initial.state_hash:initial}; distances={initial.state_hash:0}; parents={}; adjacency={}; queue=deque([initial.state_hash])
    while queue:
        current=queue.popleft(); depth=distances[current]
        if depth>=max_horizon: continue
        actions=_ref_actions(states[current],rules); adjacency[current]=actions
        for action in actions:
            if action[3] not in states:
                states[action[3]]=action[4]; distances[action[3]]=depth+1; parents[action[3]]=(current,action); queue.append(action[3])
    result={}
    for horizon in requested:
        visible={state_hash:state for state_hash,state in states.items() if distances[state_hash]<=horizon}
        improving=[s for s in visible.values() if distances[s.state_hash]>0 and s.cost<initial.cost]
        escape=min(improving,key=lambda s:(distances[s.state_hash],_ref_peak(initial,_ref_path(s.state_hash,parents)),s.state_hash),default=None)
        best=min(visible.values(),key=lambda s:(s.cost,distances[s.state_hash],s.state_hash))
        barrier=None; barrier_path=[]
        visible_adjacency={state_hash:actions for state_hash,actions in adjacency.items() if distances[state_hash]<horizon}
        for threshold in range(max([0]+[s.cost-initial.cost for s in visible.values()])+1):
            threshold_result=_ref_threshold(initial,visible,visible_adjacency,horizon,threshold)
            if threshold_result is not None: barrier_path=threshold_result[1]; barrier=max(0,_ref_peak(initial,barrier_path)-initial.cost); break
        status="EXACT_ESCAPE" if escape else "EXACT_H_LOCAL_OPTIMUM"
        escape_path=_ref_path(escape.state_hash,parents) if escape else []
        serialize=lambda path:[{"rule_id":a[0],"location":a[1],"post_state_sha256":a[3]} for a in path]
        result[str(horizon)]={"status":status,"best_cost":best.cost,"escape_depth":distances[escape.state_hash] if escape else None,"barrier_height":barrier,"states_seen":len(visible),"state_set_sha256":hashlib.sha256("\n".join(sorted(visible)).encode()).hexdigest(),"state_hashes":sorted(visible),"escape":serialize(escape_path),"barrier":serialize(barrier_path)}
    return result


def reference_search(initial: LandscapeState, rules: list[dict[str, Any]], horizon: int) -> dict[str, Any]:
    return reference_search_horizons(initial, rules, (horizon,))[str(horizon)]


def _formal_for_horizons(spec: dict[str, Any], rule_library: Path) -> dict[str, dict[str, Any]]:
    state=state_from_spec(spec)
    return search_landscape_horizons(state,rule_library,HORIZONS,rule_scope=RULE_SCOPE)


def run(output_root: Path, rule_library: Path) -> dict[str, Any]:
    cases=generate_panel(); rules=_load_rules(rule_library)
    output_root.mkdir(parents=True,exist_ok=True)
    protocol={"protocol_id":PROTOCOL_ID,"rule_scope":RULE_SCOPE,"horizons":list(HORIZONS),"case_counts":CASE_COUNTS,"total_cases":len(cases),"gate_count_range":[4,9],"qubit_range":[2,4],"rule_library_sha256":hashlib.sha256(rule_library.read_bytes()).hexdigest(),"independent_oracle":"experiments/e44_landscape_oracle.py::reference_search_horizons"}
    (output_root/"protocol.json").write_text(json.dumps(protocol,indent=2,sort_keys=True)+"\n",encoding="utf8")
    (output_root/"inputs.jsonl").write_text("".join(json.dumps(c,sort_keys=True)+"\n" for c in cases),encoding="utf8")
    rows=[]; certificates=[]; mismatch_fields=Counter(); replay_failures=0; deterministic_failures=0
    for index,spec in enumerate(cases,1):
        formal=_formal_for_horizons(spec,rule_library); state=state_from_spec(spec)
        reference=reference_search_horizons(state,rules,HORIZONS)
        deterministic_formal = _formal_for_horizons(spec,rule_library) if index in {1, 257, 513, 769} else None
        for horizon in HORIZONS:
            f=formal[str(horizon)]; ref=reference[str(horizon)]
            fields=("status","best_cost","escape_depth","barrier_height","states_seen","state_set_sha256","state_hashes")
            mismatches=[field for field in fields if f.get(field)!=ref.get(field)]
            f_escape=[{"rule_id":a["rule_id"],"location":a["location"],"post_state_sha256":a["post_state_sha256"]} for a in f["witnesses"]["escape"]]
            f_barrier=[{"rule_id":a["rule_id"],"location":a["location"],"post_state_sha256":a["post_state_sha256"]} for a in f["witnesses"]["barrier"]]
            if f_escape!=ref["escape"]: mismatches.append("escape_witness")
            if f_barrier!=ref["barrier"]: mismatches.append("barrier_witness")
            replay = replay_actions(state, f["witnesses"]["escape"], rule_library, RULE_SCOPE)
            if not replay["accepted"]: replay_failures+=1
            if deterministic_formal is not None and deterministic_formal[str(horizon)]["certificate_sha256"]!=f["certificate_sha256"]: deterministic_failures+=1
            for field in mismatches: mismatch_fields[field]+=1
            certificates.append({"case_id":spec["case_id"],"stratum":spec["stratum"],"horizon":horizon,"formal_certificate":f,"oracle_state_set_sha256":ref["state_set_sha256"]})
            rows.append({"case_id":spec["case_id"],"stratum":spec["stratum"],"horizon":horizon,"formal_status":f["status"],"oracle_status":ref["status"],"formal_best_cost":f["best_cost"],"oracle_best_cost":ref["best_cost"],"formal_escape_depth":f["escape_depth"],"oracle_escape_depth":ref["escape_depth"],"formal_barrier_height":f["barrier_height"],"oracle_barrier_height":ref["barrier_height"],"formal_states_seen":f["states_seen"],"oracle_states_seen":ref["states_seen"],"mismatch_fields":mismatches,"formal_certificate_sha256":f["certificate_sha256"],"oracle_state_set_sha256":ref["state_set_sha256"]})
        if index%32==0: print(f"E44 {index}/{len(cases)}",flush=True)
    rows_text="".join(json.dumps(row,sort_keys=True)+"\n" for row in rows)
    (output_root/"rows.jsonl").write_text(rows_text,encoding="utf8")
    certificates_text="".join(json.dumps(row,sort_keys=True)+"\n" for row in certificates)
    (output_root/"certificates.jsonl").write_text(certificates_text,encoding="utf8")
    summary={"protocol_id":PROTOCOL_ID,"rows":len(rows),"case_count":len(cases),"horizon_count":len(HORIZONS),"mismatch_count":sum(mismatch_fields.values()),"mismatch_fields":dict(mismatch_fields),"replay_failures":replay_failures,"determinism_failures":deterministic_failures,"stratum_counts":CASE_COUNTS,"stratum_results":{}}
    for stratum in CASE_COUNTS:
        subset=[row for row in rows if row["stratum"]==stratum]
        summary["stratum_results"][stratum]={"rows":len(subset),"mismatch_count":sum(bool(row["mismatch_fields"]) for row in subset),"formal_status_counts":dict(Counter(row["formal_status"] for row in subset))}
    receipt={"status":"PASS_STAGE_S4_E44" if summary["mismatch_count"]==0 and replay_failures==0 and deterministic_failures==0 else "FAIL_E44","protocol_sha256":hashlib.sha256((output_root/"protocol.json").read_bytes()).hexdigest(),"inputs_sha256":hashlib.sha256((output_root/"inputs.jsonl").read_bytes()).hexdigest(),"rows_sha256":hashlib.sha256((output_root/"rows.jsonl").read_bytes()).hexdigest(),"certificates_sha256":hashlib.sha256((output_root/"certificates.jsonl").read_bytes()).hexdigest(),"summary":summary,"zero_tolerance":summary["mismatch_count"]==0 and replay_failures==0 and deterministic_failures==0}
    (output_root/"summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf8")
    (output_root/"receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf8")
    return receipt


def main() -> int:
    parser=argparse.ArgumentParser(); parser.add_argument("--output-root",type=Path,required=True); parser.add_argument("--rule-library",type=Path,required=True); args=parser.parse_args()
    receipt=run(args.output_root,args.rule_library); print(json.dumps(receipt,sort_keys=True)); return 0 if receipt["zero_tolerance"] else 2


if __name__=="__main__": raise SystemExit(main())
