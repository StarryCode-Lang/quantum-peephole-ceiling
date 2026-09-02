# v13 Certified Rewrite Landscape: method contract draft

Status: `DRAFT_UNTIL_E44`. This is an executable-method contract and proof
outline, not manuscript prose and not a theorem claim.

## 1. Objects and normalization

A state is an ordered finite listing

\[
s=(g_0,\ldots,g_{m-1}),
\]

where every gate keeps its original integer qubit indices. A gate is normalized
as `(name, ordered_qubits, normalized_angles)`; each angle is reduced modulo
`2*pi` to the half-open interval `[-pi, pi)`. The order is part of the key,
so two listings with the same gate multiset are different states when their
orders, operands, or angles differ. Measurements, reset, dynamic control,
classical operands, and free parameters are outside the unitary state space.

The state key is the canonical JSON encoding of the ordered normalized
listing. `state_sha256` is the SHA-256 of that encoding. A state cost is the
declared primary gate cost; secondary cost fields are retained but cannot
change the primary optimum.

## 2. Legal edges

The frozen rule library is the union of:

1. the pinned Quartz v1 directions, with their explicit parameter binding and
   symbolic proof hash;
2. the existing `pair_v1` rules; and
3. the conservative structural exchange rules.

An action matches a contiguous source template in a state, binds its qubit
and parameter variables, and replaces that substring with the target template.
Actions are sorted by `(rule_id, location, binding, post_hash)`. A rule may be
used only when its source and target are valid normalized templates and its
parameter-rank condition is satisfied. The rank-increasing reverse of a
Quartz parameter-splitting rule is not legal.

Every accepted edge stores:

```text
rule_id, direction, location, binding,
pre_state_sha256, post_state_sha256, local_proof_hash
```

The transition function is pure: it returns a new state and does not mutate
the input state or the rule library.

## 3. Semantic claims kept as proof obligations

The following obligations are deliberately labelled `draft_until_E44`.

**P1 — edge soundness.** For every accepted action, the source substring and
the bound target substring have equal unitary action up to the declared global
phase. Quartz directions use the imported symbolic proof plus numeric checks;
pair and exchange rules use their fixed predicate contracts.

**P2 — contextual closure.** If two contiguous substrings have equal unitary
action on their common ordered support, replacing one by the other inside any
prefix/suffix context preserves the complete circuit unitary. This follows by
associativity of composition and tensoring with untouched wires; the replay
checker must still verify the concrete bound action.

**P3 — replay implication.** A certificate is accepted only if every action's
pre-state hash equals the prior post-state hash, every local proof hash is
valid for the rule-library hash, and the final state hash matches the claimed
output. Inductively applying P1 and P2 then implies input/output equivalence
up to global phase.

## 4. Exact landscape quantities

For input state `s0`, let `R_H(s0)` be the set of states reached by all legal
action paths of length at most `H`, including `s0`. Exact BFS uses a visited
set keyed by the complete state key and expands actions in the fixed order.

```text
best_cost_H       = min(cost(s) for s in R_H(s0))
escape_depth_H    = min { d : there is a d-edge path to cost < cost(s0) }
                    or +infinity when the exact finite search proves none
barrier_height_H  = min over improving paths of
                    (max intermediate cost - cost(s0))
                    or +infinity when no improving path is in R_H(s0)
```

The barrier is enumerated by increasing integer threshold `b`: first test the
subgraph containing states of cost at most `cost(s0)+b`, then retain the first
threshold that reaches a lower-cost state. The path length remains bounded by
`H`. Witnesses are selected deterministically by action order and state hash.

**P4 — BFS quantities.** Complete BFS visits every state in `R_H(s0)` exactly
once and therefore returns the definitions above. Threshold enumeration is
equivalent to BFS on the induced cost subgraphs, so its first successful
threshold is the minimum barrier.

**P5 — horizon monotonicity.** `R_H(s0)` is nested in `R_(H+1)(s0)`, hence
`best_cost_(H+1) <= best_cost_H`. The implementation must check and record this
property rather than assume it after truncation.

## 5. Incomplete-search contract

The exact statuses are:

```text
EXACT_ESCAPE
EXACT_H_LOCAL_OPTIMUM
WITNESS_CERTIFIED_SEARCH_INCOMPLETE
RESOURCE_BOUNDED_NO_WITNESS
UNSUPPORTED_INPUT
INVALID_RULE_LIBRARY
SEMANTIC_FAILURE
```

Only `EXACT_ESCAPE` and `EXACT_H_LOCAL_OPTIMUM` can prove an optimum or the
absence of an escape within the declared exact state space. A truncated search
may report a legal improving witness and conservative lower/upper bounds, but
may not report a local optimum. Beam search is always incomplete unless an
independent exact certificate covers the same state set.

The following explanations are separate and machine-readable:

```text
RULE_LIBRARY_GAP       no supported rule matches; omitted rules are unknown
H_INSUFFICIENT         exact search ended at H; larger horizons are unknown
RESOURCE_TRUNCATED     state/time/memory budget stopped expansion
HEURISTIC_OMISSION     beam ranking did not retain a reachable branch
GREEDY_FAILURE         terminal greedy pass did not find a valid improvement
```

“No improvement” is not a single scientific conclusion. The certificate must
carry all applicable explanations and must never convert one into another.

## 6. Certificate determinism and validation

The serialized certificate contains the normalized input, rule-library hash,
configuration, baseline/best costs and bounds, escape/barrier bounds,
`states_seen`, `expanded`, `pruned`, all action records, three witness paths,
the terminal Greedy trace, semantic/resource/exactness states, and the final
certificate hash. Re-running with the same inputs, library, configuration and
runtime protocol must produce byte-identical JSON.

E44 is the gate for upgrading these obligations from draft status. Until its
zero-tolerance oracle comparison passes, this file must continue to use
`draft_until_E44` and no downstream document may call P1–P5 theorems.
