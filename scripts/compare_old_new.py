"""
Compare old baseline summary with new results summary.
Prints a formatted comparison table to stdout.
"""
import json
import os
from pathlib import Path

BASE_DIR = str(Path(__file__).resolve().parents[1] / "data")

def load_json(path):
    with open(path, "r") as f:
        return json.load(f)

def safe_get(d, *keys, default=None):
    """Safely navigate nested dicts."""
    for k in keys:
        if isinstance(d, dict) and k in d:
            d = d[k]
        else:
            return default
    return d

def fmt(val, width=12, decimals=6):
    """Format a numeric value for table display."""
    if val is None or val == "N/A":
        return f"{'N/A':>{width}}"
    try:
        return f"{float(val):>{width}.{decimals}f}"
    except (ValueError, TypeError):
        return f"{str(val):>{width}}"

def pct_change(old, new):
    """Compute percent change, handling zero denominator."""
    if old is None or new is None or old == "N/A" or new == "N/A":
        return "N/A"
    try:
        old_f, new_f = float(old), float(new)
        if old_f == 0.0:
            if new_f == 0.0:
                return 0.0
            else:
                return float("inf")
        return ((new_f - old_f) / abs(old_f)) * 100.0
    except (ValueError, TypeError, ZeroDivisionError):
        return "N/A"


def compare_e01(old, new, rows):
    """E01 grouped by depth."""
    old_groups = safe_get(old, "E01", "per_depth", default={})
    new_groups = safe_get(new, "E01", "per_depth", default={})
    all_keys = sorted(set(list(old_groups.keys()) + list(new_groups.keys())), key=lambda x: int(x))
    
    for k in all_keys:
        og = old_groups.get(k, {})
        ng = new_groups.get(k, {})
        rows.append({
            "Experiment": "E01",
            "Group": f"depth={k}",
            "Old Mean Red.": safe_get(og, "mean_reduction", default="N/A"),
            "New Mean Red.": safe_get(ng, "mean_reduction", default="N/A"),
            "Old Success": safe_get(og, "success_rate", default="N/A"),
            "New Success": safe_get(ng, "success_rate", default="N/A"),
        })


def compare_e02(old, new, rows):
    """E02 grouped by entanglement_density."""
    old_groups = safe_get(old, "E02", "per_entanglement_density", default={})
    new_groups = safe_get(new, "E02", "per_entanglement_density", default={})
    all_keys = sorted(set(list(old_groups.keys()) + list(new_groups.keys())), key=lambda x: float(x))
    
    for k in all_keys:
        og = old_groups.get(k, {})
        ng = new_groups.get(k, {})
        rows.append({
            "Experiment": "E02",
            "Group": f"density={k}",
            "Old Mean Red.": safe_get(og, "mean_reduction", default="N/A"),
            "New Mean Red.": safe_get(ng, "mean_reduction", default="N/A"),
            "Old Success": safe_get(og, "success_rate", default="N/A"),
            "New Success": safe_get(ng, "success_rate", default="N/A"),
        })


def compare_e04(old, new, rows):
    """E04 grouped by optimizer."""
    old_groups = safe_get(old, "E04", "per_optimizer", default={})
    new_groups = safe_get(new, "E04", "per_optimizer", default={})
    all_keys = sorted(set(list(old_groups.keys()) + list(new_groups.keys())))
    
    for k in all_keys:
        og = old_groups.get(k, {})
        ng = new_groups.get(k, {})
        rows.append({
            "Experiment": "E04",
            "Group": k,
            "Old Mean Red.": safe_get(og, "mean_reduction", default="N/A"),
            "New Mean Red.": safe_get(ng, "mean_reduction", default="N/A"),
            "Old Success": safe_get(og, "success_rate", default="N/A"),
            "New Success": safe_get(ng, "success_rate", default="N/A"),
        })


def compare_e05(old, new, rows):
    """E05 - only overall available in old baseline."""
    old_ov = safe_get(old, "E05", "overall", default={})
    new_ov = safe_get(new, "E05", "overall", default={})
    rows.append({
        "Experiment": "E05",
        "Group": "OVERALL",
        "Old Mean Red.": safe_get(old_ov, "mean_reduction", default="N/A"),
        "New Mean Red.": safe_get(new_ov, "mean_reduction", default="N/A"),
        "Old Success": safe_get(old_ov, "success_rate", default="N/A"),
        "New Success": safe_get(new_ov, "success_rate", default="N/A"),
    })


def compare_e10(old, new, rows):
    """E10 grouped by family|optimizer."""
    old_groups = safe_get(old, "E10", "per_family_optimizer", default={})
    new_groups = safe_get(new, "E10", "per_family_optimizer", default={})
    all_keys = sorted(set(list(old_groups.keys()) + list(new_groups.keys())))
    
    for k in all_keys:
        og = old_groups.get(k, {})
        ng = new_groups.get(k, {})
        rows.append({
            "Experiment": "E10",
            "Group": k,
            "Old Mean Red.": safe_get(og, "mean_reduction", default="N/A"),
            "New Mean Red.": safe_get(ng, "mean_reduction", default="N/A"),
            "Old Success": safe_get(og, "success_rate", default="N/A"),
            "New Success": safe_get(ng, "success_rate", default="N/A"),
        })


def compare_generic(exp_id, old, new, rows, group_key=None, label_fn=None):
    """Generic comparison for experiments with group keys."""
    if group_key:
        old_groups = safe_get(old, exp_id, group_key, default={})
        new_groups = safe_get(new, exp_id, group_key, default={})
    else:
        old_groups = {}
        new_groups = {}
    
    if not old_groups and not new_groups:
        # Fall back to overall
        old_ov = safe_get(old, exp_id, "overall", default={})
        new_ov = safe_get(new, exp_id, "overall", default={})
        rows.append({
            "Experiment": exp_id,
            "Group": "OVERALL",
            "Old Mean Red.": safe_get(old_ov, "mean_reduction", default="N/A"),
            "New Mean Red.": safe_get(new_ov, "mean_reduction", default="N/A"),
            "Old Success": safe_get(old_ov, "success_rate", default="N/A"),
            "New Success": safe_get(new_ov, "success_rate", default="N/A"),
        })
    else:
        all_keys = sorted(set(list(old_groups.keys()) + list(new_groups.keys())))
        for k in all_keys:
            og = old_groups.get(k, {})
            ng = new_groups.get(k, {})
            lbl = label_fn(k) if label_fn else k
            rows.append({
                "Experiment": exp_id,
                "Group": lbl,
                "Old Mean Red.": safe_get(og, "mean_reduction", default="N/A"),
                "New Mean Red.": safe_get(ng, "mean_reduction", default="N/A"),
                "Old Success": safe_get(og, "success_rate", default="N/A"),
                "New Success": safe_get(ng, "success_rate", default="N/A"),
            })


def print_table(rows):
    """Print a formatted comparison table."""
    if not rows:
        print("No data to display.")
        return
    
    # Column widths
    exp_w = max(len(r["Experiment"]) for r in rows)
    grp_w = max(len(r["Group"]) for r in rows)
    val_w = 14
    
    # Header
    header = (
        f"{'Experiment':<{exp_w}}  "
        f"{'Group':<{grp_w}}  "
        f"{'Old Mean Red':>{val_w}}  "
        f"{'New Mean Red':>{val_w}}  "
        f"{'Delta':>{val_w}}  "
        f"{'% Change':>{val_w}}  "
        f"{'Old Success':>{val_w}}  "
        f"{'New Success':>{val_w}}"
    )
    sep = "=" * len(header)
    
    print(sep)
    print("OLD vs NEW RESULTS COMPARISON TABLE")
    print(sep)
    print(header)
    print("-" * len(header))
    
    prev_exp = None
    for r in rows:
        if prev_exp and r["Experiment"] != prev_exp:
            print("-" * len(header))
        prev_exp = r["Experiment"]
        
        old_mr = r["Old Mean Red."]
        new_mr = r["New Mean Red."]
        
        # Compute delta
        try:
            delta = float(new_mr) - float(old_mr)
            delta_str = f"{delta:>{val_w}.{6}f}"
        except (ValueError, TypeError):
            delta_str = f"{'N/A':>{val_w}}"
        
        # Compute % change
        pc = pct_change(old_mr, new_mr)
        if isinstance(pc, float):
            if pc == float("inf"):
                pc_str = f"{'inf':>{val_w}}"
            else:
                pc_str = f"{pc:>{val_w}.2f}%"
        else:
            pc_str = f"{'N/A':>{val_w}}"
        
        old_sr = r["Old Success"]
        new_sr = r["New Success"]
        
        line = (
            f"{r['Experiment']:<{exp_w}}  "
            f"{r['Group']:<{grp_w}}  "
            f"{fmt(old_mr, val_w)}  "
            f"{fmt(new_mr, val_w)}  "
            f"{delta_str}  "
            f"{pc_str}  "
            f"{fmt(old_sr, val_w)}  "
            f"{fmt(new_sr, val_w)}"
        )
        print(line)
    
    print(sep)
    print(f"Total comparison rows: {len(rows)}")


def print_overall_summary(old, new):
    """Print a compact overall summary for all experiments."""
    print("\n" + "=" * 90)
    print("OVERALL SUMMARY COMPARISON (all experiments)")
    print("=" * 90)
    header = (
        f"{'Exp':<6}  "
        f"{'Old Rows':>10}  "
        f"{'New Rows':>10}  "
        f"{'Old MeanRed':>14}  "
        f"{'New MeanRed':>14}  "
        f"{'Delta':>12}  "
        f"{'Old SuccRate':>14}  "
        f"{'New SuccRate':>14}"
    )
    print(header)
    print("-" * 90)
    
    for exp in ["E01", "E02", "E04", "E05", "E10", "E12", "E13", "E16"]:
        old_ov = safe_get(old, exp, "overall", default={})
        new_ov = safe_get(new, exp, "overall", default={})
        
        old_rows = safe_get(old_ov, "total_rows", default="N/A")
        new_rows = safe_get(new_ov, "total_rows", default="N/A")
        old_mr = safe_get(old_ov, "mean_reduction", default="N/A")
        new_mr = safe_get(new_ov, "mean_reduction", default="N/A")
        old_sr = safe_get(old_ov, "success_rate", default="N/A")
        new_sr = safe_get(new_ov, "success_rate", default="N/A")
        
        try:
            delta = float(new_mr) - float(old_mr)
            delta_str = f"{delta:>12.6f}"
        except (ValueError, TypeError):
            delta_str = f"{'N/A':>12}"
        
        line = (
            f"{exp:<6}  "
            f"{str(old_rows):>10}  "
            f"{str(new_rows):>10}  "
            f"{fmt(old_mr, 14)}  "
            f"{fmt(new_mr, 14)}  "
            f"{delta_str}  "
            f"{fmt(old_sr, 14)}  "
            f"{fmt(new_sr, 14)}"
        )
        print(line)
    
    print("=" * 90)


def main():
    old_path = os.path.join(BASE_DIR, "old_baseline_summary.json")
    new_path = os.path.join(BASE_DIR, "new_results_summary.json")
    
    print(f"Loading old baseline: {old_path}")
    old = load_json(old_path)
    print(f"Loading new results:  {new_path}")
    new = load_json(new_path)
    
    rows = []
    
    # Per-experiment detailed comparison
    compare_e01(old, new, rows)
    compare_e02(old, new, rows)
    compare_e04(old, new, rows)
    compare_e05(old, new, rows)
    compare_e10(old, new, rows)
    
    # E12 - old has no E12, use generic (will show new-only data)
    compare_generic("E12", old, new, rows, group_key="per_circuit_family", label_fn=lambda k: k)
    
    # E13 - old has no E13
    compare_generic("E13", old, new, rows, group_key="per_circuit_family", label_fn=lambda k: k)
    
    # E16 - old has overall only
    compare_generic("E16", old, new, rows, group_key=None)
    
    # Print detailed table
    print_table(rows)
    
    # Print overall summary
    print_overall_summary(old, new)
    
    print("\nDone.")


if __name__ == "__main__":
    main()
