"""Provenance ML dialog mixin composition."""

from .build import ProvenanceMLBuildMixin
from .dialog import ProvenanceMLDialogBaseMixin
from .workflow import ProvenanceMLWorkflowMixin


class ProvenanceMLDialogMixin(
    ProvenanceMLDialogBaseMixin,
    ProvenanceMLBuildMixin,
    ProvenanceMLWorkflowMixin,
):
    """Unified provenance ML dialog mixin."""


__all__ = [
    'ProvenanceMLBuildMixin',
    'ProvenanceMLDialogBaseMixin',
    'ProvenanceMLWorkflowMixin',
    'ProvenanceMLDialogMixin',
]
