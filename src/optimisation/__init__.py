"""Quantum circuit optimization package."""
from .base import BaseOptimizer, OptimizationResult, OptimizerType, MoveType
from .phase1 import (
    GreedyGateCancellation,
    RandomLocalSearch,
    SimulatedAnnealingOptimizer,
    GeneticAlgorithmOptimizer,
)
from .phase2 import (
    Phase2aCommutationRewriter,
    HybridPhase2aRewrite,
    CommutationRewriter,
    HybridCommuteRewrite,
    Phase2bTemplateMatcher,
)
from .ceiling_aware import CeilingAwareOptimizer, count_phase1_actions, count_phase2_actions


def create_optimizer(optimizer_type: str, **kwargs) -> BaseOptimizer:
    """Factory function to create optimizers by type name.

    Args:
        optimizer_type: One of 'greedy', 'rls', 'sa', 'ga', 'commutation', 'hybrid', 'template', 'ceiling_aware'
        **kwargs: Optimizer-specific parameters

    Returns:
        Configured optimizer instance

    Raises:
        ValueError: If optimizer_type is not recognized
    """
    if optimizer_type == "greedy":
        return GreedyGateCancellation(**kwargs)
    elif optimizer_type == "rls":
        return RandomLocalSearch(**kwargs)
    elif optimizer_type == "sa":
        return SimulatedAnnealingOptimizer(**kwargs)
    elif optimizer_type == "ga":
        return GeneticAlgorithmOptimizer(**kwargs)
    elif optimizer_type == "commutation":
        return Phase2aCommutationRewriter(**kwargs)
    elif optimizer_type == "hybrid":
        return HybridPhase2aRewrite(**kwargs)
    elif optimizer_type == "template":
        return Phase2bTemplateMatcher(**kwargs)
    elif optimizer_type == "ceiling_aware":
        return CeilingAwareOptimizer(**kwargs)
    else:
        raise ValueError(f"Unknown optimizer type: {optimizer_type}. "
                         f"Valid types: greedy, rls, sa, ga, commutation, hybrid, template, ceiling_aware")


__all__ = [
    'BaseOptimizer',
    'OptimizationResult',
    'OptimizerType',
    'MoveType',
    'GreedyGateCancellation',
    'RandomLocalSearch',
    'SimulatedAnnealingOptimizer',
    'GeneticAlgorithmOptimizer',
    'Phase2aCommutationRewriter',
    'HybridPhase2aRewrite',
    'CommutationRewriter',
    'HybridCommuteRewrite',
    'Phase2bTemplateMatcher',
    'CeilingAwareOptimizer',
    'count_phase1_actions',
    'count_phase2_actions',
    'create_optimizer',
]
