"""Canonical, validated data models for a recipe.

These Pydantic models are the source of truth for the structured recipe
representation persisted as ``recipe.json``. Fields that may be uncertain or
inferred are optional so the extraction stage can preserve uncertainty rather
than inventing values.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

PIPELINE_VERSION = "0.1.0"


class Ingredient(BaseModel):
    item: str
    quantity: str | None = None
    preparation: str | None = None
    notes: str | None = None
    confidence: float | None = None


class Instruction(BaseModel):
    step: int
    text: str
    duration: str | None = None
    temperature: str | None = None


class Recipe(BaseModel):
    title: str
    description: str | None = None
    servings: str | None = None
    prep_time: str | None = None
    cook_time: str | None = None
    total_time: str | None = None
    ingredients: list[Ingredient] = Field(default_factory=list)
    instructions: list[Instruction] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    source_url: str
    source_creator: str | None = None


class RecipeMetadata(BaseModel):
    source_url: str
    creator: str | None = None
    title_original: str
    date_added: str
    pipeline_version: str = PIPELINE_VERSION
