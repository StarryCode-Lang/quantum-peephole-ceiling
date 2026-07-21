"""Pass 3: re-probe remaining unverified refs with author/arXiv-style queries,
plus novelty probes for the project's core theoretical claims.

Outputs ref_verification_pass3.csv and novelty_probes.csv under
data/v6/ceiling_repair/scholar/.
"""

from __future__ import annotations

import csv
import json
import subprocess
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
RESULTS.mkdir(parents=True, exist_ok=True)

SCHOLAR = (
    "C:/Users/Administrator/AppData/Roaming/kimi-desktop/daimon-share/"
    "daimon/runtime/kimi-code/home/plugins/managed/scholar"
)

# (tag, query, note)
REFS3 = [
    ("10", "Maslov Dueck Miller reversible Toffoli networks synthesis", "ACM TODAES 12(4) 2008"),
    ("20", "Amy Glaudell Ross number-theoretic quantum circuits", "npj QI 4:43 2018 / arXiv:1606.02729"),
    ("21", "Duncan Kissinger Perdrix van de Wetering graph-theoretic simplification", "Quantum 4, 279 (2020)"),
    ("22", "de Beaudrap Kissinger Wetering resynthesis ZX-calculus QPL", "QPL 2022 / arXiv:2206.10843"),
    ("25", "Janzing Wocjan Beth QMA-complete identity check 2003", "IJQI 1(4) 507"),
    ("32", "Downey Fellows parameterized complexity book Springer", "Springer 2013"),
    ("33", "Nielsen geometric approach quantum circuit lower bounds quant-ph 0502070", "arXiv 2005"),
    ("35", "Shende Bullock Markov synthesis quantum logic circuits TCAD", "IEEE TCAD 25(6) 2006"),
    ("39", "Farhi Goldstone Gutmann quantum approximate optimization algorithm", "arXiv:1411.4028"),
    ("40", "Peruzzo McClean variational eigenvalue solver photonic", "Nat Commun 5:4213"),
    ("46", "Qiskit open-source framework quantum computing Javadi", "Zenodo/software"),
    ("47", "Cirq quantum AI python library NISQ", "software"),
    ("48", "Sivarajah tket retargetable compiler NISQ", "QST 6 014003"),
    ("50", "Fowler Mariantoni Martinis Cleland surface codes", "PRA 86 032324"),
    ("51", "Brandao Harrow Horodecki local random quantum circuits", "CMP 346 397"),
    ("56", "Yamashita Markov fast equivalence checking quantum circuits IEICE", "IEICE E94-A 2011"),
    ("61", "Iten Moyard Metger Sutter Woerner pattern matching quantum circuit", "ACM TQC 3(1) 2022"),
    ("63", "Pointing Quanto quantum circuit identities automatic generation", "QST 9 035045"),
    ("64", "Quarl learning-based quantum circuit optimizer OOPSLA", "PACMPL 2024"),
    ("67", "Riu reinforcement learning quantum circuit ZX-calculus Quantum journal", "Quantum 9 1634"),
    ("69", "MQT Bench Quetschlich Burgholzer Wille benchmarking", "ACM TQC 2023"),
    ("70", "QASMBench benchmark suite NISQ evaluation simulation Ang Li", "arXiv:2005.13018?"),
    ("81", "quantum circuit optimization survey Markov", "ACM Comput Surv?"),
    ("82", "Bravyi Shaydulin Hu Maslov Clifford templates symbolic Pauli", "Quantum 5 580"),
]

NOVELTY = [
    ("N1", "structural ceiling quantum circuit optimization", "claim: structural ceiling terminology/framework"),
    ("N2", "gate ordering sensitivity quantum circuit compiler optimization", "claim: listing-model sensitivity"),
    ("N3", "quantum circuit optimization representation dependence peephole", "claim: representation determines reducibility"),
    ("N4", "peephole optimization quantum circuits review", "prior art context"),
    ("N5", "compiler phase ordering problem peephole classical", "classical analog"),
    ("N6", "predicting quantum circuit compilability structural features machine learning", "claim: structural prediction of headroom"),
    ("N7", "barren plateaus concentration of measure quantum", "stat-phys context"),
    ("N8", "identity insertion rewriting local optimization gate sequences", "claim: insertion sterility"),
    ("N9", "commutation rewriting quantum circuit optimization cancellation", "prior art on commutation-based rewriting"),
    ("N10", "data structure ordering affects optimizer performance sequences", "generic analog of listing sensitivity"),
]


def run_query(tag: str, query: str, prefix: str) -> list[dict]:
    out_csv = RESULTS / f"{prefix}_{tag}.csv"
    params = {"query": query, "file_path": str(out_csv), "num_results": 5, "hl": "en"}
    cmd = ["python3", "scripts/scholar_tool.py", "call",
           "--api-name", "scholar_search",
           "--params-json", json.dumps(params)]
    subprocess.run(cmd, cwd=SCHOLAR, capture_output=True, text=True, timeout=120)
    if not out_csv.exists():
        return []
    with open(out_csv, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    rows = []
    for tag, query, note in REFS3:
        try:
            results = run_query(tag, query, "ref3")
        except Exception as exc:  # noqa: BLE001
            rows.append({"tag": tag, "kind": "ref", "query": query,
                         "status": f"ERROR: {exc}"})
            continue
        tops = [(r.get("title", "")[:70], str(r.get("year", "")),
                 r.get("authors", "")[:50]) for r in results[:3]]
        status = " | ".join(f"{t} ({y}; {a})" for t, y, a in tops) if tops else "NO_RESULTS"
        rows.append({"tag": tag, "kind": "ref", "query": query,
                     "note": note, "status": status})
        print(f"[{tag:>3s}] {status[:160]}")
        time.sleep(1.0)

    for tag, query, note in NOVELTY:
        try:
            results = run_query(tag, query, "nov")
        except Exception as exc:  # noqa: BLE001
            rows.append({"tag": tag, "kind": "novelty", "query": query,
                         "status": f"ERROR: {exc}"})
            continue
        tops = [(r.get("title", "")[:70], str(r.get("year", ""))) for r in results[:4]]
        status = " | ".join(f"{t} ({y})" for t, y in tops) if tops else "NO_RESULTS"
        rows.append({"tag": tag, "kind": "novelty", "query": query,
                     "note": note, "status": status})
        print(f"[{tag:>3s}] {status[:160]}")
        time.sleep(1.0)

    out = HERE / "ref_verification_pass3.csv"
    tmp = HERE / "ref_verification_pass3.csv.tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["tag", "kind", "query", "note", "status"])
        w.writeheader()
        w.writerows(rows)
    tmp.replace(out)
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
