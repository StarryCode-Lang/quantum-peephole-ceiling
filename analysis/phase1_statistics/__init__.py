"""Phase 1 Statistics: Postdoctoral-level statistical toolkit for PRA.

Modules
-------
multiple_comparison
    Benjamini-Hochberg FDR and Holm-Bonferroni corrections.
effect_size
    Cliff's delta and Cohen's d with confidence intervals.
power_analysis
    Post-hoc power, sample-size planning, and power curves.
bootstrap
    Bootstrap confidence intervals with convergence diagnostics.
fidelity_distribution
    Full distributional summaries and outlier detection.
"""

from .multiple_comparison import benjamini_hochberg, holm_bonferroni, fdr_control_table
from .effect_size import cliffs_delta, cohens_d, interpret_effect_size, effect_size_table
from .power_analysis import calculate_power, required_sample_size, power_curve
from .bootstrap import bootstrap_ci, bootstrap_convergence, bootstrap_distribution
from .fidelity_distribution import fidelity_summary, fidelity_outliers, fidelity_by_circuit_family

__all__ = [
    "benjamini_hochberg",
    "holm_bonferroni",
    "fdr_control_table",
    "cliffs_delta",
    "cohens_d",
    "interpret_effect_size",
    "effect_size_table",
    "calculate_power",
    "required_sample_size",
    "power_curve",
    "bootstrap_ci",
    "bootstrap_convergence",
    "bootstrap_distribution",
    "fidelity_summary",
    "fidelity_outliers",
    "fidelity_by_circuit_family",
]
