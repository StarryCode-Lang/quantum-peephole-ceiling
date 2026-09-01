from analysis.qubit_permutation_metamorphic_audit import build_audit


def test_qubit_permutation_metamorphic_audit():
    audit = build_audit(cases=8)

    assert audit["status"] == "PASS_ALL_QUBIT_PERMUTATION_METAMORPHIC_CHECKS"
    assert audit["nonidentity_permutations_checked"] == 8
    assert audit["equivalence_decisions_checked"] == 32
    assert audit["failures"] == 0
