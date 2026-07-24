"""Load the vendored eeik onboarding question sets (drives the frontend wizard)."""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

import yaml

_QUESTIONS_DIR = Path(__file__).parent / "eeik_assets" / "questions"

# The order the wizard should present the question groups.
_ORDER = (
    "project-type",
    "domain",
    "backend",
    "frontend",
    "architecture",
    "cloud",
    "ai",
    "governance",
    "delivery",
    "modernization",
)


@functools.lru_cache(maxsize=1)
def load_questions() -> list[dict[str, Any]]:
    """Return the eeik question sets as an ordered list of question dicts."""
    by_id: dict[str, dict[str, Any]] = {}
    for path in _QUESTIONS_DIR.glob("*.yaml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            by_id[path.stem] = data
    ordered = [by_id[name] for name in _ORDER if name in by_id]
    ordered.extend(v for k, v in sorted(by_id.items()) if k not in _ORDER)
    return ordered
