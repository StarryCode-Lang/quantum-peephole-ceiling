# E31 post-hoc deterministic semantic replay protocol

**Date:** 2026-08-26  
**Role:** independent post-hoc verification; it is not a pre-registered treatment,
does not replace the frozen E31 execution, and cannot upgrade the existing
transitive-source provenance rating from `PARTIAL`.

## Question addressed

The formal worker checkpoint records an output circuit hash, a same-library
fidelity summary, and common-basis counts, but it does not retain a loadable
optimized circuit.  Those summaries alone are insufficient to independently
recompute semantic equivalence or the response variable.  The replay gate fills
that evidence gap without altering any frozen execution source or excluding any
formal row.

## Mandatory gate sequence

1. Refuse execution while `formal.lock` exists or before all 28,152 scheduled
   rows are committed to the authoritative SQLite checkpoint.
2. Verify all seven directly frozen source hashes and all sixteen sources in the
   disclosed post-hoc first-party import closure.  Preserve the disclosure that
   this was not a complete cryptographic pre-run closure.
3. Run one successful cell from every listing-model by rule-set branch in two
   cold processes, using `PYTHONHASHSEED=0` and `PYTHONHASHSEED=8675309`.
   Logical input/listed/output hashes, counts, reduction, exact operator metrics,
   and QPY bytes must be identical.
4. Partition successful formal rows by
   `(input_circuit_sha256, listing_model, rule_set, window_gates)`.  Budget is
   the only collapsed dimension: it is enforced by the parent process and is
   not an optimizer input after a row completes.  Before sharing a replay, the
   audit must prove exact cross-budget identity of output hash, original and
   optimized common-basis counts, reduction, exact fidelity, template flag, and
   normalized trace.  Any disagreement fails closed.
5. In a fresh process for every unique semantic cell, reconstruct the input,
   listing and optimizer result.  Verify the parsed input hash and replayed
   output hash, independently normalize both listed input and optimized output
   to `{rz, sx, x, cx}`, and recompute
   `100 * (1 - optimized_count / original_count)`.
6. Construct dense exact operators with `Operator.from_circuit`.  Independently
   compute `Tr(Uout^dagger Uin)`, average gate fidelity
   `(|Tr|^2 + d) / (d(d+1))`, and the phase-aligned identity Frobenius norm.
   The latter uses the exact Hilbert--Schmidt equality
   `||Uout^dagger Uin - phase I||_F^2 = 2d - 2|Tr|`, avoiding an unnecessary
   cubic matrix product while evaluating the requested norm exactly.
7. Save and immediately reload one QPY output per unique semantic cell.  Pin its
   byte hash and logical circuit hash.  Emit a hash-pinned cell certificate plus
   a distinct binding certificate for every successful formal row.
8. Commit cell and row bindings atomically to a resumable SQLite checkpoint.
   A prior failure requires explicit retry; missing, foreign, partial, mutated,
   or unloadable artifacts fail closed.  Emit a PASS gate only after every
   formal success row is covered exactly once.

## Output contract

`semantic_replay/canary_gate.json` is a prerequisite, not final evidence.
The final `semantic_replay_gate.json` binds
`semantic_replay_manifest.json`, which in turn contains:

- the immutable protocol/design and formal-checkpoint boundary;
- the direct plus disclosed-transitive source hashes;
- one entry for every unique semantic replay cell;
- one row-to-cell certificate entry for every formal `status=success` row;
- a loadable QPY path and SHA-256 for every unique output;
- counts of non-success rows, which remain in the ITT analysis but have no
  successful output circuit to replay.

The gate must never be described as independent software diversity: replay uses
the frozen optimizer implementation to reconstruct the result, while semantic
metrics, response calculation, serialization checks, and checkpoint comparison
are independently implemented.  It proves deterministic reconstruction and
exact within-Qiskit operator equivalence under the frozen representation; it
does not prove equivalence under a second quantum SDK or a hardware noise model.
