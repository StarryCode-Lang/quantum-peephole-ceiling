# ⊥ exchange-reliability: axioms and per-rule matrix proof (2026-10-25)

**Status**: theory document, review grade. Companion verifier:
`scripts/verify_perp_reliability.py` (exact sympy, status in the report JSON).

## 1. The relation and the axiom

The closure engine (`src/optimisation/certified_landscape.py::_commutes`)
exposes a binary relation `⊥` on adjacent gate instances: `g ⊥ g'` licenses
exchanging the two adjacent gates in a listing. The **physical axiom** the
certificates need is

> (A)  `g ⊥ g'`  ⟹  $G\,G' = G'\,G$ as unitaries on the full register
>      (exact equality, no global-phase slack).

Under (A), every ⊥-exchange is semantics-preserving, so the fixed-point
certificate (Theorem 4 of `closure_termination_and_optimality_2026-10-24.md`)
is sound: a closed listing admits no ⊥-exchange-plus-rewrite sequence that
recreates a reducible pair, and every such sequence is physically equivalent
to the original.

Soundness of (A) is a property of the nine rules the engine implements; the
relativity note at the end records what (A) deliberately does *not* say.

## 2. The nine rules, each proven by matrix computation

The verifier constructs, for each rule, the exact $2^{w}$-dimensional
matrices ($w$ = qubit width of the case, 1–2) with angles kept symbolic where
the rule is angle-generic, and checks $GG' - G'G = 0$:

| engine rule | case | why it commutes |
|---|---|---|
| `exchange.disjoint` | $A \otimes I$, $I \otimes B$ | tensor factors commute |
| `exchange.same_single` | $G^2$, $G$ any 1q gate | $G\,G = G\,G$ |
| `exchange.same_axis_rotation` | $R_\alpha(\theta)\,R_\alpha(\theta')$ | both are $\exp(-i\theta\,\alpha/2)$ on the same axis, functions of one generator |
| `exchange.z_family` | two diagonal gates on the same wires | diagonal ⊗ diagonal is diagonal; diagonals commute |
| `exchange.cx_control_z` | $cx(c,t)\,Z_c$ | $cx$ acts as $I$ on the $Z_c$ eigenspaces |
| `exchange.cx_target_x` | $cx(c,t)\,X_t$ | $cx$ acts as $I$ on the $X_t$ eigenspaces |
| `exchange.cz_z` | $cz(q,w)\,Z_q$ | both diagonal on the same two wires |
| `exchange.same_swap` | $\mathrm{swap}^2$ | $\mathrm{swap}^2 = I$ |
| `exchange.same_cz` | $cz^2$ | $cz^2 = I$ |

`_Z_FAMILY` = {`z`, `rz`, `s`, `sdg`, `t`, `tdg`} (all diagonal 1q gates),
`_X_FAMILY` = {`x`, `rx`} (X-type 1q gates); both are
read from the engine module at verification time so the proof cannot drift
from the implementation.

**Negative controls** (the table must not be over-permissive): $X\,Z = -Z\,X
\ne Z\,X$ (the engine returns `None` for the (x, z) pair — correct, they
anticommute); $cx(c,t)\,Z_t \ne Z_t\,cx(c,t)$ (Z on the *target* does not
pass — the engine restricts `cx_control_z` to the control wire, verified);
$cx(c,t)\,X_c \ne X_c\,cx(c,t)$ (X on the *control* does not pass — the
engine restricts `cx_target_x` to the target wire, verified). Each negative
case is proven by exhibiting the differing matrix entries exactly.

## 3. What this does and does not claim (the four-layer relativity, restated)

1. *engine ⊥ vs this document's nine rules*: the rules are read from the
   engine source at run time (import, not copy), and the producing engine
   source hash is recorded in the report.
2. *nine rules vs the physical axiom (A)*: **proven here**, rule by rule,
   by exact matrix computation — this closes the "engine–physical" gap for
   every exchange the engine can perform.
3. *⊥-completeness*: NOT claimed. The nine rules are a conservative subset
   of physical commutations: pairs outside the table (e.g. the
   anticommuting (x, z) pair, which physically passes up to a global phase
   of $-1$ per crossing) are refused by the engine. Consequently the closure
   fixed-point certificate is **⊥-relative**: "no ⊥-sequence helps" does not
   preclude a physically-allowed phase-adjusted exchange sequence from
   helping. Any claim of absolute optimality must additionally handle
   phase-adjusted permeability, which the engine deliberately does not.
4. *rule soundness vs rule-library soundness*: the 1,474-rule library's
   rewrite semantics are separately validated (release-audited); this
   document only certifies the exchange (⊥) layer on top of them.

## 4. Provenance

- Verifier: `scripts/verify_perp_reliability.py`; report:
  `docs/review/science_boost/2026-10-25_perp_reliability/report.json`.
- Engine source pinned by SHA-256 at verification time (engine source hash
  mechanism from `src/provenance.py`).
- Review grade; outside the release hash chain; produced during the
  2026-10-25 execution round.
