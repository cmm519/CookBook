#!/usr/bin/env python3
"""Quick eval for cookbook-formatter Ollama model."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from app.models import Recipe

PROMPTS = [
    (
        "TEST 1 bolognese (user prompt)",
        "transcript: brown ground beef with onion and garlic, add crushed tomatoes and simmer 30 min. caption: weeknight bolognese serves 4",
    ),
    (
        "TEST 2 cookies (minimal)",
        "transcript: mix flour sugar and eggs bake at 350 for 25 minutes. caption: simple sugar cookies",
    ),
    (
        "TEST 3 shrimp",
        "transcript: saute garlic in olive oil add shrimp and lemon juice finish with parsley. caption: garlic lemon shrimp 2 servings",
    ),
]


def normalize_keys(data: dict) -> dict:
    for old, new in [
        ("prep-time", "prep_time"),
        ("cook-time", "cook_time"),
        ("total-time", "total_time"),
    ]:
        if old in data and new not in data:
            data[new] = data.pop(old)
    return data


def run_prompt(label: str, prompt: str, *, host: str = "http://localhost:11434", model: str = "cookbook-formatter") -> None:
    response = httpx.post(
        f"{host}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1},
        },
        timeout=180.0,
    )
    response.raise_for_status()
    raw = response.json().get("response", "")
    print(f"\n=== {label} ===")
    print(raw)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            print("VALIDATION FAILED: no JSON object in response")
            return
        data = json.loads(match.group(0))
    data = normalize_keys(data)
    try:
        recipe = Recipe.model_validate(data)
        print(
            f"OK — title={recipe.title!r} servings={recipe.servings!r} "
            f"ingredients={len(recipe.ingredients)} steps={len(recipe.instructions)}"
        )
    except Exception as exc:
        print(f"VALIDATION FAILED: {exc}")


def main() -> int:
    for label, prompt in PROMPTS:
        run_prompt(label, prompt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
