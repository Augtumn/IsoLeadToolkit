"""Plugin API — abstract interfaces, metadata, and error types."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class PluginMeta:
    """Plugin metadata descriptor."""
    name: str
    version: str
    api_version: str = "1.0"
    plugin_type: str = ""
    author: str = ""
    description: str = ""
    source: str = "builtin"        # "builtin" | "user" | "third_party"
    signature: str = ""             # optional integrity hash
    restricted: bool = False        # True = limited API access


class PluginError(Exception):
    """Base error for plugin operations."""


class PluginLoadError(PluginError):
    """Raised when a plugin cannot be loaded."""


class PluginValidationError(PluginError):
    """Raised when a plugin fails validation."""


@runtime_checkable
class BasePlugin(Protocol):
    """Minimal plugin interface — all plugins must implement this."""
    meta: PluginMeta

    def validate_environment(self) -> tuple[bool, str]:
        """Check dependencies/env. Returns (ok, message)."""
        ...

    def get_default_params(self) -> dict[str, Any]:
        """Return default parameter dict."""
        ...

    def build_ui(self, parent: Any = None, callback: Any = None) -> Any | None:
        """Optional: return a QWidget section for the analysis panel.
        If None, this plugin does not provide panel UI."""
        ...


@runtime_checkable
class MLClassifierPlugin(BasePlugin, Protocol):
    """Supervised classification plugin interface."""
    def fit(self, x: Any, y: Any, **params: Any) -> dict[str, Any]:
        """Train model. Returns training metadata."""
        ...

    def predict(self, x: Any) -> Any:
        """Predict class labels."""
        ...

    def predict_proba(self, x: Any) -> Any:
        """Predict class probabilities."""
        ...


@runtime_checkable
class EmbeddingPlugin(BasePlugin, Protocol):
    """Dimensionality reduction plugin interface."""
    def fit_transform(self, x: Any, **params: Any) -> Any:
        """Compute embedding. Returns ndarray (n_samples, n_components)."""
        ...
