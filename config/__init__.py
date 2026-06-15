"""Configuration package.

Exposes :func:`get_config`, a small factory that selects the proper
configuration class from the ``FLASK_ENV`` environment variable.
"""
from .config import (
    Config,
    DevelopmentConfig,
    TestingConfig,
    ProductionConfig,
    get_config,
)

__all__ = [
    "Config",
    "DevelopmentConfig",
    "TestingConfig",
    "ProductionConfig",
    "get_config",
]
