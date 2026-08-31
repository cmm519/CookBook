"""Ollama HTTP formatter."""

from __future__ import annotations

import json
import re

import httpx
from pydantic import ValidationError

from app.extraction.consolidate import consolidated_to_prompt_dict
from app.extraction.formatter_provider import FormatterProvider
from app.models import ConsolidatedSourceInput, Ingredient, Instruction, Recipe


SYSTEM_PROMPT = (
    "You are a specialized recipe extractor. Convert transcript and metadata evidence "
    "into structured JSON matching this schema: "
    '{"title": str, "description": str|null, "servings": str|null, '
    '"ingredients": [{"item": str, "quantity": str|null, "preparation": str|null, '
    '"notes": str|null, "confidence": float|null}], '
    '"instructions": [{"step": int, "text": str}], '
    '"notes": [str], "tags": [str], "source_url": str, "source_creator": str|null}. '
    "Return ONLY valid JSON. Never invent quantities when unknown — omit or use null."
)


def extract_json_object(text: str) -> dict:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError("No JSON object found in formatter response") from None
        return json.loads(match.group(0))


class OllamaFormatterProvider(FormatterProvider):
    def __init__(self, host: str, model: str, *, timeout: float = 120.0) -> None:
        self.host = host.rstrip("/")
        self.model = model
        self.timeout = timeout

    def format_recipe(self, consolidated: ConsolidatedSourceInput) -> Recipe:
        payload = consolidated_to_prompt_dict(consolidated)
        user_content = json.dumps(payload, indent=2)
        response = httpx.post(
            f"{self.host}/api/generate",
            json={
                "model": self.model,
                "prompt": f"{SYSTEM_PROMPT}\n\nEvidence:\n{user_content}",
                "stream": False,
                "format": "json",
                "options": {"temperature": 0.1},
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        body = response.json()
        raw = body.get("response", "")
        data = extract_json_object(raw)
        data.setdefault("source_url", consolidated.source_url)
        if consolidated.metadata and consolidated.metadata.author_username:
            data.setdefault("source_creator", consolidated.metadata.author_username)
        return Recipe.model_validate(data)


class MockFormatterProvider(FormatterProvider):
    def format_recipe(self, consolidated: ConsolidatedSourceInput) -> Recipe:
        title = "Imported Recipe"
        if consolidated.metadata and consolidated.metadata.title:
            title = consolidated.metadata.title
        return Recipe(
            title=title,
            description=consolidated.raw_transcript[:200] or None,
            ingredients=[Ingredient(item="see transcript", quantity=None, confidence=0.5)],
            instructions=[Instruction(step=1, text=consolidated.raw_transcript or "No steps found.")],
            source_url=consolidated.source_url,
            source_creator=consolidated.metadata.author_username if consolidated.metadata else None,
        )


def safe_format(provider: FormatterProvider, consolidated: ConsolidatedSourceInput) -> Recipe:
    try:
        return provider.format_recipe(consolidated)
    except (ValidationError, ValueError, httpx.HTTPError) as exc:
        if isinstance(provider, MockFormatterProvider):
            raise
        fallback = MockFormatterProvider()
        recipe = fallback.format_recipe(consolidated)
        recipe.notes.append(f"Formatter fallback used: {exc}")
        return recipe
