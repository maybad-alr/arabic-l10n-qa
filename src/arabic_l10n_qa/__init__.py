"""arabic-l10n-qa: a small QA linter for Arabic localization files."""

from .checks import CheckOptions, Issue, Severity, check_entry, check_pair
from .fixes import fix_mapping, fix_tree, fix_value
from .formats import (
    UnsupportedFormatError,
    flatten,
    load_file,
    load_file_with_source,
    supported_extensions,
)
from .loader import load_any_file, load_json_file, load_pair_file
from .report import build_report, format_report

__all__ = [
    "CheckOptions",
    "Issue",
    "Severity",
    "UnsupportedFormatError",
    "build_report",
    "check_entry",
    "check_pair",
    "flatten",
    "fix_mapping",
    "fix_tree",
    "fix_value",
    "format_report",
    "load_any_file",
    "load_file",
    "load_file_with_source",
    "load_json_file",
    "load_pair_file",
    "supported_extensions",
]

__version__ = "0.1.0"
