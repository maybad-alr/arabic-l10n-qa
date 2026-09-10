"""Load and flatten localization files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterator, Tuple


def flatten(data: Any, prefix: str = "") -> Iterator[Tuple[str, Any]]:
    """Yield ``(dotted.key, value)`` pairs from a nested dict.

    Lists are flattened by index, e.g. ``items.0.title``. Non-dict scalars are
    yielded as-is.
    """
    if isinstance(data, dict):
        for key, value in data.items():
            child = f"{prefix}.{key}" if prefix else str(key)
            yield from flatten(value, child)
    elif isinstance(data, list):
        for index, value in enumerate(data):
            child = f"{prefix}.{index}" if prefix else str(index)
            yield from flatten(value, child)
    else:
        yield prefix, data


def load_json_file(path: str | Path) -> Dict[str, Any]:
    """Load a JSON (or JSONC-ish) localization file into a flat dict."""
    text = Path(path).read_text(encoding="utf-8-sig")
    data = json.loads(text)
    return {key: value for key, value in flatten(data)}


def load_mapping(mapping: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in flatten(mapping)}
