from __future__ import annotations

import pytest

from scripts.write_e31_independent_verification_receipt import build_receipt


def test_receipt_refuses_partial_verification_count():
    with pytest.raises(RuntimeError, match="full certificate inventory"):
        build_receipt(checked_artifacts=33_999)
