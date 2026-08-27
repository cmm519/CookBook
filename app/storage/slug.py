"""Deterministic, filesystem-safe slug generation from recipe titles."""

from __future__ import annotations

import re

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def slugify(title: str) -> str:
    """Return a stable, lowercase, hyphen-separated slug for ``title``.

    Falls back to ``"recipe"`` when the title contains no usable characters.
    """
    slug = _NON_ALNUM.sub("-", title.strip().lower()).strip("-")
    return slug or "recipe"
