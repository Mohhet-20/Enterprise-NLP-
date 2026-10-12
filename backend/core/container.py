"""
Minimal dependency-injection container.

FastAPI's `Depends` already gives us DI at the request layer; this container
exists for the *service/repository wiring* that sits behind the API — i.e.
"which concrete Repository implementation does InferenceService get handed".

Kept intentionally simple (no magic, no reflection-based auto-wiring) so it
stays readable as the platform grows. Swap for `dependency-injector` or
similar later if the wiring graph gets large enough to need it.
"""

from typing import Callable, Dict, Type, TypeVar

T = TypeVar("T")


class Container:
    """A tiny registry mapping an interface (or key) to a factory function."""

    def __init__(self) -> None:
        self._factories: Dict[type, Callable] = {}
        self._singletons: Dict[type, object] = {}

    def register(self, interface: Type[T], factory: Callable[[], T], *, singleton: bool = False) -> None:
        self._factories[interface] = (factory, singleton)

    def resolve(self, interface: Type[T]) -> T:
        if interface not in self._factories:
            raise KeyError(
                f"No factory registered for {interface!r}. "
                f"Did you forget to call container.register(...) at startup?"
            )
        factory, singleton = self._factories[interface]
        if singleton:
            if interface not in self._singletons:
                self._singletons[interface] = factory()
            return self._singletons[interface]  # type: ignore[return-value]
        return factory()


# Process-wide container instance. Populated in backend/main.py at startup.
container = Container()
