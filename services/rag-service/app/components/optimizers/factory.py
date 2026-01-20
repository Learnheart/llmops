"""Optimizer factory for creating search result optimizers."""

from typing import Dict, List, Type

from app.components.base.factory import BaseFactory
from app.components.base.registry import ComponentRegistry
from app.components.optimizers.base import BaseOptimizer


class OptimizerFactory(BaseFactory):
    """Factory for creating optimizer instances."""

    category: str = "optimizers"
    _registry: Dict[str, Type[BaseOptimizer]] = {}

    @classmethod
    def create_chain(cls, configs: List[Dict]) -> List[BaseOptimizer]:
        """Create a chain of optimizers from configuration.

        Args:
            configs: List of optimizer configurations with 'type' field

        Returns:
            List of optimizer instances sorted by order
        """
        optimizers = []

        for config in configs:
            opt_type = config.get("type")
            if not opt_type:
                continue

            # Create optimizer with config
            optimizer = cls.create(opt_type)
            optimizers.append((optimizer, config))

        # Sort by order
        optimizers.sort(key=lambda x: x[0].order)

        return optimizers


# Register the factory with the central registry
ComponentRegistry.register_factory("optimizers", OptimizerFactory)
