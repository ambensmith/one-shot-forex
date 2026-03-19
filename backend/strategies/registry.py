"""Auto-discovers strategy files in this package."""

from __future__ import annotations

import importlib
import logging
import pkgutil
from typing import Type

from backend.strategies.base import Strategy

logger = logging.getLogger("forex_sentinel.strategies")

_registry: dict[str, Type[Strategy]] = {}


def discover_strategies() -> dict[str, Type[Strategy]]:
    """Auto-discover all Strategy subclasses in backend.strategies."""
    if _registry:
        return _registry

    import backend.strategies as pkg
    for importer, modname, ispkg in pkgutil.iter_modules(pkg.__path__):
        if modname in ("base", "registry", "__init__"):
            continue
        try:
            module = importlib.import_module(f"backend.strategies.{modname}")
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and issubclass(attr, Strategy)
                        and attr is not Strategy):
                    instance = attr()
                    _registry[instance.name] = type(instance)
                    logger.debug(f"Registered strategy: {instance.name}")
        except Exception as e:
            logger.warning(f"Failed to load strategy module {modname}: {e}")

    return _registry


def get_strategy(name: str, params: dict | None = None) -> Strategy:
    """Get a strategy instance by name with optional parameter overrides."""
    strategies = discover_strategies()
    if name not in strategies:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(strategies.keys())}")
    instance = strategies[name]()
    if params:
        instance.set_parameters(params)
    return instance
