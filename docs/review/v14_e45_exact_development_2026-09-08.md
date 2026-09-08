# v14 E45 exact development (2026-09-08)

The selected screening configuration `h3_b64_s200k` now has a separate exact
finite-horizon entrypoint.  It uses the complete ordered normalized listing as
the state key, matches rules through a first-operation index, generates child
state hashes by canonical-byte splice, retains one parent action per
discovered state, computes the minimum peak-cost barrier with a layered
minimax traversal and a safe peak-dominance prune, and marks state or time
truncation as incomplete.  It does not add reverse Quartz edges and does not
change the v13 contract.

The same regression file runs the compact search twice on the same neutral
input and compares the canonical serialized certificate bytes.  This is the
executable byte-stability check required by the v13 method contract; the
targeted exact-development regression completed with all 17 tests passing.

The selected configuration was then run over the complete fixed panel in
`data/v14/e45_full_development/`: 128 sources × 6 arms = 768 rows.  The
independent verifier returned `PASS`.  The guided exact arm produced 93
`EXACT_FINITE_HORIZON` certificates and 35 `TRUNCATED/INCOMPLETE` certificates
(27.34375% resource boundary), with zero semantic failures.  The package
receipt records status `DEVELOPMENT_COMPLETE_WITH_RESOURCE_BOUNDARY` and these
artifact hashes:

- `protocol.json`: `0d0e86c69d15b5577930d8399c6e5963ab8bc5e356c6f8e80afd44b729afc05c`
- `normalization_manifest.csv`: `0de35d33ad281b0b43dc8f5e38e76567d8c4afc14747a9eff0e7756196b1ba84`
- `grid_results.csv`: `0c1bada82fccba0f9203c7e414b19c3e6a5372f8488f56a300d61a733b97aac8`
- `config_summaries.json`: `43137b483b9bf1daca1f161a2925e80c2dffe51e478231b637e38c0fa7e6ff7b`
- `certificates.jsonl`: `8a6ae277772533270a69795b20a680b6c660ca78e5eb2a2cc91357ade4c8e48b`
- `selection.json`: `8838a3e1bcd527add76dfe1054af9f1ce4a013afe27e5d16ef8e1620464ea666`
- `receipt.json`: `4df5a050e3acd048571c7b3516bb8bb32433b091010d47183f54129f17f6a0ae`

The search implementation also exposes `search_escape_idastar`, which proves
the minimum escape depth by iterative depth bounds and a safe single-step
gate-count lower bound. Its E44-core regression matches the exact BFS escape
depth and replays the emitted witness; a zero-second budget returns the
declared `RESOURCE_BOUNDED_NO_WITNESS` / `TRUNCATED` boundary. The deadline is
also checked inside indexed candidate generation, so high-branching cells can
terminate during action construction and retain the same fail-closed status.
The IDA* search memoizes fully explored failures by
`(state_hash, remaining_depth)`; finite-depth repetitions remain allowed, so
the memoization is exact rather than a heuristic path omission. Witness
replay matches the recorded rule and location directly and checks semantic
equivalence only on the rewritten window, avoiding a full-listing unitary
multiplication for large circuits while retaining the pre/post hashes.

One `RESOURCE_BOUNDED_NO_WITNESS` cell is `qft_8`; the remaining 34 bounded cells
retain an improving witness but cannot be called exact.
The full development therefore records an exact-engine resource boundary; it
does not establish a complete exact landscape over all 128 sources or a
paper-ready certified-landscape claim.

The full package verifier is:

```text
python scripts/verify_e45_exact_development.py --output-root data/v14/e45_full_development
```

The complementary IDA* escape-depth panel is at
`data/v14/e45_idastar_escape/`. It uses the same 128-source fixed panel and
selected `h3_b64_s200k` configuration, with a declared 30-second per-cell
development budget. Its independent verifier returned `PASS` for all 128
rows: 63 `EXACT_ESCAPE` and 65 `EXACT_H_LOCAL_OPTIMUM`, with zero
resource-bounded rows. All improving witnesses replayed successfully, with
zero replay failures; the resource boundary rate is 0% under the declared
30-second per-cell budget. The package remains complementary
escape-depth evidence and does not convert the compact 35/128 boundary into a
complete exact-landscape claim.

The IDA* verifier is:

```text
python scripts/verify_v14_idastar_escape.py --output-root data/v14/e45_idastar_escape
```

Its receipt-bound artifact hashes are:

- `protocol.json`: `0765c305bbfce1cd6be74ffc235a5e8d94c8e9876c073a5bb183b8c662392bc8`
- `normalization_manifest.csv`: `7e8fe01528f9a2fb011458e31a907a6318b086017350fb1ff52f735949028524`
- `grid_results.csv`: `f47b1e0f4ea504cead6d9b5af747f3372b888dd723b9ec7b07298fa87642b471`
- `config_summaries.json`: `0a63cfcb62260192ef7dfaca3fe4fecff41f2a73bf3719cb255fa36c2b13a5ee`
- `certificates.jsonl`: `de8a829d6d52c011945408484c57abf65b66bc22bba9be3cfa4e6d80345d0516`
- `selection.json`: `b24a6dd53ea374cb6c1fc0f08b42942fda6beb1188ad4c7ef8a0f5d5c0996622`
