"""
Quantum Circuit Generator Module - Production Quality v2.1
===========================================================
Implements all 4 circuit families with full type hints, docstrings,
and error handling. Compatible with Qiskit 2.x.

Author: Q-research Team
Version: 2.1.0
"""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector
from typing import List, Tuple, Optional, Dict, Callable, Union, Any
import warnings
import hashlib
import json
from dataclasses import dataclass
from enum import Enum, auto

# Suppress specific deprecation warnings from Qiskit internals
warnings.filterwarnings('ignore', category=DeprecationWarning, module='qiskit')


# ============================================================================
# Data Structures
# ============================================================================

class CircuitFamily(Enum):
    """Supported circuit families."""
    CNOT_DIHEDRAL = auto()
    CLIFFORD = auto()
    UNIVERSAL = auto()
    STRUCTURED = auto()


class StructureType(Enum):
    """Structured circuit types."""
    BRICKWORK = auto()
    STAIRCASE = auto()
    TREE = auto()


@dataclass(frozen=True)
class CircuitConfig:
    """Immutable configuration for circuit generation."""
    n_qubits: int
    depth: int
    family: CircuitFamily
    seed: int = 42
    entanglement_density: float = 0.3
    structure_type: StructureType = StructureType.BRICKWORK
    gate_set: str = 'ht_rz_cnot'
    topology: str = 'nearest_neighbor'
    
    def __post_init__(self):
        if self.n_qubits < 1:
            raise ValueError(f"n_qubits must be >= 1, got {self.n_qubits}")
        if self.depth < 1:
            raise ValueError(f"depth must be >= 1, got {self.depth}")
        if not 0 <= self.entanglement_density <= 1:
            raise ValueError(f"entanglement_density must be in [0,1], got {self.entanglement_density}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'n_qubits': self.n_qubits,
            'depth': self.depth,
            'family': self.family.name,
            'seed': self.seed,
            'entanglement_density': self.entanglement_density,
            'structure_type': self.structure_type.name,
            'gate_set': self.gate_set,
            'topology': self.topology,
        }
    
    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'CircuitConfig':
        """Create from dictionary."""
        return cls(
            n_qubits=d['n_qubits'],
            depth=d['depth'],
            family=CircuitFamily[d['family']],
            seed=d.get('seed', 42),
            entanglement_density=d.get('entanglement_density', 0.3),
            structure_type=StructureType[d.get('structure_type', 'BRICKWORK')],
            gate_set=d.get('gate_set', 'ht_rz_cnot'),
            topology=d.get('topology', 'nearest_neighbor'),
        )


@dataclass
class CircuitMetrics:
    """Complete circuit metrics with validation."""
    gate_count: int = 0
    depth: int = 0
    two_qubit_gates: int = 0
    single_qubit_gates: int = 0
    entanglement_entropy: float = 0.0
    page_value: float = 0.0
    normalized_entropy: float = 0.0
    num_qubits: int = 0
    circuit_complexity: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'gate_count': self.gate_count,
            'depth': self.depth,
            'two_qubit_gates': self.two_qubit_gates,
            'single_qubit_gates': self.single_qubit_gates,
            'entanglement_entropy': self.entanglement_entropy,
            'page_value': self.page_value,
            'normalized_entropy': self.normalized_entropy,
            'num_qubits': self.num_qubits,
            'circuit_complexity': self.circuit_complexity,
        }


# ============================================================================
# Base Generator
# ============================================================================

class BaseCircuitGenerator:
    """Base class for all circuit generators."""
    
    def __init__(self, config: CircuitConfig):
        self.config = config
        self.rng = np.random.RandomState(config.seed)
    
    def generate(self) -> QuantumCircuit:
        """Generate a quantum circuit. Must be implemented by subclasses."""
        raise NotImplementedError
    
    def _create_register(self) -> QuantumCircuit:
        """Create a quantum circuit with the configured number of qubits."""
        return QuantumCircuit(self.config.n_qubits)
    
    def _apply_random_single_qubit(self, qc: QuantumCircuit, qubit: int) -> None:
        """Apply a random single-qubit gate."""
        gate = self.rng.choice(['h', 't', 'rz', 'rx', 'ry'])
        if gate == 'h':
            qc.h(qubit)
        elif gate == 't':
            qc.t(qubit)
        elif gate == 'rz':
            angle = self.rng.uniform(0, 2 * np.pi)
            qc.rz(angle, qubit)
        elif gate == 'rx':
            angle = self.rng.uniform(0, 2 * np.pi)
            qc.rx(angle, qubit)
        elif gate == 'ry':
            angle = self.rng.uniform(0, 2 * np.pi)
            qc.ry(angle, qubit)


# ============================================================================
# Circuit Family Generators
# ============================================================================

class CNOTDihedralGenerator(BaseCircuitGenerator):
    """
    CNOT-Dihedral circuit family.
    
    Generates circuits using the CNOT-Dihedral gate set (X, CX, Rz).
    These circuits are classically simulable but still exhibit interesting structure.
    """
    
    def generate(self) -> QuantumCircuit:
        """Generate a CNOT-Dihedral circuit."""
        qc = self._create_register()
        n = self.config.n_qubits
        d = self.config.depth
        
        for layer in range(d):
            for qubit in range(n):
                if self.rng.random() < 0.5:
                    qc.x(qubit)
                if self.rng.random() < 0.5:
                    angle = self.rng.choice([0, np.pi/2, np.pi, 3*np.pi/2])
                    qc.rz(angle, qubit)
            
            # Add CNOTs
            for qubit in range(n - 1):
                if self.rng.random() < self.config.entanglement_density:
                    qc.cx(qubit, qubit + 1)
        
        return qc


class CliffordGenerator(BaseCircuitGenerator):
    """
    Clifford circuit family.
    
    Generates circuits using the Clifford gate set (H, S, CNOT).
    These circuits are classically simulable via the Gottesman-Knill theorem.
    """
    
    def generate(self) -> QuantumCircuit:
        """Generate a Clifford circuit."""
        qc = self._create_register()
        n = self.config.n_qubits
        d = self.config.depth
        
        for layer in range(d):
            for qubit in range(n):
                gate = self.rng.choice(['h', 's', 'i'])
                if gate == 'h':
                    qc.h(qubit)
                elif gate == 's':
                    qc.s(qubit)
            
            # Add CNOTs
            for qubit in range(n - 1):
                if self.rng.random() < self.config.entanglement_density:
                    qc.cx(qubit, qubit + 1)
        
        return qc


class UniversalGenerator(BaseCircuitGenerator):
    """
    Universal circuit family.
    
    Generates circuits using a universal gate set (H, T, Rz, Rx, Ry, CNOT).
    These circuits can represent any quantum computation.
    """
    
    def generate(self) -> QuantumCircuit:
        """Generate a universal circuit."""
        qc = self._create_register()
        n = self.config.n_qubits
        d = self.config.depth
        
        single_qubit_gates = ['h', 't', 'rz', 'rx', 'ry']
        
        for layer in range(d):
            for qubit in range(n):
                if (self.rng.random() < self.config.entanglement_density and 
                    qubit < n - 1):
                    qc.cx(qubit, qubit + 1)
                else:
                    gate = self.rng.choice(single_qubit_gates)
                    angle = self.rng.uniform(0, 2 * np.pi)
                    
                    if gate == 'h':
                        qc.h(qubit)
                    elif gate == 't':
                        qc.t(qubit)
                    elif gate == 'rz':
                        qc.rz(angle, qubit)
                    elif gate == 'rx':
                        qc.rx(angle, qubit)
                    elif gate == 'ry':
                        qc.ry(angle, qubit)
        
        return qc


class StructuredGenerator(BaseCircuitGenerator):
    """
    Structured circuit family.
    
    Generates circuits with specific connectivity patterns:
    - brickwork: Alternating CNOT layers
    - staircase: Progressive entanglement
    - tree: Hierarchical entanglement
    """
    
    def generate(self) -> QuantumCircuit:
        """Generate a structured circuit."""
        if self.config.structure_type == StructureType.BRICKWORK:
            return self._brickwork()
        elif self.config.structure_type == StructureType.STAIRCASE:
            return self._staircase()
        elif self.config.structure_type == StructureType.TREE:
            return self._tree()
        else:
            raise ValueError(f"Unknown structure type: {self.config.structure_type}")
    
    def _brickwork(self) -> QuantumCircuit:
        """Generate brickwork pattern circuit."""
        qc = self._create_register()
        n = self.config.n_qubits
        d = self.config.depth
        
        for layer in range(d):
            if layer % 2 == 0:
                for qubit in range(0, n - 1, 2):
                    qc.cx(qubit, qubit + 1)
            else:
                for qubit in range(1, n - 1, 2):
                    qc.cx(qubit, qubit + 1)
            
            # Add rotation gates
            for qubit in range(n):
                angle = self.rng.uniform(0, 2 * np.pi)
                qc.rz(angle, qubit)
        
        return qc
    
    def _staircase(self) -> QuantumCircuit:
        """Generate staircase pattern circuit."""
        qc = self._create_register()
        n = self.config.n_qubits
        d = self.config.depth
        
        for layer in range(d):
            for qubit in range(min(layer + 1, n)):
                angle = self.rng.uniform(0, 2 * np.pi)
                qc.rz(angle, qubit)
                if qubit < n - 1 and qubit < layer:
                    qc.cx(qubit, qubit + 1)
        
        return qc
    
    def _tree(self) -> QuantumCircuit:
        """Generate tree pattern circuit."""
        qc = self._create_register()
        n = self.config.n_qubits
        d = self.config.depth
        
        current_layer = list(range(n))
        
        for _ in range(d):
            next_layer = []
            for i in range(0, len(current_layer) - 1, 2):
                q1, q2 = current_layer[i], current_layer[i + 1]
                qc.cx(q1, q2)
                next_layer.append(q1)
            
            for qubit in current_layer:
                angle = self.rng.uniform(0, 2 * np.pi)
                qc.rz(angle, qubit)
            
            current_layer = next_layer if next_layer else [0]
        
        return qc


# ============================================================================
# Factory Function
# ============================================================================

def create_generator(config: CircuitConfig) -> BaseCircuitGenerator:
    """Create a circuit generator based on configuration."""
    generators = {
        CircuitFamily.CNOT_DIHEDRAL: CNOTDihedralGenerator,
        CircuitFamily.CLIFFORD: CliffordGenerator,
        CircuitFamily.UNIVERSAL: UniversalGenerator,
        CircuitFamily.STRUCTURED: StructuredGenerator,
    }
    
    if config.family not in generators:
        raise ValueError(f"Unknown circuit family: {config.family}")
    
    return generators[config.family](config)


def generate_circuit(n_qubits: int, depth: int, seed: int = 42,
                     family: CircuitFamily = CircuitFamily.UNIVERSAL,
                     entanglement_density: float = 0.3,
                     structure_type: StructureType = StructureType.BRICKWORK,
                     gate_set: str = 'ht_rz_cnot',
                     topology: str = 'nearest_neighbor') -> QuantumCircuit:
    """Generate a single circuit using the v2 configuration API."""
    config = CircuitConfig(
        n_qubits=n_qubits,
        depth=depth,
        family=family,
        seed=seed,
        entanglement_density=entanglement_density,
        structure_type=structure_type,
        gate_set=gate_set,
        topology=topology,
    )
    return create_generator(config).generate()


def generate_circuit_batch(config: CircuitConfig, n_circuits: int,
                           metrics_calculator: Optional['MetricsCalculator'] = None) -> List[Tuple[QuantumCircuit, CircuitMetrics]]:
    """Generate a batch of circuits with metrics."""
    generator = create_generator(config)
    
    if metrics_calculator is None:
        metrics_calculator = MetricsCalculator()
    
    results = []
    for i in range(n_circuits):
        # Update seed for each circuit
        circuit_config = CircuitConfig(
            n_qubits=config.n_qubits,
            depth=config.depth,
            family=config.family,
            seed=config.seed + i,
            entanglement_density=config.entanglement_density,
            structure_type=config.structure_type,
        )
        gen = create_generator(circuit_config)
        circuit = gen.generate()
        metrics = metrics_calculator.calculate(circuit)
        results.append((circuit, metrics))
    
    return results


# ============================================================================
# Metrics Calculator
# ============================================================================

class MetricsCalculator:
    """Calculate circuit metrics with caching."""
    
    def __init__(self, max_cache_size: int = 4096):
        self._cache: Dict[str, CircuitMetrics] = {}
        self._max_cache_size = max_cache_size
    
    def calculate(self, circuit: QuantumCircuit) -> CircuitMetrics:
        """Calculate all metrics for a circuit."""
        # Use circuit hash as cache key
        cache_key = self._circuit_hash(circuit)
        
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        metrics = CircuitMetrics()
        metrics.gate_count = circuit.size()
        metrics.depth = circuit.depth()
        metrics.num_qubits = circuit.num_qubits
        metrics.two_qubit_gates = self._count_two_qubit_gates(circuit)
        metrics.single_qubit_gates = metrics.gate_count - metrics.two_qubit_gates
        metrics.entanglement_entropy = self._calculate_entanglement_entropy(circuit)
        metrics.page_value = self._calculate_page_value(circuit.num_qubits)
        metrics.normalized_entropy = (metrics.entanglement_entropy / metrics.page_value 
                                      if metrics.page_value > 0 else 0.0)
        metrics.circuit_complexity = self._calculate_complexity(circuit)
        
        if len(self._cache) >= self._max_cache_size:
            self._cache.pop(next(iter(self._cache)))
        self._cache[cache_key] = metrics
        return metrics
    
    def _circuit_hash(self, circuit: QuantumCircuit) -> str:
        """Generate a hash for the circuit."""
        instructions = []
        for inst in circuit.data:
            qubits = tuple(circuit.find_bit(q).index for q in inst.qubits)
            clbits = tuple(circuit.find_bit(c).index for c in inst.clbits)
            params = tuple(float(p) if isinstance(p, (int, float, np.floating)) else str(p)
                           for p in inst.operation.params)
            instructions.append((inst.operation.name, qubits, clbits, params))

        payload = {
            'num_qubits': circuit.num_qubits,
            'num_clbits': circuit.num_clbits,
            'instructions': instructions,
        }
        data = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(data.encode()).hexdigest()
    
    def _count_two_qubit_gates(self, circuit: QuantumCircuit) -> int:
        """Count two-qubit gates in circuit."""
        count = 0
        for instruction in circuit.data:
            if instruction.operation.num_qubits == 2:
                count += 1
        return count
    
    def _calculate_entanglement_entropy(self, circuit: QuantumCircuit) -> float:
        """Calculate von Neumann entanglement entropy for bipartition."""
        try:
            n = circuit.num_qubits
            if n < 2:
                return 0.0
            
            sv = Statevector.from_label('0' * n)
            sv = sv.evolve(circuit)
            
            # Bipartition: first n//2 qubits vs rest
            n_half = n // 2
            
            # Reshape to matrix form for bipartition
            dims_A = [2] * n_half
            dims_B = [2] * (n - n_half)
            
            # Use partial trace via statevector
            sv_array = np.array(sv.data)
            reshaped = sv_array.reshape([2] * n)
            
            # Trace out B subsystem
            # Contract indices for B
            axes = list(range(n_half, n))
            rho_A = np.tensordot(reshaped, reshaped.conj(), 
                                axes=(axes, axes))
            
            # Reshape to matrix
            dim_A = 2 ** n_half
            rho_A = rho_A.reshape(dim_A, dim_A)
            
            # Calculate entropy
            eigenvalues = np.linalg.eigvalsh(rho_A)
            eigenvalues = eigenvalues[eigenvalues > 1e-10]
            entropy = -np.sum(eigenvalues * np.log2(eigenvalues))
            
            return float(entropy)
        except Exception as e:
            warnings.warn(f"Failed to calculate entanglement entropy: {e}")
            return 0.0
    
    def _calculate_page_value(self, n_qubits: int) -> float:
        """Calculate Page value for entanglement entropy."""
        if n_qubits < 2:
            return 0.0
        n_half = n_qubits // 2
        n_rest = n_qubits - n_half
        dim_A = 2 ** n_half
        dim_B = 2 ** n_rest
        
        # Page value: approximately min(n_half, n_rest) for large systems
        # More precise formula for Haar-random states
        if dim_A <= dim_B:
            page = (np.log2(dim_A) - dim_A / (2 * dim_B)) 
        else:
            page = (np.log2(dim_B) - dim_B / (2 * dim_A))
        
        return float(page)
    
    def _calculate_complexity(self, circuit: QuantumCircuit) -> float:
        """Calculate circuit complexity measure."""
        n = circuit.num_qubits
        d = circuit.depth()
        g = circuit.size()
        return np.log2(g + 1) * d / n if n > 0 else 0.0
