"""
Backward-compatible re-exports — implementation lives in plugins.
"""
from __future__ import annotations

from plugins.builtins.provenance_ml_plugin import (
    ProvenanceMLError,
    run_provenance_pipeline,
)
