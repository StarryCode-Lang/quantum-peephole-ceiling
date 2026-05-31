"""End-to-end verification of all postdoc-level optimizations."""
import sys
import os
import json
from pathlib import Path

sys.path.insert(0, '.')
print(f'Python: {sys.version}')

errors = []

# 1. Syntax check experiment runner
print('\n--- 1. Syntax check: run_all_experiments_v3.py ---')
import py_compile
try:
    py_compile.compile('experiments/run_all_experiments_v3.py', doraise=True)
    print('OK')
except py_compile.PyCompileError as e:
    errors.append(f'Syntax error: {e}')
    print(f'FAIL: {e}')

# 2. Import statistical_rigor
print('\n--- 2. Import: statistical_rigor ---')
try:
    from src.analysis.statistical_rigor import (
        benjamini_hochberg, bonferroni_correction,
        compare_models, residual_analysis,
        power_analysis_sample_size, achieved_power,
        normality_tests, exponential_decay, sigmoid_decay, power_law
    )
    print('OK - all 10 functions importable')
except Exception as e:
    errors.append(f'statistical_rigor import: {e}')
    print(f'FAIL: {e}')

# 3. Import publication_style
print('\n--- 3. Import: publication_style ---')
try:
    from scripts.publication_style import (
        PUBLICATION_RCPARAMS, apply_publication_style,
        COLORBLIND_PALETTE, SEQUENTIAL_PALETTE, get_colorblind_colors,
        create_figure, add_panel_label, save_publication_figure,
        format_p_value, format_ci
    )
    print('OK - all functions importable')
except Exception as e:
    errors.append(f'publication_style import: {e}')
    print(f'FAIL: {e}')

# 4. Test statistical functions
print('\n--- 4. Test: statistical_rigor functions ---')
try:
    import numpy as np
    p_vals = np.array([0.001, 0.01, 0.03, 0.04, 0.10, 0.50])
    adj_p, threshold = benjamini_hochberg(p_vals)
    print(f'BH correction: threshold={threshold:.4f} OK')

    n_req = power_analysis_sample_size(0.5, 0.05, 0.80)
    print(f'Sample size (d=0.5, power=0.8): n={n_req} OK')

    power = achieved_power(0.5, 100)
    print(f'Achieved power (d=0.5, n=100): {power:.3f} OK')

    norm_results = normality_tests(np.random.randn(100))
    print(f'Normality tests: Shapiro p={norm_results["shapiro_wilk"]["p_value"]:.3f} OK')
except Exception as e:
    errors.append(f'statistical test: {e}')
    print(f'FAIL: {e}')

# 5. Test model comparison
print('\n--- 5. Test: model comparison (AIC/BIC) ---')
try:
    from scipy.optimize import curve_fit
    x = np.linspace(1, 50, 50)
    y_true = 0.3 * np.exp(-x / 19.0) + np.random.normal(0, 0.01, 50)
    popt_exp, _ = curve_fit(exponential_decay, x, y_true, p0=[0.3, 19.0], maxfev=5000)
    popt_sig, _ = curve_fit(sigmoid_decay, x, y_true, p0=[25, 0.1, 0.3], maxfev=5000)
    df = compare_models(y_true, {
        'exponential': lambda *p: exponential_decay(x, *p),
        'sigmoid': lambda *p: sigmoid_decay(x, *p),
    }, {
        'exponential': popt_exp,
        'sigmoid': popt_sig,
    })
    best = df.loc[df['AIC_weight'].idxmax(), 'model']
    print(f'Best model by AIC: {best}')
    assert best == 'exponential', f"Expected exponential, got {best}"
    print('AIC correctly selects exponential decay OK')
except Exception as e:
    errors.append(f'model comparison: {e}')
    print(f'FAIL: {e}')

# 6. Test publication style
print('\n--- 6. Test: publication style ---')
try:
    p1 = format_p_value(0.0001)
    p2 = format_p_value(0.023)
    ci = format_ci(0.297, 0.251, 0.343)
    colors = get_colorblind_colors(5)
    print(f'P-value (<0.001): {p1}')
    print(f'P-value (0.023): {p2}')
    print(f'CI format: {ci}')
    print(f'5 colors: {colors}')
    print('OK')
except Exception as e:
    errors.append(f'pub style: {e}')
    print(f'FAIL: {e}')

# 7. Verify output files exist
print('\n--- 7. Verify generated files ---')
expected_files = [
    'data/processed/environment_snapshot.json',
    'data/processed/baseline_statistics.json',
    'docs/manuscript_v5.md',
    'src/analysis/statistical_rigor.py',
    'scripts/publication_style.py',
    'scripts/snapshot_environment.py',
    'scripts/compute_baselines.py',
]
for f in expected_files:
    exists = Path(f).exists()
    size = Path(f).stat().st_size if exists else 0
    status = f'{size:,} bytes' if exists else 'MISSING'
    print(f'  {"OK" if exists else "FAIL"} {f} ({status})')
    if not exists:
        errors.append(f'Missing file: {f}')

# 8. Verify dead code removed
print('\n--- 8. Verify dead code removed ---')
dead_files = [
    'scripts/generate_figures.py',
    'scripts/gen_pdfs.py',
]
for f in dead_files:
    exists = Path(f).exists()
    print(f'  {"FAIL (still exists)" if exists else "OK (removed)"} {f}')
    if exists:
        errors.append(f'Dead code not removed: {f}')

# 9. Verify environment snapshot content
print('\n--- 9. Verify environment snapshot ---')
try:
    with open('data/processed/environment_snapshot.json') as f:
        snap = json.load(f)
    print(f'  Python: {snap.get("python_version", "?")}')
    print(f'  Packages: {len(snap.get("packages", {}))} recorded')
    print(f'  Source hashes: {len(snap.get("source_hashes", {}))} files hashed')
    print('OK')
except Exception as e:
    errors.append(f'snapshot verify: {e}')
    print(f'FAIL: {e}')

# Summary
print('\n' + '=' * 60)
if errors:
    print(f'VERIFICATION FAILED: {len(errors)} error(s)')
    for e in errors:
        print(f'  - {e}')
    sys.exit(1)
else:
    print('ALL VERIFICATIONS PASSED')
    sys.exit(0)
