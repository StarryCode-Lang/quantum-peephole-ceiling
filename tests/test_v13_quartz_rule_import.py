"""Contract checks for the v13 Quartz ECC import and E43 receipt."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ECC = ROOT / "data" / "v13" / "quartz_source" / "Nam_5_3_complete_ECC_set.json"
LIBRARY = ROOT / "data" / "v13" / "e43_quartz_rule_import" / "generation_a" / "rule_library.json"
RECEIPT = ROOT / "docs" / "review" / "v13_stage2_quartz_import_receipt.json"


def test_clean_quartz_source_and_e43_receipt_are_pinned():
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert receipt["upstream"]["commit"] == "c4abf876608b111b2900d59a3c4efd7982063c20"
    assert hashlib.sha256(ECC.read_bytes()).hexdigest() == receipt["upstream"]["ecc_sha256"]
    assert receipt["upstream"]["clean_source_boundary_verified"] is True


def test_e43_zero_tolerance_counts_and_independent_generation():
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    semantic = receipt["semantic_audit"]
    contract = receipt["import_contract"]
    assert contract["quartz_v1_direction_count"] == 1474
    assert semantic["symbolic_mismatch_count"] == 0
    assert semantic["numeric_mismatch_count"] == 0
    assert semantic["non_equivalent_mutant_escapes"] == 0
    assert receipt["independent_generation"]["byte_identical"] is True


def test_rule_library_contains_per_rule_proof_hashes_and_no_content_duplicates():
    library = json.loads(LIBRARY.read_text(encoding="utf-8"))
    quartz = [rule for rule in library["rules"] if rule["rule_family"] == "quartz_v1"]
    assert len(quartz) == 1474
    assert all(len(rule["symbolic_proof_hash"]) == 64 for rule in quartz)
    assert len({rule["content_hash"] for rule in library["rules"]}) == len(library["rules"])
    assert library["summary"]["content_hash_duplicate_count"] == 0
