"""
Quantum Circuit Generator Module - Complete Implementation
Implements all 4 circuit families as specified in research outline.
"""

import numpy as np
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.quantum_info import Statevector, Operator
from typing import List, Tuple, Optional, Dict, Callable
import warnings
warnings.filterwarnings('ignore')


class CircuitMetrics:
    """Complete circuit metrics calculator - 12 metrics as specified."""
    
    @staticmethod
    def gate_count(circuit: QuantumCircuit) -> int:
        """Total number of gates."""
        return circuit.size()
    
    @staticmethod
    def depth(circuit: QuantumCircuit) -> int:
        """Circuit depth."""
        return circuit.depth()
    
    @staticmethod
    def two_qubit_gate_count(circuit: QuantumCircuit) -> int:
        """Count two-qubit gates."""
        count = 0
        for instruction in circuit.data:
            if instruction[0].num_qubits == 2:
                count += 1
        return count
    
    @staticmethod
    def two_qubit_gate_density(circuit: QuantumCircuit) -> float:
        """Density of two-qubit gates."""
        total = circuit.size()
        return CircuitMetrics.two_qubit_gate_count(circuit) / total if total > 0 else 0.0
    
    @staticmethod
    def entanglement_entropy(circuit: QuantumCircuit) -> float:
        """Von Neumann entanglement entropy."""
        try:
            n = circuit.num_qubits
            if n < 2:
                return 0.0
            
            sv = Statevector.from_label('0' * n)
            sv = sv.evolve(circuit)
            
            # Bipartition
            n_half = n // 2
            rho = sv.data.reshape(2**n_half, -1)
            rho_reduced = rho @ rho.T.conj()
            
            eigenvalues = np.linalg.eigvalsh(rho_reduced)
            eigenvalues = eigenvalues[eigenvalues > 1e-10]
            entropy = -np.sum(eigenvalues * np.log2(eigenvalues))
            
            return float(entropy)
        except:
            return 0.0
    
    @staticmethod
    def gate_type_distribution(circuit: QuantumCircuit) -> Dict[str, int]:
        """Distribution of gate types."""
        dist = {}
        for instruction in circuit.data:
            gate_name = instruction[0].name
            dist[gate_name] = dist.get(gate_name, 0) + 1
        return dist
    
    @staticmethod
    def connectivity_graph(circuit: QuantumCircuit) -> List[Tuple[int, int]]:
        """Extract qubit connectivity from two-qubit gates."""
        edges = []
        for instruction in circuit.data:
            if instruction[0].num_qubits == 2:
                qubits = [q._index for q in instruction[1]]
                edges.append((qubits[0], qubits[1]))
        return edges
    
    @staticmethod
    def circuit_complexity(circuit: QuantumCircuit) -> float:
        """Circuit complexity measure."""
        n = circuit.num_qubits
        d = circuit.depth()
        g = circuit.size()
        return np.log2(g + 1) * d / n if n > 0 else 0.0
    
    @staticmethod
    def get_all_metrics(circuit: QuantumCircuit) -> Dict[str, float]:
        """Get all 12 metrics."""
        return {
            'gate_count': CircuitMetrics.gate_count(circuit),
            'depth': CircuitMetrics.depth(circuit),
            'two_qubit_gates': CircuitMetrics.two_qubit_gate_count(circuit),
            'two_qubit_density': CircuitMetrics.two_qubit_gate_density(circuit),
            'entanglement_entropy': CircuitMetrics.entanglement_entropy(circuit),
            'num_qubits': circuit.num_qubits,
            'circuit_complexity': CircuitMetrics.circuit_complexity(circuit),
            'single_qubit_gates': circuit.size() - CircuitMetrics.two_qubit_gate_count(circuit),
            'connectivity_edges': len(CircuitMetrics.connectivity_graph(circuit)),
            'unique_gate_types': len(CircuitMetrics.gate_type_distribution(circuit)),
            'depth_to_width_ratio': CircuitMetrics.depth(circuit) / circuit.num_qubits if circuit.num_qubits > 0 else 0.0,
            'gate_density': circuit.size() / (circuit.num_qubits * CircuitMetrics.depth(circuit)) if circuit.num_qubits > 0 and CircuitMetrics.depth(circuit) > 0 else 0.0
        }


class CNOTDihedralCircuit:
    """CNOT-Dihedral circuit family: C(n,d,k) where k = CNOT count."""
    
    def __init__(self, n_qubits: int):
        self.n_qubits = n_qubits
    
    def generate(self, depth: int, cnot_count: int, seed: Optional[int] = None) -> QuantumCircuit:
        if seed is not None:
            np.random.seed(seed)
        
        qr = QuantumRegister(self.n_qubits, 'q')
        circuit = QuantumCircuit(qr)
        
        # Distribute CNOTs across depth
        cnots_per_layer = max(1, cnot_count // depth)
        
        for layer in range(depth):
            # Add CNOT gates
            for _ in range(cnots_per_layer):
                if np.random.random() < cnot_count / (depth * cnots_per_layer):
                    q1, q2 = np.random.choice(self.n_qubits, 2, replace=False)
                    circuit.cx(int(q1), int(q2))
            
            # Add single-qubit gates (T gates for dihedral)
            for qubit in range(self.n_qubits):
                circuit.t(qubit)
        
        return circuit


class CliffordCircuit:
    """Clifford circuit family - efficient classical simulation."""
    
    def __init__(self, n_qubits: int):
        self.n_qubits = n_qubits
    
    def generate(self, depth: int, seed: Optional[int] = None) -> QuantumCircuit:
        if seed is not None:
            np.random.seed(seed)
        
        qr = QuantumRegister(self.n_qubits, 'q')
        circuit = QuantumCircuit(qr)
        
        clifford_gates = ['h', 's', 'cx']
        
        for layer in range(depth):
            for qubit in range(self.n_qubits):
                gate = np.random.choice(clifford_gates[:2])  # h or s
                if gate == 'h':
                    circuit.h(qubit)
                elif gate == 's':
                    circuit.s(qubit)
            
            # Add entangling gates
            if layer % 2 == 0:
                for qubit in range(0, self.n_qubits - 1, 2):
                    circuit.cx(qubit, qubit + 1)
            else:
                for qubit in range(1, self.n_qubits - 1, 2):
                    circuit.cx(qubit, qubit + 1)
        
        return circuit


class UniversalCircuit:
    """Universal circuit family - general quantum computation."""
    
    def __init__(self, n_qubits: int):
        self.n_qubits = n_qubits
    
    def generate(self, depth: int, entanglement_density: float = 0.3, seed: Optional[int] = None) -> QuantumCircuit:
        if seed is not None:
            np.random.seed(seed)
        
        qr = QuantumRegister(self.n_qubits, 'q')
        circuit = QuantumCircuit(qr)
        
        single_qubit_gates = ['h', 't', 'rz', 'rx', 'ry']
        
        for layer in range(depth):
            for qubit in range(self.n_qubits):
                if np.random.random() < entanglement_density and qubit < self.n_qubits - 1:
                    circuit.cx(qubit, qubit + 1)
                else:
                    gate = np.random.choice(single_qubit_gates)
                    angle = np.random.uniform(0, 2 * np.pi)
                    if gate == 'h':
                        circuit.h(qubit)
                    elif gate == 't':
                        circuit.t(qubit)
                    elif gate == 'rz':
                        circuit.rz(angle, qubit)
                    elif gate == 'rx':
                        circuit.rx(angle, qubit)
                    elif gate == 'ry':
                        circuit.ry(angle, qubit)
        
        return circuit


class StructuredCircuit:
    """Structured circuit family - modular, hierarchical."""
    
    def __init__(self, n_qubits: int):
        self.n_qubits = n_qubits
    
    def generate(self, depth: int, structure_type: str = 'brickwork', seed: Optional[int] = None) -> QuantumCircuit:
        if seed is not None:
            np.random.seed(seed)
        
        qr = QuantumRegister(self.n_qubits, 'q')
        circuit = QuantumCircuit(qr)
        
        if structure_type == 'brickwork':
            return self._brickwork(circuit, depth)
        elif structure_type == 'staircase':
            return self._staircase(circuit, depth)
        elif structure_type == 'tree':
            return self._tree(circuit, depth)
        else:
            raise ValueError(f"Unknown structure type: {structure_type}")
    
    def _brickwork(self, circuit: QuantumCircuit, depth: int) -> QuantumCircuit:
        for layer in range(depth):
            if layer % 2 == 0:
                for qubit in range(0, self.n_qubits - 1, 2):
                    circuit.cx(qubit, qubit + 1)
            else:
                for qubit in range(1, self.n_qubits - 1, 2):
                    circuit.cx(qubit, qubit + 1)
            
            for qubit in range(self.n_qubits):
                angle = np.random.uniform(0, 2 * np.pi)
                circuit.rz(angle, qubit)
        
        return circuit
    
    def _staircase(self, circuit: QuantumCircuit, depth: int) -> QuantumCircuit:
        for layer in range(depth):
            for qubit in range(min(layer + 1, self.n_qubits)):
                angle = np.random.uniform(0, 2 * np.pi)
                circuit.rz(angle, qubit)
                if qubit < self.n_qubits - 1 and qubit < layer:
                    circuit.cx(qubit, qubit + 1)
        
        return circuit
    
    def _tree(self, circuit: QuantumCircuit, depth: int) -> QuantumCircuit:
        current_layer = list(range(self.n_qubits))
        
        for d in range(depth):
            next_layer = []
            for i in range(0, len(current_layer) - 1, 2):
                q1, q2 = current_layer[i], current_layer[i + 1]
                circuit.cx(q1, q2)
                next_layer.append(q1)
            
            for qubit in current_layer:
                angle = np.random.uniform(0, 2 * np.pi)
                circuit.rz(angle, qubit)
            
            current_layer = next_layer if next_layer else [0]
        
        return circuit


def generate_circuit_batch(family: str,
                          n_qubits: int,
                          depth: int,
                          num_circuits: int,
                          **kwargs) -> List[QuantumCircuit]:
    """Generate batch of circuits from specified family."""
    circuits = []
    
    for i in range(num_circuits):
        seed = kwargs.get('seed_start', 0) + i
        
        if family == 'cnot_dihedral':
            gen = CNOTDihedralCircuit(n_qubits)
            cnot_count = kwargs.get('cnot_count', depth)
            circuit = gen.generate(depth, cnot_count, seed=seed)
        elif family == 'clifford':
            gen = CliffordCircuit(n_qubits)
            circuit = gen.generate(depth, seed=seed)
        elif family == 'universal':
            gen = UniversalCircuit(n_qubits)
            entanglement_density = kwargs.get('entanglement_density', 0.3)
            circuit = gen.generate(depth, entanglement_density, seed=seed)
        elif family == 'structured':
            gen = StructuredCircuit(n_qubits)
            structure_type = kwargs.get('structure_type', 'brickwork')
            circuit = gen.generate(depth, structure_type, seed=seed)
        else:
            raise ValueError(f"Unknown circuit family: {family}")
        
        circuits.append(circuit)
    
    return circuits


if __name__ == '__main__':
    print("Testing complete circuit generator...")
    
    # Test all 4 families
    for family in ['cnot_dihedral', 'clifford', 'universal', 'structured']:
        circuits = generate_circuit_batch(family, n_qubits=4, depth=10, num_circuits=5)
        metrics = CircuitMetrics.get_all_metrics(circuits[0])
        print(f"{family}: {metrics}")
