"""
Quick data exploration for E1+E3
"""
import pandas as pd
import numpy as np
import os

os.chdir("D:/Desktop/Q-research")

e1 = pd.read_csv("data/raw/exp1_phase_transition_20260530_095003.csv")
e3 = pd.read_csv("data/raw/exp3_scaling_20260530_100830.csv")

print("=== E1: success_rate vs depth ===")
e1_agg = e1.groupby('depth').agg(sr=('success','mean'), mr=('reduction','mean'), me=('normalized_entropy','mean')).reset_index()
for _, r in e1_agg.iterrows():
    print(f"  d={int(r.depth):3d}: sr={r.sr:.3f}, reduction={r.mr:.4f}, entropy={r.me:.4f}")

print()
print("=== E3: success_rate by n_qubits ===")
e3_agg = e3.groupby('n_qubits').agg(sr=('success','mean'), mr=('reduction','mean'), me=('normalized_entropy','mean')).reset_index()
for _, r in e3_agg.iterrows():
    print(f"  n={int(r.n_qubits):2d}: sr={r.sr:.3f}, reduction={r.mr:.4f}, entropy={r.me:.4f}")

print()
print("=== E3: mean success_rate vs depth for each n ===")
for n in sorted(e3.n_qubits.unique()):
    sub = e3[e3.n_qubits==n].groupby('depth').agg(sr=('success','mean')).reset_index()
    key_depths = sub[sub.depth.isin([1,5,10,15,20,25,30])]
    print(f"  n={n}:")
    for _, r in key_depths.iterrows():
        print(f"    d={int(r.depth)}: sr={r.sr:.3f}")

print()
print("=== E1: success vs normalized_entropy bins ===")
e1['entropy_bin'] = pd.cut(e1['normalized_entropy'], bins=[0,0.2,0.4,0.6,0.8,1.0])
e1_ent = e1.groupby('entropy_bin').agg(sr=('success','mean'), mr=('reduction','mean'), cnt=('success','count')).reset_index()
for _, r in e1_ent.iterrows():
    print(f"  {r.entropy_bin}: sr={r.sr:.3f}, reduction={r.mr:.4f}, cnt={r.cnt}")

print()
print("=== E3: success vs normalized_entropy bins ===")
e3['entropy_bin'] = pd.cut(e3['normalized_entropy'], bins=[0,0.2,0.4,0.6,0.8,1.0])
e3_ent = e3.groupby('entropy_bin').agg(sr=('success','mean'), mr=('reduction','mean'), cnt=('success','count')).reset_index()
for _, r in e3_ent.iterrows():
    print(f"  {r.entropy_bin}: sr={r.sr:.3f}, reduction={r.mr:.4f}, cnt={r.cnt}")

print()
print("=== Correlations ===")
print(f"E1: entropy vs success correlation: {e1['normalized_entropy'].corr(e1['success']):.4f}")
print(f"E1: entropy vs reduction correlation: {e1['normalized_entropy'].corr(e1['reduction']):.4f}")
print(f"E1: depth vs success correlation: {e1['depth'].corr(e1['success']):.4f}")
print(f"E1: depth vs reduction correlation: {e1['depth'].corr(e1['reduction']):.4f}")

print(f"E3: entropy vs success correlation: {e3['normalized_entropy'].corr(e3['success']):.4f}")
print(f"E3: entropy vs reduction correlation: {e3['normalized_entropy'].corr(e3['reduction']):.4f}")
print(f"E3: depth vs success correlation: {e3['depth'].corr(e3['success']):.4f}")
print(f"E3: n_qubits vs success correlation: {e3['n_qubits'].corr(e3['success']):.4f}")