# Thm 10 (candidate): bounded-horizon search vs commutation closure

**Date:** 2026-10-22
**Status:** candidate theorem, evidence-backed, not yet peer-reviewed.
**Supersedes:** the 2026-10-19 formulation `L >= ceil(delta_cost / delta_max)`, which is
correct but vacuous on the instances of interest (it gives L >= 1 where L = 4).
**Evidence:** E50 (horizon scaling), E52 (mechanism census), E55 (cross-engine probe).

---

## 1. Why the old formulation was wrong

The 2026-10-19 note proposed a path-length bound from the ratio of the required cost drop to
the largest single-action drop. On the Bernstein–Vazirani family the library's largest
reduction is 2 and the required drop is 2, so the bound reads `L >= 1` while the measured
first improving horizon is 4–7. The bound is true and useless: it bounds the *reducing* part
of the path and ignores the *neutral* part, which is where all the difficulty lives.

The 2026-10-22 census (E52) supplies the missing structure: every escape witness has the
shape

```
k neutral steps  +  1 reducing step
```

with `k >= 0`, and the reducing step is always a `pair_v1` rule. So the object to bound is
`k`, not the cost drop.

## 2. Definitions

**Listing.** A total order on the gates of a circuit. Fixed throughout.

**Adjacent-transposition step.** Swapping two gates that occupy adjacent positions in the
listing and are related by an implemented commutation law. The project's library implements
at least three laws:

| Law | Rule id | Derivable from disjoint support? |
|---|---|---|
| disjoint support | `exchange.disjoint` | yes |
| diagonal through CX control | `exchange.cx_control_z` | **no** |
| H-conjugated CX reversal | `quartz_v1:10_2`, `15_2`, `11_2`, `45_2` | no (changes gate content) |

**Exchange distance `d(C)`.** The minimum number of adjacent-transposition steps needed to
bring some reducible pair of `C` into adjacent positions, or `inf` if no sequence does.

**Bounded-horizon engine `E(h)`.** An engine that explores at most `h` actions from the
root and returns the best cost it certifies.

**Closure engine `E*`.** An engine that applies a commutation law repeatedly until no
adjacent transposition is available, then reduces, and iterates to a fixed point.

## 3. Proposition 1 (necessity of the horizon)

> If `d(C) = k < inf`, then `E(h)` certifies no improvement for every `h <= k`, and `E(k+1)`
> certifies one.

*Argument.* Any improving path must contain a reducing step, and a reducing step requires its
two gates to be adjacent. Between the root and that adjacency, every adjacent transposition
moves the pair one position closer at best, so at least `k` transpositions are needed before
the reducing step. A path of `h` actions contains at most `h` transpositions, so `h >= k+1`.
The upper direction is constructive: perform the `k` transpositions, then the reduction.

*Status.* The lower direction is a counting argument and is tight by construction. The upper
direction is confirmed on every instance where the transpositions are individually legal:
E52 measured `d = 0` on 49 roots and all 49 escape at depth exactly 1 (49/49, zero false
positives); E55 case A has `d = 1` and the project engine escapes at `h = 3` but not `h = 1`.

## 4. Proposition 2 (closure dominates on cost)

> On the same instance, `E*` reaches the same improvement in `O(m^2)` time, where `m` is the
> gate count, independently of `k`.

*Argument.* Each gate pair is considered once per reduction round; the number of rounds is
bounded by the number of reducing steps, which is at most `m/2`. No exponential factor in `k`
appears, because the closure does not enumerate action sequences — it computes the
reachability relation directly.

*Status.* This is the standard argument for commutation-based peephole passes. What is new
here is the empirical contrast, below.

## 5. Empirical contrast (E55)

Circuits written directly in `{h, x, rz, cx}`; `rz(t) ... rz(-t)` around CX gates whose
*control* wire carries the `rz`. Because a diagonal gate commutes with the control of a CX,
both `rz` should merge and vanish. Optimal cost = number of CX gates.

| Case | k | Optimal | qiskit L3 | tket FPO | tket RR | BQSKit | project `E(1)` | project `E(3)` |
|---|---|---|---|---|---|---|---|---|
| A (control, 1 CX) | 1 | 1 | **1** | **1** | 3 | 3 | 3 | **1** |
| B (control, 6 CX) | 6 | 6 | **6** | **6** | 8 | 8 | 8 | **8** |
| C (target; negative control) | — | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| E (control + X on target) | 2 | 2 | **2** | **2** | 4 | 4 | 4 | **2** |

Reading:

1. **The law is implemented in the field.** qiskit `optimization_level=3` and tket
   `FullPeepholeOptimise` solve A, B and E, including the `k = 6` case. The blind spot is
   therefore **not** an industry-wide gap; the earlier framing ("the engine's commutation
   relation is incomplete") was wrong and is withdrawn.
2. **The project engine has the rule but not the depth.** It solves A (`k=1`, needs `h>=2`)
   and E (`k=2`, needs `h>=3`) at `h=3`, and fails B (`k=6`, needs `h>=7`) at `h=3`. This is
   exactly Proposition 1, and it is the first instance where the same engine both succeeds
   and fails purely as a function of `k`.
3. **Closure engines win on cost.** qiskit and tket do not enumerate action sequences; they
   compute reachability. They are unaffected by `k`.
4. **The negative control holds.** Case C (`rz` on the CX *target*) is non-commuting and no
   engine removes it. So the successes above are not "tools delete gates indiscriminately".

## 6. What this means for the project

This is the sharpest result of the review cycle and it cuts both ways.

**For the paper.** The claim becomes a *separation between two algorithm classes on the same
problem*, with an existence proof from production tools:

> Bounded-horizon peephole search requires `h >= d(C) + 1` and therefore fails on any family
> whose exchange distance grows with size (E50: `k = 0,1,1,4,4,4,5` for `n = 4..16`), at a
> cost exponential in `h`. Commutation closure reaches the same improvement in `O(m^2)`,
> independently of `k`, and is what qiskit and tket already do. The certified landscape is
> therefore best read as a *measurement instrument* — it certifies what a bounded engine
> cannot see — not as a competitive optimizer.

**Against the project's framing.** If closure is polynomial and always at least as good, then
the 76,236 window searches are, as an *optimizer*, dominated. Their value is evidential: they
certify optimality within a declared rule domain, which closure does not. Any sentence that
presents the landscape as an optimization result must be removed.

**The open question that would restore the optimizer claim.** Closure is optimal only with
respect to the implemented commutation laws. Whether a *content-changing* step (CX reversal)
can unlock reductions that no commutation closure reaches is open. E52 finds 3 of 14 genuine
escapes are content-changing, so the answer is plausibly yes — but 3 instances are not a
theorem.

## 7. Boundaries

- One listing model per instance; `d(C)` is listing-relative.
- One rule domain (`e44_core_v1`); a larger library can only decrease `d`.
- E55 uses 4 hand-built circuits with `n <= 7`. It is a *probe*, not a benchmark; the
  conclusion "qiskit and tket implement the law" is supported, the conclusion "no engine
  fails it" is not.
- The `k` values in E50 are measured on one generator (`make_bernstein_vazirani(seed=42)`)
  and one normaliser.

## 8. What would make this a theorem

1. Prove Proposition 2's cost bound for a named closure algorithm (not "the standard
   argument").
2. Prove that `d(C)` grows without bound for a natural family. E50 gives a measured
   sequence; the missing step is a lower bound on the number of CX gates an `H` must cross,
   which is a statement about the generator's structure, not about optimization.
3. Show a family where closure provably cannot reach the optimum and a bounded search can —
   this is the only route that restores an optimizer claim.
