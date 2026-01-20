"""Base factory class for creating pipeline components."""

from typing import Any, Dict, List, Type, TypeVar

from app.components.base.component import BaseComponent

T = TypeVar("T", bound=BaseComponent)


class ComponentNotFoundError(Exception):
    """Raised when a component is not found in the registry."""

    def __init__(self, name: str, category: str, available: List[str] = None):
        self.name = name
        self.category = category
        self.available = available or []
        available_str = ", ".join(self.available) if self.available else "none"
        super().__init__(
            f"Component '{name}' not found in category '{category}'. "
            f"Available: {available_str}"
        )


class BaseFactory:
    """Abstract base factory for creating pipeline components.

    Each component category (parsers, chunkers, etc.) has its own factory
    that inherits from this class.
    """

    category: str = ""
    _registry: Dict[str, Type[BaseComponent]] = {}

    @classmethod
    def register(cls, name: str, component_class: Type[T]) -> None:
        """Register a component class with the factory.

        Args:
            name: Unique name for the component
            component_class: The component class to register
        """
        cls._registry[name] = component_class

    @classmethod
    def unregister(cls, name: str) -> None:
        """Unregister a component from the factory.

        Args:
            name: Name of the component to remove
        """
        cls._registry.pop(name, None)

    @classmethod
    def create(cls, name: str, **kwargs) -> BaseComponent:
        """Factory method to create a component instance.

        Args:
            name: Name of the component to create
            **kwargs: Arguments to pass to the component constructor

        Returns:
            Instance of the requested component

        Raises:
            ComponentNotFoundError: If the component is not registered
        """
        if name not in cls._registry:
            raise ComponentNotFoundError(
                name=name,
                category=cls.category,
                available=list(cls._registry.keys()),
            )
        return cls._registry[name](**kwargs)

    @classmethod
    def get(cls, name: str) -> Type[BaseComponent]:
        """Get a component class without instantiating it.

        Args:
            name: Name of the component

        Returns:
            The component class

        Raises:
            ComponentNotFoundError: If the component is not registered
        """
        if name not in cls._registry:
            raise ComponentNotFoundError(
                name=name,
                category=cls.category,
                available=list(cls._registry.keys()),
            )
        return cls._registry[name]

    @classmethod
    def list_available(cls) -> List[Dict[str, Any]]:
        """List all available components in this factory.

        Returns:
            List of component info dictionaries
        """
        result = []
        for name, component_class in cls._registry.items():
            # Create a temporary instance to get metadata
            instance = component_class()
            result.append(instance.to_dict())
        return result

    @classmethod
    def get_component_info(cls, name: str) -> Dict[str, Any]:
        """Get detailed information about a component.

        Args:
            name: Name of the component

        Returns:
            Dictionary with component information

        Raises:
            ComponentNotFoundError: If the component is not registered
        """
        if name not in cls._registry:
            raise ComponentNotFoundError(
                name=name,
                category=cls.category,
                available=list(cls._registry.keys()),
            )
        instance = cls._registry[name]()
        return instance.to_dict()

    @classmethod
    def has(cls, name: str) -> bool:
        """Check if a component is registered.

        Args:
            name: Name of the component

        Returns:
            True if the component exists, False otherwise
        """
        return name in cls._registry

    @classmethod
    def list_names(cls) -> List[str]:
        """List all registered component names.

        Returns:
            List of component names
        """
        return list(cls._registry.keys())
