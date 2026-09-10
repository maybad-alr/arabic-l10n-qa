"""Individual QA checks for Arabic localization strings.

Every check is intentionally dependency-free and returns plain data, so the
same rules can be reused from a CLI, a CI job, or an editor extension.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, Iterable, List, Optional, Sequence


class Severity(IntEnum):
    INFO = 10
    WARNING = 20
    ERROR = 30

    @classmethod
    def parse(cls, value: str) -> "Severity":
        value = (value or "").strip().lower()
        for member in cls:
            if member.name.lower() == value:
                return member
        raise ValueError(f"unknown severity: {value!r}")

    @property
    def label(self) -> str:
        return self.name.lower()


@dataclass(frozen=True)
class Issue:
    key: str
    code: str
    severity: Severity
    message: str

    def as_dict(self) -> Dict[str, str]:
        return {
            "key": self.key,
            "code": self.code,
            "severity": self.severity.label,
            "message": self.message,
        }


@dataclass
class CheckOptions:
    """Toggles for the optional, more opinionated checks."""

    check_punctuation: bool = True
    check_bidi_controls: bool = True
    check_mixed_script_spacing: bool = True
    check_tatweel: bool = True
    check_ellipsis: bool = True
    check_digits: bool = True
    check_punctuation_spacing: bool = True
    check_brackets: bool = True
    check_joiners: bool = True
    check_repeated_words: bool = True
    check_double_space: bool = True
    # Values that are identical in source and target but are legitimately
    # untranslated (brand names, code, symbols).
    ignore_untranslated_values: Sequence[str] = field(default_factory=tuple)


ARABIC_RANGES = (
    "\u0600-\u06FF"  # Arabic
    "\u0750-\u077F"  # Arabic Supplement
    "\u08A0-\u08FF"  # Arabic Extended-A
    "\uFB50-\uFDFF"  # Arabic Presentation Forms-A
    "\uFE70-\uFEFF"  # Arabic Presentation Forms-B
)

ARABIC_RE = re.compile(f"[{ARABIC_RANGES}]")

# {name}, {{name}}, {0}, %s, %d, %1$s, $PLURAL$, %(name)s
PLACEHOLDER_RE = re.compile(
    r"\{\{?[A-Za-z0-9_.\-]+\}?\}"
    r"|%\d+\$[sdif@]"
    r"|%\([A-Za-z0-9_]+\)[sdif]"
    r"|%[sdif@]"
    r"|\$[A-Za-z0-9_]+\$"
)
TAG_RE = re.compile(r"</?([A-Za-z][\w:\-]*)")
URL_RE = re.compile(r"https?://[^\s<>\"']+|www\.[^\s<>\"']+")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")

TATWEEL = "\u0640"
ASCII_ELLIPSIS = "..."

BIDI_CONTROL_CHARS = {
    "\u202A": "LRE",
    "\u202B": "RLE",
    "\u202C": "PDF",
    "\u202D": "LRO",
    "\u202E": "RLO",
    "\u2066": "LRI",
    "\u2067": "RLI",
    "\u2068": "FSI",
    "\u2069": "PDI",
    "\u200E": "LRM",
    "\u200F": "RLM",
}

# Punctuation that is usually wrong inside Arabic prose.
# char -> (name, codepoint, detection pattern). A comma between digits ("1,000")
# is a thousands separator rather than punctuation, so it is not matched.
WRONG_PUNCTUATION = {
    ",": ("Arabic comma", "U+060C", re.compile(r"(?<!\d),(?!\d)")),
    ";": ("Arabic semicolon", "U+061B", re.compile(";")),
    "?": ("Arabic question mark", "U+061F", re.compile(r"\?")),
}

# Arabic punctuation binds to the preceding word, unlike its ASCII counterparts.
ARABIC_PUNCTUATION_CHARS = "\u060C\u061B\u061F"

# Arabic-Indic (٠-٩) versus Western (0-9) digits. Mixing both styles in one
# string is almost always an accident rather than a deliberate choice.
ARABIC_INDIC_DIGITS = "\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669"
ASCII_DIGITS = "0123456789"

# Zero-width joiners leak in from copy-pasted text and break search/matching.
JOINER_CHARS = {
    "\u200D": "ZWJ",
    "\u200C": "ZWNJ",
}

BRACKET_PAIRS = (
    ("(", ")"),
    ("[", "]"),
    ("{", "}"),
    ("\u00AB", "\u00BB"),  # guillemets, common in Arabic typography
)

WORD_SPLIT_RE = re.compile(
    "[\u0009-\u000D \u00A0\u060C\u061B\u061F.!?\u060D\u2010-\u2015\u2026]+"
)


def _strip_context(value: str) -> str:
    """Remove placeholders/tags/links so prose checks do not fire on them."""
    value = URL_RE.sub(" ", value)
    value = EMAIL_RE.sub(" ", value)
    value = PLACEHOLDER_RE.sub(" ", value)
    value = re.sub(r"<[^>]*>", " ", value)
    value = re.sub(r"&[a-zA-Z]+;|&#\d+;", " ", value)
    return value


def _multiplicity(items: Iterable[str]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for item in items:
        counts[item] = counts.get(item, 0) + 1
    return counts


def _has_arabic(value: str) -> bool:
    return bool(ARABIC_RE.search(value))


def check_pair(
    key: str,
    source: Optional[str],
    target: Optional[str],
    options: Optional[CheckOptions] = None,
) -> List[Issue]:
    """Check one source/target string pair.

    ``source`` may be ``None`` when only the Arabic file is available; in that
    case cross-language checks are skipped and only Arabic prose checks run.
    """

    options = options or CheckOptions()
    issues: List[Issue] = []

    def add(code: str, severity: Severity, message: str) -> None:
        issues.append(Issue(key=key, code=code, severity=severity, message=message))

    if target is None:
        add("missing.translation", Severity.ERROR, "target string is missing")
        return issues

    if not isinstance(target, str):
        add("type.invalid", Severity.ERROR, f"target is not a string (got {type(target).__name__})")
        return issues

    if target.strip() == "":
        add("empty.translation", Severity.ERROR, "target string is empty")
        return issues

    if source is not None and source != "":
        if target == source:
            ignored = target in set(options.ignore_untranslated_values)
            if not ignored:
                add("untranslated.identical", Severity.WARNING, "target is identical to source")

        # Placeholders -----------------------------------------------------
        src_ph = _multiplicity(PLACEHOLDER_RE.findall(source))
        tgt_ph = _multiplicity(PLACEHOLDER_RE.findall(target))
        if src_ph != tgt_ph:
            add(
                "placeholder.mismatch",
                Severity.ERROR,
                f"placeholders differ: source={sorted(src_ph.items())} target={sorted(tgt_ph.items())}",
            )

        # HTML tags --------------------------------------------------------
        src_tags = _multiplicity(TAG_RE.findall(source))
        tgt_tags = _multiplicity(TAG_RE.findall(target))
        if src_tags != tgt_tags:
            add(
                "html.mismatch",
                Severity.ERROR,
                f"html tags differ: source={sorted(src_tags.items())} target={sorted(tgt_tags.items())}",
            )

        # URLs and e-mails -------------------------------------------------
        if sorted(URL_RE.findall(source)) != sorted(URL_RE.findall(target)):
            add("url.mismatch", Severity.ERROR, "URLs differ between source and target")
        if sorted(EMAIL_RE.findall(source)) != sorted(EMAIL_RE.findall(target)):
            add("email.mismatch", Severity.ERROR, "e-mail addresses differ between source and target")

        # Leading/trailing whitespace -------------------------------------
        if source[:1].isspace() != target[:1].isspace() or source[-1:].isspace() != target[-1:].isspace():
            add(
                "whitespace.edge",
                Severity.WARNING,
                "leading/trailing whitespace differs from source",
            )

        # Digits (Arabic-Indic vs ASCII) ----------------------------------
        if re.search(r"\d", source) and _has_arabic(target):
            if not re.search(r"\d", target):
                add("digits.missing", Severity.WARNING, "source contains digits but target does not")

    # Arabic prose checks --------------------------------------------------
    if _has_arabic(target):
        if options.check_mixed_script_spacing:
            if re.search(f"[{ARABIC_RANGES}][A-Za-z]", target) or re.search(f"[A-Za-z][{ARABIC_RANGES}]", target):
                add(
                    "script.mixed_spacing",
                    Severity.WARNING,
                    "Arabic and Latin text are adjacent without a space",
                )

        if options.check_punctuation:
            prose = _strip_context(target)
            for wrong, (name, codepoint, pattern) in WRONG_PUNCTUATION.items():
                if pattern.search(prose):
                    add(
                        "punctuation.ascii",
                        Severity.WARNING,
                        f"ASCII {wrong!r} found in Arabic text; prefer the {name} ({codepoint})",
                    )

        if options.check_punctuation_spacing:
            prose = _strip_context(target)
            if re.search(r"\s+[" + ARABIC_PUNCTUATION_CHARS + r"]", prose):
                add(
                    "punctuation.space_before",
                    Severity.WARNING,
                    "space before Arabic punctuation; it should bind to the preceding word",
                )
            if re.search(
                "[" + ARABIC_PUNCTUATION_CHARS + "](?=[A-Za-z" + ARABIC_RANGES + "])",
                prose,
            ):
                add(
                    "punctuation.missing_space_after",
                    Severity.WARNING,
                    "missing space after Arabic punctuation",
                )

        if options.check_digits:
            prose = _strip_context(target)
            uses_arabic_indic = any(char in prose for char in ARABIC_INDIC_DIGITS)
            uses_western = any(char in prose for char in ASCII_DIGITS)
            if uses_arabic_indic and uses_western:
                add(
                    "digits.mixed_style",
                    Severity.WARNING,
                    "Arabic-Indic and Western digits are mixed in one string",
                )

        if options.check_brackets:
            prose = _strip_context(target)
            for opening, closing in BRACKET_PAIRS:
                opened = prose.count(opening)
                closed = prose.count(closing)
                if opened != closed:
                    add(
                        "brackets.unbalanced",
                        Severity.WARNING,
                        f"unbalanced brackets: {opened}x {opening!r} vs {closed}x {closing!r}",
                    )

        if options.check_joiners:
            found = sorted({name for char, name in JOINER_CHARS.items() if char in target})
            if found:
                add(
                    "arabic.joiner_chars",
                    Severity.WARNING,
                    f"invisible joiner characters present: {', '.join(found)}",
                )

        if options.check_repeated_words:
            words = [word for word in WORD_SPLIT_RE.split(_strip_context(target)) if word]
            for first, second in zip(words, words[1:]):
                if (
                    first == second
                    and len(first) >= 2
                    and re.fullmatch("[" + ARABIC_RANGES + "]+", first)
                ):
                    add(
                        "arabic.repeated_word",
                        Severity.WARNING,
                        f"word repeated twice in a row: {first!r}",
                    )
                    break

        if options.check_double_space and re.search(r"\S {2,}\S", target):
            add(
                "arabic.double_space",
                Severity.INFO,
                "multiple consecutive spaces inside the string",
            )

        if options.check_bidi_controls:
            found = sorted({name for char, name in BIDI_CONTROL_CHARS.items() if char in target})
            if found:
                add(
                    "bidi.control_chars",
                    Severity.WARNING,
                    f"embedded bidi control characters present: {', '.join(found)}",
                )

        if options.check_tatweel and target.count(TATWEEL) >= 2:
            add("arabic.tatweel", Severity.INFO, "repeated tatweel (kashida) characters found")

        if options.check_ellipsis and ASCII_ELLIPSIS in target:
            add("typography.ellipsis", Severity.INFO, "ASCII '...' found; prefer the ellipsis character")

    return issues


def check_entry(key: str, value: object, options: Optional[CheckOptions] = None) -> List[Issue]:
    """Check a single Arabic string without an English source."""
    if isinstance(value, str):
        return check_pair(key, None, value, options)
    return [Issue(key=key, code="type.invalid", severity=Severity.ERROR, message="value is not a string")]
