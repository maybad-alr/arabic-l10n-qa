"""Parsers for the localization file formats arabic-l10n-qa understands.

Real localization pipelines rarely use a single format: gettext `.po` files show
up in Linux/desktop apps, `.strings` in iOS projects, `.properties` in Java
stacks, CSV in spreadsheets handed over by translation vendors, and YAML in
modern web apps. Supporting them is what makes the checks broadly usable.

JSON and CSV parsing use the standard library. YAML requires the optional
``PyYAML`` dependency and fails with a clear message when it is missing.
"""

from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterator, List, Tuple


class UnsupportedFormatError(ValueError):
    """Raised when no parser is registered for a file extension."""


def flatten(data: Any, prefix: str = "") -> Iterator[Tuple[str, Any]]:
    """Yield ``(dotted.key, value)`` pairs from a nested structure.

    Lists are flattened by index, e.g. ``items.0.title``.
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


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        return value[1:-1]
    return value


def _unescape(value: str) -> str:
    return (
        value.replace("\\n", "\n")
        .replace("\\t", "\t")
        .replace("\\r", "\r")
        .replace('\\"', '"')
        .replace("\\\\", "\\")
    )


# --------------------------------------------------------------------------
# JSON
# --------------------------------------------------------------------------


def parse_json(text: str) -> Dict[str, Any]:
    data = json.loads(text)
    return {key: value for key, value in flatten(data)}


# --------------------------------------------------------------------------
# gettext .po / .pot
# --------------------------------------------------------------------------

_PO_MSGID_RE = re.compile(r"^msgid\s+(.*)$")
_PO_MSGSTR_RE = re.compile(r"^msgstr(?:\[\d+\])?\s+(.*)$")


def _parse_po_entries(text: str) -> List[Tuple[str, str]]:
    """Return ``(msgid, msgstr)`` pairs from a PO file, in file order.

    Comments, contexts and plural forms are skipped; the singular ``msgstr``
    wins. Multi-line strings joined from adjacent quoted fragments are handled.
    The file header (empty msgid) is omitted.
    """
    entries: List[Tuple[str, str]] = []
    msgid: Any = None
    msgstr: Any = None
    pending: Any = None

    def flush() -> None:
        nonlocal msgid, msgstr, pending
        if isinstance(msgid, str) and isinstance(msgstr, str) and msgid != "":
            entries.append((msgid, msgstr))
        msgid = None
        msgstr = None
        pending = None

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("msgctxt") or line.startswith("msgid_plural"):
            continue

        match = _PO_MSGID_RE.match(line)
        if match:
            flush()
            msgid = _unescape(_strip_quotes(match.group(1)))
            pending = "id"
            continue

        match = _PO_MSGSTR_RE.match(line)
        if match:
            msgstr = _unescape(_strip_quotes(match.group(1)))
            pending = "str"
            continue

        if line.startswith('"'):
            fragment = _unescape(_strip_quotes(line))
            if pending == "id" and isinstance(msgid, str):
                msgid += fragment
            elif pending == "str" and isinstance(msgstr, str):
                msgstr += fragment

    flush()
    return entries


def parse_po(text: str) -> Dict[str, str]:
    """Parse gettext PO entries into ``{msgid: msgstr}``."""
    return {msgid: msgstr for msgid, msgstr in _parse_po_entries(text)}


def parse_po_pairs(text: str) -> Dict[str, Tuple[str, str]]:
    """Parse PO entries into ``{msgid: (msgid, msgstr)}``.

    A PO file already carries its source language in the ``msgid``, so the
    source strings can be checked without a second file.
    """
    return {msgid: (msgid, msgstr) for msgid, msgstr in _parse_po_entries(text)}


# --------------------------------------------------------------------------
# Java .properties
# --------------------------------------------------------------------------


def parse_properties(text: str) -> Dict[str, str]:
    entries: Dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("!"):
            continue
        for separator in ("=", ":"):
            if separator in line:
                key, value = line.split(separator, 1)
                entries[key.strip()] = value.strip()
                break
        else:
            entries[line] = ""
    return entries


# --------------------------------------------------------------------------
# iOS / macOS .strings
# --------------------------------------------------------------------------

_STRINGS_RE = re.compile(
    r'^\s*"((?:[^"\\]|\\.)*)"\s*=\s*"((?:[^"\\]|\\.)*)"\s*;',
    re.MULTILINE,
)


def parse_strings(text: str) -> Dict[str, str]:
    return {
        _unescape(key): _unescape(value) for key, value in _STRINGS_RE.findall(text)
    }


# --------------------------------------------------------------------------
# CSV / TSV
# --------------------------------------------------------------------------


def parse_csv(text: str, delimiter: str = ",") -> Dict[str, str]:
    entries: Dict[str, str] = {}
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    for index, row in enumerate(reader):
        if not row:
            continue
        key = row[0].strip()
        value = row[1] if len(row) > 1 else ""
        if index == 0 and key.lower() in {"key", "id", "msgid", "string"}:
            continue
        entries[key] = value
    return entries


def parse_tsv(text: str) -> Dict[str, str]:
    return parse_csv(text, delimiter="\t")


# --------------------------------------------------------------------------
# YAML (optional dependency)
# --------------------------------------------------------------------------


def parse_yaml(text: str) -> Dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise UnsupportedFormatError(
            "YAML support requires PyYAML. Install it with: pip install PyYAML"
        ) from exc
    data = yaml.safe_load(text)
    if data is None:
        return {}
    return {key: value for key, value in flatten(data)}


PARSERS = {
    ".json": parse_json,
    ".jsonc": parse_json,
    ".po": parse_po,
    ".pot": parse_po,
    ".properties": parse_properties,
    ".strings": parse_strings,
    ".stringsdict": parse_strings,
    ".csv": parse_csv,
    ".tsv": parse_tsv,
    ".yaml": parse_yaml,
    ".yml": parse_yaml,
}

# Formats that carry the source language alongside the translation.
EMBEDDED_SOURCE_EXTENSIONS = {".po", ".pot"}


def supported_extensions() -> List[str]:
    return sorted(PARSERS)


def load_file(path: str | Path) -> Dict[str, Any]:
    """Load any supported localization file into a flat ``{key: value}`` dict."""
    file_path = Path(path)
    extension = file_path.suffix.lower()
    parser = PARSERS.get(extension)
    if parser is None:
        raise UnsupportedFormatError(
            f"unsupported file type {extension!r} for {file_path.name}. "
            f"Supported: {', '.join(supported_extensions())}"
        )
    text = file_path.read_text(encoding="utf-8-sig")
    return parser(text)


def load_file_with_source(path: str | Path) -> Tuple[Any, Dict[str, Any]]:
    """Load a file, returning ``(source, target)`` flat dicts.

    For formats that embed the source language (gettext ``.po``/``.pot``) the
    ``msgid`` becomes the source map, so a single Arabic file can be validated
    against its own originals. For all other formats ``source`` is ``None``.
    """
    file_path = Path(path)
    extension = file_path.suffix.lower()
    if extension in EMBEDDED_SOURCE_EXTENSIONS:
        text = file_path.read_text(encoding="utf-8-sig")
        pairs = parse_po_pairs(text)
        source = {key: msgid for key, (msgid, _) in pairs.items()}
        target = {key: msgstr for key, (_, msgstr) in pairs.items()}
        return source, target
    return None, load_file(file_path)
