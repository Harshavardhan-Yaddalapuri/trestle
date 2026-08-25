"""Optional generic extraction strategies for event sources without an adapter."""

from backend.services.events.generic.pipeline import GenericEventPipeline

__all__ = ["GenericEventPipeline"]
