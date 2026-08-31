"""HEB-ordered shopping list."""

from __future__ import annotations

import uuid

from app.models import AisleCategory, Recipe, ShoppingListItem
from app.storage import PackageStorage

AISLE_ORDER = [
    AisleCategory.produce,
    AisleCategory.meat,
    AisleCategory.deli,
    AisleCategory.bread,
    AisleCategory.dairy,
    AisleCategory.frozen,
    AisleCategory.cooking,
    AisleCategory.snacks,
    AisleCategory.other,
]

AISLE_KEYWORDS: dict[AisleCategory, tuple[str, ...]] = {
    AisleCategory.produce: ("onion", "garlic", "tomato", "lettuce", "pepper", "herb", "lemon"),
    AisleCategory.meat: ("chicken", "beef", "pork", "sausage", "bacon", "fish", "shrimp"),
    AisleCategory.deli: ("ham", "turkey", "salami", "cheese slice"),
    AisleCategory.bread: ("bread", "bun", "tortilla", "roll"),
    AisleCategory.dairy: ("milk", "butter", "cream", "yogurt", "cheese"),
    AisleCategory.frozen: ("frozen", "ice cream"),
    AisleCategory.cooking: ("oil", "flour", "sugar", "salt", "pepper", "soy", "vinegar", "spice"),
    AisleCategory.snacks: ("chip", "cracker", "nut"),
}


def classify_aisle(ingredient_name: str) -> AisleCategory:
    lower = ingredient_name.lower()
    for aisle, keywords in AISLE_KEYWORDS.items():
        if any(keyword in lower for keyword in keywords):
            return aisle
    return AisleCategory.other


def build_shopping_list(storage: PackageStorage, slugs: list[str]) -> list[ShoppingListItem]:
    merged: dict[str, ShoppingListItem] = {}
    for slug in slugs:
        recipe = storage.read_recipe(slug)
        for ingredient in recipe.ingredients:
            key = ingredient.item.strip().lower()
            if not key:
                continue
            if key in merged:
                item = merged[key]
                if ingredient.quantity and item.quantity and item.quantity != ingredient.quantity:
                    item.quantity = f"{item.quantity} + {ingredient.quantity}"
                elif ingredient.quantity and not item.quantity:
                    item.quantity = ingredient.quantity
                if slug not in item.source_recipe_slugs:
                    item.source_recipe_slugs.append(slug)
            else:
                merged[key] = ShoppingListItem(
                    item_id=f"item-{uuid.uuid4().hex[:8]}",
                    ingredient_name=ingredient.item,
                    quantity=ingredient.quantity,
                    aisle_category=classify_aisle(ingredient.item),
                    source_recipe_slugs=[slug],
                )

    items = list(merged.values())
    items.sort(key=lambda i: (AISLE_ORDER.index(i.aisle_category), i.ingredient_name.lower()))
    return items
