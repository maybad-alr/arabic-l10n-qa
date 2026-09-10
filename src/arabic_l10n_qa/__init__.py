"""arabic-l10n-qa: a small QA linter for Arabic localization files."""

from .checks import Issue, Severity, check_entry, check_pair
from .loader import flatten, load_json_file
from .report import build_report, format_report

__all__ = [
    "Issue",
    "Severity",
    "check_entry",
    "check_pair",
    "flatten",
    "load_json_file",
    "build_report",
    "format_report",
]

__version__ = "0.1.0"
