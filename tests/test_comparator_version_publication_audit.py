import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_targeted_arxiv_publication_audit_is_explicit_and_fail_bounded():
    audit = json.loads(
        (ROOT / "release/comparator_version_publication_audit.json").read_text(
            encoding="utf-8"
        )
    )
    assert audit["status"] == "PARTIAL_TARGETED_PRIMARY_VERSION_RECONCILIATION"
    assert {record["name"] for record in audit["comparators"]} == {"Quartz", "GUOQ"}
    for record in audit["comparators"]:
        assert record["arxiv_pages"] > 0 and record["formal_pages"] > 0
        assert record["arxiv_pdf_bytes"] > 0 and record["formal_pdf_bytes"] > 0
        assert re.fullmatch(r"[0-9a-f]{64}", record["arxiv_pdf_sha256"])
        assert re.fullmatch(r"[0-9a-f]{64}", record["formal_pdf_sha256"])
        assert record["material_difference"]
        assert record["central_claim_reversal_found"] is False
    assert audit["metric_dispositions"]["3.18"].startswith("PARTIAL:")
    assert "full manuscript bibliography" in audit["metric_dispositions"]["3.18"]

