"""Batch verification of manuscript references via the Scholar plugin.

Queries Scholar by paper title for each of the 45 references in
docs/manuscript/manuscript.md and records whether a plausible match
(title similarity + year proximity) is found. Evidence CSVs are kept
under data/v6/ceiling_repair/scholar/results/.

Usage:
    python data/v6/ceiling_repair/scholar/verify_refs.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
RESULTS.mkdir(parents=True, exist_ok=True)

SCHOLAR = (
    "C:/Users/Administrator/AppData/Roaming/kimi-desktop/daimon-share/"
    "daimon/runtime/kimi-code/home/plugins/managed/scholar"
)

# (ref_id, title_query, expected_year, expected_first_author_surname)
REFS = [
    ("1", "Peephole optimization McKeeman", 1965, "McKeeman"),
    ("2", "Using peephole optimization on intermediate code", 1982, "Tanenbaum"),
    ("4", "Superoptimizer a look at the smallest program", 1987, "Massalin"),
    ("8", "Elementary gates for quantum computation", 1995, "Barenco"),
    ("9", "Quantum Computation and Quantum Information Nielsen Chuang", 2010, "Nielsen"),
    ("10", "Techniques for the synthesis of reversible Toffoli networks", 2007, "Maslov"),
    ("13", "meet-in-the-middle algorithm fast synthesis depth-optimal quantum circuits", 2013, "Amy"),
    ("16", "Fast and efficient exact synthesis of Clifford+T circuits", 2013, "Kliuchnikov"),
    ("20", "Number-theoretic characterizations of optimal quantum circuits diagonal unitaries", 2018, "Amy"),
    ("21", "Graph-theoretic Simplification of Quantum Circuits ZX-calculus", 2020, "Duncan"),
    ("22", "Faster resynthesis with the ZX-calculus", 2022, "de Beaudrap"),
    ("25", "Non-identity-check is QMA-complete", 2003, "Janzing"),
    ("27", "Stabilizer codes and quantum error correction Gottesman thesis", 1997, "Gottesman"),
    ("28", "Improved simulation of stabilizer circuits", 2004, "Aaronson"),
    ("29", "The Solovay-Kitaev algorithm Dawson Nielsen", 2006, "Dawson"),
    ("30", "Quantum computational supremacy Harrow Montanaro", 2017, "Harrow"),
    ("32", "Fundamentals of Parameterized Complexity Downey Fellows", 2013, "Downey"),
    ("33", "A geometric approach to quantum circuit lower bounds", 2005, "Nielsen"),
    ("35", "Synthesis of Quantum-Logic Circuits Shende Bullock Markov", 2006, "Shende"),
    ("38", "Quantum complexity theory Bernstein Vazirani", 1997, "Bernstein"),
    ("39", "A quantum approximate optimization algorithm Farhi", 2014, "Farhi"),
    ("40", "A variational eigenvalue solver on a photonic quantum processor", 2014, "Peruzzo"),
    ("41", "A fast quantum mechanical algorithm for database search", 1996, "Grover"),
    ("42", "Strategies for quantum computing molecular energies unitary coupled cluster", 2019, "Romero"),
    ("43", "A new quantum ripple-carry addition circuit", 2004, "Cuccaro"),
    ("45", "Temporally unstructured quantum computation", 2019, "Shepherd"),
    ("46", "Qiskit open-source framework quantum computing", 2024, "Qiskit"),
    ("47", "Cirq Python library NISQ circuits", 2023, "Cirq"),
    ("48", "t|ket> retargetable compiler for NISQ devices", 2020, "Sivarajah"),
    ("50", "Surface codes towards practical large-scale quantum computation", 2012, "Fowler"),
    ("51", "Local random quantum circuits approximate polynomial-designs", 2016, "Brandao"),
    ("56", "Fast equivalence checking of quantum circuits Yamashita", 2011, "Yamashita"),
    ("61", "Exact and practical pattern matching for quantum circuit optimization", 2022, "Iten"),
    ("62", "Quartz superoptimization of quantum circuits", 2022, "Xu"),
    ("63", "Quanto optimizing quantum circuits automatic generation circuit identities", 2024, "Pointing"),
    ("64", "Quarl learning-based quantum circuit optimizer", 2024, "Li"),
    ("65", "Quantum circuit optimization with AlphaTensor", 2025, "Ruiz"),
    ("66", "Relaxed peephole optimization quantum", 2021, "Liu"),
    ("67", "Reinforcement learning quantum circuit optimization ZX-calculus", 2025, "Riu"),
    ("68", "200-line Python micro-benchmark suite NISQ circuit compilers", 2025, "Merilehto"),
    ("69", "MQT Bench benchmarking software design automation quantum computing", 2023, "Nitsch"),
    ("70", "QASMBench low-layer QASM benchmark suite", 2021, "Wang"),
    ("78", "Automated optimization of large quantum circuits continuous parameters", 2018, "Nam"),
    ("81", "Quantum circuit optimization survey ACM Computing Surveys", 2022, "Patel"),
    ("82", "Clifford circuit optimization templates symbolic Pauli gates", 2021, "Bravyi"),
]


def normalize(s: str) -> str:
    return "".join(c for c in s.lower() if c.isalnum() or c.isspace()).split()


def title_similarity(a: str, b: str) -> float:
    ta, tb = set(normalize(a)), set(normalize(b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def run_query(ref_id: str, query: str) -> list[dict]:
    out_csv = RESULTS / f"ref_{ref_id}.csv"
    params = {"query": query, "file_path": str(out_csv), "num_results": 5, "hl": "en"}
    cmd = ["python3", "scripts/scholar_tool.py", "call",
           "--api-name", "scholar_search",
           "--params-json", json.dumps(params)]
    p = subprocess.run(cmd, cwd=SCHOLAR, capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        return []
    if not out_csv.exists():
        return []
    import csv
    with open(out_csv, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    rows = []
    for ref_id, query, year, surname in REFS:
        try:
            results = run_query(ref_id, query)
        except Exception as exc:  # noqa: BLE001
            rows.append({"ref_id": ref_id, "query": query, "status": f"ERROR: {exc}"})
            continue
        best, best_sim = None, 0.0
        for r in results:
            sim = title_similarity(query, r.get("title", ""))
            if sim > best_sim:
                best, best_sim = r, sim
        if best is None:
            status = "NOT_FOUND"
        else:
            byear = str(best.get("year", ""))
            authors = best.get("authors", "")
            year_ok = byear.isdigit() and abs(int(byear) - year) <= 2
            author_ok = surname.lower() in authors.lower()
            if best_sim >= 0.5 and (year_ok or author_ok):
                status = f"VERIFIED sim={best_sim:.2f} year={byear} ({best.get('title','')[:80]})"
            elif best_sim >= 0.35:
                status = f"WEAK_MATCH sim={best_sim:.2f} year={byear} ({best.get('title','')[:80]})"
            else:
                status = f"NOT_FOUND best_sim={best_sim:.2f} ({best.get('title','')[:60]})"
        rows.append({"ref_id": ref_id, "query": query, "status": status})
        print(f"[{ref_id:>2s}] {status}")
        time.sleep(1.0)  # be polite to the service

    import csv
    out = HERE / "ref_verification.csv"
    tmp = HERE / "ref_verification.csv.tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["ref_id", "query", "status"])
        w.writeheader()
        w.writerows(rows)
    tmp.replace(out)
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
