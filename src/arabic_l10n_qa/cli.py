"""Command line interface for arabic-l10n-qa."""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional, Sequence

from .checks import CheckOptions, Severity
from .formats import UnsupportedFormatError, supported_extensions
from .loader import load_any_file, load_pair_file
from .report import build_report, counts_by_severity, format_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="arabic-l10n-qa",
        description=(
            "QA lint Arabic localization files (placeholders, HTML, bidi, punctuation). "
            "Supported formats: " + ", ".join(supported_extensions()) + "."
        ),
    )
    parser.add_argument("target", help="Path to the Arabic localization file to lint.")
    parser.add_argument(
        "-s",
        "--source",
        help="Optional source-language file to compare against (same format family).",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=("text", "json", "github"),
        default="text",
        help="Report format (default: text).",
    )
    parser.add_argument(
        "--min-severity",
        choices=("info", "warning", "error"),
        default="info",
        help="Only report issues at or above this severity.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when any warning or info issue is found.",
    )
    parser.add_argument(
        "--no-punctuation",
        action="store_true",
        help="Disable Arabic punctuation checks.",
    )
    parser.add_argument(
        "--no-bidi",
        action="store_true",
        help="Disable bidi control-character checks.",
    )
    parser.add_argument(
        "--no-mixed-spacing",
        action="store_true",
        help="Disable mixed Arabic/Latin spacing checks.",
    )
    parser.add_argument(
        "--ignore-untranslated",
        action="append",
        default=[],
        metavar="VALUE",
        help="Exact value that may legitimately stay untranslated. Repeatable.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        embedded_source, target = load_pair_file(args.target)
    except FileNotFoundError:
        print(f"error: file not found: {args.target}", file=sys.stderr)
        return 2
    except UnsupportedFormatError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - surface parse errors to the user
        print(f"error: could not parse {args.target}: {exc}", file=sys.stderr)
        return 2

    source = None
    if args.source:
        try:
            source = load_any_file(args.source)
        except UnsupportedFormatError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        except Exception as exc:  # noqa: BLE001
            print(f"error: could not parse {args.source}: {exc}", file=sys.stderr)
            return 2
    elif embedded_source:
        # gettext files carry the source language in the msgid.
        source = embedded_source

    options = CheckOptions(
        check_punctuation=not args.no_punctuation,
        check_bidi_controls=not args.no_bidi,
        check_mixed_script_spacing=not args.no_mixed_spacing,
        ignore_untranslated_values=tuple(args.ignore_untranslated),
    )

    issues = build_report(source, target, options)
    minimum = Severity.parse(args.min_severity)
    visible = [issue for issue in issues if issue.severity >= minimum]

    print(format_report(visible, fmt=args.format, target_name=args.target))

    summary = counts_by_severity(issues)
    if summary["error"]:
        return 1
    if args.strict and (summary["warning"] or summary["info"]):
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
