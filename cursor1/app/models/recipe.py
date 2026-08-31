"""Recipe domain models."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class Ingredient(BaseModel):
    item: str
    quantity: str | None = None
    preparation: str | None = None
    notes: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


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
    ingredients: list[Ingredient] = Field(min_length=1)
    instructions: list[Instruction] = Field(min_length=1)
    notes: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    source_url: str
    source_creator: str | None = None

    @field_validator("title")
    @classmethod
    def title_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("title must be non-empty")
        return value.strip()

    @field_validator("instructions")
    @classmethod
    def instructions_sequential(cls, value: list[Instruction]) -> list[Instruction]:
        for index, instruction in enumerate(value, start=1):
            if instruction.step != index:
                raise ValueError("instruction steps must be sequential starting at 1")
        return value


class AisleCategory(str, Enum):
    deli = "deli"
    produce = "produce"
    meat = "meat"
    bread = "bread"
    cooking = "cooking"
    frozen = "frozen"
    snacks = "snacks"
    dairy = "dairy"
    other = "other"


class ShoppingListItem(BaseModel):
    item_id: str
    ingredient_name: str
    quantity: str | None = None
    aisle_category: AisleCategory = AisleCategory.other
    source_recipe_slugs: list[str] = Field(default_factory=list)
    checked: bool = False
