"""Safe, opt-in automatic fixes for Arabic localization strings.

Only transformations that cannot change meaning are applied, and protected
segments (URLs, e-mail addresses, placeholders, HTML tags) are never touched —
rewriting punctuation inside a URL query string would break it.

Supported fixes:

* ASCII ``,`` ``;`` ``?`` become the Arabic comma, semicolon and question mark
  inside Arabic prose (a comma between digits is left alone, so ``1,000``
  survives).
* Whitespace before Arabic punctuation is removed.
* Runs of two or more internal spaces collapse to one.

Anything more opinionated (rewording, diacritics, digit style) is deliberately
left to a human.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from .checks import ARABIC_RE, EMAIL_RE, PLACEHOLDER_RE, URL_RE

ARABIC_COMMA = "\u060C"
ARABIC_SEMICOLON = "\u061B"
ARABIC_QUESTION = "\u061F"

# Segments that must never be rewritten keep odd capture-group indexes after split.
_PROTECTED_RE = re.compile(
    "("
    + URL_RE.pattern
    + "|"
    + EMAIL_RE.pattern
    + "|"
    + PLACEHOLDER_RE.pattern
    + r"|<[^>]*>"
    + ")"
)

_SPACE_BEFORE_ARABIC_PUNCT_RE = re.compile(
    "[\u0009-\u000D \u00A0]+(["
    + ARABIC_COMMA
    + ARABIC_SEMICOLON
    + ARABIC_QUESTION
    + "])"
)
_COMMA_RE = re.compile(r"(?<!\d),(?!\d)")
_SEMICOLON_RE = re.compile(";")
_QUESTION_RE = re.compile(r"\?")
_MULTI_SPACE_RE = re.compile(r"(?<=\S) {2,}(?=\S)")


def _transform_unprotected(value: str, transform) -> str:
    """Apply ``transform`` to the parts of ``value`` that are not protected."""
    parts = _PROTECTED_RE.split(value)
    for index in range(0, len(parts), 2):
        parts[index] = transform(parts[index])
    return "".join(parts)


def fix_value(value: str) -> Tuple[str, List[str]]:
    """Return ``(fixed_value, applied_codes)`` for one string.

    Non-Arabic strings and non-strings are returned unchanged, so this is safe
    to run across an entire file.
    """
    if not isinstance(value, str) or not ARABIC_RE.search(value):
        return value, []

    applied: List[str] = []
    fixed = value

    def tighten(segment: str) -> str:
        return _SPACE_BEFORE_ARABIC_PUNCT_RE.sub(r"\1", segment)

    candidate = _transform_unprotected(fixed, tighten)
    if candidate != fixed:
        fixed = candidate
        applied.append("punctuation.space_before")

    def localize(segment: str) -> str:
        segment = _COMMA_RE.sub(ARABIC_COMMA, segment)
        segment = _SEMICOLON_RE.sub(ARABIC_SEMICOLON, segment)
        segment = _QUESTION_RE.sub(ARABIC_QUESTION, segment)
        return segment

    candidate = _transform_unprotected(fixed, localize)
    if candidate != fixed:
        fixed = candidate
        applied.append("punctuation.ascii")

    def collapse(segment: str) -> str:
        return _MULTI_SPACE_RE.sub(" ", segment)

    candidate = _transform_unprotected(fixed, collapse)
    if candidate != fixed:
        fixed = candidate
        applied.append("arabic.double_space")

    return fixed, applied


def fix_mapping(mapping: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, int]]:
    """Fix every string value in a flat mapping."""
    fixed: Dict[str, Any] = {}
    counts: Dict[str, int] = {}
    for key, value in mapping.items():
        if isinstance(value, str):
            new_value, applied = fix_value(value)
            fixed[key] = new_value
            for code in applied:
                counts[code] = counts.get(code, 0) + 1
        else:
            fixed[key] = value
    return fixed, counts


def fix_tree(node: Any) -> Tuple[Any, Dict[str, int]]:
    """Recursively fix strings inside a parsed JSON structure.

    Returns the new structure plus a per-code count of applied fixes, so the
    caller can report what changed.
    """
    counts: Dict[str, int] = {}

    def walk(value: Any) -> Any:
        if isinstance(value, str):
            new_value, applied = fix_value(value)
            for code in applied:
                counts[code] = counts.get(code, 0) + 1
            return new_value
        if isinstance(value, dict):
            return {key: walk(item) for key, item in value.items()}
        if isinstance(value, list):
            return [walk(item) for item in value]
        return value

    return walk(node), counts
