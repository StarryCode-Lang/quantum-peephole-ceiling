"""
Wire-Consecutive Listing (WCL) Preprocessor
============================================
Reorders circuit gates into Wire-Consecutive Listing order for improved
Phase 1 optimizer performance.

Theorem 1(b) shows that under Layer-by-Layer (LBL) listing, the Phase 1
action space S1(C) can be structurally empty for n>=2. WCL reorders gates
so that all gates on qubit 0 appear first (in circuit order), then qubit 1,
etc. This is NOT a circuit transformation -- it is a listing reorder that
preserves unitary equivalence by maintaining the relative order of any two
gates that share a qubit.

Two-qubit gates are assigned to the wire of their lowest-index qubit
("primary wire") while dependency constraints from their other qubit(s)
are still respected via topological sorting.

Version: 1.0.0
"""

from __future__ import annotations

import copy
import heapq
from collections import defaultdict
from typing import List, Set, Tuple

from qiskit import QuantumCircuit


class WireTraversalPreprocessor:
    """Reorder circuit gates into Wire-Consecutive Listing (WCL).

    WCL groups gates by their *primary wire* (lowest qubit index each gate
    acts on), producing a listing where all gates on qubit 0 appear first
    (preserving their original relative order), then all gates on qubit 1,
    and so on.  Two-qubit (or multi-qubit) gates are placed at the position
    of their primary wire.

    Correctness
    -----------
    The relative ordering of any two gates that share at least one qubit is
    preserved via a dependency DAG and topological sort.  Because gates on
    disjoint qubits commute, reordering them does not change the circuit
    unitary.  The resulting circuit is therefore unitarily equivalent to the
    input.

    Algorithm
    ---------
    1. For each gate, record the set of qubits it acts on.
    2. Build a dependency DAG: for every qubit q, add directed edges between
       consecutive gates on q (in original listing order).  Edges are
       deduplicated so that gates sharing multiple qubits produce only one
       edge.
    3. Assign each gate a *primary wire* = min(qubits it acts on).
    4. Topological sort via Kahn's algorithm with a min-heap keyed on
       ``(primary_wire, original_index)``.  This ensures gates are emitted
       in wire-consecutive order while respecting all dependency constraints.
    5. Build a new circuit with the reordered gate list.

    Usage
    -----
    >>> preprocessor = WireTraversalPreprocessor()
    >>> wcl_circuit = preprocessor.preprocess(circuit)
    """

    def preprocess(self, circuit: QuantumCircuit) -> QuantumCircuit:
        """Return a new circuit with gates reordered into WCL.

        Parameters
        ----------
        circuit : QuantumCircuit
            The input circuit.  Not modified.

        Returns
        -------
        QuantumCircuit
            A deep copy of *circuit* with ``.data`` reordered into
            wire-consecutive listing.  Unitarily equivalent to the input.
        """
        n_gates = len(circuit.data)
        if n_gates <= 1:
            return copy.deepcopy(circuit)

        # ------------------------------------------------------------------
        # Step 1: Per-gate qubit sets and per-qubit gate lists
        # ------------------------------------------------------------------
        gate_qubits: List[Set[int]] = []
        qubit_to_gates: dict[int, List[int]] = defaultdict(list)

        for idx, inst in enumerate(circuit.data):
            qubits = {circuit.find_bit(q).index for q in inst.qubits}
            gate_qubits.append(qubits)
            for q in qubits:
                qubit_to_gates[q].append(idx)

        # ------------------------------------------------------------------
        # Step 2: Build dependency DAG (deduplicated edges)
        #
        # For each qubit, consecutive gates on that qubit must preserve
        # their relative listing order.  We add edges only between
        # *consecutive* gates on the same qubit; transitivity handles the
        # rest.  A set deduplicates edges that arise when two gates share
        # multiple qubits (e.g., back-to-back CNOTs on the same pair).
        # ------------------------------------------------------------------
        edges: Set[Tuple[int, int]] = set()
        for _q, gates_on_q in qubit_to_gates.items():
            for k in range(len(gates_on_q) - 1):
                edges.add((gates_on_q[k], gates_on_q[k + 1]))

        in_degree = [0] * n_gates
        adj: dict[int, List[int]] = defaultdict(list)
        for i, j in edges:
            adj[i].append(j)
            in_degree[j] += 1

        # ------------------------------------------------------------------
        # Step 3: Primary wire assignment
        # ------------------------------------------------------------------
        primary_wire = [min(qs) for qs in gate_qubits]

        # ------------------------------------------------------------------
        # Step 4: Heap-based Kahn's topological sort
        #
        # Priority key: (primary_wire, original_index).
        # This greedily emits gates for the lowest-numbered wire first,
        # breaking ties by original listing order.
        # ------------------------------------------------------------------
        heap: List[Tuple[int, int]] = []
        for idx in range(n_gates):
            if in_degree[idx] == 0:
                heapq.heappush(heap, (primary_wire[idx], idx))

        order: List[int] = []
        while heap:
            _pw, idx = heapq.heappop(heap)
            order.append(idx)
            for j in adj[idx]:
                in_degree[j] -= 1
                if in_degree[j] == 0:
                    heapq.heappush(heap, (primary_wire[j], j))

        # Safety check: if the DAG had a cycle (should not happen for a
        # valid circuit listing), fall back to original order.
        if len(order) != n_gates:
            return copy.deepcopy(circuit)

        # ------------------------------------------------------------------
        # Step 5: Build output circuit with reordered gate list
        # ------------------------------------------------------------------
        result = copy.deepcopy(circuit)
        result.data = [circuit.data[i] for i in order]

        return result
