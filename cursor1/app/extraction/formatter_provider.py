"""Formatter provider interface."""

from abc import ABC, abstractmethod

from app.models import ConsolidatedSourceInput, Recipe


class FormatterProvider(ABC):
    @abstractmethod
    def format_recipe(self, consolidated: ConsolidatedSourceInput) -> Recipe:
        """Produce structured Recipe JSON from consolidated evidence."""
