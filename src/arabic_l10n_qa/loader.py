"""Load and flatten localization files.

This module is the compatibility surface for the format parsers in
``formats``. New code should use :func:`load_any_file`, which dispatches on the
file extension instead of assuming JSON.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .formats import (
    PARSERS,
    UnsupportedFormatError,
    flatten,
    load_file,
    load_file_with_source,
    parse_json,
    supported_extensions,
)

__all__ = [
    "PARSERS",
    "UnsupportedFormatError",
    "flatten",
    "load_any_file",
    "load_file",
    "load_file_with_source",
    "load_json_file",
    "load_pair_file",
    "load_mapping",
    "supported_extensions",
]


def load_json_file(path: str | Path) -> Dict[str, Any]:
    """Load a JSON localization file into a flat dict."""
    text = Path(path).read_text(encoding="utf-8-sig")
    return parse_json(text)


def load_any_file(path: str | Path) -> Dict[str, Any]:
    """Load any supported localization file into a flat dict."""
    return load_file(path)


def load_pair_file(path: str | Path):
    """Load a file as ``(source, target)``, using embedded source when present."""
    return load_file_with_source(path)


def load_mapping(mapping: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in flatten(mapping)}
