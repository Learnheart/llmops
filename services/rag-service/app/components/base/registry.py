"""Central registry for all RAG pipeline components."""

from typing import Any, Dict, List, Type

from app.components.base.component import BaseComponent
from app.components.base.factory import BaseFactory


class ComponentRegistry:
    """Central registry for all component factories.

    Provides a unified interface to discover and access all registered
    components across all categories (parsers, chunkers, embedders, etc.).
    """

    _factories: Dict[str, Type[BaseFactory]] = {}

    @classmethod
    def register_factory(cls, category: str, factory: Type[BaseFactory]) -> None:
        """Register a component factory.

        Args:
            category: Category name (e.g., 'parsers', 'chunkers')
            factory: The factory class for this category
        """
        cls._factories[category] = factory

    @classmethod
    def get_factory(cls, category: str) -> Type[BaseFactory]:
        """Get a factory by category.

        Args:
            category: Category name

        Returns:
            The factory class for this category

        Raises:
            KeyError: If the category is not registered
        """
        if category not in cls._factories:
            raise KeyError(f"Factory for category '{category}' not found. "
                           f"Available: {list(cls._factories.keys())}")
        return cls._factories[category]

    @classmethod
    def list_categories(cls) -> List[str]:
        """List all registered component categories.

        Returns:
            List of category names
        """
        return list(cls._factories.keys())

    @classmethod
    def list_components(cls, category: str) -> List[str]:
        """List component names in a specific category.

        Args:
            category: Category name

        Returns:
            List of component names in the category
        """
        factory = cls.get_factory(category)
        return factory.list_names()

    @classmethod
    def get_all_components(cls) -> Dict[str, List[Dict[str, Any]]]:
        """Get all components grouped by category.

        Returns:
            Dictionary mapping category names to lists of component info
        """
        result = {}
        for category, factory in cls._factories.items():
            result[category] = factory.list_available()
        return result

    @classmethod
    def get_component_info(cls, category: str, name: str) -> Dict[str, Any]:
        """Get information about a specific component.

        Args:
            category: Category name
            name: Component name

        Returns:
            Dictionary with component information
        """
        factory = cls.get_factory(category)
        return factory.get_component_info(name)

    @classmethod
    def create_component(cls, category: str, name: str, **kwargs) -> BaseComponent:
        """Create a component instance.

        Args:
            category: Category name
            name: Component name
            **kwargs: Arguments to pass to the component constructor

        Returns:
            Instance of the requested component
        """
        factory = cls.get_factory(category)
        return factory.create(name, **kwargs)

    @classmethod
    def has_component(cls, category: str, name: str) -> bool:
        """Check if a component exists.

        Args:
            category: Category name
            name: Component name

        Returns:
            True if the component exists, False otherwise
        """
        if category not in cls._factories:
            return False
        factory = cls._factories[category]
        return factory.has(name)
