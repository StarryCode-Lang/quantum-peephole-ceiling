# E32 telemetry verifier erratum (2026-08-31)

The formal E32 scientific run and all frozen source/result bytes remain
unchanged. The protocol-frozen v1 independent verifier incorrectly expected
96 manifest members (90 receipts plus six roots), although the manifest
intentionally contains 186 members: 90 worker payloads, 90 receipts, and six
root artifacts. It therefore failed closed on cardinality after the formal
run.

`scripts/verify_e32_telemetry_panel_v2.py` corrects only this independent
accounting rule and additionally checks every payload/receipt treatment pair,
run order, monotonic event stream, first-valid and earliest-best event index,
receipt hash, and all 186 artifact hashes. The v1 file is retained byte-for-byte
because its hash is part of the pre-execution frozen protocol. The v2 result
must be reported together with this erratum; it is not evidence that the v1
verifier passed.
