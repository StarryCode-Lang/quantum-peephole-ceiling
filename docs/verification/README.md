# Verification Artifacts

`fidelity_fallback_calibration.csv` and `fidelity_fallback_calibration.json`
record an exact-versus-sampled calibration of the large-circuit fidelity path.
The calibration includes local and entangling mismatches at multiple qubit
counts. Regenerate with:

```bash
python scripts/characterize_fidelity_fallback.py --n-values 3 5 8 --samples 1000
```

Exact unitary comparison remains the preferred publication path. Sampled
fidelity is an uncertainty-bearing estimate and must not be described as an
exact certificate.
